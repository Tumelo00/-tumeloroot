"""MTK Bridge - opens mtkclient in its own CMD window with visible output."""

from __future__ import annotations

import logging
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from typing import Callable, Optional

from tumeloroot.core.platform_utils import find_mtkclient

logger = logging.getLogger(__name__)
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

LOG_KEYWORDS = [
    'waiting', 'detected', 'handshake', 'success',
    'fail', 'error', 'wrote', 'written', 'bypass', 'unlock',
    'done', 'uploading', 'patched', 'gpt', 'dumping',
    'boot to', 'brom', 'device', 'seccfg', 'vbmeta',
    'already', 'configur', 'flags', 'reading', 'step',
    'connected', 'complete',
]

SUCCESS_KEYWORDS = [
    'success', 'done', 'wrote', 'written', 'detected',
    'unlock', 'already', 'patched', 'complete',
]


def find_python() -> str:
    if getattr(sys, 'frozen', False):
        for name in ["python", "python3"]:
            found = shutil.which(name)
            if found:
                return found
        return "python"
    return sys.executable


class MtkBridge:
    """Opens mtkclient in a real CMD window with visible output."""

    VBMETA_PARTS = [
        "vbmeta_a", "vbmeta_b",
        "vbmeta_system_a", "vbmeta_system_b",
        "vbmeta_vendor_a", "vbmeta_vendor_b",
    ]

    def __init__(self, log_callback: Optional[Callable] = None):
        self._mtk_path = find_mtkclient()
        self._python = find_python()
        self._log_cb = log_callback

    def _log(self, msg: str, level: str = "INFO"):
        if self._log_cb:
            try:
                self._log_cb(msg, level)
            except Exception:
                pass

    # ── Internal helpers ──────────────────────────────────────

    def _log_file(self) -> str:
        return os.path.join(self._mtk_path, "_tr_output.log")

    def _done_file(self) -> str:
        return os.path.join(self._mtk_path, "_tr_done.marker")

    def _bat_file(self) -> str:
        return os.path.join(self._mtk_path, "_tr_run.bat")

    def _cleanup(self, *extra_files):
        for f in extra_files:
            try:
                os.unlink(f)
            except OSError:
                pass

    def _poll_and_wait(self, max_wait: int = 900) -> str:
        """Poll _tr_output.log for keyword lines, wait for _tr_done.marker."""
        log_file = self._log_file()
        done_file = self._done_file()
        elapsed = 0
        last_log_size = 0

        while elapsed < max_wait:
            time.sleep(3)
            elapsed += 3

            if os.path.isfile(log_file):
                try:
                    with open(log_file, 'r', errors='ignore') as lf:
                        content = lf.read()
                    if len(content) > last_log_size:
                        for line in content[last_log_size:].splitlines():
                            clean = ANSI_RE.sub('', line.strip())
                            if not clean:
                                continue
                            low = clean.lower()
                            if any(k in low for k in LOG_KEYWORDS):
                                if 'error' in low or 'fail' in low:
                                    self._log(clean, "ERROR")
                                elif any(k in low for k in SUCCESS_KEYWORDS):
                                    self._log(clean, "SUCCESS")
                                elif 'waiting' in low or 'handshake' in low:
                                    self._log(clean, "WARNING")
                                else:
                                    self._log(clean, "INFO")
                        last_log_size = len(content)
                except Exception:
                    pass

            if os.path.isfile(done_file):
                time.sleep(1)
                break

        output = ""
        if os.path.isfile(log_file):
            with open(log_file, 'r', errors='ignore') as lf:
                output = ANSI_RE.sub('', lf.read())

        return output

    def _launch_bat(self, bat_content: str, title: str) -> str:
        """Write bat, launch in CMD, poll, return output."""
        log_file = self._log_file()
        done_file = self._done_file()
        bat_file = self._bat_file()

        self._cleanup(log_file, done_file)

        with open(bat_file, 'w') as f:
            f.write(bat_content)

        try:
            subprocess.Popen(
                f'start "Tumeloroot - {title}" cmd /c "{bat_file}"',
                shell=True, cwd=self._mtk_path,
            )
            self._log("CMD window opened!", "INFO")

            output = self._poll_and_wait()

            self._cleanup(done_file, bat_file)
            return output

        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            return str(e)

    def _write_connect_block(self, f):
        """Write BROM connect code with retry and USB re-enumeration."""
        f.write('import usb.core\n')
        f.write('import usb.backend.libusb1\n\n')
        f.write('MTK_VID = 0x0E8D\n')
        f.write('MTK_PIDS = [0x0003, 0x6000, 0x2000, 0x2001, 0x20FF, 0x3000]\n\n')
        # USB monitor function
        f.write('def wait_for_mtk_usb(timeout=120):\n')
        f.write('    """Wait for MediaTek USB device to appear."""\n')
        f.write('    import time as _t\n')
        f.write('    print("Scanning for MediaTek USB device...")\n')
        f.write('    waited = 0\n')
        f.write('    while waited < timeout:\n')
        f.write('        try:\n')
        f.write('            devs = usb.core.find(find_all=True)\n')
        f.write('            for d in devs:\n')
        f.write('                if d.idVendor == MTK_VID:\n')
        f.write('                    print(f"MediaTek device found! VID={hex(d.idVendor)} PID={hex(d.idProduct)}")\n')
        f.write('                    return True\n')
        f.write('        except Exception:\n')
        f.write('            pass\n')
        f.write('        _t.sleep(1)\n')
        f.write('        waited += 1\n')
        f.write('        if waited % 15 == 0:\n')
        f.write('            print(f"  Still scanning... ({waited}s) - Enter BROM mode now!")\n')
        f.write('    return False\n\n')
        # Main connect with retry
        f.write('print("=" * 50)\n')
        f.write('print("Waiting for device in BROM mode...")\n')
        f.write('print("Power OFF device > Hold Vol Up + Vol Down > Plug USB cable")\n')
        f.write('print("Release buttons after 3-5 seconds")\n')
        f.write('print("=" * 50)\n')
        f.write('print("")\n\n')
        f.write('MAX_RETRIES = 5\n')
        f.write('mtk = None\n')
        f.write('da = None\n\n')
        f.write('for _attempt in range(MAX_RETRIES):\n')
        f.write('    if _attempt > 0:\n')
        f.write('        print(f"\\n--- Retry {_attempt}/{MAX_RETRIES-1} ---")\n')
        f.write('        time.sleep(3)\n')
        f.write('    try:\n')
        f.write('        config = MtkConfig(loglevel=logging.INFO, gui=None, guiprogress=None)\n')
        f.write('        config.gpt_settings = GptSettings("0", "0", "0")\n')
        f.write('        config.reconnect = True\n')
        f.write('        config.uartloglevel = 2\n')
        f.write('        _mtk = Mtk(config=config, loglevel=logging.INFO)\n')
        f.write('        _da = DaHandler(_mtk, logging.INFO)\n')
        f.write('        _mtk = _da.connect(_mtk, ".")\n')
        f.write('        if _mtk is not None:\n')
        f.write('            print("Connected! Configuring DA...")\n')
        f.write('            _mtk = _da.configure_da(_mtk)\n')
        f.write('            print("DA configured!")\n')
        f.write('            mtk = _mtk\n')
        f.write('            da = _da\n')
        f.write('            break\n')
        f.write('        else:\n')
        f.write('            print("Connect returned None, will retry...")\n')
        f.write('    except Exception as _e:\n')
        f.write('        print(f"Connection error: {_e}")\n')
        f.write('        print("Will retry...")\n\n')
        f.write('if mtk is None:\n')
        f.write('    print("ERROR: Could not connect after multiple attempts!")\n')
        f.write('    print("Make sure device is in BROM mode and try again.")\n')
        f.write('    sys.exit(1)\n\n')

    def _mtk_cmd(self, args: str) -> str:
        mtk_py = os.path.join(self._mtk_path, "mtk.py")
        return f'"{self._python}" -u "{mtk_py}" {args}'

    def _bat_header(self, title: str, step: str, instruction: str) -> str:
        return (
            'echo.\n'
            'echo =============================================\n'
            f'echo   Tumeloroot - {title}\n'
            f'echo   {step}\n'
            f'echo   {instruction}\n'
            'echo =============================================\n'
            'echo.\n'
        )

    def _bat_footer(self) -> str:
        done_file = self._done_file()
        return (
            'echo.\n'
            'echo =============================================\n'
            'echo   Finished!\n'
            'echo =============================================\n'
            f'echo DONE > "{done_file}"\n'
            'echo Press any key to close...\n'
            'pause >nul\n'
        )

    # ── Single-command runner (for backup, printgpt, etc.) ────

    def run_command(self, args: list[str], wait_msg: str = "",
                    title: str = "mtkclient") -> tuple[bool, str]:
        if not self._mtk_path:
            self._log("mtkclient not found!", "ERROR")
            return False, ""

        log_file = self._log_file()
        mtk_args = ' '.join(args)
        cmd_display = f"python mtk.py {mtk_args}"

        self._log(f"Running: {cmd_display}", "INFO")
        if wait_msg:
            self._log(wait_msg, "WARNING")

        bat = '@echo off\n'
        bat += f'cd /d "{self._mtk_path}"\n'
        bat += self._bat_header(title, f"Running: {cmd_display}",
                                "Plug in device in BROM mode NOW!")
        bat += f'({self._mtk_cmd(mtk_args)}) > "{log_file}" 2>&1\n'
        bat += self._bat_footer()

        output = self._launch_bat(bat, title)

        success = any(k in output for k in [
            "Successfully wrote seccfg", "GPT Table", "Wrote",
            "already unlocked", "ALL VBMETA",
        ])

        return success, output

    # ── All-in-one Python scripts ─────────────────────────────

    def _write_unlock_script(self, script_path: str, clear_frp: bool = False):
        """Write Python script: seccfg unlock + vbmeta flags=3 + optional FRP clear.

        Steps in ONE BROM connection:
          1. seccfg("unlock") -- unlock the bootloader
          2. Read each vbmeta FROM DEVICE, patch flags=3, write back
          3. (optional) Zero FRP partition to skip Google account after reset

        NO partition restoration from backup files -- vbmeta is read live from
        the device's own partitions and only the flags byte is changed.
        Without vbmeta flags=3, unlocked bootloader fails dm-verity = no boot.
        """
        log_file = self._log_file()
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write('# -*- coding: utf-8 -*-\n')
            f.write('import struct, sys, os, logging, tempfile\n')
            f.write(f'os.chdir(r"{self._mtk_path}")\n')
            f.write(f'sys.path.insert(0, r"{self._mtk_path}")\n\n')
            # Import mtkclient FIRST (it reconfigures stdout in utils.py)
            f.write('from mtkclient.Library.mtk_class import Mtk\n')
            f.write('from mtkclient.Library.DA.mtk_da_handler import DaHandler\n')
            f.write('from mtkclient.config.mtk_config import MtkConfig\n')
            f.write('from mtkclient.Library.Partitions.gpt import GptSettings\n\n')
            # THEN set up Tee (after mtkclient did its stdout reconfigure)
            f.write('class _Tee:\n')
            f.write('    def __init__(self, orig, logf):\n')
            f.write('        self.orig = orig\n')
            f.write('        self.logf = logf\n')
            f.write('    def write(self, data):\n')
            f.write('        self.orig.write(data)\n')
            f.write('        self.orig.flush()\n')
            f.write('        try:\n')
            f.write('            self.logf.write(data)\n')
            f.write('            self.logf.flush()\n')
            f.write('        except Exception:\n')
            f.write('            pass\n')
            f.write('    def flush(self):\n')
            f.write('        self.orig.flush()\n')
            f.write('    def __getattr__(self, name):\n')
            f.write('        return getattr(self.orig, name)\n\n')
            f.write(f'_lf = open(r"{log_file}", "w", encoding="utf-8", errors="replace")\n')
            f.write('sys.stdout = _Tee(sys.stdout, _lf)\n')
            f.write('sys.stderr = _Tee(sys.stderr, _lf)\n\n')
            # Connect with retry
            self._write_connect_block(f)
            f.write('tmpdir = tempfile.mkdtemp(prefix="tr_unlock_")\n\n')
            # Step 1: seccfg unlock
            f.write('print("\\n=== STEP 1: UNLOCKING SECCFG ===")\n')
            f.write('try:\n')
            f.write('    result = mtk.daloader.seccfg("unlock")\n')
            f.write('    if result[0]:\n')
            f.write('        print(f"seccfg: {result[1]}")\n')
            f.write('        print("Successfully wrote seccfg!")\n')
            f.write('    else:\n')
            f.write('        print(f"seccfg warning: {result[1]}")\n')
            f.write('except Exception as e:\n')
            f.write('    print(f"seccfg error: {e}")\n\n')
            # Step 2: Patch vbmeta flags=3 (read from DEVICE, not backup files)
            vbmeta_list = repr(self.VBMETA_PARTS)
            f.write('print("\\n=== STEP 2: PATCHING VBMETA (flags=3, disable dm-verity) ===")\n')
            f.write('print("Reading vbmeta partitions from DEVICE and patching flags...")\n')
            f.write(f'vbmeta_parts = {vbmeta_list}\n')
            f.write('patched_count = 0\n')
            f.write('for vb in vbmeta_parts:\n')
            f.write('    print(f"  {vb}: reading from device...")\n')
            f.write('    rd = os.path.join(tmpdir, vb + "_read.img")\n')
            f.write('    try:\n')
            f.write('        da.da_read(vb, "user", rd)\n')
            f.write('        with open(rd, "rb") as rf:\n')
            f.write('            vdata = bytearray(rf.read())\n')
            f.write('        if len(vdata) < 0x80:\n')
            f.write('            print(f"  {vb}: too small ({len(vdata)} bytes), skipping")\n')
            f.write('            continue\n')
            f.write('        old_flags = struct.unpack(">I", vdata[0x78:0x7C])[0]\n')
            f.write('        if old_flags == 3:\n')
            f.write('            print(f"  {vb}: flags already 3, skipping")\n')
            f.write('            patched_count += 1\n')
            f.write('            continue\n')
            f.write('        vdata[0x78:0x7C] = struct.pack(">I", 3)\n')
            f.write('        wd = os.path.join(tmpdir, vb + "_patched.img")\n')
            f.write('        with open(wd, "wb") as wf:\n')
            f.write('            wf.write(vdata)\n')
            f.write('        da.da_write("user", [wd], [vb])\n')
            f.write('        print(f"  {vb}: flags {old_flags} -> 3 PATCHED OK")\n')
            f.write('        patched_count += 1\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {vb}: ERROR: {e}")\n\n')
            f.write('print(f"\\nPatched {patched_count}/{len(vbmeta_parts)} vbmeta partitions")\n')
            # Step 3 (optional): Clear FRP partition
            if clear_frp:
                f.write('\nprint("\\n=== STEP 3: CLEARING FRP (Factory Reset Protection) ===")\n')
                f.write('print("This removes Google account verification after factory reset.")\n')
                f.write('frp_parts = ["frp"]\n')
                f.write('frp_cleared = 0\n')
                f.write('for fp in frp_parts:\n')
                f.write('    print(f"  {fp}: reading from device...")\n')
                f.write('    rd = os.path.join(tmpdir, fp + "_read.img")\n')
                f.write('    try:\n')
                f.write('        da.da_read(fp, "user", rd)\n')
                f.write('        size = os.path.getsize(rd)\n')
                f.write('        print(f"  {fp}: {size} bytes, zeroing...")\n')
                f.write('        wd = os.path.join(tmpdir, fp + "_zero.img")\n')
                f.write('        with open(wd, "wb") as wf:\n')
                f.write('            wf.write(b"\\x00" * size)\n')
                f.write('        da.da_write("user", [wd], [fp])\n')
                f.write('        print(f"  {fp}: CLEARED OK")\n')
                f.write('        frp_cleared += 1\n')
                f.write('    except Exception as e:\n')
                f.write('        print(f"  {fp}: ERROR: {e}")\n')
                f.write('print(f"\\nCleared {frp_cleared}/{len(frp_parts)} FRP partitions")\n')
            f.write('print("\\n=== UNLOCK COMPLETE ===")\n')
            f.write('print("Bootloader unlocked + dm-verity disabled!")\n')
            if clear_frp:
                f.write('print("FRP cleared - no Google account needed after reset.")\n')
            f.write('print("Orange state at boot is NORMAL - device will boot fine now.")\n')

    # ── Read stock image from device (BROM) ────────────────────

    def _write_read_stock_script(self, script_path: str, partition: str, output_file: str):
        """Write Python script: connect BROM, read partition, save to file."""
        log_file = self._log_file()
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write('# -*- coding: utf-8 -*-\n')
            f.write('import sys, os, logging\n')
            f.write(f'os.chdir(r"{self._mtk_path}")\n')
            f.write(f'sys.path.insert(0, r"{self._mtk_path}")\n\n')
            f.write('from mtkclient.Library.mtk_class import Mtk\n')
            f.write('from mtkclient.Library.DA.mtk_da_handler import DaHandler\n')
            f.write('from mtkclient.config.mtk_config import MtkConfig\n')
            f.write('from mtkclient.Library.Partitions.gpt import GptSettings\n\n')
            # Tee
            f.write('class _Tee:\n')
            f.write('    def __init__(self, orig, logf):\n')
            f.write('        self.orig = orig\n')
            f.write('        self.logf = logf\n')
            f.write('    def write(self, data):\n')
            f.write('        self.orig.write(data)\n')
            f.write('        self.orig.flush()\n')
            f.write('        try:\n')
            f.write('            self.logf.write(data)\n')
            f.write('            self.logf.flush()\n')
            f.write('        except Exception:\n')
            f.write('            pass\n')
            f.write('    def flush(self):\n')
            f.write('        self.orig.flush()\n')
            f.write('    def __getattr__(self, name):\n')
            f.write('        return getattr(self.orig, name)\n\n')
            f.write(f'_lf = open(r"{log_file}", "w", encoding="utf-8", errors="replace")\n')
            f.write('sys.stdout = _Tee(sys.stdout, _lf)\n')
            f.write('sys.stderr = _Tee(sys.stderr, _lf)\n\n')
            # Connect with retry
            self._write_connect_block(f)
            # Read partition
            f.write(f'print("\\n=== READING {partition} ===")\n')
            f.write(f'output_file = r"{output_file}"\n')
            f.write('try:\n')
            f.write(f'    da.da_read("{partition}", "user", output_file)\n')
            f.write('    if os.path.exists(output_file):\n')
            f.write('        size = os.path.getsize(output_file)\n')
            f.write('        print(f"Read {size} bytes -> {output_file}")\n')
            f.write('        print("READ COMPLETE")\n')
            f.write('    else:\n')
            f.write('        print("ERROR: Output file not created!")\n')
            f.write('except Exception as e:\n')
            f.write('    print(f"READ ERROR: {e}")\n')

    def read_stock_image(self, partition: str, output_path: str) -> bool:
        """Read a partition from device via BROM. Opens CMD with real-time output."""
        if not self._mtk_path:
            self._log("mtkclient not found!", "ERROR")
            return False

        self._log(f"=== READ {partition} FROM DEVICE ===", "INFO")

        script_path = os.path.join(self._mtk_path, "_tr_read_stock.py")
        self._write_read_stock_script(script_path, partition, output_path)

        bat = '@echo off\n'
        bat += f'cd /d "{self._mtk_path}"\n'
        bat += self._bat_header(
            f"Read {partition}",
            f"Reading {partition} from device",
            "Plug in device in BROM mode NOW!",
        )
        bat += f'"{self._python}" -u "{script_path}"\n'
        bat += self._bat_footer()

        output = self._launch_bat(bat, f"Read {partition}")
        self._cleanup(script_path)

        if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            self._log(f"{partition}: {size_mb:.1f} MB read OK", "SUCCESS")
            return True

        self._log(f"Failed to read {partition}!", "ERROR")
        return False

    # ── Root flash script (flash patched vendor_boot + vbmeta) ──

    def _write_root_flash_script(
        self, script_path: str, patched_image: str,
        flash_targets: list[str], vbmeta_parts: list[str],
    ):
        """Write Python script: flash patched image + patch all vbmeta flags=3.

        Everything runs in ONE BROM connection.
        """
        log_file = self._log_file()
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write('# -*- coding: utf-8 -*-\n')
            f.write('import struct, sys, os, logging, tempfile\n')
            f.write(f'os.chdir(r"{self._mtk_path}")\n')
            f.write(f'sys.path.insert(0, r"{self._mtk_path}")\n\n')
            # Import mtkclient FIRST (it reconfigures stdout in utils.py)
            f.write('from mtkclient.Library.mtk_class import Mtk\n')
            f.write('from mtkclient.Library.DA.mtk_da_handler import DaHandler\n')
            f.write('from mtkclient.config.mtk_config import MtkConfig\n')
            f.write('from mtkclient.Library.Partitions.gpt import GptSettings\n\n')
            # THEN set up Tee (after mtkclient did its stdout reconfigure)
            f.write('class _Tee:\n')
            f.write('    def __init__(self, orig, logf):\n')
            f.write('        self.orig = orig\n')
            f.write('        self.logf = logf\n')
            f.write('    def write(self, data):\n')
            f.write('        self.orig.write(data)\n')
            f.write('        self.orig.flush()\n')
            f.write('        try:\n')
            f.write('            self.logf.write(data)\n')
            f.write('            self.logf.flush()\n')
            f.write('        except Exception:\n')
            f.write('            pass\n')
            f.write('    def flush(self):\n')
            f.write('        self.orig.flush()\n')
            f.write('    def __getattr__(self, name):\n')
            f.write('        return getattr(self.orig, name)\n\n')
            f.write(f'_lf = open(r"{log_file}", "w", encoding="utf-8", errors="replace")\n')
            f.write('sys.stdout = _Tee(sys.stdout, _lf)\n')
            f.write('sys.stderr = _Tee(sys.stderr, _lf)\n\n')
            # Connect with retry
            self._write_connect_block(f)
            f.write('tmpdir = tempfile.mkdtemp(prefix="tr_root_")\n\n')

            # ── Step 1: Flash patched image to all target slots ──
            f.write('print("\\n=== STEP 1: FLASHING PATCHED IMAGE ===")\n')
            f.write(f'patched_file = r"{patched_image}"\n')
            f.write('if not os.path.exists(patched_file):\n')
            f.write('    print(f"ERROR: Patched file not found: {patched_file}")\n')
            f.write('    sys.exit(1)\n')
            f.write('with open(patched_file, "rb") as pf:\n')
            f.write('    patched_data = pf.read()\n')
            f.write('print(f"Patched image size: {len(patched_data)} bytes")\n\n')
            # Build flash targets list
            targets_str = repr(flash_targets)
            f.write(f'flash_targets = {targets_str}\n')
            f.write('flashed = 0\n')
            f.write('for slot in flash_targets:\n')
            f.write('    print(f"  {slot}: reading partition size...")\n')
            f.write('    size_file = os.path.join(tmpdir, slot + "_size.img")\n')
            f.write('    try:\n')
            f.write('        da.da_read(slot, "user", size_file)\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {slot}: read error: {e}, SKIPPING!")\n')
            f.write('        continue\n')
            f.write('    part_size = os.path.getsize(size_file)\n')
            f.write('    data = patched_data\n')
            f.write('    if len(data) < part_size:\n')
            f.write('        data = data + b"\\x00" * (part_size - len(data))\n')
            f.write('    elif len(data) > part_size:\n')
            f.write('        data = data[:part_size]\n')
            f.write('    wfile = os.path.join(tmpdir, slot + "_flash.img")\n')
            f.write('    with open(wfile, "wb") as wf:\n')
            f.write('        wf.write(data)\n')
            f.write('    print(f"  {slot}: flashing {len(patched_data)} -> {len(data)} bytes...")\n')
            f.write('    try:\n')
            f.write('        da.da_write("user", [wfile], [slot])\n')
            f.write('        print(f"  {slot}: FLASHED OK")\n')
            f.write('        flashed += 1\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {slot}: FLASH ERROR: {e}")\n\n')
            f.write('print(f"\\nFlashed {flashed}/{len(flash_targets)} slots")\n\n')

            # ── Step 2: Patch all vbmeta (flags=3) ──
            vbmeta_str = repr(vbmeta_parts)
            f.write('print("\\n=== STEP 2: PATCHING VBMETA (flags=3) ===")\n')
            f.write(f'vbmeta_parts = {vbmeta_str}\n')
            f.write('patched_count = 0\n')
            f.write('for vb in vbmeta_parts:\n')
            f.write('    print(f"  {vb}: reading...")\n')
            f.write('    rd = os.path.join(tmpdir, vb + "_read.img")\n')
            f.write('    try:\n')
            f.write('        da.da_read(vb, "user", rd)\n')
            f.write('        with open(rd, "rb") as rf:\n')
            f.write('            vdata = bytearray(rf.read())\n')
            f.write('        old_flags = struct.unpack(">I", vdata[0x78:0x7C])[0]\n')
            f.write('        vdata[0x78:0x7C] = struct.pack(">I", 3)\n')
            f.write('        new_flags = struct.unpack(">I", vdata[0x78:0x7C])[0]\n')
            f.write('        wd = os.path.join(tmpdir, vb + "_patched.img")\n')
            f.write('        with open(wd, "wb") as wf:\n')
            f.write('            wf.write(vdata)\n')
            f.write('        da.da_write("user", [wd], [vb])\n')
            f.write('        print(f"  {vb}: flags {old_flags} -> {new_flags} PATCHED OK")\n')
            f.write('        patched_count += 1\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {vb}: ERROR: {e}")\n\n')
            f.write('print(f"\\nPatched {patched_count}/{len(vbmeta_parts)} vbmeta partitions")\n')
            f.write('print("\\n=== ROOT FLASH COMPLETE ===")\n')

    def flash_root(
        self, patched_image: str,
        flash_targets: list[str], vbmeta_parts: list[str],
    ) -> bool:
        """Flash patched image + disable vbmeta — ALL in ONE BROM connection.

        Args:
            patched_image: Path to Magisk-patched vendor_boot image.
            flash_targets: Partition names to flash (e.g. vendor_boot_a, vendor_boot_b).
            vbmeta_parts: Vbmeta partition names to patch flags=3.
        """
        if not self._mtk_path:
            self._log("mtkclient not found!", "ERROR")
            return False

        if not os.path.isfile(patched_image):
            self._log(f"Patched image not found: {patched_image}", "ERROR")
            return False

        self._log("=== ROOT FLASH ===", "INFO")
        self._log("ONE connection — flash + vbmeta in single session!", "INFO")

        script_path = os.path.join(self._mtk_path, "_tr_root_flash.py")
        self._write_root_flash_script(script_path, patched_image, flash_targets, vbmeta_parts)

        bat = '@echo off\n'
        bat += f'cd /d "{self._mtk_path}"\n'
        bat += self._bat_header(
            "Root Flash",
            "Flash patched vendor_boot + disable vbmeta",
            "Plug in device in BROM mode NOW!",
        )
        bat += f'"{self._python}" -u "{script_path}"\n'
        bat += self._bat_footer()

        output = self._launch_bat(bat, "Root Flash")
        self._cleanup(script_path)

        success = any(k in output for k in [
            "ROOT FLASH COMPLETE", "FLASHED OK", "PATCHED OK",
        ])

        if success:
            self._log("Root images flashed + vbmeta disabled!", "SUCCESS")
        else:
            self._log("Flash may have failed — check CMD window", "WARNING")

        self._log("=== ROOT FLASH COMPLETE ===", "SUCCESS")
        return success

    # ── Root ALL-IN-ONE: read + wait for PC patch + flash ─────

    def _root_ready_marker(self) -> str:
        return os.path.join(self._mtk_path, "_tr_root_ready.marker")

    def _root_patched_marker(self) -> str:
        return os.path.join(self._mtk_path, "_tr_root_patched.marker")

    def _root_stock_file(self) -> str:
        return os.path.join(self._mtk_path, "_tr_root_stock.img")

    def _root_patched_file(self) -> str:
        return os.path.join(self._mtk_path, "_tr_root_patched.img")

    def _root_progress_file(self) -> str:
        return os.path.join(self._mtk_path, "_tr_root_progress.txt")

    def _write_progress(self, progress_file: str, msg: str):
        """Append progress message for CMD window to display."""
        try:
            with open(progress_file, 'a', encoding='utf-8', errors='replace') as f:
                f.write(msg + '\n')
        except Exception:
            pass

    def _write_unlock_root_script(
        self, script_path: str, partition: str,
        flash_targets: list, vbmeta_parts: list,
        clear_frp: bool = False,
        backup_partitions: list = None,
        backup_dir: str = None,
    ):
        """ALL-IN-ONE: backup + unlock + vbmeta + FRP + read + patch + flash.

        Single BROM session does EVERYTHING:
          0. (optional) Backup partitions
          1. seccfg unlock
          2. Patch vbmeta flags=3
          3. (optional) Clear FRP
          4. Read vendor_boot_a -> READY marker
          5. Wait for PATCHED marker (PC patches)
          6. Flash patched image to all slots
        """
        log_file = self._log_file()
        stock_file = self._root_stock_file()
        patched_file = self._root_patched_file()
        ready_marker = self._root_ready_marker()
        patched_marker = self._root_patched_marker()

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write('# -*- coding: utf-8 -*-\n')
            f.write('import struct, sys, os, logging, tempfile, time\n')
            f.write(f'os.chdir(r"{self._mtk_path}")\n')
            f.write(f'sys.path.insert(0, r"{self._mtk_path}")\n\n')
            f.write('from mtkclient.Library.mtk_class import Mtk\n')
            f.write('from mtkclient.Library.DA.mtk_da_handler import DaHandler\n')
            f.write('from mtkclient.config.mtk_config import MtkConfig\n')
            f.write('from mtkclient.Library.Partitions.gpt import GptSettings\n\n')
            # Tee
            f.write('class _Tee:\n')
            f.write('    def __init__(self, orig, logf):\n')
            f.write('        self.orig = orig\n')
            f.write('        self.logf = logf\n')
            f.write('    def write(self, data):\n')
            f.write('        self.orig.write(data)\n')
            f.write('        self.orig.flush()\n')
            f.write('        try:\n')
            f.write('            self.logf.write(data)\n')
            f.write('            self.logf.flush()\n')
            f.write('        except Exception:\n')
            f.write('            pass\n')
            f.write('    def flush(self):\n')
            f.write('        self.orig.flush()\n')
            f.write('    def __getattr__(self, name):\n')
            f.write('        return getattr(self.orig, name)\n\n')
            f.write(f'_lf = open(r"{log_file}", "w", encoding="utf-8", errors="replace")\n')
            f.write('sys.stdout = _Tee(sys.stdout, _lf)\n')
            f.write('sys.stderr = _Tee(sys.stderr, _lf)\n\n')
            # Connect
            self._write_connect_block(f)
            f.write('tmpdir = tempfile.mkdtemp(prefix="tr_unlockroot_")\n\n')

            # Calculate total steps
            has_backup = backup_partitions and backup_dir
            total_steps = 6 + (1 if has_backup else 0)
            step_num = 0

            # Step 0: Backup (optional)
            if has_backup:
                step_num += 1
                parts_repr = repr(backup_partitions)
                f.write(f'print("\\n=== STEP {step_num}/{total_steps}: BACKING UP PARTITIONS ===")\n')
                f.write(f'backup_parts = {parts_repr}\n')
                f.write(f'backup_dir = r"{backup_dir}"\n')
                f.write('import os\n')
                f.write('os.makedirs(backup_dir, exist_ok=True)\n')
                f.write('bk_ok = 0\n')
                f.write('bk_total = len(backup_parts)\n')
                f.write('for bi, bp in enumerate(backup_parts):\n')
                f.write('    print(f"  [{bi+1}/{bk_total}] Reading {bp}...")\n')
                f.write('    bk_path = os.path.join(backup_dir, bp + ".img")\n')
                f.write('    try:\n')
                f.write('        da.da_read(bp, "user", bk_path)\n')
                f.write('        if os.path.isfile(bk_path) and os.path.getsize(bk_path) > 0:\n')
                f.write('            sz = os.path.getsize(bk_path)\n')
                f.write('            print(f"    {bp}: {sz:,} bytes OK")\n')
                f.write('            bk_ok += 1\n')
                f.write('        else:\n')
                f.write('            print(f"    {bp}: FAILED")\n')
                f.write('    except Exception as e:\n')
                f.write('        print(f"    {bp}: {e}")\n')
                f.write('print(f"Backed up {bk_ok}/{bk_total} partitions")\n\n')

            # Step: seccfg unlock
            step_num += 1
            f.write(f'print("\\n=== STEP {step_num}/{total_steps}: UNLOCKING SECCFG ===")\n')
            f.write('try:\n')
            f.write('    result = mtk.daloader.seccfg("unlock")\n')
            f.write('    if result[0]:\n')
            f.write('        print(f"seccfg: {result[1]}")\n')
            f.write('        print("Successfully wrote seccfg!")\n')
            f.write('    else:\n')
            f.write('        print(f"seccfg warning: {result[1]}")\n')
            f.write('except Exception as e:\n')
            f.write('    print(f"seccfg error: {e}")\n\n')

            # Step: vbmeta flags=3
            step_num += 1
            vbmeta_list = repr(vbmeta_parts)
            f.write(f'print("\\n=== STEP {step_num}/{total_steps}: PATCHING VBMETA (flags=3) ===")\n')
            f.write(f'vbmeta_parts = {vbmeta_list}\n')
            f.write('patched_vb = 0\n')
            f.write('for vb in vbmeta_parts:\n')
            f.write('    rd = os.path.join(tmpdir, vb + "_read.img")\n')
            f.write('    try:\n')
            f.write('        da.da_read(vb, "user", rd)\n')
            f.write('        with open(rd, "rb") as rf:\n')
            f.write('            vdata = bytearray(rf.read())\n')
            f.write('        if len(vdata) < 0x80:\n')
            f.write('            continue\n')
            f.write('        old = struct.unpack(">I", vdata[0x78:0x7C])[0]\n')
            f.write('        if old == 3:\n')
            f.write('            print(f"  {vb}: already flags=3")\n')
            f.write('            patched_vb += 1\n')
            f.write('            continue\n')
            f.write('        vdata[0x78:0x7C] = struct.pack(">I", 3)\n')
            f.write('        wd = os.path.join(tmpdir, vb + "_patched.img")\n')
            f.write('        with open(wd, "wb") as wf:\n')
            f.write('            wf.write(vdata)\n')
            f.write('        da.da_write("user", [wd], [vb])\n')
            f.write('        print(f"  {vb}: {old} -> 3 OK")\n')
            f.write('        patched_vb += 1\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {vb}: {e}")\n')
            f.write('print(f"Patched {patched_vb}/{len(vbmeta_parts)} vbmeta")\n\n')

            # Step: FRP (optional)
            step_num += 1
            if clear_frp:
                f.write(f'print("\\n=== STEP {step_num}/{total_steps}: CLEARING FRP ===")\n')
                f.write('try:\n')
                f.write('    rd = os.path.join(tmpdir, "frp_read.img")\n')
                f.write('    da.da_read("frp", "user", rd)\n')
                f.write('    size = os.path.getsize(rd)\n')
                f.write('    wd = os.path.join(tmpdir, "frp_zero.img")\n')
                f.write('    with open(wd, "wb") as wf:\n')
                f.write('        wf.write(b"\\x00" * size)\n')
                f.write('    da.da_write("user", [wd], ["frp"])\n')
                f.write('    print(f"FRP cleared ({size} bytes zeroed)")\n')
                f.write('except Exception as e:\n')
                f.write('    print(f"FRP error: {e}")\n\n')
            else:
                f.write(f'print("\\n=== STEP {step_num}/{total_steps}: FRP SKIP (not selected) ===")\n\n')

            # Step: Read vendor_boot
            step_num += 1
            f.write(f'print("\\n=== STEP {step_num}/{total_steps}: READING {partition} ===")\n')
            f.write(f'stock_file = r"{stock_file}"\n')
            f.write(f'ready_marker = r"{ready_marker}"\n')
            f.write('try:\n')
            f.write(f'    da.da_read("{partition}", "user", stock_file)\n')
            f.write('    if os.path.exists(stock_file):\n')
            f.write('        sz = os.path.getsize(stock_file)\n')
            f.write('        print(f"Read {sz:,} bytes")\n')
            f.write('        with open(ready_marker, "w") as mf:\n')
            f.write('            mf.write("READY")\n')
            f.write('        print("STOCK IMAGE READY - waiting for PC Magisk patch...")\n')
            f.write('    else:\n')
            f.write('        print("ERROR: read failed!")\n')
            f.write('        sys.exit(1)\n')
            f.write('except Exception as e:\n')
            f.write('    print(f"READ ERROR: {e}")\n')
            f.write('    sys.exit(1)\n\n')

            # Step: Wait for patched file (with progress feedback)
            step_num += 1
            progress_file = self._root_progress_file()
            f.write(f'print("\\n=== STEP {step_num}/{total_steps}: PC MAGISK PATCH ===")\n')
            f.write('print("PC is patching the boot image with Magisk now.")\n')
            f.write('print("DO NOT close this window! This takes 10-30 seconds.")\n')
            f.write('print("")\n')
            f.write(f'patched_marker = r"{patched_marker}"\n')
            f.write(f'patched_file = r"{patched_file}"\n')
            f.write(f'progress_file = r"{progress_file}"\n')
            f.write('waited = 0\n')
            f.write('progress_pos = 0\n')
            f.write('while waited < 300:\n')
            f.write('    if os.path.exists(patched_marker):\n')
            f.write('        print("\\nPatched image received!")\n')
            f.write('        break\n')
            # Read NEW lines from append-mode progress file
            f.write('    try:\n')
            f.write('        if os.path.exists(progress_file):\n')
            f.write('            with open(progress_file, "r", errors="ignore") as pf:\n')
            f.write('                pf.seek(progress_pos)\n')
            f.write('                new_data = pf.read()\n')
            f.write('                progress_pos = pf.tell()\n')
            f.write('            if new_data.strip():\n')
            f.write('                for pline in new_data.strip().splitlines():\n')
            f.write('                    pline = pline.strip()\n')
            f.write('                    if pline:\n')
            f.write('                        print(f"  [PC] {pline}")\n')
            f.write('    except Exception:\n')
            f.write('        pass\n')
            f.write('    time.sleep(1)\n')
            f.write('    waited += 1\n')
            f.write('    if waited % 30 == 0 and not os.path.exists(progress_file):\n')
            f.write('        print(f"  Still waiting for PC... ({waited}s)")\n')
            f.write('else:\n')
            f.write('    print("ERROR: Timed out waiting for patch!")\n')
            f.write('    sys.exit(1)\n\n')
            # Print any remaining progress lines
            f.write('try:\n')
            f.write('    if os.path.exists(progress_file):\n')
            f.write('        with open(progress_file, "r", errors="ignore") as pf:\n')
            f.write('            pf.seek(progress_pos)\n')
            f.write('            remaining = pf.read().strip()\n')
            f.write('        if remaining:\n')
            f.write('            for pline in remaining.splitlines():\n')
            f.write('                pline = pline.strip()\n')
            f.write('                if pline:\n')
            f.write('                    print(f"  [PC] {pline}")\n')
            f.write('except Exception:\n')
            f.write('    pass\n')
            # Clean up progress file
            f.write('try:\n')
            f.write('    os.unlink(progress_file)\n')
            f.write('except Exception:\n')
            f.write('    pass\n\n')

            # Step: Flash patched image
            step_num += 1
            targets_str = repr(flash_targets)
            f.write(f'print("\\n=== STEP {step_num}/{total_steps}: FLASHING PATCHED IMAGE ===")\n')
            f.write('with open(patched_file, "rb") as pf:\n')
            f.write('    patched_data = pf.read()\n')
            f.write('print(f"Patched image: {len(patched_data):,} bytes")\n')
            f.write(f'flash_targets = {targets_str}\n')
            f.write('flashed = 0\n')
            f.write('for slot in flash_targets:\n')
            f.write('    sz_file = os.path.join(tmpdir, slot + "_sz.img")\n')
            f.write('    try:\n')
            f.write('        da.da_read(slot, "user", sz_file)\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {slot}: {e}, SKIP")\n')
            f.write('        continue\n')
            f.write('    psz = os.path.getsize(sz_file)\n')
            f.write('    data = patched_data\n')
            f.write('    if len(data) < psz:\n')
            f.write('        data = data + b"\\x00" * (psz - len(data))\n')
            f.write('    elif len(data) > psz:\n')
            f.write('        data = data[:psz]\n')
            f.write('    wf = os.path.join(tmpdir, slot + "_flash.img")\n')
            f.write('    with open(wf, "wb") as f:\n')
            f.write('        f.write(data)\n')
            f.write('    try:\n')
            f.write('        da.da_write("user", [wf], [slot])\n')
            f.write('        print(f"  {slot}: FLASHED OK")\n')
            f.write('        flashed += 1\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {slot}: {e}")\n\n')
            f.write('print(f"Flashed {flashed}/{len(flash_targets)} slots")\n')
            f.write('print("\\n=== ALL DONE ===")\n')
            f.write('print("Bootloader unlocked + Magisk rooted!")\n')
            f.write('print("Reboot device to verify root.")\n')

    def unlock_and_root(
        self, partition: str, flash_targets: list,
        vbmeta_parts: list, clear_frp: bool = False,
        patch_callback=None,
        backup_partitions: list = None,
        backup_dir: str = None,
    ) -> bool:
        """ALL-IN-ONE single BROM session: backup + unlock + root.

        0. Backup partitions (optional)
        1. seccfg unlock
        2. vbmeta flags=3
        3. FRP clear (optional)
        4. Read vendor_boot -> PC Magisk patch -> flash back
        """
        if not self._mtk_path:
            self._log("mtkclient not found!", "ERROR")
            return False

        # Clean markers
        for fn in [self._root_ready_marker(), self._root_patched_marker(),
                    self._root_stock_file(), self._root_patched_file()]:
            try:
                os.unlink(fn)
            except OSError:
                pass

        self._log("=== ALL-IN-ONE (Single BROM Session) ===", "INFO")
        if backup_partitions:
            self._log(f"Will backup {len(backup_partitions)} partitions first", "INFO")

        script_path = os.path.join(self._mtk_path, "_tr_unlock_root.py")
        self._write_unlock_root_script(
            script_path, partition, flash_targets, vbmeta_parts, clear_frp,
            backup_partitions=backup_partitions, backup_dir=backup_dir,
        )

        bat = '@echo off\n'
        bat += f'cd /d "{self._mtk_path}"\n'
        bat += self._bat_header(
            "Unlock + Root",
            "seccfg + vbmeta + read + patch + flash",
            "Plug in device in BROM mode NOW!",
        )
        bat += f'"{self._python}" -u "{script_path}"\n'
        bat += self._bat_footer()

        # Launch CMD
        log_file = self._log_file()
        done_file = self._done_file()
        bat_file = self._bat_file()
        self._cleanup(log_file, done_file)
        with open(bat_file, 'w') as bf:
            bf.write(bat)

        try:
            subprocess.Popen(
                f'start "Tumeloroot - Unlock + Root" cmd /c "{bat_file}"',
                shell=True, cwd=self._mtk_path,
            )
            self._log("CMD window opened!", "INFO")
        except Exception as e:
            self._log(f"Launch error: {e}", "ERROR")
            return False

        # Poll for READY marker (unlock + vbmeta + read done)
        ready_marker = self._root_ready_marker()
        last_log_size = 0
        waited = 0
        while waited < 600:
            time.sleep(2)
            waited += 2

            # Forward log
            if os.path.isfile(log_file):
                try:
                    with open(log_file, 'r', errors='ignore') as lf:
                        content = lf.read()
                    if len(content) > last_log_size:
                        for line in content[last_log_size:].splitlines():
                            clean = ANSI_RE.sub('', line.strip())
                            if not clean:
                                continue
                            low = clean.lower()
                            if any(k in low for k in LOG_KEYWORDS):
                                if 'error' in low or 'fail' in low:
                                    self._log(clean, "ERROR")
                                elif any(k in low for k in SUCCESS_KEYWORDS):
                                    self._log(clean, "SUCCESS")
                                elif 'waiting' in low:
                                    self._log(clean, "WARNING")
                                else:
                                    self._log(clean, "INFO")
                        last_log_size = len(content)
                except Exception:
                    pass

            if os.path.isfile(ready_marker):
                self._log("Stock image ready for patching!", "SUCCESS")
                break
            if os.path.isfile(done_file):
                self._log("Script ended early", "ERROR")
                break
        else:
            self._log("Timed out waiting for device", "ERROR")
            return False

        # PC-side patch (progress file lets CMD window show what's happening)
        stock_file = self._root_stock_file()
        patched_file = self._root_patched_file()

        if not os.path.isfile(stock_file):
            self._log("Stock image missing!", "ERROR")
            self._write_progress(self._root_progress_file(), "ERROR: Stock image missing!")
            return False

        if patch_callback:
            self._log("Patching with Magisk on PC...", "INFO")
            # Clear progress file at start
            progress_file = self._root_progress_file()
            try:
                with open(progress_file, 'w', encoding='utf-8') as pf:
                    pf.write("Starting Magisk patch...\n")
            except Exception:
                pass
            ok = patch_callback(stock_file, patched_file)
            if not ok or not os.path.isfile(patched_file):
                self._log("Magisk patch FAILED!", "ERROR")
                # Read what the patcher logged for debugging
                try:
                    with open(progress_file, 'r', errors='ignore') as pf:
                        patch_log = pf.read().strip()
                    if patch_log:
                        self._log(f"Patch log:\n{patch_log}", "ERROR")
                        # Also append failure to progress so CMD shows it
                        self._write_progress(progress_file, "PATCH FAILED! See details above.")
                except Exception:
                    self._write_progress(progress_file, "PATCH FAILED!")
                return False
            mb = os.path.getsize(patched_file) / (1024 * 1024)
            self._log(f"Patched: {mb:.1f} MB", "SUCCESS")
            self._write_progress(progress_file, f"Patch complete! {mb:.1f} MB")

        # Signal script to flash
        with open(self._root_patched_marker(), 'w') as mf:
            mf.write("PATCHED")
        self._log("Signaled BROM to flash...", "INFO")

        # Wait for completion
        output = self._poll_and_wait(max_wait=600)
        self._cleanup(script_path, self._root_ready_marker(),
                       self._root_patched_marker(), self._root_progress_file(),
                       bat_file)

        success = "ALL DONE" in output
        if success:
            self._log("UNLOCK + ROOT COMPLETE!", "SUCCESS")
        else:
            self._log("May have failed - check CMD", "WARNING")
        return success

    def _write_root_all_script(
        self, script_path: str, partition: str,
        flash_targets: list, vbmeta_parts: list,
    ):
        """Write Python script: single BROM session root flow.

        1. Connect BROM
        2. Read vendor_boot_a -> save to stock file -> write READY marker
        3. Wait for PATCHED marker (GUI patches on PC)
        4. Read patched file -> flash to all slots
        5. Patch vbmeta flags=3 (safety net)
        """
        log_file = self._log_file()
        stock_file = self._root_stock_file()
        patched_file = self._root_patched_file()
        ready_marker = self._root_ready_marker()
        patched_marker = self._root_patched_marker()

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write('# -*- coding: utf-8 -*-\n')
            f.write('import struct, sys, os, logging, tempfile, time\n')
            f.write(f'os.chdir(r"{self._mtk_path}")\n')
            f.write(f'sys.path.insert(0, r"{self._mtk_path}")\n\n')
            f.write('from mtkclient.Library.mtk_class import Mtk\n')
            f.write('from mtkclient.Library.DA.mtk_da_handler import DaHandler\n')
            f.write('from mtkclient.config.mtk_config import MtkConfig\n')
            f.write('from mtkclient.Library.Partitions.gpt import GptSettings\n\n')
            # Tee
            f.write('class _Tee:\n')
            f.write('    def __init__(self, orig, logf):\n')
            f.write('        self.orig = orig\n')
            f.write('        self.logf = logf\n')
            f.write('    def write(self, data):\n')
            f.write('        self.orig.write(data)\n')
            f.write('        self.orig.flush()\n')
            f.write('        try:\n')
            f.write('            self.logf.write(data)\n')
            f.write('            self.logf.flush()\n')
            f.write('        except Exception:\n')
            f.write('            pass\n')
            f.write('    def flush(self):\n')
            f.write('        self.orig.flush()\n')
            f.write('    def __getattr__(self, name):\n')
            f.write('        return getattr(self.orig, name)\n\n')
            f.write(f'_lf = open(r"{log_file}", "w", encoding="utf-8", errors="replace")\n')
            f.write('sys.stdout = _Tee(sys.stdout, _lf)\n')
            f.write('sys.stderr = _Tee(sys.stderr, _lf)\n\n')
            # Connect with retry
            self._write_connect_block(f)
            f.write('tmpdir = tempfile.mkdtemp(prefix="tr_root_")\n\n')

            # Step 1: Read vendor_boot
            f.write(f'print("\\n=== STEP 1: READING {partition} FROM DEVICE ===")\n')
            f.write(f'stock_file = r"{stock_file}"\n')
            f.write(f'ready_marker = r"{ready_marker}"\n')
            f.write('try:\n')
            f.write(f'    da.da_read("{partition}", "user", stock_file)\n')
            f.write('    if os.path.exists(stock_file):\n')
            f.write('        size = os.path.getsize(stock_file)\n')
            f.write('        print(f"Read {size:,} bytes from device")\n')
            f.write('        # Signal GUI that stock image is ready for patching\n')
            f.write('        with open(ready_marker, "w") as mf:\n')
            f.write('            mf.write("READY")\n')
            f.write('        print("STOCK IMAGE READY - waiting for PC-side Magisk patch...")\n')
            f.write('    else:\n')
            f.write('        print("ERROR: Failed to read partition!")\n')
            f.write('        sys.exit(1)\n')
            f.write('except Exception as e:\n')
            f.write('    print(f"READ ERROR: {e}")\n')
            f.write('    sys.exit(1)\n\n')

            # Step 2: Wait for patched file
            f.write('print("\\n=== STEP 2: WAITING FOR MAGISK PATCH (PC-side) ===")\n')
            f.write('print("DO NOT close this window! Patching on PC...")\n')
            f.write(f'patched_marker = r"{patched_marker}"\n')
            f.write(f'patched_file = r"{patched_file}"\n')
            f.write('waited = 0\n')
            f.write('while waited < 300:  # 5 min max\n')
            f.write('    if os.path.exists(patched_marker):\n')
            f.write('        print("Patched image received!")\n')
            f.write('        break\n')
            f.write('    time.sleep(1)\n')
            f.write('    waited += 1\n')
            f.write('    if waited % 10 == 0:\n')
            f.write('        print(f"  Still waiting... ({waited}s)")\n')
            f.write('else:\n')
            f.write('    print("ERROR: Timed out waiting for patched image!")\n')
            f.write('    sys.exit(1)\n\n')
            f.write('if not os.path.exists(patched_file):\n')
            f.write('    print("ERROR: Patched file not found!")\n')
            f.write('    sys.exit(1)\n')
            f.write('psize = os.path.getsize(patched_file)\n')
            f.write('print(f"Patched image: {psize:,} bytes")\n\n')

            # Step 3: Flash patched image to all slots
            targets_str = repr(flash_targets)
            f.write('print("\\n=== STEP 3: FLASHING PATCHED IMAGE ===")\n')
            f.write('with open(patched_file, "rb") as pf:\n')
            f.write('    patched_data = pf.read()\n')
            f.write(f'flash_targets = {targets_str}\n')
            f.write('flashed = 0\n')
            f.write('for slot in flash_targets:\n')
            f.write('    print(f"  {slot}: reading partition size...")\n')
            f.write('    size_file = os.path.join(tmpdir, slot + "_size.img")\n')
            f.write('    try:\n')
            f.write('        da.da_read(slot, "user", size_file)\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {slot}: read error: {e}, SKIPPING!")\n')
            f.write('        continue\n')
            f.write('    part_size = os.path.getsize(size_file)\n')
            f.write('    data = patched_data\n')
            f.write('    if len(data) < part_size:\n')
            f.write('        data = data + b"\\x00" * (part_size - len(data))\n')
            f.write('    elif len(data) > part_size:\n')
            f.write('        data = data[:part_size]\n')
            f.write('    wfile = os.path.join(tmpdir, slot + "_flash.img")\n')
            f.write('    with open(wfile, "wb") as wf:\n')
            f.write('        wf.write(data)\n')
            f.write('    print(f"  {slot}: flashing {len(data):,} bytes...")\n')
            f.write('    try:\n')
            f.write('        da.da_write("user", [wfile], [slot])\n')
            f.write('        print(f"  {slot}: FLASHED OK")\n')
            f.write('        flashed += 1\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {slot}: FLASH ERROR: {e}")\n\n')
            f.write('print(f"Flashed {flashed}/{len(flash_targets)} slots")\n\n')

            # Step 4: Patch vbmeta (safety net - in case unlock didn't do it)
            vbmeta_str = repr(vbmeta_parts)
            f.write('print("\\n=== STEP 4: VERIFYING VBMETA FLAGS ===")\n')
            f.write(f'vbmeta_parts = {vbmeta_str}\n')
            f.write('for vb in vbmeta_parts:\n')
            f.write('    rd = os.path.join(tmpdir, vb + "_check.img")\n')
            f.write('    try:\n')
            f.write('        da.da_read(vb, "user", rd)\n')
            f.write('        with open(rd, "rb") as rf:\n')
            f.write('            vdata = bytearray(rf.read())\n')
            f.write('        if len(vdata) < 0x80:\n')
            f.write('            continue\n')
            f.write('        flags = struct.unpack(">I", vdata[0x78:0x7C])[0]\n')
            f.write('        if flags != 3:\n')
            f.write('            vdata[0x78:0x7C] = struct.pack(">I", 3)\n')
            f.write('            wd = os.path.join(tmpdir, vb + "_fix.img")\n')
            f.write('            with open(wd, "wb") as wf:\n')
            f.write('                wf.write(vdata)\n')
            f.write('            da.da_write("user", [wd], [vb])\n')
            f.write('            print(f"  {vb}: flags {flags} -> 3 FIXED")\n')
            f.write('        else:\n')
            f.write('            print(f"  {vb}: flags OK (3)")\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {vb}: {e}")\n\n')

            f.write('print("\\n=== ROOT COMPLETE ===")\n')
            f.write('print("Magisk-patched vendor_boot flashed to all slots!")\n')
            f.write('print("Reboot device to verify root.")\n')

    def root_and_flash(
        self, partition: str, flash_targets: list,
        vbmeta_parts: list, patch_callback=None,
    ) -> bool:
        """Single BROM session: read vendor_boot, wait for PC patch, flash back.

        Args:
            partition: Partition to read (e.g. "vendor_boot_a")
            flash_targets: Slots to flash patched image to
            vbmeta_parts: Vbmeta partitions to verify/fix
            patch_callback: Called when stock image is ready.
                            Signature: (stock_path, patched_path) -> bool
        """
        if not self._mtk_path:
            self._log("mtkclient not found!", "ERROR")
            return False

        # Clean markers
        for f in [self._root_ready_marker(), self._root_patched_marker(),
                   self._root_stock_file(), self._root_patched_file()]:
            try:
                os.unlink(f)
            except OSError:
                pass

        self._log("=== ROOT: Single BROM Session ===", "INFO")
        self._log("Read -> PC Patch -> Flash (no reconnect!)", "INFO")

        script_path = os.path.join(self._mtk_path, "_tr_root_all.py")
        self._write_root_all_script(
            script_path, partition, flash_targets, vbmeta_parts,
        )

        bat = '@echo off\n'
        bat += f'cd /d "{self._mtk_path}"\n'
        bat += self._bat_header(
            "Root - Single Session",
            "Read + Patch + Flash vendor_boot",
            "Plug in device in BROM mode NOW!",
        )
        bat += f'"{self._python}" -u "{script_path}"\n'
        bat += self._bat_footer()

        # Launch BAT (non-blocking, returns after CMD opens)
        log_file = self._log_file()
        done_file = self._done_file()
        bat_file = self._bat_file()

        self._cleanup(log_file, done_file)
        with open(bat_file, 'w') as bf:
            bf.write(bat)

        try:
            subprocess.Popen(
                f'start "Tumeloroot - Root" cmd /c "{bat_file}"',
                shell=True, cwd=self._mtk_path,
            )
            self._log("CMD window opened! Waiting for BROM connection...", "INFO")
        except Exception as e:
            self._log(f"Error launching: {e}", "ERROR")
            return False

        # Wait for READY marker (stock image read from device)
        self._log("Waiting for device to be read...", "WARNING")
        ready_marker = self._root_ready_marker()
        waited = 0
        while waited < 600:  # 10 min max for BROM connect + read
            time.sleep(2)
            waited += 2

            # Forward log lines
            if os.path.isfile(log_file):
                try:
                    with open(log_file, 'r', errors='ignore') as lf:
                        content = lf.read()
                    for line in content.splitlines():
                        clean = ANSI_RE.sub('', line.strip())
                        if clean:
                            low = clean.lower()
                            if any(k in low for k in LOG_KEYWORDS):
                                if 'error' in low or 'fail' in low:
                                    self._log(clean, "ERROR")
                                elif any(k in low for k in SUCCESS_KEYWORDS):
                                    self._log(clean, "SUCCESS")
                                else:
                                    self._log(clean, "INFO")
                except Exception:
                    pass

            if os.path.isfile(ready_marker):
                self._log("Stock image read from device!", "SUCCESS")
                break

            if os.path.isfile(done_file):
                self._log("Script ended before stock image was ready", "ERROR")
                return False
        else:
            self._log("Timed out waiting for stock image", "ERROR")
            return False

        # Call PC-side patch
        stock_file = self._root_stock_file()
        patched_file = self._root_patched_file()

        if not os.path.isfile(stock_file):
            self._log("Stock image file missing!", "ERROR")
            return False

        size_mb = os.path.getsize(stock_file) / (1024 * 1024)
        self._log(f"Stock image: {size_mb:.1f} MB", "INFO")

        if patch_callback:
            self._log("Patching with Magisk on PC...", "INFO")
            patch_ok = patch_callback(stock_file, patched_file)
            if not patch_ok or not os.path.isfile(patched_file):
                self._log("PC-side Magisk patch failed!", "ERROR")
                return False
            patched_mb = os.path.getsize(patched_file) / (1024 * 1024)
            self._log(f"Patched image: {patched_mb:.1f} MB", "SUCCESS")

        # Signal script to continue flashing
        patched_marker = self._root_patched_marker()
        with open(patched_marker, 'w') as mf:
            mf.write("PATCHED")
        self._log("Signaled BROM script to flash...", "INFO")

        # Wait for completion
        output = self._poll_and_wait(max_wait=600)

        self._cleanup(script_path, ready_marker, patched_marker, bat_file)

        success = "ROOT COMPLETE" in output
        if success:
            self._log("ROOT SUCCESSFUL! Reboot device to verify.", "SUCCESS")
        else:
            self._log("Root may have failed - check CMD window", "WARNING")

        return success

    # ── Unlock (ONE BROM connection!) ──────────────────────────

    def unlock_bootloader(self, clear_frp: bool = False) -> bool:
        """Unlock bootloader via seccfg + disable dm-verity via vbmeta flags.

        Single Python script, ONE BROM connection:
          1. seccfg("unlock") -- unlock bootloader
          2. Read each vbmeta FROM DEVICE, patch flags=3, write back
          3. (optional) Zero FRP partition to skip Google account after reset

        This ensures the device can boot after unlock. Without vbmeta flags=3,
        the unlocked bootloader fails dm-verity verification and won't boot.
        No backup files are used -- vbmeta is read live from device.
        """
        if not self._mtk_path:
            self._log("mtkclient not found!", "ERROR")
            return False

        self._log("=== BOOTLOADER UNLOCK ===", "INFO")
        self._log("seccfg unlock + vbmeta flags=3 (dm-verity disable)", "INFO")
        if clear_frp:
            self._log("FRP clear enabled - Google account lock will be removed", "INFO")

        script_path = os.path.join(self._mtk_path, "_tr_unlock_all.py")

        self._write_unlock_script(script_path, clear_frp=clear_frp)

        bat = '@echo off\n'
        bat += f'cd /d "{self._mtk_path}"\n'
        bat += self._bat_header(
            "Bootloader Unlock",
            "seccfg unlock + vbmeta dm-verity disable",
            "Plug in device in BROM mode NOW!",
        )
        bat += f'"{self._python}" -u "{script_path}"\n'
        bat += self._bat_footer()

        output = self._launch_bat(bat, "Bootloader Unlock")

        self._cleanup(script_path)

        unlocked = any(k in output for k in [
            "Successfully wrote seccfg", "already unlocked",
            "UNLOCK COMPLETE",
        ])

        if unlocked:
            self._log("Bootloader unlocked + vbmeta patched!", "SUCCESS")
            self._log("Orange state at boot is NORMAL — device will boot.", "INFO")

        self._log("=== UNLOCK COMPLETE ===", "SUCCESS")
        return unlocked or "UNLOCK COMPLETE" in output

    # ── Backup all partitions (single BROM session) ────────

    def _backup_done_marker(self) -> str:
        return os.path.join(self._mtk_path, "_tr_backup_done.marker")

    def backup_all(self, partition_names: list, backup_dir: str) -> bool:
        """Read ALL partitions in a single BROM session."""
        if not self._mtk_path:
            self._log("mtkclient not found!", "ERROR")
            return False

        os.makedirs(backup_dir, exist_ok=True)
        marker = self._backup_done_marker()
        try:
            os.unlink(marker)
        except OSError:
            pass

        self._log(f"=== BACKUP {len(partition_names)} PARTITIONS ===", "INFO")

        script_path = os.path.join(self._mtk_path, "_tr_backup.py")
        self._write_backup_script(script_path, partition_names, backup_dir)

        bat = '@echo off\n'
        bat += f'cd /d "{self._mtk_path}"\n'
        bat += self._bat_header(
            "Backup Partitions",
            f"Reading {len(partition_names)} partitions in one session",
            "Plug in device in BROM mode NOW!",
        )
        bat += f'"{self._python}" -u "{script_path}"\n'
        bat += self._bat_footer()

        log_file = self._log_file()
        done_file = self._done_file()
        bat_file = self._bat_file()
        self._cleanup(log_file, done_file)
        with open(bat_file, 'w') as bf:
            bf.write(bat)

        try:
            subprocess.Popen(
                f'start "Tumeloroot - Backup" cmd /c "{bat_file}"',
                shell=True, cwd=self._mtk_path,
            )
            self._log("CMD window opened!", "INFO")
        except Exception as e:
            self._log(f"Launch error: {e}", "ERROR")
            return False

        output = self._poll_and_wait(max_wait=900)
        self._cleanup(script_path, bat_file)

        success = os.path.isfile(marker)
        if success:
            self._log("ALL PARTITIONS BACKED UP!", "SUCCESS")
            try:
                os.unlink(marker)
            except OSError:
                pass
        else:
            self._log("Backup may have failed - check CMD", "WARNING")

        return success

    def _write_backup_script(self, script_path: str,
                              partition_names: list, backup_dir: str):
        """Write Python script: read all partitions in single BROM session."""
        log_file = self._log_file()
        marker = self._backup_done_marker()

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write('# -*- coding: utf-8 -*-\n')
            f.write('import sys, os, logging\n')
            f.write(f'os.chdir(r"{self._mtk_path}")\n')
            f.write(f'sys.path.insert(0, r"{self._mtk_path}")\n\n')
            f.write('from mtkclient.Library.mtk_class import Mtk\n')
            f.write('from mtkclient.Library.DA.mtk_da_handler import DaHandler\n')
            f.write('from mtkclient.config.mtk_config import MtkConfig\n')
            f.write('from mtkclient.Library.Partitions.gpt import GptSettings\n\n')
            # Tee
            f.write('class _Tee:\n')
            f.write('    def __init__(self, orig, logf):\n')
            f.write('        self.orig = orig\n')
            f.write('        self.logf = logf\n')
            f.write('    def write(self, data):\n')
            f.write('        self.orig.write(data)\n')
            f.write('        self.orig.flush()\n')
            f.write('        try:\n')
            f.write('            self.logf.write(data)\n')
            f.write('            self.logf.flush()\n')
            f.write('        except Exception:\n')
            f.write('            pass\n')
            f.write('    def flush(self):\n')
            f.write('        self.orig.flush()\n')
            f.write('    def __getattr__(self, name):\n')
            f.write('        return getattr(self.orig, name)\n\n')
            f.write(f'_lf = open(r"{log_file}", "w", encoding="utf-8", errors="replace")\n')
            f.write('sys.stdout = _Tee(sys.stdout, _lf)\n')
            f.write('sys.stderr = _Tee(sys.stderr, _lf)\n\n')
            # Connect
            self._write_connect_block(f)
            # Read partitions
            parts_repr = repr(partition_names)
            backup_dir_escaped = backup_dir.replace('\\', '\\\\')
            f.write(f'partitions = {parts_repr}\n')
            f.write(f'backup_dir = r"{backup_dir}"\n')
            f.write('os.makedirs(backup_dir, exist_ok=True)\n')
            f.write('total = len(partitions)\n')
            f.write('ok_count = 0\n\n')
            f.write('for i, part in enumerate(partitions):\n')
            f.write('    print(f"\\n=== [{i+1}/{total}] Reading {part} ===")\n')
            f.write('    out_path = os.path.join(backup_dir, part + ".img")\n')
            f.write('    try:\n')
            f.write('        da.da_read(part, "user", out_path)\n')
            f.write('        if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:\n')
            f.write('            sz = os.path.getsize(out_path)\n')
            f.write('            print(f"  {part}: {sz:,} bytes OK")\n')
            f.write('            ok_count += 1\n')
            f.write('        else:\n')
            f.write('            print(f"  {part}: FAILED (empty)")\n')
            f.write('    except Exception as e:\n')
            f.write('        print(f"  {part}: ERROR - {e}")\n\n')
            f.write('print(f"\\n=== BACKUP DONE: {ok_count}/{total} partitions ===")\n')
            f.write('if ok_count == total:\n')
            f.write(f'    with open(r"{marker}", "w") as mf:\n')
            f.write('        mf.write("DONE")\n')
            f.write('    print("ALL PARTITIONS BACKED UP!")\n')
            f.write('else:\n')
            f.write('    print(f"WARNING: {total - ok_count} partitions failed")\n')
            f.write(f'    with open(r"{marker}", "w") as mf:\n')
            f.write('        mf.write("PARTIAL")\n')

    # ── Partition utilities ───────────────────────────────────

    def read_partition(self, name: str, output_file: str) -> bool:
        fname = os.path.basename(output_file)
        ok, output = self.run_command(
            ["r", name, fname],
            wait_msg=f"Reading {name}...",
            title=f"Read {name}",
        )
        src = os.path.join(self._mtk_path, fname)
        if os.path.isfile(src) and os.path.getsize(src) > 0:
            if src != output_file:
                shutil.move(src, output_file)
            return True
        return False

    def write_partition(self, name: str, input_file: str) -> bool:
        fname = os.path.basename(input_file)
        dst = os.path.join(self._mtk_path, fname)
        if input_file != dst:
            shutil.copy2(input_file, dst)
        ok, output = self.run_command(
            ["w", name, fname],
            wait_msg=f"Writing {name}...",
            title=f"Write {name}",
        )
        try:
            if dst != input_file:
                os.unlink(dst)
        except OSError:
            pass
        return "Wrote" in output

    def print_gpt(self) -> tuple[bool, str]:
        return self.run_command(
            ["printgpt"],
            wait_msg="Plug in device in BROM mode!",
            title="Read GPT",
        )
