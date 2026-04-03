"""MTK Bridge - wrapper around mtkclient's Python API for BROM operations."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

from tumeloroot.core.platform_utils import find_mtkclient, ensure_mtkclient_in_path

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str, str], None]


class MtkBridge:
    """High-level wrapper around mtkclient for BROM operations.

    All operations require the device to be connected in BROM mode
    (power off, hold Vol Up + Vol Down, connect USB).
    """

    def __init__(
        self,
        mtkclient_path: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
    ):
        self._mtkclient_path = mtkclient_path or find_mtkclient()
        self._progress_cb = progress_callback
        self._log_cb = log_callback
        self._mtk = None
        self._da_handler = None
        self._connected = False

        if self._mtkclient_path:
            ensure_mtkclient_in_path(self._mtkclient_path)

    def _log(self, msg: str, level: str = "INFO") -> None:
        logger.log(getattr(logging, level, logging.INFO), msg)
        if self._log_cb:
            try:
                self._log_cb(msg, level)
            except RuntimeError:
                pass  # GUI may be destroyed

    def _progress(self, current: int, total: int, msg: str = "") -> None:
        if self._progress_cb:
            try:
                self._progress_cb(current, total, msg)
            except RuntimeError:
                pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect_brom(self) -> bool:
        """Connect to device in BROM mode via mtkclient.

        Returns:
            True if connection was successful.
        """
        self._log("Initializing mtkclient connection...")
        try:
            from mtkclient.Library.mtk_class import Mtk
            from mtkclient.Library.DA.mtk_da_handler import DaHandler
            from mtkclient.config.mtk_config import MtkConfig
        except ImportError as e:
            self._log(f"mtkclient not found: {e}", "ERROR")
            return False

        try:
            config = MtkConfig(loglevel=logging.INFO, gui=None, guiprogress=None)
            self._mtk = Mtk(config=config, loglevel=logging.INFO)
            self._da_handler = DaHandler(self._mtk, loglevel=logging.INFO)

            self._log("Waiting for device in BROM mode...")
            self._mtk = self._da_handler.connect(self._mtk, directory=".")

            if self._mtk is None:
                self._log("Failed to connect to device", "ERROR")
                self._connected = False
                return False

            self._log("Device connected! Configuring DA...")
            self._connected = True
            self._log("BROM connection established successfully", "SUCCESS")
            return True

        except Exception as e:
            self._log(f"Connection error: {e}", "ERROR")
            self._connected = False
            return False

    def read_partition(self, name: str) -> Optional[bytes]:
        """Read a partition by name using temporary file.

        Args:
            name: Partition name (e.g., 'vendor_boot_a', 'seccfg').

        Returns:
            Partition data as bytes, or None on failure.
        """
        if not self._connected or not self._da_handler:
            self._log("Not connected to device", "ERROR")
            return None

        self._log(f"Reading partition: {name}")
        try:
            # Use temp file since da_read writes to file
            with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tmp:
                tmp_path = tmp.name

            self._da_handler.da_read(
                partitionname=name,
                parttype="user",
                filename=tmp_path,
                display=True,
            )

            if os.path.isfile(tmp_path) and os.path.getsize(tmp_path) > 0:
                with open(tmp_path, "rb") as f:
                    data = f.read()
                self._log(f"Read {len(data)} bytes from {name}")
                return data
            else:
                self._log(f"Partition {name} read returned empty file", "ERROR")
                return None
        except Exception as e:
            self._log(f"Failed to read partition {name}: {e}", "ERROR")
            return None
        finally:
            try:
                if os.path.isfile(tmp_path):
                    os.unlink(tmp_path)
            except (OSError, UnboundLocalError):
                pass

    def write_partition(self, name: str, data: bytes) -> bool:
        """Write data to a partition using temporary file.

        Args:
            name: Partition name.
            data: Data to write.

        Returns:
            True if write was successful.
        """
        if not self._connected or not self._da_handler:
            self._log("Not connected to device", "ERROR")
            return False

        self._log(f"Writing {len(data)} bytes to partition: {name}")
        try:
            # Write data to temp file, then flash
            with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            result = self._da_handler.da_write(
                partitionname=name,
                filename=tmp_path,
                parttype="user",
                display=True,
            )
            self._log(f"Successfully wrote to {name}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"Failed to write partition {name}: {e}", "ERROR")
            return False
        finally:
            try:
                if os.path.isfile(tmp_path):
                    os.unlink(tmp_path)
            except (OSError, UnboundLocalError):
                pass

    def unlock_bootloader(self) -> bool:
        """Unlock the bootloader via seccfg modification.

        Returns:
            True if unlock was successful.
        """
        if not self._connected or not self._mtk:
            self._log("Not connected to device", "ERROR")
            return False

        self._log("Unlocking bootloader (seccfg)...")
        try:
            result = self._mtk.daloader.seccfg("unlock")
            # seccfg returns various types depending on implementation
            # Check for truthy result or explicit success indicators
            if result is not None and result is not False:
                self._log("Bootloader unlocked successfully!", "SUCCESS")
                return True
            else:
                self._log("Bootloader unlock returned failure status", "ERROR")
                return False
        except Exception as e:
            self._log(f"Bootloader unlock error: {e}", "ERROR")
            return False

    def lock_bootloader(self) -> bool:
        """Lock the bootloader (re-lock seccfg)."""
        if not self._connected or not self._mtk:
            self._log("Not connected", "ERROR")
            return False
        try:
            result = self._mtk.daloader.seccfg("lock")
            return result is not None and result is not False
        except Exception as e:
            self._log(f"Lock error: {e}", "ERROR")
            return False

    def get_gpt_info(self) -> dict:
        """Get GPT partition table information.

        Returns:
            Dict with partition names as keys, {offset, size} as values.
        """
        if not self._connected or not self._mtk:
            return {}

        try:
            result = self._mtk.daloader.get_gpt(parttype="user")
            if result is None:
                return {}

            gpt_data, guid_gpt = result
            if guid_gpt is None:
                return {}

            partitions = {}
            # Handle both GPT and PMT partition table types
            entries = getattr(guid_gpt, "partentries", None)
            if entries is None:
                return {}

            for partition in entries:
                name = getattr(partition, "name", "")
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="ignore")
                name = name.rstrip("\x00").strip()
                if name:
                    sector = getattr(partition, "sector", 0)
                    sectors = getattr(partition, "sectors", 0)
                    partitions[name] = {
                        "offset": sector * 512,
                        "size": sectors * 512,
                    }
            return partitions
        except Exception as e:
            self._log(f"Failed to read GPT: {e}", "ERROR")
            return {}

    def get_device_info(self) -> dict:
        """Get device hardware information."""
        if not self._connected or not self._mtk:
            return {}

        info = {}
        try:
            config = self._mtk.config
            if hasattr(config, "hwcode") and config.hwcode:
                info["hwcode"] = hex(config.hwcode)
            if hasattr(config, "target_config"):
                info["target_config"] = str(getattr(config, "target_config", ""))
            if hasattr(config, "hwparam") and config.hwparam:
                meid = getattr(config.hwparam, "meid", None)
                if meid:
                    info["meid"] = meid if isinstance(meid, str) else meid.hex()
        except Exception as e:
            logger.debug(f"Error getting device info: {e}")
        return info

    def disconnect(self) -> None:
        """Disconnect from the device and clean up."""
        self._log("Disconnecting from device...")
        try:
            if self._mtk:
                port = getattr(self._mtk, "port", None)
                if port and hasattr(port, "close"):
                    port.close()
        except Exception as e:
            logger.debug(f"Disconnect cleanup error: {e}")
        self._connected = False
        self._mtk = None
        self._da_handler = None
        self._log("Disconnected")
