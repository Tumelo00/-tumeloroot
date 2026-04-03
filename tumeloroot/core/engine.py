"""Root Engine - main orchestrator that coordinates all rooting steps."""

from __future__ import annotations

import logging
import os
from enum import Enum
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

ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str, str], None]


class RootStep(Enum):
    PREREQUISITES = "prerequisites"
    CONNECT = "connect"
    BACKUP = "backup"
    UNLOCK = "unlock"
    PATCH_VBMETA = "patch_vbmeta"
    PATCH_MAGISK = "patch_magisk"
    FLASH = "flash"
    VERIFY = "verify"


class StepState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RootEngine:
    """Main orchestrator - coordinates all rooting steps.

    Usage:
        profile = DeviceProfile.load("devices/lenovo_tb330xup.yaml")
        engine = RootEngine(profile, progress_cb, log_cb)
        engine.run_step("prerequisites")
        engine.run_step("connect")
        engine.run_step("backup")
        ...
    """

    def __init__(
        self,
        device_profile: DeviceProfile,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
    ):
        self.profile = device_profile
        self._progress_cb = progress_callback
        self._log_cb = log_callback

        # Validate profile
        errors = device_profile.validate()
        if errors:
            for err in errors:
                logger.warning(f"Profile issue: {err}")

        self._states: dict[RootStep, StepState] = {s: StepState.PENDING for s in RootStep}
        self._backup_dir: Optional[str] = None
        self._patched_image_path: Optional[str] = None

        self._mtk = MtkBridge(progress_callback=progress_callback, log_callback=log_callback)
        self._adb = AdbBridge()
        self._checker = PrerequisiteChecker()
        self._backup_mgr: Optional[BackupManager] = None
        self._magisk: Optional[MagiskPatcher] = None

    def _log(self, msg: str, level: str = "INFO") -> None:
        logger.log(getattr(logging, level, logging.INFO), msg)
        if self._log_cb:
            self._log_cb(msg, level)

    def _progress(self, current: int, total: int, msg: str = "") -> None:
        if self._progress_cb:
            self._progress_cb(current, total, msg)

    def get_state(self) -> dict[str, str]:
        return {step.value: state.value for step, state in self._states.items()}

    def run_step(self, step_name: str) -> bool:
        """Run a single step by name."""
        step = RootStep(step_name)
        self._states[step] = StepState.RUNNING
        self._log(f"Starting step: {step.value}")

        handlers = {
            RootStep.PREREQUISITES: self._run_prerequisites,
            RootStep.CONNECT: self._run_connect,
            RootStep.BACKUP: self._run_backup,
            RootStep.UNLOCK: self._run_unlock,
            RootStep.PATCH_VBMETA: self._run_patch_vbmeta,
            RootStep.PATCH_MAGISK: self._run_patch_magisk,
            RootStep.FLASH: self._run_flash,
            RootStep.VERIFY: self._run_verify,
        }

        try:
            success = handlers[step]()
            self._states[step] = StepState.SUCCESS if success else StepState.FAILED
            status = "completed" if success else "FAILED"
            self._log(f"Step {step.value}: {status}", "SUCCESS" if success else "ERROR")
            return success
        except Exception as e:
            self._states[step] = StepState.FAILED
            self._log(f"Step {step.value} error: {e}", "ERROR")
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
        self._log("Connecting to device in BROM mode...")
        return self._mtk.connect_brom()

    def _run_backup(self) -> bool:
        backup_dir = get_default_backup_dir()
        self._backup_mgr = BackupManager(backup_dir, self._mtk)

        partitions = self.profile.partitions.backup_list
        self._log(f"Backing up {len(partitions)} partitions...")

        def on_progress(name, current, total):
            self._progress(current, total, f"Backing up {name}")
            self._log(f"  [{current + 1}/{total}] {name}")

        result = self._backup_mgr.create_backup(partitions, on_progress)
        if result:
            self._backup_dir = result
            self._log(f"Backup saved to: {result}")

            valid, errors = self._backup_mgr.verify_backup(result)
            if valid:
                self._log("Backup verification: OK")
            else:
                self._log(f"Backup verification failed: {errors}", "WARNING")
            return True
        return False

    def _run_unlock(self) -> bool:
        self._log("Unlocking bootloader via seccfg...")
        return self._mtk.unlock_bootloader()

    def _run_patch_vbmeta(self) -> bool:
        self._log("Patching vbmeta partitions to disable verification...")
        offset = self.profile.vbmeta.flags_offset
        flags = self.profile.vbmeta.flags_value

        for vbmeta_name in self.profile.vbmeta.partitions:
            self._log(f"  Reading {vbmeta_name}...")
            data = self._mtk.read_partition(vbmeta_name)
            if data is None:
                self._log(f"  Failed to read {vbmeta_name}", "ERROR")
                return False

            patched = patch_vbmeta(data, flags=flags, offset=offset)
            if not verify_patch(patched, flags, offset):
                self._log(f"  Patch verification failed for {vbmeta_name}", "ERROR")
                return False

            self._log(f"  Writing patched {vbmeta_name}...")
            if not self._mtk.write_partition(vbmeta_name, patched):
                self._log(f"  Failed to write {vbmeta_name}", "ERROR")
                return False

            self._log(f"  {vbmeta_name}: OK")

        self._log("All vbmeta partitions patched")
        return True

    def _run_patch_magisk(self) -> bool:
        self._log("Patching image with Magisk...")
        self._log("Device needs to be booted to Android for this step")
        self._log("Waiting for ADB connection...")

        if not self._adb.wait_for_device(timeout=180):
            self._log("Device not found via ADB", "ERROR")
            return False

        self._magisk = MagiskPatcher(self._adb)
        target = self.profile.partitions.root_target
        target_a = f"{target}_a" if self.profile.boot_structure.ab_device else target

        # Read the target partition image from backup
        if self._backup_dir:
            img_path = os.path.join(self._backup_dir, f"{target_a}.img")
            if os.path.isfile(img_path):
                output = os.path.join(self._backup_dir, f"{target}_patched.img")
                success = self._magisk.patch_image_via_adb(
                    img_path, output, log_callback=lambda m: self._log(f"  {m}")
                )
                if success:
                    self._patched_image_path = output
                    self._log(f"Patched image saved: {output}")
                return success

        self._log("No backup image found for patching", "ERROR")
        return False

    def _run_flash(self) -> bool:
        if not self._patched_image_path or not os.path.isfile(self._patched_image_path):
            self._log("No patched image available", "ERROR")
            return False

        self._log("Flashing patched image to device...")
        self._log("Device needs to be in BROM mode for this step")

        if not self._mtk.is_connected:
            self._log("Reconnecting to BROM...")
            if not self._mtk.connect_brom():
                return False

        with open(self._patched_image_path, "rb") as f:
            patched_data = f.read()
        flash_targets = self.profile.partitions.flash_targets

        for target in flash_targets:
            self._log(f"  Flashing {target} ({len(patched_data) // 1024 // 1024}MB)...")
            if not self._mtk.write_partition(target, patched_data):
                self._log(f"  Failed to flash {target}", "ERROR")
                return False
            self._log(f"  {target}: OK")

        self._log("Flash completed successfully!")
        return True

    def _run_verify(self) -> bool:
        self._log("Verifying root access...")
        self._log("Waiting for device to boot...")

        if not self._adb.wait_for_device(timeout=180):
            self._log("Device not found via ADB", "ERROR")
            return False

        if self._adb.check_root():
            magisk_ver = self._adb.get_magisk_version()
            self._log(f"ROOT VERIFIED! Magisk version: {magisk_ver}", "SUCCESS")
            return True

        self._log("Root verification failed - su not available", "ERROR")
        return False

    def emergency_restore(self) -> bool:
        """Restore all partitions from backup (emergency recovery)."""
        if not self._backup_dir or not self._backup_mgr:
            self._log("No backup available for restore", "ERROR")
            return False

        self._log("EMERGENCY RESTORE: Restoring all partitions...")
        if not self._mtk.is_connected:
            if not self._mtk.connect_brom():
                self._log("Cannot connect to device for restore", "ERROR")
                return False

        return self._backup_mgr.full_restore(
            self._backup_dir,
            progress_callback=lambda name, i, t: self._log(f"  Restoring {name} [{i + 1}/{t}]"),
        )
