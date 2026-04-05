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

1. **Device enters BROM mode** - Power off > Hold Power + Vol Up + Vol Down > Plug USB
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
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools
pip install -e .
python -m tumeloroot
```

## Manual Root Guide for Linux Users

> **There is no GUI application for Linux.** The Tumeloroot GUI (`.exe`) is Windows-only. There is no one-click tool that handles everything automatically on Linux. On Linux, the entire process is done **manually through the terminal using command-line tools**. No programming knowledge is required — just copy and paste the commands below in order.

This guide uses **mtkclient** for bootloader unlocking and partition operations via BROM exploit — no fastboot required for the critical steps.

### Pre-Flight Checklist

Before starting, go through this checklist:

- [ ] Tablet battery is **at least 50%** charged (a dead battery during flash = potential brick)
- [ ] You have a **data-capable USB-C cable** (not a charge-only cable — see how to test below)
- [ ] You have **at least 500 MB free disk space** on your Linux computer (for images + backups)
- [ ] You have **backed up** all important data on the tablet (photos, contacts, app data — everything will be erased or may be erased)
- [ ] You are **not** using a USB hub — connect directly to your computer's USB port
- [ ] Your Linux user has **sudo** privileges

**How to test if your USB cable supports data transfer:**
1. Connect the tablet to your computer with the cable
2. On the tablet notification bar, check if it says "USB for file transfer" or similar
3. If you only see "Charging" with no file transfer option, the cable is charge-only — use a different cable
4. Alternatively: if `adb devices` shows the device, the cable works

**Before you start, understand these concepts:**

| Term | Meaning |
|------|---------|
| **ADB** | Android Debug Bridge — communicates with the tablet while Android is running, over USB |
| **mtkclient** | Open-source tool that exploits MediaTek's BROM (Boot ROM) to read/write partitions at the hardware level, bypassing Android entirely |
| **BROM mode** | A low-level hardware mode on MediaTek chips. The tablet screen stays black, but the chip is listening over USB. Enter by holding Power + Vol Up + Vol Down while plugging USB |
| **vendor_boot** | The partition that holds the kernel ramdisk on GKI (Generic Kernel Image) devices. On older devices this was in `boot`, but Android 13+ with GKI uses `vendor_boot` instead. Magisk patches this partition |
| **A/B slots** | This device has two copies of every system partition (`_a` and `_b`). Android switches between them for seamless updates. We flash our patched image to **both** slots so root survives any slot switch |
| **Magisk** | The root framework. It patches the vendor_boot image to inject `su` (superuser) access while keeping the system partition untouched |
| **seccfg** | Security configuration partition on MediaTek devices. Stores the bootloader lock state. Erasing it with mtkclient unlocks the bootloader |
| **Partition** | A section of the device's internal storage, like a hard drive partition on a PC. Each partition holds a specific part of the system (kernel, system apps, user data, etc.) |
| **Flash** | Writing a raw image file directly to a partition. This replaces the partition's entire contents |
| **Brick** | When a device becomes unbootable and unresponsive — essentially a "brick". Having backups and BROM access prevents permanent bricks on MediaTek devices |

---

### Step 1 — Install Required Software

#### 1.1 — Update your system

Always start with a fully updated system to avoid dependency issues:

```bash
# Ubuntu / Debian
sudo apt update && sudo apt upgrade -y

# Arch Linux
sudo pacman -Syu

# Fedora
sudo dnf upgrade -y
```

#### 1.2 — Install ADB, Python, and USB libraries

```bash
# Ubuntu / Debian
sudo apt install -y adb android-tools-fastboot python3 python3-pip python3-venv git libusb-1.0-0 unzip wget curl

# Arch Linux
sudo pacman -S android-tools python python-pip git libusb unzip wget curl

