"""ADB Bridge - subprocess wrapper for Android Debug Bridge operations."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Optional

from tumeloroot.core.platform_utils import find_adb

logger = logging.getLogger(__name__)


class AdbBridge:
    """Wrapper around ADB for device communication when Android is booted."""

    def __init__(self, adb_path: Optional[str] = None):
        self._adb = adb_path or find_adb()
        if not self._adb:
            logger.warning("ADB binary not found")

    @property
    def available(self) -> bool:
        return self._adb is not None

    def _run(self, args: list[str], timeout: int = 30) -> tuple[int, str]:
        """Run an ADB command and return (exit_code, output)."""
        if not self._adb:
            return -1, "ADB not found"
        cmd = [self._adb] + args
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            output = (result.stdout + result.stderr).strip()
            return result.returncode, output
        except subprocess.TimeoutExpired:
            return -1, "Command timed out"
        except Exception as e:
            return -1, str(e)

    def devices(self) -> list[str]:
        """List connected ADB device serial numbers."""
        code, output = self._run(["devices"])
        if code != 0:
            return []
        serials = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serials.append(parts[0])
        return serials

    def wait_for_device(self, timeout: int = 120) -> bool:
        """Wait for a device to appear on ADB."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.devices():
                return True
            time.sleep(5)
        return False

    def shell(self, cmd: str, timeout: int = 30) -> tuple[int, str]:
        """Run a shell command on the device."""
        return self._run(["shell", cmd], timeout=timeout)

    def push(self, local: str, remote: str) -> bool:
        """Push a file to the device."""
        code, _ = self._run(["push", local, remote], timeout=300)
        return code == 0

    def pull(self, remote: str, local: str) -> bool:
        """Pull a file from the device."""
        code, _ = self._run(["pull", remote, local], timeout=300)
        return code == 0

    def install_apk(self, apk_path: str) -> bool:
        """Install an APK on the device."""
        code, output = self._run(["install", "-r", apk_path], timeout=60)
        return code == 0 and "Success" in output

    def reboot(self, mode: str = "") -> bool:
        """Reboot the device. mode: '', 'bootloader', 'recovery'."""
        args = ["reboot"]
        if mode:
            args.append(mode)
        code, _ = self._run(args)
        return code == 0

    def get_prop(self, prop: str) -> str:
        """Get a system property value."""
        code, output = self.shell(f"getprop {prop}")
        return output.strip() if code == 0 else ""

    def check_root(self) -> bool:
        """Check if the device has root access via su."""
        code, output = self.shell("su -c id")
        return "uid=0(root)" in output

    def get_magisk_version(self) -> str:
        """Get installed Magisk version if available."""
        code, output = self.shell("su -c magisk -v")
        return output.strip() if code == 0 and output.strip() else ""
