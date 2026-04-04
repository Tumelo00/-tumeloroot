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

If you prefer to root manually without the Tumeloroot GUI, or you are on a native Linux system without WSL, follow the steps below using standard command-line tools.

### Prerequisites

**ADB and Fastboot:**

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y adb fastboot

# Arch Linux
sudo pacman -S android-tools

# Fedora
sudo dnf install -y android-tools
```

Or install manually from Google:
```bash
cd ~
wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
unzip platform-tools-latest-linux.zip
echo 'export PATH="$HOME/platform-tools:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify the installation:
```bash
adb version
fastboot --version
```

**USB permissions (udev rules):**

```bash
sudo tee /etc/udev/rules.d/51-android.rules <<'EOF'
# Lenovo
SUBSYSTEM=="usb", ATTR{idVendor}=="17ef", MODE="0666", GROUP="plugdev"
# MediaTek Fastboot / Preloader
SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev $USER
```

> Log out and back in after the group change.

**Magisk APK:**

Download the latest release from the [Magisk GitHub releases page](https://github.com/topjohnwu/Magisk/releases).

**Create a working directory:**
```bash
mkdir -p ~/lenovo_root && cd ~/lenovo_root
```

### Step 1 — Prepare the Device

On the **tablet**:

1. Go to **Settings > About Tablet**, tap **Build Number** 7 times to enable Developer Options
2. Go to **Settings > Developer Options**, enable:
   - **USB Debugging** — ON
   - **OEM Unlocking** — ON
3. Connect the tablet via USB
4. Approve the **"Allow USB debugging?"** dialog on the tablet (check "Always allow")

Verify connection from your terminal:
```bash
adb devices
# Expected output:
# XXXXXXXXX    device
```

### Step 2 — Unlock the Bootloader

> **This will factory reset the device. All data will be erased.**

```bash
adb reboot bootloader
```

Wait for the fastboot screen, then:
```bash
fastboot devices                  # verify device is visible
fastboot flashing unlock          # send unlock command
```

On the tablet screen: use volume keys to select **"Unlock the bootloader"** and confirm with the power button.

The device will wipe and reboot. After the initial setup completes, repeat Step 1 (enable Developer Options and USB Debugging again).

### Step 3 — Extract the vendor_boot Image

> **Why vendor_boot?** Devices with Android 13+ using GKI (Generic Kernel Image) store the ramdisk in `vendor_boot`, not `boot`. Magisk patches `vendor_boot` on these devices.

Find the active slot:
```bash
adb shell getprop ro.boot.slot_suffix
# Returns _a or _b
```

Extract using one of these methods:

**Method A — mtkclient (no root needed):**
```bash
pip3 install mtkclient
# Power off the tablet completely, hold Vol Up + Vol Down, then plug USB
mtk r vendor_boot_<slot> ~/lenovo_root/vendor_boot.img
```

**Method B — ADB with root (if device is already rooted):**
```bash
adb shell su -c 'dd if=/dev/block/by-name/vendor_boot_<slot> of=/sdcard/vendor_boot.img bs=4096'
adb pull /sdcard/vendor_boot.img ~/lenovo_root/vendor_boot.img
adb shell rm /sdcard/vendor_boot.img
```

> Replace `<slot>` with `_a` or `_b` depending on the active slot.

**Back up the original immediately:**
```bash
cp ~/lenovo_root/vendor_boot.img ~/lenovo_root/vendor_boot_ORIGINAL_BACKUP.img
```

### Step 4 — Patch with Magisk

Install Magisk on the tablet and send the image:
```bash
adb install ~/lenovo_root/Magisk.apk
adb push ~/lenovo_root/vendor_boot.img /sdcard/Download/vendor_boot.img
```

On the **tablet**:

1. Open **Magisk**
2. Tap **Install** next to "Magisk"
3. Select **"Select and Patch a File"**
4. Navigate to **Downloads**, select **vendor_boot.img**
5. Wait for **"All done!"**

Pull the patched image back:
```bash
# Check the file name
adb shell ls /sdcard/Download/magisk_patched*

# Pull it (replace XXXXX with actual number from output above)
adb pull /sdcard/Download/magisk_patched-XXXXX.img ~/lenovo_root/magisk_patched_vendor_boot.img
```

### Step 5 — Flash the Patched Image

```bash
adb reboot bootloader
# Wait ~10 seconds for fastboot mode
fastboot devices
fastboot flash vendor_boot_<slot> ~/lenovo_root/magisk_patched_vendor_boot.img
fastboot reboot
```

> Replace `<slot>` with `_a` or `_b`.

### Step 6 — Verify Root

After the device finishes booting:
```bash
adb shell su -c 'id'
```

> A Magisk permission dialog will appear on the tablet — tap **Allow**.

Expected output:
```
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

If you see `uid=0(root)` — root is working.

```bash
adb shell su -c 'magisk -v'    # Magisk version string
adb shell su -c 'magisk -V'    # Magisk version code
```

### Restoring Stock (Unroot)

Flash the original backup to remove root:
```bash
adb reboot bootloader
fastboot flash vendor_boot_<slot> ~/lenovo_root/vendor_boot_ORIGINAL_BACKUP.img
fastboot reboot
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
