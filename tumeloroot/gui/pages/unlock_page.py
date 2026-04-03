"""Unlock Page - bootloader unlock via seccfg with clear explanation."""

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QLabel, QPushButton, QMessageBox, QGroupBox,
)
from PySide6.QtCore import Qt, QThread, Signal


class UnlockWorker(QThread):
    finished = Signal(bool)
    log = Signal(str, str)

    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        self._orig_log_cb = engine._log_cb

    def run(self):
        self._engine._log_cb = lambda msg, lvl: self.log.emit(msg, lvl)
        try:
            self.finished.emit(self._engine.run_step("unlock"))
        finally:
            self._engine._log_cb = self._orig_log_cb


class UnlockPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Unlock Bootloader")
        self._done = False
        self._engine = None

        layout = QVBoxLayout(self)

        # Explanation
        explain_group = QGroupBox("What is bootloader unlock?")
        explain_layout = QVBoxLayout()
        explain = QLabel(
            "The bootloader is the first program that runs when your device turns on.\n"
            "By default, it is LOCKED — meaning it only boots official Lenovo software.\n\n"
            "To install Magisk (root), we need to UNLOCK it.\n"
            "This is done by modifying the 'seccfg' (security config) partition.\n\n"
            "After unlock, your device will show an 'Orange State' warning at boot.\n"
            "This is NORMAL and means the bootloader is unlocked."
        )
        explain.setWordWrap(True)
        explain.setStyleSheet("color: #c0c0d0; padding: 8px; line-height: 1.4;")
        explain_layout.addWidget(explain)
        explain_group.setLayout(explain_layout)
        layout.addWidget(explain_group)

        layout.addSpacing(8)

        # Warning
        warning = QLabel(
            "WARNING: Unlocking MAY erase all data on the device (factory reset).\n"
            "Your backup from the previous step will protect you if something goes wrong."
        )
        warning.setStyleSheet(
            "color: #f0a030; padding: 12px; background-color: #2a2a1e; "
            "border-radius: 6px; font-weight: bold;"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        layout.addSpacing(12)

        # Status
        self._status = QLabel("Ready to unlock. Click the button below to proceed.")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("font-size: 13px; padding: 8px; color: #a0a0b0;")
        layout.addWidget(self._status)

        # Unlock button
        self._unlock_btn = QPushButton("Unlock Bootloader")
        self._unlock_btn.setStyleSheet(
            "QPushButton { font-size: 16px; padding: 14px 32px; }"
        )
        self._unlock_btn.clicked.connect(self._confirm_unlock)
        layout.addWidget(self._unlock_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Result
        self._result = QLabel("")
        self._result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result.setStyleSheet("font-size: 18px; padding: 12px;")
        layout.addWidget(self._result)

        layout.addStretch()

    def set_engine(self, engine):
        self._engine = engine

    def _confirm_unlock(self) -> None:
        reply = QMessageBox.warning(
            self, "Confirm Bootloader Unlock",
            "Are you sure you want to unlock the bootloader?\n\n"
            "This may erase all data on the device.\n"
            "Make sure your backup from the previous step is complete.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._do_unlock()

    def _do_unlock(self) -> None:
        self._unlock_btn.setEnabled(False)
        self._status.setText("Unlocking bootloader... Please wait, do not disconnect!")
        self._status.setStyleSheet("color: #f0a030; font-size: 13px; padding: 8px; font-weight: bold;")
        self._result.setText("")

        self._worker = UnlockWorker(self._engine)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_log(self, msg: str, level: str) -> None:
        wizard = self.wizard()
        if wizard and hasattr(wizard, '_log'):
            wizard._log.append_log(msg, level)

    def _on_done(self, success: bool) -> None:
        self._done = success
        self._unlock_btn.setEnabled(True)
        if success:
            self._status.setText("")
            self._result.setText("BOOTLOADER UNLOCKED!")
            self._result.setStyleSheet(
                "color: #4ecca3; font-size: 22px; font-weight: bold; padding: 16px;"
            )
        else:
            self._status.setText("Unlock failed. Check the log below for details. You can retry.")
            self._status.setStyleSheet("color: #e94560; font-size: 13px; padding: 8px;")
            self._result.setText("")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._done
