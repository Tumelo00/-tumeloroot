# Tumeloroot

**Plug-and-play MediaTek device bootloader unlock and root tool.**

Tumeloroot automates the entire process of unlocking the bootloader and rooting MediaTek-based Android devices using mtkclient and Magisk. Just connect your device, select your model, and click through the wizard.

## Features

- **One-click workflow** - Guided wizard from start to finish
- **Automatic backup** - Backs up all critical partitions with SHA-256 verification before any changes
- **Smart ramdisk detection** - Automatically patches the correct partition (boot, init_boot, or vendor_boot)
- **A/B slot support** - Patches both slots for reliability
- **Emergency restore** - One-click restore from backup if anything goes wrong
- **Expandable** - Add new devices by creating simple YAML profile files
- **Dark themed GUI** - Modern, clean PySide6 interface

## Supported Devices

| Device | Codename | Chipset | Android | Ramdisk In | Status |
|--------|----------|---------|---------|------------|--------|
| Lenovo Tab K11 | TB330XUP | MT6768/MT6769 | 15 | vendor_boot | Verified |

## Installation

### From Source

```bash
git clone https://github.com/Tumelo00/tumeloroot.git
cd tumeloroot
pip install -e .
```

### Run

```bash
python -m tumeloroot
```

Or after pip install:

```bash
tumeloroot
```

## Requirements

- Python 3.9+
- Windows 10/11 (Linux support planned)
- USB cable
- [mtkclient](https://github.com/bkerler/mtkclient) (auto-detected)
- UsbDk driver (Windows)
- ADB (Android Debug Bridge)

## How It Works

1. **Prerequisites** - Checks and installs all required tools
2. **Connect** - Guides you to enter BROM mode and connects via mtkclient
3. **Backup** - Backs up seccfg, boot, vendor_boot, and vbmeta partitions
4. **Unlock** - Unlocks the bootloader via seccfg modification
5. **Patch & Flash** - Disables vbmeta verification, patches ramdisk with Magisk, flashes to both slots
6. **Verify** - Confirms root access via ADB

## Adding New Device Support

1. Copy `tumeloroot/devices/_template.yaml` to a new file (e.g., `my_device.yaml`)
2. Fill in your device's specifications (chipset hwcode, partition layout, ramdisk location)
3. The most critical field is `ramdisk_partition` - this determines which partition Magisk patches
4. Submit a pull request to share with the community!

### Finding Your Ramdisk Partition

The ramdisk can be in `boot`, `init_boot`, or `vendor_boot`. To determine which:

```bash
# Check each image with magiskboot:
magiskboot unpack boot.img        # Look for RAMDISK_SZ > 0
magiskboot unpack init_boot.img   # Look for RAMDISK_SZ > 0
magiskboot unpack vendor_boot.img # Look for RAMDISK_SZ > 0 (check header: VNDRBOOT)
```

## License

GPLv3 with name protection. You can modify and redistribute this software, but modified versions **must not** use the name "Tumeloroot". See [LICENSE](LICENSE) for details.

## Credits

- [mtkclient](https://github.com/bkerler/mtkclient) by bkerler - MediaTek flash and exploit tool
- [Magisk](https://github.com/topjohnwu/Magisk) by topjohnwu - The magic mask for Android
- XDA Developers community - For research and device-specific knowledge

## Disclaimer

This tool is provided for educational and research purposes. Unlocking the bootloader and rooting your device may void your warranty and could potentially brick your device. Use at your own risk. Always ensure you have a backup before proceeding.
