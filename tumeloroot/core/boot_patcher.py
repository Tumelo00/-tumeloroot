"""Boot Image Patcher - uses Magisk's own magiskboot via WSL.

Extracts magiskboot (x86_64) from the Magisk APK, then runs it through
WSL to unpack, patch, and repack vendor_boot images. This is the same
tool chain Magisk itself uses, so results are reliable.

Target binaries (arm64) go into the ramdisk; host tool (x86_64) runs in WSL.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import traceback
import zipfile
from typing import Optional


def _win_to_wsl(path: str) -> str:
    """Convert Windows path to WSL path: C:\\foo\\bar -> /mnt/c/foo/bar"""
    path = path.replace('\\', '/')
    if len(path) >= 2 and path[1] == ':':
        drive = path[0].lower()
        return f'/mnt/{drive}{path[2:]}'
    return path


def _run_wsl(cmd: str, cwd: str, log_cb=None, timeout: int = 120) -> tuple[int, str]:
    """Run a command in WSL via a temp script file to avoid quoting issues."""
    wsl_cwd = _win_to_wsl(cwd)
    if log_cb:
        # Show short version in log
        short = cmd if len(cmd) < 80 else cmd[:77] + "..."
        log_cb(f"[WSL] {short}")
    try:
        # Write command to a temp .sh file to avoid nested quote hell
        script_path = os.path.join(cwd, '_wsl_cmd.sh')
        with open(script_path, 'w', newline='\n') as sf:
            sf.write('#!/bin/bash\n')
            sf.write(f'cd "{wsl_cwd}"\n')
            sf.write(f'{cmd}\n')
        wsl_script = _win_to_wsl(script_path)
        full_cmd = f'wsl bash "{wsl_script}"'

        result = subprocess.run(
            full_cmd, shell=True, capture_output=True,
            text=True, timeout=timeout, errors='replace',
        )
        output = (result.stdout + result.stderr).strip()
        if log_cb and output:
            for line in output.splitlines()[:20]:
                log_cb(f"  {line}")

        # Cleanup script
        try:
            os.unlink(script_path)
        except OSError:
            pass

        return result.returncode, output
    except subprocess.TimeoutExpired:
        if log_cb:
            log_cb("WSL command timed out!")
        return -1, "timeout"
    except Exception as e:
        if log_cb:
            log_cb(f"WSL error: {e}")
            log_cb(traceback.format_exc())
        return -1, str(e)


def _extract_magisk_files(apk_path: str, work_dir: str, log_cb=None) -> bool:
    """Extract required files from Magisk APK into work_dir."""
    # Host tool (runs in WSL x86_64)
    host_files = {
        'lib/x86_64/libmagiskboot.so': 'magiskboot',
    }
    # Target binaries (go into the device ramdisk - arm64)
    target_files = {
        'lib/arm64-v8a/libmagiskinit.so': 'magiskinit',
        'lib/arm64-v8a/libmagisk.so': 'magisk',
        'lib/arm64-v8a/libinit-ld.so': 'init-ld',
        'assets/stub.apk': 'stub.apk',
    }

    all_files = {**host_files, **target_files}

    try:
        with zipfile.ZipFile(apk_path) as zf:
            for zpath, name in all_files.items():
                try:
                    data = zf.read(zpath)
                    out = os.path.join(work_dir, name)
                    with open(out, 'wb') as f:
                        f.write(data)
                    if log_cb:
                        log_cb(f"  Extracted {name} ({len(data):,} bytes)")
                except KeyError:
                    if log_cb:
                        log_cb(f"  WARNING: {zpath} not found in APK")
                    if name == 'magiskboot' or name == 'magiskinit':
                        return False
    except Exception as e:
        if log_cb:
            log_cb(f"APK extraction failed: {e}")
            log_cb(traceback.format_exc())
        return False

    return True


def patch_boot_image(
    image_path: str,
    output_path: str,
    magisk_apk: str,
    log_cb=None,
) -> bool:
    """Patch a vendor_boot image with Magisk using magiskboot via WSL.

    Args:
        image_path:  Path to stock vendor_boot read from device.
        output_path: Where to write the Magisk-patched image.
        magisk_apk:  Path to Magisk APK file.
        log_cb:      Optional callback ``(msg: str) -> None``.

    Returns:
        True on success.
    """
    def _log(m: str):
        if log_cb:
            log_cb(m)

    try:
        # Verify WSL
        _log("Checking WSL availability...")
        ret, out = _run_wsl('echo OK', os.environ.get('TEMP', '.'))
        if ret != 0 or 'OK' not in out:
            _log("ERROR: WSL is not available! Install WSL to patch boot images.")
            _log(f"WSL check returned: ret={ret}, output='{out}'")
            return False
        _log("WSL is available.")

        _log(f"Stock image: {image_path}")
        if not os.path.isfile(image_path):
            _log(f"ERROR: Stock image not found at {image_path}")
            return False

        img_size = os.path.getsize(image_path)
        _log(f"Image size: {img_size:,} bytes")

        sha1 = hashlib.sha1(open(image_path, 'rb').read()).hexdigest()
        _log(f"SHA1: {sha1}")

        _log(f"Magisk APK: {magisk_apk}")
        if not os.path.isfile(magisk_apk):
            _log(f"ERROR: Magisk APK not found at {magisk_apk}")
            return False

        # Create work directory
        work_dir = tempfile.mkdtemp(prefix='tumeloroot_patch_')
        _log(f"Work dir: {work_dir}")

        try:
            # 1. Extract Magisk files from APK
            _log("Step 1: Extracting Magisk files from APK...")
            if not _extract_magisk_files(magisk_apk, work_dir, _log):
                _log("ERROR: Failed to extract Magisk files from APK!")
                return False
            _log("APK extraction complete.")

            # 2. Copy stock image to work dir
            _log("Step 2: Copying stock image to work dir...")
            stock_name = 'vendor_boot.img'
            stock_copy = os.path.join(work_dir, stock_name)
            shutil.copy2(image_path, stock_copy)
            _log(f"Copied to {stock_copy}")

            # List work dir contents
            _log("Work dir contents:")
            for fn in os.listdir(work_dir):
                fpath = os.path.join(work_dir, fn)
                fsize = os.path.getsize(fpath) if os.path.isfile(fpath) else 0
                _log(f"  {fn}: {fsize:,} bytes")

            # 3. Make magiskboot executable and unpack
            _log("Step 3: Unpacking vendor_boot with magiskboot...")
            ret, out = _run_wsl('chmod +x magiskboot', work_dir, _log)
            if ret != 0:
                _log(f"WARNING: chmod failed (ret={ret}), trying anyway...")

            ret, out = _run_wsl(f'./magiskboot unpack {stock_name}', work_dir, _log)
            if ret not in (0, 3):
                # 3 = vendor boot detected (expected)
                _log(f"ERROR: magiskboot unpack failed (exit code {ret})")
                _log(f"Output: {out}")
                return False
            if ret == 3:
                _log("Vendor boot image detected (expected)")
            _log("Unpack complete.")

            # List work dir after unpack
            _log("Work dir after unpack:")
            for fn in os.listdir(work_dir):
                fpath = os.path.join(work_dir, fn)
                if os.path.isdir(fpath):
                    _log(f"  {fn}/ (directory)")
                    for sub in os.listdir(fpath):
                        subpath = os.path.join(fpath, sub)
                        subsize = os.path.getsize(subpath) if os.path.isfile(subpath) else 0
                        _log(f"    {sub}: {subsize:,} bytes")
                else:
                    fsize = os.path.getsize(fpath)
                    _log(f"  {fn}: {fsize:,} bytes")

            # 4. Find ramdisk
            _log("Step 4: Finding ramdisk...")
            ramdisk = None
            for path in ['ramdisk.cpio', 'vendor_ramdisk/init_boot.cpio',
                         'vendor_ramdisk/ramdisk.cpio']:
                check_path = os.path.join(work_dir, path.replace('/', os.sep))
                if os.path.isfile(check_path):
                    ramdisk = path
                    break

            if not ramdisk:
                _log("ERROR: No ramdisk found after unpack!")
                # List what was unpacked
                ret, out = _run_wsl('find . -type f | head -30', work_dir, _log)
                return False

            _log(f"Ramdisk found: {ramdisk}")

            # 5. Backup original ramdisk
            _log("Step 5: Backing up original ramdisk...")
            _run_wsl(f'cp {ramdisk} ramdisk.cpio.orig', work_dir, _log)

            # 6. Compress target binaries with xz (what Magisk expects)
            # Output names match Magisk boot_patch.sh convention:
            #   magisk -> magisk.xz, stub.apk -> stub.xz, init-ld -> init-ld.xz
            _log("Step 6: Compressing target binaries with xz...")
            compress_map = {
                'magisk': 'magisk.xz',
                'stub.apk': 'stub.xz',      # NOTE: output is stub.xz, NOT stub.apk.xz
                'init-ld': 'init-ld.xz',
            }
            for src_name, xz_name in compress_map.items():
                src = os.path.join(work_dir, src_name)
                if os.path.isfile(src):
                    ret, out = _run_wsl(
                        f'./magiskboot compress=xz {src_name} {xz_name}',
                        work_dir, _log,
                    )
                    if ret != 0:
                        _log(f"WARNING: Failed to compress {src_name} -> {xz_name} (ret={ret})")
                        _log(f"Output: {out}")
                    else:
                        # Verify .xz file was created
                        xz_path = os.path.join(work_dir, xz_name)
                        if os.path.isfile(xz_path):
                            xz_size = os.path.getsize(xz_path)
                            _log(f"  {xz_name}: {xz_size:,} bytes OK")
                        else:
                            _log(f"  WARNING: {xz_name} not created!")
                else:
                    _log(f"  {src_name}: not found, skipping")

            # Check all required xz files exist
            required_xz = ['magisk.xz', 'stub.xz', 'init-ld.xz']
            for rxz in required_xz:
                rxz_path = os.path.join(work_dir, rxz)
                if not os.path.isfile(rxz_path):
                    _log(f"ERROR: Required file {rxz} not found after compression!")
                    _log("Cannot proceed without all compressed binaries.")
                    return False

            # 7. Create Magisk config
            _log("Step 7: Creating Magisk config...")
            config_content = (
                f"KEEPVERITY=false\n"
                f"KEEPFORCEENCRYPT=true\n"
                f"RECOVERYMODE=false\n"
                f"VENDORBOOT=true\n"
                f"SHA1={sha1}\n"
            )
            config_path = os.path.join(work_dir, 'config')
            with open(config_path, 'w', newline='\n') as f:
                f.write(config_content)
            _log(f"Config written: {config_content.strip()}")

            # 8. Patch ramdisk with magiskboot cpio
            _log("Step 8: Patching ramdisk with Magisk...")
            cpio_cmd = (
                f'./magiskboot cpio {ramdisk} '
                f'"add 0750 init magiskinit" '
                f'"mkdir 0750 overlay.d" '
                f'"mkdir 0750 overlay.d/sbin" '
                f'"add 0644 overlay.d/sbin/magisk.xz magisk.xz" '
                f'"add 0644 overlay.d/sbin/stub.xz stub.xz" '
                f'"add 0644 overlay.d/sbin/init-ld.xz init-ld.xz" '
                f'"patch" '
                f'"backup ramdisk.cpio.orig" '
                f'"mkdir 000 .backup" '
                f'"add 000 .backup/.magisk config"'
            )
            ret, out = _run_wsl(cpio_cmd, work_dir, _log)
            if ret != 0:
                _log(f"ERROR: ramdisk patch failed! (exit code {ret})")
                _log(f"Full output: {out}")
                return False
            _log("Ramdisk patched successfully.")

            # 9. Repack
            _log("Step 9: Repacking vendor_boot image...")
            ret, out = _run_wsl(
                f'./magiskboot repack {stock_name} patched.img',
                work_dir, _log,
            )
            if ret != 0:
                _log(f"ERROR: repack failed! (exit code {ret})")
                _log(f"Full output: {out}")
                return False
            _log("Repack complete.")

            # 10. Copy patched image to output
            _log("Step 10: Saving patched image...")
            patched_path = os.path.join(work_dir, 'patched.img')
            if not os.path.isfile(patched_path):
                _log("ERROR: patched.img not created!")
                _log("Listing work dir:")
                for fn in os.listdir(work_dir):
                    _log(f"  {fn}")
                return False

            patched_size = os.path.getsize(patched_path)
            _log(f"Patched image: {patched_size:,} bytes")

            # Atomic write
            tmp = output_path + ".tmp"
            shutil.copy2(patched_path, tmp)
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(tmp, output_path)
            _log(f"Saved: {output_path}")
            _log("PATCH COMPLETE!")

            return True

        finally:
            # Cleanup work dir
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass

    except Exception as e:
        _log(f"PATCH FAILED: {e}")
        _log(traceback.format_exc())
        return False
