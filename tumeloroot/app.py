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

<h3 style="color: #f0a030;">1. INTENDED PURPOSE &mdash; EDUCATIONAL AND RESEARCH USE ONLY</h3>
<p>{__app_name__} is developed and distributed <b>strictly for educational and security research
purposes</b>. Its primary goal is to allow advanced users, developers, and security researchers to
study MediaTek device boot chains, bootloader security, and Android system internals on devices
they legally own.</p>
<p>This software includes functionality for bootloader unlocking, rooting (via Magisk patching),
vbmeta/dm-verity modification, and <b>FRP (Factory Reset Protection) clearing</b>. The FRP clearing
feature is provided solely to assist legitimate device owners who have been locked out of their
own devices (e.g., after a factory reset where the original Google account credentials are
unavailable).</p>

<h3 style="color: #f0a030;">2. LEGAL OWNERSHIP REQUIREMENT</h3>
<p><b>You MUST be the legal owner of any device you modify using this software.</b> By using
{__app_name__}, you represent and warrant that:</p>
<ul>
<li>You are the lawful owner of the target device, or you have explicit written authorization
from the legal owner to perform these modifications.</li>
<li>The device is not stolen, lost, or subject to any dispute of ownership.</li>
<li>You are not using this software to circumvent theft protection mechanisms (including FRP)
on any device that you do not legally own.</li>
</ul>
<p style="color: #ff4444;"><b>WARNING: Using FRP bypass tools on stolen or unlawfully obtained
devices is a criminal offense in most jurisdictions and may result in prosecution.</b></p>

<h3 style="color: #f0a030;">3. LEGAL COMPLIANCE</h3>
<p>You acknowledge that the use of this software may be subject to various laws and regulations,
including but not limited to:</p>
<ul>
<li>The <b>Digital Millennium Copyright Act (DMCA)</b> (United States)</li>
<li>The <b>Computer Fraud and Abuse Act (CFAA)</b> (United States)</li>
<li>The <b>Computer Misuse Act</b> (United Kingdom)</li>
<li>The <b>Turkish Penal Code (TCK)</b> provisions on unauthorized access to information systems
(Articles 243&ndash;245)</li>
<li>The <b>EU Directive on Attacks Against Information Systems</b> (2013/40/EU)</li>
<li>Equivalent computer crime and intellectual property laws in your jurisdiction</li>
</ul>
<p>You are solely responsible for determining whether your use of this software complies with
all applicable local, national, and international laws. The developers make no representation
that the use of this software is legal in your jurisdiction for your intended purpose.</p>

<h3 style="color: #f0a030;">4. PROHIBITED USES &mdash; ANTI-MISUSE</h3>
<p>The developers of {__app_name__} <b>do NOT encourage, condone, support, or facilitate</b> any
illegal or unethical use of this software. The following uses are <b>strictly prohibited</b>:</p>
<ul>
<li>Bypassing FRP or any theft protection on devices the user does not legally own</li>
<li>Gaining unauthorized access to devices, accounts, or data belonging to others</li>
<li>Reselling, trafficking, or distributing stolen or illegally modified devices</li>
<li>Offering paid "FRP unlock" or "phone unlocking" services using this software</li>
<li>Using this software as part of a commercial phone repair/unlock business that
processes devices without verifying the customer's legal ownership</li>
<li>Modifying or repackaging this software to remove or obscure these anti-misuse warnings,
ownership checks, or legal disclaimers</li>
<li>Distributing this software through channels that primarily serve device theft
(e.g., forums, groups, or services dedicated to unlocking stolen phones)</li>
<li>Using this software on devices subject to law enforcement holds, court orders,
or active theft investigations</li>
<li>Any activity that violates applicable laws or infringes on the rights of others</li>
</ul>
<p style="color: #ff4444;"><b>This software is NOT a commercial FRP bypass tool. It is an
educational and research tool. Any use for unlocking stolen devices, running paid unlock
services, or similar activities is a violation of this agreement and may constitute a
criminal offense.</b></p>

<h3 style="color: #f0a030;">5. ASSUMPTION OF RISK</h3>
<p>You acknowledge that bootloader unlocking, rooting, vbmeta flashing, dm-verity disabling,
and FRP clearing are <b>inherently risky operations</b>. These operations modify critical system
partitions and security configurations of your device.
<b>You assume all risks</b> associated with using this software, including but not limited to:</p>
<ul>
<li>Permanent device damage (bricking)</li>
<li>Complete and irrecoverable data loss</li>
<li>Voiding of manufacturer warranty</li>
<li>Loss of access to secure applications (banking, DRM, SafetyNet/Play Integrity, etc.)</li>
<li>Security vulnerabilities introduced by an unlocked bootloader or disabled dm-verity</li>
<li>Device instability, boot loops, or boot failures</li>
<li>Loss of OTA (over-the-air) update capability</li>
<li>Potential legal consequences arising from misuse</li>
</ul>

<h3 style="color: #f0a030;">6. NO WARRANTY</h3>
<p>This software is provided <b>"AS IS" and "AS AVAILABLE" without warranty of any kind</b>,
express or implied, including but not limited to the warranties of merchantability, fitness for
a particular purpose, noninfringement, and accuracy. The entire risk as to the quality,
performance, and results of the software is with you. No oral or written information or advice
given by the developers shall create a warranty.</p>

