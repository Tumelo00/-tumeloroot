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

        layout.addWidget(QLabel(
            "Boot the device normally:\n"
            "1. Disconnect USB cable\n"
            "2. Power on the device\n"
            "3. Wait for Android to fully boot\n"
            "4. Reconnect USB cable\n"
            "5. Press 'Check Root' below"
        ))
        layout.addSpacing(20)

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
