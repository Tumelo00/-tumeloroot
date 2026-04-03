"""Root Wizard - main QWizard with step indicator and log console."""

from PySide6.QtWidgets import QWizard, QVBoxLayout, QWidget, QLabel, QMessageBox
from PySide6.QtCore import Qt

from tumeloroot import __app_name__, __version__
from tumeloroot.core.engine import RootEngine
from tumeloroot.gui.widgets.log_console import LogConsole
from tumeloroot.gui.widgets.device_animation import StepIndicator
from tumeloroot.gui.pages.welcome_page import WelcomePage
from tumeloroot.gui.pages.oem_unlock_page import OemUnlockPage
from tumeloroot.gui.pages.prerequisites_page import PrerequisitesPage
from tumeloroot.gui.pages.connect_page import ConnectPage
from tumeloroot.gui.pages.backup_page import BackupPage
from tumeloroot.gui.pages.unlock_page import UnlockPage
from tumeloroot.gui.pages.patch_page import PatchPage
from tumeloroot.gui.pages.verify_page import VerifyPage
from tumeloroot.gui.pages.complete_page import CompletePage


class RootWizard(QWizard):
    """Main wizard with step indicator, log console, and all pages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} v{__version__} - MediaTek Root Tool")
        self.setMinimumSize(950, 780)
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.WizardOption.NoCancelButton, True)

        # Step indicator at top (updated for 9 steps)
        self._step_indicator = StepIndicator()
        self._step_indicator.STEPS = [
            ("Select", "device"),
            ("OEM", "unlock"),
            ("Check", "prereqs"),
            ("Connect", "BROM"),
            ("Backup", "partitions"),
            ("Unlock", "bootloader"),
            ("Patch", "& flash"),
            ("Verify", "root"),
            ("Done", "!"),
        ]

        # Log console
        self._log = LogConsole()
        self._log.setFixedHeight(110)
        self._engine = None

        # Create pages in correct order
        self._welcome = WelcomePage()
        self._oem_unlock = OemUnlockPage()
        self._prereqs = PrerequisitesPage()
        self._connect = ConnectPage()
        self._backup = BackupPage()
        self._unlock = UnlockPage()
        self._patch = PatchPage()
        self._verify = VerifyPage()
        self._complete = CompletePage()

        self._page_ids = []
        for page in [
            self._welcome,
            self._oem_unlock,
            self._prereqs,
            self._connect,
            self._backup,
            self._unlock,
            self._patch,
            self._verify,
            self._complete,
        ]:
            pid = self.addPage(page)
            self._page_ids.append(pid)

        # Button text
        self.setButtonText(QWizard.WizardButton.NextButton, "  Next >  ")
        self.setButtonText(QWizard.WizardButton.BackButton, "  < Back  ")
        self.setButtonText(QWizard.WizardButton.FinishButton, "  Finish  ")

        self.currentIdChanged.connect(self._on_page_changed)
        self._inject_widgets()

    def _inject_widgets(self):
        """Inject step indicator at top and log console above buttons."""
        main_layout = self.layout()
        if main_layout:
            main_layout.insertWidget(0, self._step_indicator)
            count = main_layout.count()
            main_layout.insertWidget(count - 1, self._log)

    def reject(self):
        reply = QMessageBox.question(
            self, "Exit Tumeloroot?",
            "Are you sure you want to exit?\n\n"
            "If a process is running, exiting may leave your device in an incomplete state.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            super().reject()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Exit Tumeloroot?",
            "Are you sure you want to exit?\n\n"
            "If a process is running, exiting may leave your device in an incomplete state.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

    def _on_page_changed(self, page_id: int) -> None:
        try:
            idx = self._page_ids.index(page_id)
            self._step_indicator.set_step(idx)
        except ValueError:
            pass

        current = self.currentPage()
        if isinstance(current, PrerequisitesPage) and self._engine is None:
            profile = self._welcome.get_selected_profile()
            if profile:
                self._init_engine(profile)

    def _init_engine(self, profile) -> None:
        def log_cb(msg, level):
            self._log.append_log(msg, level)

        def progress_cb(current, total, msg):
            pass

        self._engine = RootEngine(profile, progress_cb, log_cb)
        self._log.append_log(f"Device selected: {profile.display_name}", "INFO")

        self._connect.set_engine(self._engine)
        self._backup.set_engine(self._engine)
        self._unlock.set_engine(self._engine)
        self._patch.set_engine(self._engine)
        self._verify.set_engine(self._engine)
        self._complete.set_engine(self._engine)
        self._complete.set_log_console(self._log)

    def get_log_console(self) -> LogConsole:
        return self._log
