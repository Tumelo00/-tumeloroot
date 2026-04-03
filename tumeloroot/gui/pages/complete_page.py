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
            "What was done:\n"
            "  - Bootloader unlocked (seccfg)\n"
            "  - vbmeta verification disabled\n"
            "  - Ramdisk patched with Magisk\n"
            "  - Patched image flashed to both A/B slots\n\n"
            "Your partition backups are safely stored.\n"
            "You can now use Magisk modules and root apps."
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
