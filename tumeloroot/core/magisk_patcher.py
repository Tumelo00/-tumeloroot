"""Magisk Patcher - patch boot/vendor_boot images with Magisk via ADB."""

from __future__ import annotations

import glob
import logging
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional

from tumeloroot.core.adb_bridge import AdbBridge
from tumeloroot.core.platform_utils import get_assets_dir

logger = logging.getLogger(__name__)

MAGISK_GITHUB_API = "https://api.github.com/repos/topjohnwu/Magisk/releases/latest"
MAGISK_PKG = "com.topjohnwu.magisk"


class MagiskPatcher:
    """Handles Magisk patching of boot/vendor_boot images via ADB."""

    def __init__(self, adb: AdbBridge, magisk_apk_path: Optional[str] = None):
        self._adb = adb
        self._apk_path = magisk_apk_path or self._find_local_apk()

    @staticmethod
    def _find_local_apk() -> Optional[str]:
        """Find a locally stored Magisk APK."""
        assets = Path(get_assets_dir()) / "magisk"
        if assets.is_dir():
            apks = sorted(assets.glob("Magisk*.apk"), reverse=True)
            if apks:
                return str(apks[0])
        home = Path.home() / "Downloads"
        if home.is_dir():
            apks = sorted(home.glob("Magisk*.apk"), reverse=True)
            if apks:
                return str(apks[0])
        return None

    def download_magisk(self, target_dir: Optional[str] = None) -> Optional[str]:
        """Download the latest Magisk APK from GitHub.

        Returns:
            Path to the downloaded APK, or None on failure.
        """
        target = Path(target_dir or get_assets_dir()) / "magisk"
        target.mkdir(parents=True, exist_ok=True)

        try:
            import json
            with urllib.request.urlopen(MAGISK_GITHUB_API, timeout=30) as resp:
                release = json.loads(resp.read())
            tag = release["tag_name"]
            for asset in release.get("assets", []):
                if asset["name"].endswith(".apk") and "Magisk" in asset["name"]:
                    url = asset["browser_download_url"]
                    dest = target / asset["name"]
                    logger.info(f"Downloading Magisk {tag}: {url}")
                    urllib.request.urlretrieve(url, str(dest))
                    self._apk_path = str(dest)
                    return str(dest)
        except Exception as e:
            logger.error(f"Failed to download Magisk: {e}")
        return None

    def ensure_magisk_installed(self) -> bool:
        """Ensure Magisk app is installed on the device."""
        code, output = self._adb.shell(f"pm list packages | grep {MAGISK_PKG}")
        if MAGISK_PKG in output:
            return True

        if not self._apk_path or not os.path.isfile(self._apk_path):
            logger.info("Magisk APK not found locally, downloading...")
            if not self.download_magisk():
                return False

        logger.info(f"Installing Magisk from {self._apk_path}")
        return self._adb.install_apk(self._apk_path)

    def patch_image_via_adb(
        self,
        image_path: str,
        output_path: str,
        log_callback=None,
    ) -> bool:
        """Patch a boot/vendor_boot image using Magisk on the device.

        Flow:
        1. Push image to device
        2. Open Magisk app to patch (user manually selects the file)
        3. Pull patched image back

        For automated patching, this uses magiskboot directly on device.

        Args:
            image_path: Local path to the image to patch.
            output_path: Local path to save the patched image.
            log_callback: Optional callback for log messages.

        Returns:
            True if patching was successful.
        """
        def _log(msg):
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        # Ensure Magisk is installed
        if not self.ensure_magisk_installed():
            _log("Failed to install Magisk")
            return False

        # Push image to device
        remote_img = "/sdcard/Download/tumeloroot_patch.img"
        _log(f"Pushing image to device ({os.path.getsize(image_path) // 1024 // 1024}MB)...")
        if not self._adb.push(image_path, remote_img):
            _log("Failed to push image to device")
            return False

        # Setup magiskboot and patch on device
        _log("Setting up Magisk tools on device...")
        setup_ok = self._setup_magisk_tools()
        if not setup_ok:
            _log("Falling back to manual Magisk patching. Open Magisk > Install > Select and Patch > choose tumeloroot_patch.img")
            return self._manual_patch_flow(remote_img, output_path, _log)

        # Automated patch via boot_patch.sh
        _log("Patching image with Magisk...")
        code, output = self._adb.shell(
            "cd /data/local/tmp/mwork && "
            "KEEPVERITY=false KEEPFORCEENCRYPT=true PATCHVBMETAFLAG=false "
            "sh boot_patch.sh /sdcard/Download/tumeloroot_patch.img"
        )
        _log(output)

        if "new-boot.img" not in output and "Repacking" not in output:
            _log("Automated patch failed, trying manual method...")
            return self._manual_patch_flow(remote_img, output_path, _log)

        # Pull patched image
        _log("Pulling patched image from device...")
        if self._adb.pull("/data/local/tmp/mwork/new-boot.img", output_path):
            _log(f"Patched image saved to {output_path}")
            return True

        return False

    def _setup_magisk_tools(self) -> bool:
        """Extract magiskboot and other tools from Magisk APK on device."""
        code, apk_path = self._adb.shell(f"pm path {MAGISK_PKG}")
        if code != 0:
            return False
        apk_path = apk_path.replace("package:", "").strip()

        setup_cmds = f"""
rm -rf /data/local/tmp/mwork && mkdir -p /data/local/tmp/mwork && cd /data/local/tmp/mwork &&
unzip -o {apk_path} assets/boot_patch.sh assets/util_functions.sh assets/stub.apk lib/arm64-v8a/libmagiskboot.so lib/arm64-v8a/libmagiskinit.so lib/arm64-v8a/libmagiskpolicy.so lib/arm64-v8a/libmagisk.so lib/arm64-v8a/libinit-ld.so lib/arm64-v8a/libbusybox.so 2>/dev/null &&
mv assets/* . && mv lib/arm64-v8a/libmagiskboot.so magiskboot && mv lib/arm64-v8a/libmagiskinit.so magiskinit &&
mv lib/arm64-v8a/libmagiskpolicy.so magiskpolicy && mv lib/arm64-v8a/libmagisk.so magisk &&
mv lib/arm64-v8a/libinit-ld.so init-ld 2>/dev/null; mv lib/arm64-v8a/libbusybox.so busybox 2>/dev/null;
chmod 755 magiskboot magiskinit magiskpolicy magisk init-ld busybox 2>/dev/null &&
echo SETUP_OK
"""
        code, output = self._adb.shell(setup_cmds)
        return "SETUP_OK" in output

    def _manual_patch_flow(self, remote_img: str, output_path: str, _log) -> bool:
        """Fallback: user patches manually via Magisk app, we find and pull the result."""
        _log("Please open Magisk app > Install > Select and Patch a File")
        _log(f"Select: {remote_img}")
        _log("Waiting for patched file to appear...")

        # Wait for patched file (up to 5 minutes)
        for _ in range(60):
            patched = self.find_patched_file()
            if patched:
                _log(f"Found patched file: {patched}")
                return self._adb.pull(patched, output_path)
            time.sleep(5)

        _log("Timed out waiting for patched file")
        return False

    def find_patched_file(self) -> Optional[str]:
        """Find the latest magisk_patched*.img on the device."""
        code, output = self._adb.shell("ls -t /sdcard/Download/magisk_patched*.img 2>/dev/null")
        if code == 0 and output.strip():
            return output.strip().split("\n")[0]
        return None