# Fedora
sudo dnf install -y android-tools python3 python3-pip git libusb unzip wget curl
```

Verify ADB is installed:
```bash
adb version
```

Expected output (version may differ):
```
Android Debug Bridge version 1.0.41
```

If `adb` is not found after install, try logging out and back in, or run `hash -r`.

#### 1.3 — Install mtkclient

mtkclient is the tool that communicates with MediaTek's Boot ROM over USB. It is recommended to install it inside a **Python virtual environment** to avoid conflicts with system packages:

```bash
python3 -m venv ~/mtk-venv
source ~/mtk-venv/bin/activate
pip install --upgrade pip setuptools
pip install mtkclient
```

> **Important:** Every time you open a new terminal to use mtkclient, you need to activate the virtual environment first:
> ```bash
> source ~/mtk-venv/bin/activate
> ```

> **If you get `ModuleNotFoundError: No module named 'Cryptodome'`** when running mtkclient, install `pycryptodome` explicitly:
> ```bash
> source ~/mtk-venv/bin/activate
> pip install pycryptodome
> ```
> On some Linux distributions (like Gentoo), the system package installs as `Crypto` instead of `Cryptodome`. Installing `pycryptodome` via pip inside the venv fixes this.

Verify mtkclient is installed:
```bash
python3 -m mtk --help
```

If you see a help/usage message, the installation was successful.

#### 1.4 — Set up USB permissions (udev rules)

Without these rules, Linux will block unprivileged access to USB devices. Both ADB and mtkclient need them:

```bash
sudo tee /etc/udev/rules.d/51-android.rules <<'EOF'
# Lenovo (ADB mode)
SUBSYSTEM=="usb", ATTR{idVendor}=="17ef", MODE="0666", GROUP="plugdev"
# MediaTek BROM / Preloader (mtkclient)
SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666", GROUP="plugdev"
EOF
```

Reload the rules and add your user to the `plugdev` group:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -aG plugdev $USER
```

> **You must log out and back in** (or reboot) for the group change to take effect. This is a one-time step.

To verify the group was added:
```bash
groups
```
You should see `plugdev` in the output.

#### 1.5 — Verify everything is installed correctly

Run all verification commands at once:
```bash
echo "=== ADB ===" && adb version | head -1 && echo "=== Python ===" && python3 --version && echo "=== mtkclient ===" && python3 -m mtk --help 2>&1 | head -1 && echo "=== USB permissions ===" && groups | grep -o plugdev && echo "=== All checks passed ==="
```

If any command fails, go back to the relevant step above and fix it before proceeding.

#### 1.6 — Create working directory and download Magisk

```bash
mkdir -p ~/lenovo_root
cd ~/lenovo_root
```

