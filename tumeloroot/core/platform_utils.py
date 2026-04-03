"""Platform utilities for OS detection, path helpers, and dependency location."""

import os
import sys
import shutil
import platform
from pathlib import Path
from typing import Optional


def is_windows() -> bool:
    return platform.system() == "Windows"


def is_linux() -> bool:
    return platform.system() == "Linux"


def find_adb() -> Optional[str]:
    """Locate the ADB binary on the system."""
    candidates = []
    if is_windows():
        candidates = [
            r"C:\adb.exe",
            r"C:\platform-tools\adb.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        ]
    else:
        candidates = ["/usr/bin/adb", "/usr/local/bin/adb"]

    for path in candidates:
        if os.path.isfile(path):
            return path

    found = shutil.which("adb")
    if found:
        return found
    return None


def find_mtkclient() -> Optional[str]:
    """Locate the mtkclient installation directory."""
    candidates = [
        Path.home() / "mtkclient",
        Path(r"C:\Users") / os.getenv("USERNAME", "") / "mtkclient",
        Path("/opt/mtkclient"),
    ]

    for path in candidates:
        if (path / "mtk.py").is_file():
            return str(path)

    try:
        import mtkclient
        return str(Path(mtkclient.__file__).parent.parent)
    except ImportError:
        pass

    return None


def ensure_mtkclient_in_path(mtkclient_path: Optional[str] = None) -> bool:
    """Add mtkclient to sys.path if not already importable."""
    try:
        import mtkclient  # noqa: F401
        return True
    except ImportError:
        pass

    path = mtkclient_path or find_mtkclient()
    if path and os.path.isdir(path):
        if path not in sys.path:
            sys.path.insert(0, path)
        try:
            import mtkclient  # noqa: F401
            return True
        except ImportError:
            pass
    return False


def find_libusb() -> Optional[str]:
    """Locate libusb-1.0.dll (Windows only)."""
    if not is_windows():
        return "system"

    candidates = [
        Path.home() / "mtkclient" / "libusb-1.0.dll",
        Path(sys.executable).parent / "libusb-1.0.dll",
        Path(r"C:\Windows\System32\libusb-1.0.dll"),
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def check_usbdk_installed() -> bool:
    """Check if UsbDk driver is installed (Windows only)."""
    if not is_windows():
        return True
    usbdk_path = Path(r"C:\Program Files\UsbDk Runtime Library\UsbDkController.exe")
    return usbdk_path.is_file()


def get_default_backup_dir() -> str:
    """Get the default backup directory."""
    backup_dir = Path.home() / "TumelorootBackups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return str(backup_dir)


def get_devices_dir() -> str:
    """Get the directory containing device profile YAML files."""
    return str(Path(__file__).parent.parent / "devices")


def get_assets_dir() -> str:
    """Get the assets directory."""
    return str(Path(__file__).parent.parent / "assets")
