"""Complete Page - summary and finish."""

from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PySide6.QtCore import Qt

from tumeloroot import __app_name__


class CompletePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Complete")
        self.setFinalPage(True)
        self._engine = None
        self._log_console = None

        layout = QVBoxLayout(self)

        title = QLabel(f"Congratulations!")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)

        self._summary = QLabel(
            "Your device has been successfully rooted!\n\n"
            "What was done (single BROM session):\n"
            "  \u2713 7 partitions backed up safely\n"
            "  \u2713 Bootloader unlocked (seccfg)\n"
            "  \u2713 dm-verity disabled (6 vbmeta partitions)\n"
            "  \u2713 FRP cleared (if selected)\n"
            "  \u2713 vendor_boot patched with Magisk\n"
            "  \u2713 Patched image flashed to both A/B slots\n\n"
            "IMPORTANT REMINDERS:\n"
            "  - Every reboot: hold Power button during 'orange state' warning\n"
            "  - Download & install Magisk APK from GitHub if not already done\n"
            "  - In Magisk app: 'Install to Inactive Slot' if prompted\n"
            "  - Verify root with 'Root Checker' from Google Play Store\n"
            "  - After OTA updates, you will need to re-root\n\n"
            "Your backups are in the TumelorootBackups folder.\n"
            "Keep backup files safe for emergency restore.\n\n"
            "DISCLAIMER: The developer accepts no responsibility for any\n"
            "damage, data loss, or issues resulting from this process."
        )
        self._summary.setWordWrap(True)
        self._summary.setStyleSheet("padding: 16px; background-color: #16213e; border-radius: 8px;")
        layout.addWidget(self._summary)
        layout.addSpacing(10)

        save_btn = QPushButton("Save Log")
        save_btn.setObjectName("secondary")
        save_btn.clicked.connect(self._save_log)
        layout.addWidget(save_btn)

        credit = QLabel(
            f"Powered by {__app_name__}\n"
            "Built with mtkclient & Magisk\n"
            "Share your device profile on XDA Forums!"
        )
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit.setStyleSheet("color: #6a6a8e; padding: 12px;")
        layout.addWidget(credit)
        layout.addStretch()

    def set_engine(self, engine):
        self._engine = engine

    def set_log_console(self, console):
        self._log_console = console

    def _save_log(self) -> None:
        if not self._log_console:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "tumeloroot_log.txt", "Text Files (*.txt)")
        if path:
            self._log_console.save_log(path)