Download the latest Magisk APK from the [official GitHub releases page](https://github.com/topjohnwu/Magisk/releases):
```bash
wget -O ~/lenovo_root/Magisk.apk https://github.com/topjohnwu/Magisk/releases/download/v28.1/Magisk-v28.1.apk
```

> **Important:** The version number (`v28.1`) changes over time. Check the releases page for the latest version and update the URL accordingly.

Verify the download:
```bash
ls -lh ~/lenovo_root/Magisk.apk
```

The file should be a few MB in size (typically 10-15 MB). If it is 0 bytes or shows an HTML error page, the download failed — check the URL.

Verify it is a valid APK (not an error page):
```bash
file ~/lenovo_root/Magisk.apk
```

Expected: `Zip archive data` or `Java archive data`. If it says `HTML document`, the URL was wrong — re-download.

#### 1.7 — Summary of files in working directory

At this point your `~/lenovo_root/` directory should contain:
```
~/lenovo_root/
└── Magisk.apk          (Magisk installer, ~10-15 MB)
```

By the end of the process, it will look like:
```
~/lenovo_root/
├── Magisk.apk                        (Magisk installer)
├── vendor_boot_a.img                 (extracted from device)
├── vendor_boot_b.img                 (extracted from device)
├── vendor_boot_a_BACKUP.img          (safety backup — DO NOT DELETE)
├── vendor_boot_b_BACKUP.img          (safety backup — DO NOT DELETE)
└── magisk_patched_vendor_boot.img    (patched by Magisk — this gets flashed)
```

---

### Step 2 — Enable USB Debugging and Authorize ADB

This step is done **on the tablet** to allow your computer to communicate with it.

#### 2.1 — Enable Developer Options

1. Open **Settings** on the tablet
2. Scroll down to **About Tablet**
3. Find **Build Number** and tap it **7 times** rapidly
4. You will see: "You are now a developer!"

#### 2.2 — Enable USB Debugging and OEM Unlocking

1. Go back to **Settings**
2. Open **Developer Options** (now visible near the bottom)
3. Enable **USB Debugging** → toggle ON
4. Enable **OEM Unlocking** → toggle ON

> **"OEM Unlocking" not visible?** Make sure the tablet is connected to the internet and signed into a Google account. Some devices require waiting 24 hours after first sign-in.

#### 2.3 — Connect and Authorize

1. Connect the tablet to your Linux computer with a **data-capable** USB-C cable
2. On the tablet, a dialog appears: **"Allow USB debugging?"**
3. Check **"Always allow from this computer"**
4. Tap **Allow**

#### 2.4 — Verify the connection

```bash
adb devices
```

Expected output:
```
List of devices attached
XXXXXXXXX    device
```

**Troubleshooting:**
- If the list is empty: check cable, try a different USB port (avoid hubs), check USB Debugging is ON
- If it says `unauthorized`: look at the tablet screen for the permission dialog and approve it
- If it says `no permissions`: your udev rules are not working — revisit Step 1.4 and reboot

#### 2.5 — Note the active slot

```bash
adb shell getprop ro.boot.slot_suffix
```

This returns `_a` or `_b`. **Write this down** — you will need it to know which slot is active, though we will flash both slots.

#### 2.6 — Note device information (for your records)

```bash
adb shell getprop ro.product.model
adb shell getprop ro.build.display.id
adb shell getprop ro.boot.hardware
```

Save this output somewhere — it confirms you are working with the correct device.

For Lenovo Tab K11, expected values:
```
ro.product.model: TB330XUP
ro.boot.hardware: mt8786
```

If your model is different, the partition layout may differ. This guide is specifically written for the **TB330XUP**.

---

### Step 3 — Unlock Bootloader via BROM (mtkclient)

> **WARNING: This step will factory reset the device. ALL data on the tablet will be erased. Back up anything important before proceeding.**

#### 3.1 — Power off the tablet completely

Hold the power button → tap "Power off" → wait until the screen is completely black and the device is fully off.

#### 3.2 — Enter BROM mode

1. **Hold Power + Vol Up + Vol Down** buttons on the tablet simultaneously
2. **While holding all three buttons**, plug the USB cable into the tablet
3. The tablet screen will stay black — this is normal
4. Keep holding the buttons for 5-10 seconds

> **How to know it worked:** Your Linux terminal will show mtkclient detecting the device when you run the next command. If mtkclient says "Waiting for device", the device is not in BROM mode — unplug, power off, and try again.

#### 3.3 — Run the unlock command

```bash
cd ~/lenovo_root
python3 -m mtk e seccfg
```

Expected output (last lines):
```
Erasing seccfg ...
Done.
```

If you see `Done`, the bootloader is now unlocked. The device will factory reset on the next boot.

> **What just happened?** The `seccfg` (security configuration) partition stores whether the bootloader is locked or unlocked. By erasing it, the device defaults to "unlocked" state. This is a MediaTek-specific mechanism — other manufacturers use different methods.

**If mtkclient says "Waiting for device":**
- Unplug the USB cable
- Make sure the tablet is completely powered off (hold power for 15 seconds to force off)
- Try again: hold Power + Vol Up + Vol Down → plug USB
- Try a different USB port (USB 2.0 ports sometimes work better than USB 3.0)
- On some systems, you may need to run with `sudo`: `sudo python3 -m mtk e seccfg`
- Check `dmesg | tail -20` to see if the USB device is detected at all

**If mtkclient says "DAInit failed" or similar error:**
- This can happen if the device is not fully powered off
- Remove USB cable, hold power button for 30 seconds to fully drain any residual power
- Wait 5 seconds, then try the BROM entry sequence again

---

### Step 4 — Extract vendor_boot via BROM (mtkclient)

We need to extract the vendor_boot partition from the device so Magisk can patch it.

#### 4.1 — Re-enter BROM mode

After the unlock command, the device may have exited BROM mode. Re-enter:

1. Unplug USB cable
2. Make sure the tablet is off (hold power 15 seconds to force off)
3. Hold Power + Vol Up + Vol Down → plug USB

#### 4.2 — Extract vendor_boot from slot A

```bash
python3 -m mtk r vendor_boot_a ~/lenovo_root/vendor_boot_a.img
```

Expected output (last lines):
```
Reading vendor_boot_a ...
Done.
```

#### 4.3 — Re-enter BROM mode and extract slot B

Unplug USB → force off tablet → hold Power + Vol Up + Vol Down → plug USB:

```bash
python3 -m mtk r vendor_boot_b ~/lenovo_root/vendor_boot_b.img
```

#### 4.4 — Verify the extracted files

```bash
ls -lh ~/lenovo_root/vendor_boot_a.img ~/lenovo_root/vendor_boot_b.img
```

Both files should be approximately **64 MB** (67108864 bytes). If either file is 0 bytes or missing, re-enter BROM mode and try again.

#### 4.5 — Verify file integrity with checksums

Generate checksums so you can verify the files are not corrupted:
```bash
sha256sum ~/lenovo_root/vendor_boot_a.img ~/lenovo_root/vendor_boot_b.img
```

Save the output somewhere. If you ever need to verify a file hasn't changed:
```bash
sha256sum ~/lenovo_root/vendor_boot_a_BACKUP.img
# Compare with the original hash
```

#### 4.6 — Create backup copies

These backups are your safety net. If anything goes wrong, you can restore them:

```bash
cp ~/lenovo_root/vendor_boot_a.img ~/lenovo_root/vendor_boot_a_BACKUP.img
cp ~/lenovo_root/vendor_boot_b.img ~/lenovo_root/vendor_boot_b_BACKUP.img
```

Verify the backups exist:
```bash
ls -lh ~/lenovo_root/*BACKUP*
```

> **Do not skip this step.** Without these backups, a failed flash could leave the device unbootable with no recovery path other than a full firmware flash.

---

### Step 5 — First Boot After Unlock + Re-enable ADB

#### 5.1 — Boot the tablet

Unplug USB, then hold the power button to turn on the tablet. The first boot after unlocking will:
- Show a warning about unlocked bootloader (this is normal — it will appear on every boot)
- Factory reset the device
- Show the initial setup wizard

This first boot may take 2-5 minutes. **Do not press any buttons or unplug during this time.** Be patient — the device is reformatting its data partition.

#### 5.2 — Complete initial setup

Go through the setup wizard:
- Connect to WiFi
- Sign in with Google account (or skip)
- Complete the remaining setup steps

#### 5.3 — Re-enable Developer Options and USB Debugging

Repeat the exact same steps from **Step 2**:
1. Settings > About Tablet > tap Build Number 7 times
2. Settings > Developer Options > USB Debugging ON
3. Connect USB cable
4. Approve "Allow USB debugging?" on the tablet

#### 5.4 — Verify ADB connection

```bash
adb devices
```

You should see `XXXXXXXXX    device` again. If not, troubleshoot using the tips in Step 2.4.

---

### Step 6 — Install Magisk and Patch vendor_boot

#### 6.1 — Install the Magisk app on the tablet

```bash
adb install ~/lenovo_root/Magisk.apk
```

Expected output:
```
Performing Streamed Install
Success
```

If you see `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, uninstall the old version first:
```bash
adb uninstall com.topjohnwu.magisk
adb install ~/lenovo_root/Magisk.apk
```

#### 6.2 — Send the vendor_boot image to the tablet

```bash
adb push ~/lenovo_root/vendor_boot_a.img /sdcard/Download/vendor_boot.img
```

Expected output:
```
~/lenovo_root/vendor_boot_a.img: 1 file pushed, X.X MB/s (67108864 bytes in X.XXXs)
```

#### 6.3 — Patch the image using Magisk (on the tablet)

Now pick up the tablet and do the following:

1. Open the **Magisk** app from the app drawer
2. On the home screen, find the **"Magisk"** section
3. Tap the **"Install"** button next to it
4. A dialog appears — select **"Select and Patch a File"**
5. A file picker opens — navigate to **Downloads**
6. Select **vendor_boot.img**
7. Magisk will start patching. You will see a log with various steps
8. Wait until the very last line says **"All done!"**

> **Do not interrupt the patching process.** It takes 10-30 seconds. If Magisk shows an error, re-push the vendor_boot.img and try again.

The patched file is now saved in `/sdcard/Download/` with a name like `magisk_patched-28100_XXXXX.img`.

> **What does Magisk do during patching?** It unpacks the vendor_boot image, injects the Magisk init binary into the ramdisk, re-packs the image, and signs it. The result is a vendor_boot that loads Magisk's init process before Android starts, giving it root-level control.

---

### Step 7 — Pull the Patched Image to Computer

#### 7.1 — Find the patched file name

```bash
adb shell ls -la /sdcard/Download/magisk_patched*
```

Example output:
```
-rw-rw---- 1 root sdcard_rw 67108864 2026-04-05 01:23 /sdcard/Download/magisk_patched-28100_a1b2c.img
```

#### 7.2 — Pull the file

Copy the exact file name from the output above and use it in the pull command:

```bash
adb pull /sdcard/Download/magisk_patched-28100_a1b2c.img ~/lenovo_root/magisk_patched_vendor_boot.img
```

> **Replace** `magisk_patched-28100_a1b2c.img` with the actual file name from your output.

#### 7.3 — Verify the patched image

```bash
ls -lh ~/lenovo_root/magisk_patched_vendor_boot.img
```

The file should be approximately **64 MB**, same as the original. If it is significantly smaller or 0 bytes, the patch failed — repeat Step 6.

Compare the size with the original to make sure they match:
```bash
ls -l ~/lenovo_root/vendor_boot_a.img ~/lenovo_root/magisk_patched_vendor_boot.img
```

Both files must have the **exact same byte count**. If they differ, something went wrong during patching.

---

### Step 8 — Flash Patched Image via BROM (mtkclient)

Now we write the Magisk-patched vendor_boot image back to the tablet, replacing the original on both slots.

> **Is this dangerous?** Writing a partition is the most critical step. If the power goes out or the USB cable disconnects during a write, the partition could be left in a corrupted state. However, since we are using **BROM mode** (hardware-level access), you can always re-enter BROM and re-flash — even if the device does not boot. This is the advantage of MediaTek devices: **BROM access is always available regardless of software state.** As long as you have your backup files, you cannot permanently brick the device.

Now we write the Magisk-patched vendor_boot image back to the tablet, replacing the original on both slots.

#### 8.1 — Power off the tablet

Hold power → Power off → wait until fully off.

#### 8.2 — Enter BROM mode and flash slot A

Hold Power + Vol Up + Vol Down → plug USB:

```bash
python3 -m mtk w vendor_boot_a ~/lenovo_root/magisk_patched_vendor_boot.img
```

Expected output:
```
Writing vendor_boot_a ...
Done.
```

#### 8.3 — Re-enter BROM mode and flash slot B

Unplug USB → force off → hold Power + Vol Up + Vol Down → plug USB:

```bash
python3 -m mtk w vendor_boot_b ~/lenovo_root/magisk_patched_vendor_boot.img
```

Expected output:
```
Writing vendor_boot_b ...
Done.
```

> **Both slots are now patched.** This ensures root works regardless of which slot Android boots from.

---

### Step 9 — Reboot and Verify Root

#### 9.1 — Boot the tablet

Unplug USB, hold the power button to turn on the tablet. Wait for it to fully boot to the home screen. This may take 1-2 minutes.

#### 9.2 — Connect USB and test root

```bash
adb devices
```

Make sure the device shows as `device` (not `unauthorized`).

```bash
adb shell su -c 'id'
```

> **Important:** When you run this command, a **Magisk superuser permission dialog** will appear on the tablet screen. You must tap **"Allow"** on the tablet. If you miss it, the command will fail — just run it again.

Expected output:
```
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

If you see `uid=0(root)` — **root is successful!**

#### 9.3 — Verify Magisk details

```bash
adb shell su -c 'magisk -v'
adb shell su -c 'magisk -V'
```

Example output:
```
28.1:MAGISK:R
28100
```

#### 9.4 — Verify the active slot

```bash
adb shell getprop ro.boot.slot_suffix
```

#### 9.5 — Check SELinux status

```bash
adb shell getenforce
```

Expected: `Enforcing` — Magisk does not weaken SELinux, it runs in its own context (`u:r:magisk:s0`).

---

### Restoring Stock (Unroot)

If you need to remove root or recover from a boot issue, flash the original backup images via BROM.

#### Power off the tablet, enter BROM mode, and flash the originals:

Slot A:
```bash
python3 -m mtk w vendor_boot_a ~/lenovo_root/vendor_boot_a_BACKUP.img
```

Re-enter BROM mode. Slot B:
```bash
python3 -m mtk w vendor_boot_b ~/lenovo_root/vendor_boot_b_BACKUP.img
```

Reboot the tablet. It will boot with the stock vendor_boot — no root.

> After restoring stock, uninstall the Magisk app from the tablet if it is still installed.

---

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `adb devices` shows nothing | Check USB cable (must be data-capable, not charge-only). Try a different USB port. Check USB Debugging is enabled |
| `adb devices` shows `unauthorized` | Approve the dialog on the tablet screen. If no dialog appears, revoke USB debugging authorizations in Developer Options and reconnect |
| `adb devices` shows `no permissions` | udev rules not applied — revisit Step 1.4, then reboot your computer |
| mtkclient says "Waiting for device" | Tablet is not in BROM mode. Unplug, force off (hold power 15s), then hold Power + Vol Up + Vol Down and plug USB. Try USB 2.0 port |
| `pip3 install mtkclient` fails with "externally-managed" | Use a virtual environment: `python3 -m venv ~/mtk-venv && source ~/mtk-venv/bin/activate && pip install mtkclient` |
| `ModuleNotFoundError: No module named 'Cryptodome'` | Install pycryptodome in your venv: `source ~/mtk-venv/bin/activate && pip install pycryptodome`. On some distros (Gentoo, Arch), the system package uses the old `Crypto` name instead of `Cryptodome` |
| `pip install -e .` fails with `Cannot import 'setuptools.backends._legacy'` | Update setuptools: `pip install --upgrade setuptools pip`. This error occurs with older setuptools versions |
| Magisk "Install" button is grayed out | Make sure you downloaded the full Magisk APK (not the stub). Re-download from GitHub releases |
| Patched image is 0 bytes | Magisk patch failed. Re-push vendor_boot.img and patch again. Make sure the original image is valid (64 MB) |
| Device stuck in boot loop after flash | Flash the backup images via BROM (see "Restoring Stock" above) |
| `su -c 'id'` returns "permission denied" | Tap "Allow" on the Magisk dialog on the tablet. If no dialog, open Magisk app → Superuser tab → check if Shell has permission |
| Bootloader warning on every boot | This is normal for unlocked bootloaders. It will appear every time you boot. Just wait a few seconds and the device continues booting |

---

### Common Mistakes — What NOT to Do

| Mistake | Why It's Bad |
|---------|--------------|
| Flashing `boot` instead of `vendor_boot` | GKI devices use vendor_boot for the ramdisk. Patching boot will have no effect, or worse, could cause a boot loop |
| Installing Magisk modules on this device | Lenovo Tab K11 boot loops with Magisk modules. Do NOT install any modules |
| Using `service.d` scripts | Same as modules — causes boot loop on this device |
| Removing Motorola system packages | This device has hidden Motorola dependencies (AudioService, ColorDisplayService). Removing them causes SystemServer crash → boot loop |
| Changing volume values via `settings put` | Can crash AudioPolicyManager. Use the volume buttons instead |
| Unplugging USB during a `mtk w` (write) operation | Can corrupt the partition. If this happens, re-enter BROM and re-flash the backup |
| Skipping the backup step | Without backups, a bad flash means you need a full stock firmware to recover |
| Using a charge-only USB cable | BROM mode requires data transfer. If mtkclient can't detect the device, the cable might be charge-only |
| Running mtkclient without udev rules | Results in "Permission denied" or "Waiting for device". Set up udev rules first (Step 1.4) |
| Patching vendor_boot_b instead of vendor_boot_a in Magisk | Always patch the **active slot's** image (usually `_a`). We push `vendor_boot_a.img` to the tablet for patching, then flash the result to both slots |

---

### Frequently Asked Questions

**Q: Will I lose my data?**
A: Yes, unlocking the bootloader (Step 3) triggers a factory reset. Back up everything first. After that, the remaining steps (patching, flashing) do NOT erase data.

**Q: Will this void my warranty?**
A: Unlocking the bootloader may void the warranty depending on your region and manufacturer policy. Lenovo's policy varies by market.

**Q: Can I get OTA (over-the-air) updates after rooting?**
A: OTA updates will likely fail because the vendor_boot partition has been modified. If you want to update, restore stock first, apply the update, then re-root.

**Q: Can I re-lock the bootloader after rooting?**
A: Technically possible, but **not recommended** while rooted. Re-locking with a modified vendor_boot will trigger Android Verified Boot and the device will not boot. Restore stock first if you want to re-lock.

**Q: Is BROM mode the same as fastboot?**
A: No. Fastboot is an Android bootloader feature — it requires the bootloader to be running. BROM is a hardware-level mode built into the MediaTek chip itself — it works even if the bootloader, Android, or anything else is completely broken. BROM is always available on MediaTek devices.

**Q: My device shows "orange state" or "unlocked bootloader" warning on boot — is this normal?**
A: Yes. This warning appears every time an unlocked device boots. It does not affect functionality. The device will continue booting normally after a few seconds.

**Q: I flashed the wrong file / wrong partition. What do I do?**
A: Enter BROM mode and flash the backup file. BROM access is always available, so you can always recover. This is why we create backups in Step 4.

**Q: Do I need internet on my Linux machine during the process?**
A: Only for Step 1 (downloading tools and Magisk). Steps 2-9 are fully offline — all communication happens over USB.

**Q: How long does the entire process take?**
A: Approximately 20-40 minutes for a first-timer, including the factory reset setup time. Experienced users can do it in 10-15 minutes.

---

### Device Partition Map (Lenovo Tab K11 — TB330XUP)

For reference, these are the relevant partitions on this device:

| Partition | Block Device | Size | Purpose |
|-----------|-------------|------|---------|
| `vendor_boot_a` | `/dev/block/mmcblk0p29` | 64 MB | Kernel ramdisk (slot A) — **Magisk patches this** |
| `vendor_boot_b` | `/dev/block/mmcblk0p47` | 64 MB | Kernel ramdisk (slot B) — **Magisk patches this** |
| `seccfg` | varies | small | Bootloader lock state — **erased to unlock** |
| `boot_a` / `boot_b` | varies | varies | GKI kernel image (do NOT patch on this device) |
| `vbmeta_a` / `vbmeta_b` | varies | varies | Android Verified Boot metadata |
| `userdata` | varies | large | User data, apps, settings (wiped on bootloader unlock) |

> This partition map is specific to the TB330XUP. Other devices will have different layouts.

---

### Quick Reference — Full Command Sequence

```bash
# ---- Step 1: Install tools ----
sudo apt update && sudo apt upgrade -y
sudo apt install -y adb android-tools-fastboot python3 python3-pip python3-venv git libusb-1.0-0 unzip wget curl
pip3 install mtkclient
sudo tee /etc/udev/rules.d/51-android.rules <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="17ef", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev $USER
# >>> LOG OUT AND BACK IN <<<
mkdir -p ~/lenovo_root && cd ~/lenovo_root
wget -O Magisk.apk https://github.com/topjohnwu/Magisk/releases/download/v28.1/Magisk-v28.1.apk

# ---- Step 2: Verify ADB connection ----
adb devices                              # must show "device"
adb shell getprop ro.boot.slot_suffix    # note: _a or _b

# ---- Step 3: Unlock bootloader ----
# >>> POWER OFF tablet, hold Power + Vol Up + Vol Down, plug USB <<<
python3 -m mtk e seccfg

# ---- Step 4: Extract vendor_boot ----
# >>> Re-enter BROM: unplug, force off, Power + Vol Up + Vol Down, plug USB <<<
python3 -m mtk r vendor_boot_a ~/lenovo_root/vendor_boot_a.img
# >>> Re-enter BROM <<<
python3 -m mtk r vendor_boot_b ~/lenovo_root/vendor_boot_b.img
cp ~/lenovo_root/vendor_boot_a.img ~/lenovo_root/vendor_boot_a_BACKUP.img
cp ~/lenovo_root/vendor_boot_b.img ~/lenovo_root/vendor_boot_b_BACKUP.img

# ---- Step 5: Boot tablet, complete setup, re-enable USB debugging ----
adb devices                              # must show "device" again

# ---- Step 6: Install Magisk, push image ----
adb install ~/lenovo_root/Magisk.apk
adb push ~/lenovo_root/vendor_boot_a.img /sdcard/Download/vendor_boot.img
# >>> ON TABLET: Magisk > Install > Select and Patch a File > vendor_boot.img <<<
# >>> Wait for "All done!" <<<

# ---- Step 7: Pull patched image ----
adb shell ls /sdcard/Download/magisk_patched*
adb pull /sdcard/Download/magisk_patched-XXXXX.img ~/lenovo_root/magisk_patched_vendor_boot.img

# ---- Step 8: Flash patched image ----
# >>> POWER OFF tablet, hold Power + Vol Up + Vol Down, plug USB <<<
python3 -m mtk w vendor_boot_a ~/lenovo_root/magisk_patched_vendor_boot.img
# >>> Re-enter BROM <<<
python3 -m mtk w vendor_boot_b ~/lenovo_root/magisk_patched_vendor_boot.img

# ---- Step 9: Verify root ----
# >>> Boot tablet, connect USB <<<
adb shell su -c 'id'
# uid=0(root) gid=0(root) = ROOT SUCCESSFUL!
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
