"""Verify Page - root access verification via ADB."""

from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QThread, Signal


class VerifyWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, engine):
        super().__init__()
        self._engine = engine

    def run(self):
        ok = self._engine.run_step("verify")
        ver = self._engine._adb.get_magisk_version() if ok else ""
        self.finished.emit(ok, ver)


class VerifyPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Verify Root")
        self._done = False
        self._engine = None

        layout = QVBoxLayout(self)

        instructions = QLabel(
            "After the rooting process completes, follow these steps carefully:\n\n"
            "1. Unplug USB cable from the device\n"
            "2. Long-press Power button to turn on the device\n"
            "3. IMPORTANT: An 'orange state' warning will appear at boot\n"
            "   HOLD the Power button until the warning disappears!\n"
            "   If you don't hold Power, the device may get stuck.\n"
            "4. Wait for Android to fully boot to the home screen\n"
            "5. Download Magisk APK from GitHub:\n"
            "   github.com/topjohnwu/Magisk/releases > Magisk-vXX.X.apk\n"
            "6. Install the Magisk APK on your device\n"
            "7. Open Magisk app and try 'Direct Install' first:\n"
            "   Magisk > Install > Direct Install (Recommended)\n"
            "   If Direct Install fails or is not available, use:\n"
            "   Magisk > Install > Install to Inactive Slot\n"
            "8. After Magisk finishes, reboot the device\n"
            "9. HOLD Power button during orange state warning again\n"
            "10. Install 'Root Checker' from Play Store to verify root\n"
            "11. Reconnect USB cable to PC for automatic verification below"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        layout.addSpacing(6)

        orange_warning = QLabel(
            "CRITICAL: Every time you restart the device, an 'orange state'\n"
            "warning will appear. You MUST hold the Power button until\n"
            "the warning disappears. This is normal for unlocked bootloaders.\n"
            "Failing to hold Power may cause a boot delay or partial bootloop."
        )
        orange_warning.setWordWrap(True)
        orange_warning.setStyleSheet(
            "color: #e94560; padding: 10px; background-color: #2a1a1e; "
            "border-radius: 6px; font-weight: bold; font-size: 12px;"
        )
        layout.addWidget(orange_warning)
        layout.addSpacing(6)

        disclaimer_note = QLabel(
            "Note: Any issues arising from the rooting process, including boot\n"
            "problems, data loss, or device malfunction, are the sole responsibility\n"
            "of the user. The developers accept no liability. Use at your own risk."
        )
        disclaimer_note.setWordWrap(True)
        disclaimer_note.setStyleSheet(
            "color: #a0a0b0; padding: 8px; background-color: #16213e; "
            "border-radius: 6px; font-size: 11px; font-style: italic;"
        )
        layout.addWidget(disclaimer_note)
        layout.addSpacing(6)

        self._check_btn = QPushButton("Check Root")
        self._check_btn.clicked.connect(self._check)
        layout.addWidget(self._check_btn)

        self._result = QLabel("")
        self._result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result.setStyleSheet("font-size: 20px; padding: 20px;")
        layout.addWidget(self._result)

        self._details = QLabel("")
        self._details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._details.setStyleSheet("color: #a0a0b0;")
        layout.addWidget(self._details)
        layout.addStretch()

    def set_engine(self, engine):
        self._engine = engine

    def _check(self) -> None:
        self._check_btn.setEnabled(False)
        self._result.setText("Checking root access...")
        self._result.setStyleSheet("color: #f0a030; font-size: 20px; padding: 20px;")

        self._worker = VerifyWorker(self._engine)
        self._worker.finished.connect(self._on_result)
        self._worker.start()

    def _on_result(self, success: bool, magisk_ver: str) -> None:
        self._done = success
        self._check_btn.setEnabled(True)
        if success:
            self._result.setText("ROOT SUCCESSFUL!")
            self._result.setStyleSheet("color: #4ecca3; font-size: 24px; font-weight: bold; padding: 20px;")
            self._details.setText(f"Magisk version: {magisk_ver}" if magisk_ver else "uid=0(root) confirmed")
        else:
            self._result.setText("ROOT NOT DETECTED")
            self._result.setStyleSheet("color: #e94560; font-size: 20px; font-weight: bold; padding: 20px;")
            self._details.setText("Make sure the device is booted and USB debugging is enabled.")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._done
