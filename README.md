# Tumeloroot

**MediaTek device bootloader unlock and root tool for educational and research purposes.**

Tumeloroot automates the entire process of unlocking the bootloader and rooting MediaTek-based Android devices. It uses mtkclient (BROM exploit) and Magisk in a single session - connect your device, select your model, and follow the wizard.

## Features

- **Single BROM Session** - Backup, unlock, patch, and flash all in one connection
- **Automatic Backup** - Backs up all critical partitions before any changes
- **Magisk Root** - Patches vendor_boot with Magisk using magiskboot via WSL
- **A/B Slot Support** - Flashes patched image to both slots for reliability
- **dm-verity Disable** - Patches all vbmeta partitions (flags=3) automatically
- **FRP Bypass** - Optional Factory Reset Protection clearing
- **Expandable** - Add new devices with simple YAML profile files
- **Dark Themed GUI** - Modern PySide6 wizard interface with real-time progress

## Verified Devices

| Device | Codename | Chipset | Android | Ramdisk In | Status |
|--------|----------|---------|---------|------------|--------|
| Lenovo Tab K11 | TB330XUP | MT6768/MT6769 (Helio P65/G85) | 15 | vendor_boot | Verified |

## Requirements

- Windows 10/11 with WSL (Windows Subsystem for Linux) installed
- Python 3.9+ (for running from source)
- USB cable (data transfer capable)
- [mtkclient](https://github.com/bkerler/mtkclient) installed and accessible
- UsbDk driver (for USB communication)
- [Magisk APK](https://github.com/topjohnwu/Magisk/releases) in Downloads folder or assets/magisk/
- ADB (Android Debug Bridge) for root verification

## How It Works

Everything happens in a **single BROM connection**:

1. **Device enters BROM mode** - Power off > Hold Vol Up + Vol Down > Plug USB
2. **Backup** - Reads 7 critical partitions (seccfg, boot_a/b, vendor_boot_a/b, vbmeta_a/b)
3. **Unlock** - Modifies seccfg to unlock the bootloader
4. **dm-verity** - Patches all 6 vbmeta partitions with flags=3
5. **FRP** - Optionally clears Factory Reset Protection
6. **Read** - Dumps vendor_boot_a (64 MB) from device
7. **Magisk Patch** - Uses magiskboot (extracted from Magisk APK) via WSL to patch the image
8. **Flash** - Writes patched vendor_boot to both A and B slots

After reboot, install the Magisk app and select "Install to inactive slot" if prompted.

## Installation

### Pre-built EXE
Download `Tumeloroot.exe` from the releases page and run it directly.

### From Source
```bash
git clone https://github.com/Tumelo00/-tumeloroot.git
cd tumeloroot
pip install -e .
python -m tumeloroot
```

## Manual Root Guide for Linux Users

If you prefer to root manually without the Tumeloroot GUI, or you are on a native Linux system, follow the steps below. This guide uses **mtkclient** for bootloader unlocking and partition operations via BROM exploit — no fastboot required for the critical steps.

> **Why vendor_boot?** This device uses Android 15 with GKI (Generic Kernel Image). On GKI devices, the ramdisk lives in `vendor_boot`, not `boot`. Magisk must patch `vendor_boot`.

> **A/B Slots:** This device has two slots (`_a` and `_b`). We flash the patched image to both slots for reliability.

---

### Step 1 — Install ADB and mtkclient

Install ADB (for communicating with the tablet while Android is running) and mtkclient (for BROM-level operations):

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y adb python3 python3-pip libusb-1.0-0

# Arch Linux
sudo pacman -S android-tools python python-pip libusb

# Fedora
sudo dnf install -y android-tools python3 python3-pip libusb
```

Install mtkclient:
```bash
pip3 install mtkclient
```

Set up USB permissions so both ADB and mtkclient can access the device without `sudo`:
```bash
sudo tee /etc/udev/rules.d/51-android.rules <<'EOF'
# Lenovo (ADB)
SUBSYSTEM=="usb", ATTR{idVendor}=="17ef", MODE="0666", GROUP="plugdev"
# MediaTek BROM / Preloader (mtkclient)
SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev $USER
```

> **Log out and back in** for the group change to take effect.

Verify the installations:
```bash
adb version
python3 -m mtk --help
```

Create a working directory for all files:
```bash
mkdir -p ~/lenovo_root && cd ~/lenovo_root
```

Download the latest Magisk APK from [GitHub releases](https://github.com/topjohnwu/Magisk/releases) and save it to `~/lenovo_root/Magisk.apk`.

---

### Step 2 — Enable USB Debugging and Authorize ADB

On the **tablet**:

1. Go to **Settings > About Tablet**, tap **Build Number** 7 times
   → "You are now a developer!" message appears
2. Go to **Settings > Developer Options**, enable:
   - **USB Debugging** → ON
   - **OEM Unlocking** → ON
3. Connect the tablet to your computer via USB-C cable
4. A dialog appears on the tablet: **"Allow USB debugging?"**
   → Check **"Always allow from this computer"** → tap **Allow**

Verify the connection from your terminal:
```bash
adb devices
```

Expected output:
```
List of devices attached
XXXXXXXXX    device
```

If it says `unauthorized`, check the tablet for the permission dialog and approve it.

Note the active slot (you will need this later):
```bash
adb shell getprop ro.boot.slot_suffix
```

This returns `_a` or `_b`. Write it down.

---

### Step 3 — Unlock Bootloader via BROM (mtkclient)

> **WARNING: Unlocking the bootloader will factory reset the device. All data will be erased.**

Power off the tablet completely. Then enter BROM mode:

1. **Hold Vol Up + Vol Down** buttons on the tablet
2. **While holding both buttons**, plug the USB cable into the tablet
3. Keep holding until mtkclient detects the device

Run the unlock command:
```bash
python3 -m mtk e seccfg
```

Expected output (last lines):
```
Erasing seccfg ...
Done.
```

The bootloader is now unlocked. The device will factory reset on the next boot.

---

### Step 4 — Extract vendor_boot via BROM (mtkclient)

While still in BROM mode (or re-enter: power off → hold Vol Up + Vol Down → plug USB):

```bash
python3 -m mtk r vendor_boot_a ~/lenovo_root/vendor_boot_a.img
```

Re-enter BROM mode, then extract the second slot as backup:
```bash
python3 -m mtk r vendor_boot_b ~/lenovo_root/vendor_boot_b.img
```

Verify the files:
```bash
ls -lh ~/lenovo_root/vendor_boot_*.img
```

Both files should be approximately 64 MB. If either is 0 bytes, the extraction failed — retry.

Save backup copies:
```bash
cp ~/lenovo_root/vendor_boot_a.img ~/lenovo_root/vendor_boot_a_BACKUP.img
cp ~/lenovo_root/vendor_boot_b.img ~/lenovo_root/vendor_boot_b_BACKUP.img
```

> **Keep these backups safe.** You will need them to restore stock if something goes wrong.

---

### Step 5 — First Boot After Unlock + Re-enable ADB

Reboot the tablet by disconnecting USB and holding the power button. The device will factory reset and show the initial setup wizard.

1. Complete the initial setup (WiFi, Google account, etc.)
2. **Repeat Step 2**: enable Developer Options, USB Debugging, and authorize ADB
3. Reconnect USB and verify:

```bash
adb devices
# Should show: XXXXXXXXX    device
```

---

### Step 6 — Install Magisk and Patch vendor_boot

Install the Magisk app on the tablet and push the extracted vendor_boot image:
```bash
adb install ~/lenovo_root/Magisk.apk
adb push ~/lenovo_root/vendor_boot_a.img /sdcard/Download/vendor_boot.img
```

Now on the **tablet**:

1. Open the **Magisk** app
2. Tap **Install** (next to "Magisk" on the home screen)
3. Select **"Select and Patch a File"**
4. Navigate to **Downloads** folder
5. Select **vendor_boot.img**
6. Wait until you see **"All done!"**

---

### Step 7 — Pull the Patched Image to Computer

Find and pull the patched file:
```bash
adb shell ls /sdcard/Download/magisk_patched*
```

This shows something like `magisk_patched-28100_XXXXX.img`. Pull it:
```bash
adb pull /sdcard/Download/magisk_patched-XXXXX.img ~/lenovo_root/magisk_patched_vendor_boot.img
```

> Replace `XXXXX` with the actual number from the output above.

Verify the file:
```bash
ls -lh ~/lenovo_root/magisk_patched_vendor_boot.img
```

Should be approximately the same size as the original vendor_boot (~64 MB).

---

### Step 8 — Flash Patched Image via BROM (mtkclient)

Power off the tablet. Enter BROM mode (hold Vol Up + Vol Down → plug USB).

Flash the patched image to **both slots** for reliability:
```bash
python3 -m mtk w vendor_boot_a ~/lenovo_root/magisk_patched_vendor_boot.img
```

Re-enter BROM mode, then flash the second slot:
```bash
python3 -m mtk w vendor_boot_b ~/lenovo_root/magisk_patched_vendor_boot.img
```

---

### Step 9 — Reboot and Verify Root

Disconnect USB, power on the tablet normally. Wait for it to fully boot.

Reconnect USB and test root access:
```bash
adb shell su -c 'id'
```

> A Magisk superuser permission dialog will appear on the tablet — tap **Allow**.

Expected output:
```
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

If you see `uid=0(root)` — **root is successful!**

Verify Magisk version:
```bash
adb shell su -c 'magisk -v'
adb shell su -c 'magisk -V'
```

---

### Restoring Stock (Unroot)

If you need to remove root or fix a boot issue, flash the original backups via BROM.

Power off the tablet. Enter BROM mode (Vol Up + Vol Down → plug USB):
```bash
python3 -m mtk w vendor_boot_a ~/lenovo_root/vendor_boot_a_BACKUP.img
```

Re-enter BROM mode:
```bash
python3 -m mtk w vendor_boot_b ~/lenovo_root/vendor_boot_b_BACKUP.img
```

Reboot — the device will boot with stock vendor_boot, no root.

---

### Quick Reference — Full Command Sequence

```bash
# Step 1: Install tools
sudo apt update && sudo apt install -y adb python3 python3-pip libusb-1.0-0
pip3 install mtkclient

# Step 2: Verify ADB connection
adb devices
adb shell getprop ro.boot.slot_suffix    # note: _a or _b

# Step 3: Unlock bootloader (BROM — power off, Vol Up+Down, plug USB)
python3 -m mtk e seccfg

# Step 4: Extract vendor_boot (re-enter BROM for each)
python3 -m mtk r vendor_boot_a ~/lenovo_root/vendor_boot_a.img
python3 -m mtk r vendor_boot_b ~/lenovo_root/vendor_boot_b.img
cp ~/lenovo_root/vendor_boot_a.img ~/lenovo_root/vendor_boot_a_BACKUP.img
cp ~/lenovo_root/vendor_boot_b.img ~/lenovo_root/vendor_boot_b_BACKUP.img

# Step 5: (tablet) complete setup, re-enable USB debugging
adb devices

# Step 6: Install Magisk, push image, patch on tablet
adb install ~/lenovo_root/Magisk.apk
adb push ~/lenovo_root/vendor_boot_a.img /sdcard/Download/vendor_boot.img
# -> Tablet: Magisk > Install > Select and Patch a File > vendor_boot.img

# Step 7: Pull patched image
adb pull /sdcard/Download/magisk_patched-XXXXX.img ~/lenovo_root/magisk_patched_vendor_boot.img

# Step 8: Flash patched image (BROM — power off, Vol Up+Down, plug USB)
python3 -m mtk w vendor_boot_a ~/lenovo_root/magisk_patched_vendor_boot.img
python3 -m mtk w vendor_boot_b ~/lenovo_root/magisk_patched_vendor_boot.img

# Step 9: Reboot, verify root
adb shell su -c 'id'
# uid=0(root) = SUCCESS
```

---

## Adding New Device Support

1. Copy `tumeloroot/devices/_template.yaml` to a new file
2. Fill in your device specifications
3. The critical field is `ramdisk_partition` - determines which partition Magisk patches
4. Test with your device and submit a pull request

### Finding Your Ramdisk Partition
```bash
# Use magiskboot to check each image:
magiskboot unpack boot.img         # Standard boot ramdisk
magiskboot unpack init_boot.img    # GKI 2.0 devices
magiskboot unpack vendor_boot.img  # Vendor boot (like Lenovo Tab K11)
```
The one with `RAMDISK_SZ > 0` is your target.

## Contributing

Tumeloroot is built on open-source tools and we believe in giving back. If you use our framework to add support for new devices or develop improvements:

- **Submit your device profiles** back to the project so everyone benefits
- **Bug fixes and features** should be contributed upstream under GPLv3
- **Derivative works** must attribute Tumeloroot and use the same GPLv3 license
- **Don't fragment** — keep improvements under one roof so the community grows together

See [LICENSE](LICENSE) for full contribution and derivative work terms.

## License

GPLv3 with name protection and contribution terms. Modified versions must use a different name and attribute Tumeloroot. See [LICENSE](LICENSE).

## Credits

- [mtkclient](https://github.com/bkerler/mtkclient) by bkerler
- [Magisk](https://github.com/topjohnwu/Magisk) by topjohnwu
- XDA Developers community

## Disclaimer

This software is provided **strictly for educational and security research purposes**. It must only be used on devices you legally own. The FRP clearing feature is intended for device owners who have forgotten their credentials, not for circumventing theft protection on stolen devices. Misuse may violate local and international laws. The developers assume no liability for any misuse, damage, or legal consequences. Use at your own risk.
