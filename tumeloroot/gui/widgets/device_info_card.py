"""Device Info Card widget - displays device profile information."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout
from tumeloroot.core.device_profile import DeviceProfile


class DeviceInfoCard(QWidget):
    """Displays device profile info in a card layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._group = QGroupBox("Device Information")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._grid = QGridLayout()
        self._labels = {}
        fields = [
            ("Manufacturer", "manufacturer"),
            ("Model", "model"),
            ("Codename", "codename"),
            ("Android", "android"),
            ("Chipset", "chipset"),
            ("Ramdisk In", "ramdisk"),
            ("A/B Slots", "ab"),
            ("Root Target", "root_target"),
        ]
        for i, (display, key) in enumerate(fields):
            name_label = QLabel(f"{display}:")
            name_label.setStyleSheet("color: #a0a0b0; font-weight: bold;")
            value_label = QLabel("-")
            self._labels[key] = value_label
            self._grid.addWidget(name_label, i, 0)
            self._grid.addWidget(value_label, i, 1)

        self._group.setLayout(self._grid)
        layout.addWidget(self._group)

    def set_profile(self, profile: DeviceProfile) -> None:
        self._labels["manufacturer"].setText(profile.manufacturer)
        self._labels["model"].setText(profile.model)
        self._labels["codename"].setText(profile.codename)
        self._labels["android"].setText(str(profile.android_version))
        self._labels["chipset"].setText(profile.chipset.name)
        self._labels["ramdisk"].setText(profile.boot_structure.ramdisk_partition)
        self._labels["ab"].setText("Yes" if profile.boot_structure.ab_device else "No")
        self._labels["root_target"].setText(profile.partitions.root_target)

    def clear(self) -> None:
        for label in self._labels.values():
            label.setText("-")