<h3 style="color: #f0a030;">7. LIMITATION OF LIABILITY</h3>
<p>In no event shall the authors, contributors, or copyright holders of {__app_name__} be liable
for <b>any claim, damages, or other liability</b>, whether in an action of contract, tort, or
otherwise, arising from, out of, or in connection with the software or the use or other dealings
in the software. This includes but is not limited to:</p>
<ul>
<li>Direct, indirect, incidental, special, exemplary, or consequential damages</li>
<li>Loss of data, profits, goodwill, or business opportunities</li>
<li>Device repair or replacement costs</li>
<li>Any damages resulting from device malfunction or bricking</li>
<li>Legal fees or penalties arising from misuse of the software</li>
<li>Any third-party claims related to your use of the software</li>
</ul>

<h3 style="color: #f0a030;">8. USER RESPONSIBILITY</h3>
<p><b>You assume ALL legal responsibility</b> for how you use this software. You are solely
responsible for:</p>
<ul>
<li>Ensuring you are the legal owner of (or have authorization to modify) the target device</li>
<li>Backing up all important data before using this software</li>
<li>Ensuring your device is compatible with the selected device profile</li>
<li>Understanding the consequences of bootloader unlocking, rooting, vbmeta modification,
dm-verity disabling, and FRP clearing</li>
<li>Complying with all applicable laws and regulations in your jurisdiction</li>
<li>Any modifications made to your device through this software</li>
<li>Any legal consequences that may arise from your use of this software</li>
</ul>

<h3 style="color: #f0a030;">9. NOT AFFILIATED</h3>
<p>{__app_name__} is <b>not affiliated with, endorsed by, or sponsored by</b> any device manufacturer,
chipset maker, or software provider, including but not limited to Lenovo, MediaTek, Google,
the Magisk/topjohnwu project, or any other company or individual. All product names, trademarks,
and registered trademarks are property of their respective owners. Any references to third-party
products or services are for identification purposes only.</p>

<h3 style="color: #f0a030;">10. OPEN SOURCE LICENSE</h3>
<p>This software is licensed under the <b>GNU General Public License v3 (GPLv3)</b> with additional
terms as permitted by Section 7 of the GPL. You may modify and redistribute this software under
a different name in compliance with the GPLv3, but the name "{__app_name__}" is protected under
the additional terms and must not be used for modified or derivative versions.</p>

<h3 style="color: #f0a030;">11. CONTRIBUTION & DERIVATIVE WORKS</h3>
<p>If you develop <b>device profiles, patches, bug fixes, or new features</b> using the {__app_name__}
framework, architecture, or codebase, you are <b>strongly encouraged to contribute</b> those
improvements back to the original {__app_name__} project. This ensures the community benefits
from collective work and prevents fragmentation.</p>
<p>Per the terms of the GPLv3 license and the additional terms below:</p>
<ul>
<li>Any <b>derivative work</b> that uses {__app_name__}'s core architecture (BROM bridge, boot patcher,
device profile system, or GUI wizard framework) must be distributed under the same GPLv3 license
and must include <b>prominent attribution</b> to the original {__app_name__} project.</li>
<li>Derivative works must clearly indicate which portions originate from {__app_name__} and include
a link to the original project repository.</li>
<li>Device profiles (YAML files) created using {__app_name__}'s profile format and tooling are
considered part of the {__app_name__} ecosystem. Contributors are encouraged to submit these
profiles to the upstream project so all users benefit.</li>
<li>Distributing closed-source or proprietary software built on {__app_name__}'s GPLv3-licensed
code is a <b>violation of the license</b>.</li>
</ul>

<h3 style="color: #f0a030;">12. FREE DISTRIBUTION REQUIREMENT</h3>
<p>{__app_name__} is and will always be <b>free software</b>. As an additional condition under
Section 7 of the GPLv3:</p>
<ul>
<li><b>Derivative works must be distributed free of charge.</b> You may NOT sell, license for a fee,
or otherwise charge money for any software that is based on, derived from, or incorporates
{__app_name__}'s code, architecture, or device profile format.</li>
<li>You may NOT bundle {__app_name__} or any derivative with paid products, paid subscriptions,
or premium services. This includes "freemium" models where core functionality derived from
{__app_name__} is locked behind a paywall.</li>
<li>You may NOT offer {__app_name__} or any derivative as a paid service (e.g., "pay-per-unlock",
"premium rooting service", etc.).</li>
<li>You may accept <b>voluntary donations</b> for your derivative work, provided that the software
itself remains freely available to all users regardless of whether they donate.</li>
<li>This requirement applies to the software itself. It does not restrict charging for unrelated
services such as hardware repair, consulting, or technical support, provided the software
is still distributed for free.</li>
</ul>
<p style="color: #e94560;"><b>Selling or commercially exploiting {__app_name__} or any derivative
work based on its code is a violation of this license.</b></p>

<p style="color: #4ecca3;"><b>Help the project grow: submit your device profiles, bug fixes,
and improvements back to {__app_name__} so the entire community benefits!</b></p>

<h3 style="color: #f0a030;">12. GOVERNING LAW</h3>
<p>To the extent permitted by applicable law, this agreement and any disputes arising from the
use of this software shall be governed by the laws of the <b>Republic of Turkey</b>. The developer
is based in Turkey and complies with Turkish law, including the Turkish Penal Code (TCK) and
Law No. 5651 on the Regulation of Publications on the Internet. Users in other jurisdictions are
responsible for compliance with their own local laws.</p>

<hr>
<p style="text-align: center; color: #a0a0b0;">
<i>By clicking "I Accept" below, you confirm that you have read, understood, and agree
to all terms stated above. You confirm that you are the legal owner of (or have authorization
to modify) the device you intend to use with this software. You acknowledge that the developers
bear no responsibility for any damage to your device or any legal consequences arising from
your use of this software.</i></p>
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
            "I have read and accept all terms above. I confirm that I am the LEGAL OWNER "
            "of the device I intend to modify. I understand that the developers are NOT "
            "responsible for any damage to my device or legal consequences of misuse."
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
