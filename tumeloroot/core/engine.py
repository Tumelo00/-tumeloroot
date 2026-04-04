"""Root Engine - main orchestrator that coordinates all rooting steps."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, Optional

from tumeloroot.core.adb_bridge import AdbBridge
from tumeloroot.core.backup_manager import BackupManager
from tumeloroot.core.device_profile import DeviceProfile
from tumeloroot.core.magisk_patcher import MagiskPatcher
from tumeloroot.core.mtk_bridge import MtkBridge
from tumeloroot.core.prerequisite_checker import PrerequisiteChecker
from tumeloroot.core.vbmeta_patcher import patch_vbmeta, verify_patch
from tumeloroot.core.platform_utils import get_default_backup_dir

logger = logging.getLogger(__name__)

LogCallback = Callable[[str, str], None]


class RootEngine:
    """Main orchestrator for all rooting steps."""

    def __init__(
        self,
        device_profile: DeviceProfile,
        progress_callback=None,
        log_callback: Optional[LogCallback] = None,
    ):
        self.profile = device_profile
        self._progress_cb = progress_callback
        self._log_cb = log_callback

        errors = device_profile.validate()
        if errors:
            for err in errors:
                logger.warning(f"Profile issue: {err}")

        self._backup_dir: Optional[str] = None
        self._stock_image_path: Optional[str] = None
        self._patched_image_path: Optional[str] = None

        self._mtk = MtkBridge(log_callback=log_callback)
        self._adb = AdbBridge()
        self._checker = PrerequisiteChecker()

    def _log(self, msg: str, level: str = "INFO") -> None:
        logger.log(getattr(logging, level, logging.INFO), msg)
        if self._log_cb:
            self._log_cb(msg, level)

    def run_step(self, step_name: str, **kwargs) -> bool:
        self._log(f"Starting step: {step_name}")
        handlers = {
            "prerequisites": self._run_prerequisites,
            "connect": self._run_connect,
            "backup": self._run_backup,
            "unlock": self._run_unlock,
            "read_stock": self._run_read_stock,
            "patch_magisk": self._run_patch_magisk,
            "flash": self._run_flash,
            "root_all": self._run_root_all,
            "unlock_and_root": self._run_unlock_and_root,
            "verify": self._run_verify,
        }
        handler = handlers.get(step_name)
        if not handler:
            self._log(f"Unknown step: {step_name}", "ERROR")
            return False
        try:
            return handler(**kwargs)
        except Exception as e:
            self._log(f"Step {step_name} error: {e}", "ERROR")
            return False

    def _run_prerequisites(self) -> bool:
        results = self._checker.check_all()
        all_ok = True
        for r in results:
            status = "OK" if r.available else "MISSING"
            self._log(f"  {r.name}: {status} ({r.version})")
            if r.required and not r.available:
                all_ok = False
        return all_ok

    def _run_connect(self) -> bool:
        """Test connection by reading GPT."""
        self._log("Testing BROM connection...")
        ok, output = self._mtk.print_gpt()
        return ok

    def _run_backup(self) -> bool:
        backup_dir = get_default_backup_dir()
        mgr = BackupManager(backup_dir, self._mtk)
        partitions = self.profile.partitions.backup_list
        self._log(f"Backing up {len(partitions)} partitions...")
        result = mgr.create_backup(
            partitions,
            progress_callback=lambda name, i, t: self._log(f"  [{i+1}/{t}] Backing up {name}")
        )
        if result:
            self._backup_dir = result
            self._log(f"Backup saved to: {result}", "SUCCESS")
            return True
        return False

    def _run_unlock(self, clear_frp: bool = False) -> bool:
        """Unlock bootloader — runs mtkclient in CMD window."""
        return self._mtk.unlock_bootloader(clear_frp=clear_frp)

    # ── Root: Read stock + Magisk patch + Flash ────────────────

    def _run_read_stock(self) -> bool:
        """Read vendor_boot from device via BROM.

        Opens a CMD window, connects BROM, reads the partition, saves to PC.
        This guarantees we have the EXACT image currently on the device.
        """
        target = self.profile.partitions.root_target  # "vendor_boot"
        slot = f"{target}_a"                          # "vendor_boot_a"

        self._log(f"=== READ {slot} FROM DEVICE ===", "INFO")

        # Save to temp dir so it works regardless of backup state
        output_path = os.path.join(
            tempfile.gettempdir(), f"tumeloroot_stock_{slot}.img"
        )

        # Clean old file if exists
        if os.path.isfile(output_path):
            os.remove(output_path)

        ok = self._mtk.read_stock_image(slot, output_path)
        if ok and os.path.isfile(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            self._stock_image_path = output_path
            self._log(f"Stock {slot}: {size_mb:.1f} MB saved to {output_path}", "SUCCESS")
            return True

        self._log(f"Failed to read {slot} from device!", "ERROR")
        return False

    def _run_patch_magisk(self) -> bool:
        """Patch vendor_boot with Magisk via ADB.

        Flow:
          1. Wait for device on ADB (user boots to Android)
          2. Use the stock image read from device in previous step
          3. Install Magisk APK on device
          4. Push vendor_boot, patch with Magisk, pull back patched image
        """
        self._log("=== MAGISK PATCH ===", "INFO")

        # Use stock image from read_stock step
        if not self._stock_image_path or not os.path.isfile(self._stock_image_path):
            self._log("Stock image not found! Run 'Read from device' step first.", "ERROR")
            return False

        size_mb = os.path.getsize(self._stock_image_path) / (1024 * 1024)
        self._log(f"Stock image: {self._stock_image_path} ({size_mb:.1f} MB)")

        # Wait for ADB device
        self._log("Waiting for device on ADB...", "WARNING")
        self._log("Boot your device to Android, connect USB, allow USB debugging.", "WARNING")

        if not self._adb.wait_for_device(timeout=300):
            self._log("Device not found on ADB after 5 minutes!", "ERROR")
            self._log("Make sure device is booted, USB connected, debugging enabled.", "ERROR")
            return False

        self._log("Device found on ADB!", "SUCCESS")

        # Output path for patched image (next to stock)
        out_dir = os.path.dirname(self._stock_image_path)
        patched_path = os.path.join(out_dir, "tumeloroot_magisk_patched.img")

        # Patch via Magisk
        patcher = MagiskPatcher(self._adb)
        success = patcher.patch_image_via_adb(
            self._stock_image_path,
            patched_path,
            log_callback=lambda msg: self._log(msg),
        )

        if success and os.path.isfile(patched_path):
            patched_mb = os.path.getsize(patched_path) / (1024 * 1024)
            self._patched_image_path = patched_path
            self._log(f"Patched image: {patched_path} ({patched_mb:.1f} MB)", "SUCCESS")
            self._log("=== MAGISK PATCH COMPLETE ===", "SUCCESS")
            return True

        self._log("Magisk patching failed!", "ERROR")
        return False

    def _run_flash(self) -> bool:
        """Flash patched vendor_boot + disable vbmeta via BROM.

        Single BROM connection:
          1. Flash patched vendor_boot to both A/B slots
          2. Patch all vbmeta partitions (flags=3)
        """
        if not self._patched_image_path or not os.path.isfile(self._patched_image_path):
            self._log("No patched image found! Run Magisk patch first.", "ERROR")
            return False

        self._log("=== FLASH + VBMETA ===", "INFO")
        flash_targets = self.profile.partitions.flash_targets
        vbmeta_parts = self.profile.vbmeta.partitions
        self._log(f"Flash targets: {', '.join(flash_targets)}")
        self._log(f"Vbmeta targets: {', '.join(vbmeta_parts)}")

        return self._mtk.flash_root(
            self._patched_image_path,
            flash_targets,
            vbmeta_parts,
        )

    # ── Root ALL-IN-ONE: single BROM session ──────────────────

    def _run_root_all(self) -> bool:
        """Single BROM session: read vendor_boot, Magisk patch on PC, flash back.

        Flow:
          1. BROM script reads vendor_boot_a from device
          2. PC patches with Magisk (boot_patcher.py - pure Python)
          3. BROM script flashes patched image to both A/B slots
          4. BROM script verifies vbmeta flags=3
        """
        self._log("=== ROOT ALL-IN-ONE ===", "INFO")

        target = self.profile.partitions.root_target  # "vendor_boot"
        slot = f"{target}_a"
        flash_targets = self.profile.partitions.flash_targets
        vbmeta_parts = self.profile.vbmeta.partitions

        # Find Magisk APK
        magisk_apk = self._find_magisk_apk()
        if not magisk_apk:
            self._log("Magisk APK not found!", "ERROR")
            self._log("Please download Magisk APK to Downloads folder.", "ERROR")
            return False
        self._log(f"Magisk APK: {magisk_apk}", "INFO")

        def _patch_callback(stock_path: str, patched_path: str) -> bool:
            """Called by mtk_bridge when stock image is ready."""
            from tumeloroot.core.boot_patcher import patch_boot_image
            self._log("Starting PC-side Magisk patch...", "INFO")
            return patch_boot_image(
                image_path=stock_path,
                output_path=patched_path,
                magisk_apk=magisk_apk,
                log_cb=lambda msg: self._log(msg),
            )

        return self._mtk.root_and_flash(
            partition=slot,
            flash_targets=flash_targets,
            vbmeta_parts=vbmeta_parts,
            patch_callback=_patch_callback,
        )

    # ── Unlock + Root ALL-IN-ONE: single BROM session ─────────

    def _run_unlock_and_root(self, clear_frp: bool = False) -> bool:
        """Single BROM session: backup + unlock + root - EVERYTHING.

        Flow (one BROM connection):
          0. Backup critical partitions
          1. seccfg unlock (bootloader)
          2. vbmeta flags=3 (disable dm-verity)
          3. FRP clear (optional)
          4. Read vendor_boot_a from device
          5. PC patches with Magisk (magiskboot via WSL)
          6. Flash patched image to both A/B slots
        """
        self._log("=== ALL-IN-ONE (Single BROM Session) ===", "INFO")

        target = self.profile.partitions.root_target
        slot = f"{target}_a"
        flash_targets = self.profile.partitions.flash_targets
        vbmeta_parts = self.profile.vbmeta.partitions

        # Backup partitions
        backup_list = self.profile.partitions.backup_list
        backup_dir = None
        if backup_list:
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(get_default_backup_dir(), f"backup_{timestamp}")
            self._log(f"Will backup {len(backup_list)} partitions to: {backup_dir}", "INFO")
            self._backup_dir = backup_dir

        # Find Magisk APK
        magisk_apk = self._find_magisk_apk()
        if not magisk_apk:
            self._log("Magisk APK not found!", "ERROR")
            self._log("Please download Magisk APK to Downloads folder.", "ERROR")
            return False
        self._log(f"Magisk APK: {magisk_apk}", "INFO")

        def _patch_callback(stock_path: str, patched_path: str) -> bool:
            """Called by mtk_bridge when stock image is ready."""
            from tumeloroot.core.boot_patcher import patch_boot_image
            self._log("Starting PC-side Magisk patch (magiskboot via WSL)...", "INFO")

            # Progress file so CMD window shows what's happening
            progress_file = self._mtk._root_progress_file()

            def _log_with_progress(msg):
                self._log(msg)
                # Append to progress file for CMD window
                try:
                    with open(progress_file, 'a', encoding='utf-8', errors='replace') as pf:
                        pf.write(msg + '\n')
                except Exception:
                    pass

            return patch_boot_image(
                image_path=stock_path,
                output_path=patched_path,
                magisk_apk=magisk_apk,
                log_cb=_log_with_progress,
            )

        return self._mtk.unlock_and_root(
            partition=slot,
            flash_targets=flash_targets,
            vbmeta_parts=vbmeta_parts,
            clear_frp=clear_frp,
            patch_callback=_patch_callback,
            backup_partitions=backup_list,
            backup_dir=backup_dir,
        )

    def _find_magisk_apk(self) -> Optional[str]:
        """Find Magisk APK on PC."""
        from pathlib import Path
        # Check assets dir
        assets = Path(os.path.dirname(__file__)).parent / "assets" / "magisk"
        if assets.is_dir():
            apks = sorted(assets.glob("Magisk*.apk"), reverse=True)
            if apks:
                return str(apks[0])
        # Check Downloads
        downloads = Path.home() / "Downloads"
        if downloads.is_dir():
            apks = sorted(downloads.glob("Magisk*.apk"), reverse=True)
            if apks:
                return str(apks[0])
        return None

    # ── Verify ───────────────────────────────────────────────────

    def _run_verify(self) -> bool:
        self._log("Checking root access via ADB...")
        if not self._adb.wait_for_device(timeout=120):
            self._log("Device not found via ADB", "ERROR")
            return False
        if self._adb.check_root():
            ver = self._adb.get_magisk_version()
            self._log(f"ROOT VERIFIED! Magisk: {ver}", "SUCCESS")
            return True
        self._log("Root not detected", "ERROR")
        return False

    def get_state(self) -> dict:
        return {}
