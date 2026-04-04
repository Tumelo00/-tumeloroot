"""OEM Unlock Page - guide user with visual illustrations for each step."""

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QGroupBox,
)
from PySide6.QtCore import Qt

from tumeloroot.gui.widgets.step_illustrations import (
    PhoneSettingsIllustration,
    OemToggleIllustration,
    UsbDebugIllustration,
)


class OemUnlockPage(QWizardPage):
    """Guides the user through enabling OEM Unlock with visual illustrations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Enable OEM Unlock")
        self._confirmed = False

        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "These settings must be enabled BEFORE the rooting process.\n"
            "OEM Unlock allows bootloader modification.\n"
            "USB Debugging is needed for root verification after reboot."
        )
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px;")
        header.setWordWrap(True)
        layout.addWidget(header)
        layout.addSpacing(4)

        # Step 1: Developer Options — with illustration
        step1_group = QGroupBox("Step 1: Enable Developer Options")
        step1_layout = QHBoxLayout()
        self._illust1 = PhoneSettingsIllustration()
        step1_layout.addWidget(self._illust1)
        step1_desc = QLabel(
            "1. Open Settings\n"
            "2. Go to Settings > About Tablet\n"
            "3. Find Build Number\n"
            "4. Tap it 7 times rapidly\n"
            '5. You\'ll see "You are now a developer!"'
        )
        step1_desc.setStyleSheet("color: #c0c0d0; font-size: 12px; line-height: 1.5; padding: 8px;")
        step1_layout.addWidget(step1_desc, 1)
        step1_group.setLayout(step1_layout)
        layout.addWidget(step1_group)

        # Step 2: OEM Unlock — with illustration
        step2_group = QGroupBox("Step 2: Enable OEM Unlocking")
        step2_layout = QHBoxLayout()
        self._illust2 = OemToggleIllustration()
        step2_layout.addWidget(self._illust2)
        step2_desc = QLabel(
            "1. Go back to Settings\n"
            "2. Open Developer Options\n"
            "3. Find OEM Unlocking toggle\n"
            "4. Turn it ON\n"
            "5. Confirm the warning popup"
        )
        step2_desc.setStyleSheet("color: #c0c0d0; font-size: 12px; line-height: 1.5; padding: 8px;")
        step2_layout.addWidget(step2_desc, 1)
        step2_group.setLayout(step2_layout)
        layout.addWidget(step2_group)

        # Step 3: USB Debugging — with illustration
        step3_group = QGroupBox("Step 3: Enable USB Debugging")
        step3_layout = QHBoxLayout()
        self._illust3 = UsbDebugIllustration()
        step3_layout.addWidget(self._illust3)
        step3_desc = QLabel(
            "1. In Developer Options\n"
            "2. Find USB Debugging toggle\n"
            "3. Turn it ON\n"
            "4. This is needed for the VERIFICATION step after root\n"
            "   (not for the BROM process itself)"
        )
        step3_desc.setStyleSheet("color: #c0c0d0; font-size: 12px; line-height: 1.5; padding: 8px;")
        step3_layout.addWidget(step3_desc, 1)
        step3_group.setLayout(step3_layout)
        layout.addWidget(step3_group)

        # Confirmation
        self._checkbox = QCheckBox(
            "I have completed all 3 steps (Developer Options ON, OEM Unlock ON, USB Debugging ON)"
        )
        self._checkbox.setStyleSheet("font-weight: bold; padding: 8px;")
        self._checkbox.stateChanged.connect(self._on_check)
        layout.addWidget(self._checkbox)

    def _on_check(self, state):
        self._confirmed = state == 2
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._confirmed
