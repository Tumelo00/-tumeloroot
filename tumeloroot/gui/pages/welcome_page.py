"""Welcome Page - device selection and risk acknowledgment."""

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QSpacerItem, QSizePolicy,
)
from PySide6.QtCore import Qt

from tumeloroot import __app_name__, __version__
from tumeloroot.core.device_profile import DeviceProfile
from tumeloroot.gui.widgets.device_info_card import DeviceInfoCard


class WelcomePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Welcome")
        self._profiles: list[DeviceProfile] = []
        self._selected_profile: DeviceProfile | None = None

        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"{__app_name__} v{__version__}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Plug-and-play MediaTek bootloader unlock & root tool")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # Device selector
        layout.addWidget(QLabel("Select your device:"))
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_device_changed)
        layout.addWidget(self._combo)
        layout.addSpacing(10)

        # Device info card
        self._info_card = DeviceInfoCard()
        layout.addWidget(self._info_card)
        layout.addSpacing(10)

        # Warning
        warning = QLabel(
            "WARNING: This tool will unlock the bootloader and root your device.\n"
            "This may void your warranty and could potentially brick your device.\n"
            "Ensure you have backed up all important data before proceeding."
        )
        warning.setStyleSheet("color: #f0a030; padding: 12px; background-color: #2a2a1e; border-radius: 6px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        # Acknowledgment
        self._checkbox = QCheckBox("I understand the risks and want to proceed")
        self._checkbox.stateChanged.connect(self.completeChanged)
        layout.addWidget(self._checkbox)

        layout.addStretch()

    def initializePage(self) -> None:
        self._profiles = DeviceProfile.list_available()
        self._combo.clear()
        self._combo.addItem("-- Select Device --")
        for p in self._profiles:
            self._combo.addItem(p.display_name)

    def _on_device_changed(self, index: int) -> None:
        if index > 0 and index - 1 < len(self._profiles):
            self._selected_profile = self._profiles[index - 1]
            self._info_card.set_profile(self._selected_profile)
        else:
            self._selected_profile = None
            self._info_card.clear()
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._selected_profile is not None and self._checkbox.isChecked()

    def get_selected_profile(self) -> DeviceProfile | None:
        return self._selected_profile
