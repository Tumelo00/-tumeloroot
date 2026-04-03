"""Tumeloroot Application - main entry point."""

import sys
import logging

from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QWidget, QDialog, QLabel,
    QTextBrowser, QPushButton, QHBoxLayout, QCheckBox,
)
from PySide6.QtCore import Qt

from tumeloroot import __app_name__, __version__
from tumeloroot.gui.theme import load_dark_theme
from tumeloroot.gui.wizard import RootWizard


DISCLAIMER_TEXT = f"""
<h2 style="color: #e94560; text-align: center;">{__app_name__} v{__version__}</h2>
<h3 style="color: #e94560; text-align: center;">END USER LICENSE AGREEMENT & DISCLAIMER</h3>
<hr>

<p>By using this software, you acknowledge and agree to the following terms and conditions.
<b>If you do not agree, close this application immediately.</b></p>

<h3 style="color: #f0a030;">1. ASSUMPTION OF RISK</h3>
<p>You acknowledge that bootloader unlocking and device rooting are <b>inherently risky operations</b>.
These operations modify critical system partitions and security configurations of your device.
<b>You assume all risks</b> associated with using this software, including but not limited to:</p>
<ul>
<li>Permanent device damage (bricking)</li>
<li>Complete data loss</li>
<li>Voiding of manufacturer warranty</li>
<li>Loss of access to secure applications (banking, DRM, etc.)</li>
<li>Security vulnerabilities introduced by unlocked bootloader</li>
<li>Device instability or boot failures</li>
</ul>

<h3 style="color: #f0a030;">2. NO WARRANTY</h3>
<p>This software is provided <b>"AS IS" without warranty of any kind</b>, express or implied,
including but not limited to the warranties of merchantability, fitness for a particular purpose,
and noninfringement. The entire risk as to the quality and performance of the software is with you.</p>

<h3 style="color: #f0a030;">3. LIMITATION OF LIABILITY</h3>
<p>In no event shall the authors, contributors, or copyright holders of {__app_name__} be liable
for <b>any claim, damages, or other liability</b>, whether in an action of contract, tort, or otherwise,
arising from, out of, or in connection with the software or the use or other dealings in the software.
This includes but is not limited to:</p>
<ul>
<li>Direct, indirect, incidental, special, or consequential damages</li>
<li>Loss of data, profits, or business opportunities</li>
<li>Device repair or replacement costs</li>
<li>Any damages resulting from device malfunction</li>
</ul>

<h3 style="color: #f0a030;">4. USER RESPONSIBILITY</h3>
<p>You are solely responsible for:</p>
<ul>
<li>Backing up all important data before using this software</li>
<li>Ensuring your device is compatible with the selected device profile</li>
<li>Understanding the consequences of bootloader unlocking and rooting</li>
<li>Complying with all applicable laws and regulations in your jurisdiction</li>
<li>Any modifications made to your device through this software</li>
</ul>

<h3 style="color: #f0a030;">5. NOT AFFILIATED</h3>
<p>{__app_name__} is <b>not affiliated with, endorsed by, or sponsored by</b> any device manufacturer,
including but not limited to Lenovo, MediaTek, Google, or any other company.
All trademarks are property of their respective owners.</p>

<h3 style="color: #f0a030;">6. OPEN SOURCE</h3>
<p>This software is licensed under the <b>GNU General Public License v3</b> with additional
name protection terms. You may modify and redistribute this software under a different name,
but the name "{__app_name__}" is protected and must not be used for modified versions.</p>

<hr>
<p style="text-align: center; color: #a0a0b0;">
<i>By clicking "I Accept" below, you confirm that you have read, understood, and agree
to all terms stated above. You acknowledge that the developers bear no responsibility
for any damage to your device.</i></p>
"""


class DisclaimerDialog(QDialog):
    """Disclaimer dialog that must be accepted before the app launches."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} - License Agreement")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        self._accepted = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Scrollable text
        browser = QTextBrowser()
        browser.setHtml(DISCLAIMER_TEXT)
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet(
            "QTextBrowser { background-color: #0f0f1e; color: #d0d0e0; "
            "border: 1px solid #2a2a4e; border-radius: 6px; padding: 12px; "
            "font-size: 13px; }"
        )
        layout.addWidget(browser)

        # Checkbox
        self._checkbox = QCheckBox(
            "I have read and accept all terms above. I understand that the developers "
            "are NOT responsible for any damage to my device."
        )
        self._checkbox.setStyleSheet("QCheckBox { color: #e0e0e0; font-weight: bold; padding: 8px; }")
        self._checkbox.stateChanged.connect(self._on_check_changed)
        layout.addWidget(self._checkbox)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._decline_btn = QPushButton("Decline && Exit")
        self._decline_btn.setStyleSheet(
            "QPushButton { background-color: #3a3a5e; color: #a0a0b0; "
            "border: none; padding: 10px 24px; border-radius: 6px; font-weight: bold; }"
            "QPushButton:hover { background-color: #4a4a6e; }"
        )
        self._decline_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._decline_btn)

        self._accept_btn = QPushButton("I Accept")
        self._accept_btn.setEnabled(False)
        self._accept_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(self._accept_btn)

        layout.addLayout(btn_layout)

    def _on_check_changed(self, state: int) -> None:
        self._accept_btn.setEnabled(state == 2)  # Qt.Checked = 2

    def _on_accept(self) -> None:
        self._accepted = True
        self.accept()

    @property
    def was_accepted(self) -> bool:
        return self._accepted


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """Main entry point for Tumeloroot GUI application."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {__app_name__} v{__version__}")

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)

    # Apply dark theme
    load_dark_theme(app)

    # Show disclaimer - must accept before proceeding
    disclaimer = DisclaimerDialog()
    if disclaimer.exec() != QDialog.DialogCode.Accepted or not disclaimer.was_accepted:
        logger.info("Disclaimer declined. Exiting.")
        sys.exit(0)

    logger.info("Disclaimer accepted. Launching main application.")

    # Launch wizard as standalone window (keeps native Next/Back/Cancel buttons)
    wizard = RootWizard()
    log_console = wizard.get_log_console()
    log_console.append_log(f"{__app_name__} v{__version__} ready", "SUCCESS")
    log_console.append_log("Select your device and click Next to begin", "INFO")

    wizard.finished.connect(lambda result: app.quit())
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
