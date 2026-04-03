"""Prerequisite Checker - verify and install dependencies."""

from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from tumeloroot.core.platform_utils import (
    check_usbdk_installed, find_adb, find_libusb, find_mtkclient, is_windows,
)

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    name: str
    available: bool
    version: str
    required: bool
    install_func: Optional[Callable] = None


class PrerequisiteChecker:
    """Checks and optionally installs all required dependencies."""

    def check_all(self) -> list[CheckResult]:
        """Check all prerequisites and return results."""
        return [
            self.check_python(),
            self.check_mtkclient(),
            self.check_usbdk(),
            self.check_libusb(),
            self.check_adb(),
        ]

    def check_python(self) -> CheckResult:
        v = sys.version.split()[0]
        ok = sys.version_info >= (3, 9)
        return CheckResult("Python 3.9+", ok, v, required=True)

    def check_mtkclient(self) -> CheckResult:
        path = find_mtkclient()
        if path:
            return CheckResult("mtkclient", True, path, required=True, install_func=self.install_mtkclient)
        return CheckResult("mtkclient", False, "Not found", required=True, install_func=self.install_mtkclient)

    def check_usbdk(self) -> CheckResult:
        if not is_windows():
            return CheckResult("UsbDk", True, "Not needed (Linux)", required=False)
        ok = check_usbdk_installed()
        ver = "Installed" if ok else "Not found"
        return CheckResult("UsbDk Driver", ok, ver, required=True, install_func=self.install_usbdk)

    def check_libusb(self) -> CheckResult:
        path = find_libusb()
        if path:
            return CheckResult("libusb", True, path, required=True, install_func=self.install_libusb)
        return CheckResult("libusb", False, "Not found", required=True, install_func=self.install_libusb)

    def check_adb(self) -> CheckResult:
        path = find_adb()
        if path:
            return CheckResult("ADB", True, path, required=True)
        return CheckResult("ADB", False, "Not found", required=True)

    @staticmethod
    def install_mtkclient() -> bool:
        """Clone and install mtkclient."""
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "git+https://github.com/bkerler/mtkclient.git"],
                check=True, capture_output=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install mtkclient: {e}")
            return False
        except FileNotFoundError:
            logger.error("pip not found")
            return False

    @staticmethod
    def install_usbdk() -> bool:
        """Download and install UsbDk (Windows only)."""
        if not is_windows():
            return True
        try:
            import urllib.request
            url = "https://github.com/daynix/UsbDk/releases/download/v1.00-22/UsbDk_1.0.22_x64.msi"
            dest = str(Path.home() / "Downloads" / "UsbDk_1.0.22_x64.msi")
            logger.info(f"Downloading UsbDk to {dest}")
            urllib.request.urlretrieve(url, dest)
            subprocess.run(["msiexec", "/i", dest, "/quiet", "/norestart"], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"UsbDk installer failed: {e}")
            return False
        except OSError as e:
            logger.error(f"Failed to download UsbDk: {e}")
            return False

    @staticmethod
    def install_libusb() -> bool:
        """Download and place libusb-1.0.dll."""
        if not is_windows():
            return True
        try:
            import urllib.request
            url = "https://github.com/libusb/libusb/releases/download/v1.0.27/libusb-1.0.27.7z"
            dest = str(Path.home() / "Downloads" / "libusb-1.0.27.7z")
            logger.info(f"Downloading libusb to {dest}")
            urllib.request.urlretrieve(url, dest)
            logger.info("Downloaded. Please extract libusb-1.0.dll to your mtkclient folder.")
            return False  # Manual step required
        except OSError as e:
            logger.error(f"Failed to download libusb: {e}")
            return False
