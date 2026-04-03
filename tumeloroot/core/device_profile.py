"""Device profile loader - reads YAML device configurations."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from tumeloroot.core.platform_utils import get_devices_dir


@dataclass
class ChipsetInfo:
    name: str = ""
    hwcode: str = "0x000"
    usb_vid: str = "0x0E8D"
    usb_pid: str = "0x0003"


@dataclass
class BootStructure:
    kernel_partition: str = "boot"
    ramdisk_partition: str = "vendor_boot"
    init_boot_used: bool = False
    ab_device: bool = True


@dataclass
class PartitionConfig:
    backup_list: list[str] = field(default_factory=list)
    root_target: str = "vendor_boot"
    flash_targets: list[str] = field(default_factory=list)


@dataclass
class VbmetaConfig:
    flags_offset: int = 0x78
    flags_value: int = 3
    partitions: list[str] = field(default_factory=list)


@dataclass
class BromInstructions:
    steps: list[str] = field(default_factory=list)


@dataclass
class DeviceProfile:
    """Complete device profile loaded from a YAML file."""

    manufacturer: str = ""
    model: str = ""
    codename: str = ""
    android_version: int = 0
    chipset: ChipsetInfo = field(default_factory=ChipsetInfo)
    boot_structure: BootStructure = field(default_factory=BootStructure)
    partitions: PartitionConfig = field(default_factory=PartitionConfig)
    vbmeta: VbmetaConfig = field(default_factory=VbmetaConfig)
    brom_instructions: BromInstructions = field(default_factory=BromInstructions)
    source_file: str = ""

    @classmethod
    def load(cls, yaml_path: str) -> DeviceProfile:
        """Load a device profile from a YAML file."""
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        dev = data.get("device", {})
        chip = data.get("chipset", {})
        boot = data.get("boot_structure", {})
        parts = data.get("partitions", {})
        vbm = data.get("vbmeta", {})
        brom = data.get("brom_instructions", {})

        # Parse vbmeta flags_offset (handle hex strings)
        flags_offset = vbm.get("flags_offset", 0x78)
        if isinstance(flags_offset, str):
            flags_offset = int(flags_offset, 16) if flags_offset.startswith("0x") else int(flags_offset)

        return cls(
            manufacturer=dev.get("manufacturer", ""),
            model=dev.get("model", ""),
            codename=dev.get("codename", ""),
            android_version=dev.get("android_version", 0),
            chipset=ChipsetInfo(
                name=chip.get("name", ""),
                hwcode=chip.get("hwcode", "0x000"),
                usb_vid=chip.get("usb_vid", "0x0E8D"),
                usb_pid=chip.get("usb_pid", "0x0003"),
            ),
            boot_structure=BootStructure(
                kernel_partition=boot.get("kernel_partition", "boot"),
                ramdisk_partition=boot.get("ramdisk_partition", "vendor_boot"),
                init_boot_used=boot.get("init_boot_used", False),
                ab_device=boot.get("ab_device", True),
            ),
            partitions=PartitionConfig(
                backup_list=parts.get("backup_list", []),
                root_target=parts.get("root_target", "vendor_boot"),
                flash_targets=parts.get("flash_targets", []),
            ),
            vbmeta=VbmetaConfig(
                flags_offset=flags_offset,
                flags_value=vbm.get("flags_value", 3),
                partitions=vbm.get("partitions", []),
            ),
            brom_instructions=BromInstructions(steps=brom.get("steps", [])),
            source_file=yaml_path,
        )

    @classmethod
    def list_available(cls, devices_dir: Optional[str] = None) -> list[DeviceProfile]:
        """List all available device profiles from the devices directory."""
        d = devices_dir or get_devices_dir()
        profiles = []
        if not os.path.isdir(d):
            return profiles

        for fname in sorted(os.listdir(d)):
            if fname.endswith(".yaml") and not fname.startswith("_"):
                try:
                    profile = cls.load(os.path.join(d, fname))
                    profiles.append(profile)
                except Exception:
                    continue
        return profiles

    def validate(self) -> list[str]:
        """Validate the profile and return a list of errors (empty = valid)."""
        errors = []
        if not self.manufacturer:
            errors.append("Missing device.manufacturer")
        if not self.model:
            errors.append("Missing device.model")
        if not self.codename:
            errors.append("Missing device.codename")
        if not self.chipset.hwcode:
            errors.append("Missing chipset.hwcode")
        if not self.boot_structure.ramdisk_partition:
            errors.append("Missing boot_structure.ramdisk_partition")
        if not self.partitions.backup_list:
            errors.append("Missing partitions.backup_list")
        if not self.partitions.root_target:
            errors.append("Missing partitions.root_target")
        if not self.partitions.flash_targets:
            errors.append("Missing partitions.flash_targets")
        if not self.vbmeta.partitions:
            errors.append("Missing vbmeta.partitions")
        return errors

    @property
    def display_name(self) -> str:
        return f"{self.manufacturer} {self.model} ({self.codename})"
