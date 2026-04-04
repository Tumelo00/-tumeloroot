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
