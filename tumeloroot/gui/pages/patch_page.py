"""Patch Page - single BROM session: backup + unlock + root (all-in-one)."""

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QLabel, QPushButton, QGroupBox, QCheckBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from tumeloroot.gui.widgets.progress_panel import ProgressPanel
from tumeloroot.gui.widgets.device_animation import BromAnimation


class UnlockRootWorker(QThread):
    """Single BROM session: backup + unlock + Magisk root."""
    step_update = Signal(str, str)
    log = Signal(str, str)
    finished = Signal(bool)

    def __init__(self, engine, clear_frp: bool = False):
        super().__init__()
        self._engine = engine
        self._clear_frp = clear_frp
        self._orig_log_cb = engine._log_cb

    def run(self):
        self._engine._log_cb = lambda msg, lvl: self.log.emit(msg, lvl)
        try:
            self.step_update.emit("unlock_root", "running")
            success = self._engine.run_step(
                "unlock_and_root", clear_frp=self._clear_frp,
            )
            if success:
                self.step_update.emit("unlock_root", "done")
            else:
                self.step_update.emit("unlock_root", "failed")
            self.finished.emit(success)
        finally:
            self._engine._log_cb = self._orig_log_cb


class PatchPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Unlock & Root")
        self._done = False
        self._engine = None
        self._started = False

        layout = QVBoxLayout(self)

        # Animation
        self._animation = BromAnimation()
        layout.addWidget(self._animation, alignment=Qt.AlignmentFlag.AlignCenter)

        # Header
        header = QLabel(
            "Single BROM session does everything:\n"
            "Backup + Unlock + Vbmeta + FRP + Magisk Patch + Flash"
        )
        header.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px;")
        header.setWordWrap(True)
        layout.addWidget(header)

        # How it works
        explain_group = QGroupBox("Single BROM session - does EVERYTHING")
        explain_layout = QVBoxLayout()
        explain = QLabel(
            "1. Backup critical partitions (seccfg, boot, vendor_boot, vbmeta)\n"
            "2. Unlock bootloader (seccfg modification)\n"
            "3. Disable dm-verity (vbmeta flags=3 on all 6 partitions)\n"
            "4. Clear FRP (optional - skip Google account after reset)\n"
            "5. Read vendor_boot from device (64 MB)\n"
            "6. Patch with Magisk on PC (magiskboot via WSL)\n"
            "7. Flash patched vendor_boot to BOTH A/B slots\n\n"
            "All steps run in ONE BROM connection. DO NOT close the CMD window!"
        )
        explain.setWordWrap(True)
        explain.setStyleSheet(
            "color: #a0a0b0; font-size: 12px; line-height: 1.4; padding: 4px;"
        )
        explain_layout.addWidget(explain)
        explain_group.setLayout(explain_layout)
        layout.addWidget(explain_group)

        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self._root_panel = ProgressPanel()
        self._root_panel.set_step("Backup + Unlock + Root + Flash (single BROM session)")
        progress_layout.addWidget(self._root_panel)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Instructions
        self._instr = QLabel(
            "Enter BROM mode:\n"
            "  1. Power OFF the device completely\n"
            "  2. Hold Power + Vol Up + Vol Down together\n"
            "  3. While holding all three buttons, plug USB cable into PC\n"
            "  4. Wait 3-5 seconds, then release\n\n"
            "The app scans for your device automatically."
        )
        self._instr.setWordWrap(True)
        self._instr.setStyleSheet(
            "color: #f0a030; padding: 10px; background-color: #2a2a1e; "
            "border-radius: 6px; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(self._instr)

        layout.addSpacing(4)

        # FRP checkbox
        self._frp_checkbox = QCheckBox(
            "  Clear FRP (skip Google account setup after factory reset)"
        )
        self._frp_checkbox.setChecked(True)
        self._frp_checkbox.setStyleSheet(
            "QCheckBox { color: #c0c0d0; font-size: 13px; padding: 8px 4px; }"
            "QCheckBox::indicator { width: 20px; height: 20px; }"
        )
        layout.addWidget(self._frp_checkbox)

        layout.addSpacing(4)

        # Retry button (hidden initially, shown on failure)
        self._retry_btn = QPushButton("Retry")
        self._retry_btn.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 10px 28px; }"
        )
        self._retry_btn.clicked.connect(self._retry)
        self._retry_btn.setVisible(False)
        layout.addWidget(self._retry_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("font-size: 14px; padding: 8px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

    def set_engine(self, engine):
        self._engine = engine

    def initializePage(self):
        """Auto-start when page opens - no button needed."""
        if not self._started and self._engine:
            # Small delay so the page renders first
            QTimer.singleShot(500, self._auto_start)

    def _auto_start(self):
        """Start the process automatically."""
        if self._started:
            return
        self._started = True
        self._frp_checkbox.setEnabled(False)
        self._status.setText(
            "Scanning for device... Enter BROM mode now!"
        )
        self._status.setStyleSheet(
            "color: #f0a030; font-size: 14px; padding: 8px; font-weight: bold;"
        )
        self._animation.set_state("connecting")

        clear_frp = self._frp_checkbox.isChecked()
        self._worker = UnlockRootWorker(self._engine, clear_frp=clear_frp)
        self._worker.step_update.connect(self._on_step_update)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _retry(self):
        """Retry after failure."""
        self._started = False
        self._retry_btn.setVisible(False)
        self._root_panel.set_status("", "#a0a0b0")
        self._auto_start()

    def _on_step_update(self, step: str, status: str) -> None:
        if status == "running":
            self._root_panel.set_status("Running...", "#f0a030")
            self._status.setText("BROM session active - working...")
            self._status.setStyleSheet(
                "color: #f0a030; font-size: 13px; padding: 8px; font-weight: bold;"
            )
        elif status == "done":
            self._root_panel.set_completed(True)
            self._animation.set_state("connected")
        elif status == "failed":
            self._root_panel.set_completed(False)
            self._animation.set_state("failed")

    def _on_log(self, msg: str, level: str) -> None:
        wizard = self.wizard()
        if wizard and hasattr(wizard, '_log'):
            wizard._log.append_log(msg, level)

        # Update status with key messages
        low = msg.lower()
        if "scanning" in low or "waiting" in low:
            self._status.setText("Scanning for device... Enter BROM mode now!")
            self._status.setStyleSheet(
                "color: #f0a030; font-size: 14px; padding: 8px; font-weight: bold;"
            )
        elif "mediatek device found" in low or "detected" in low:
            self._status.setText(msg)
            self._status.setStyleSheet(
                "color: #4ecca3; font-size: 14px; padding: 8px; font-weight: bold;"
            )
            self._animation.set_state("detected")
        elif "connected" in low and "configur" in low:
            self._status.setText("Device connected! Processing...")
            self._status.setStyleSheet(
                "color: #4ecca3; font-size: 14px; padding: 8px; font-weight: bold;"
            )
        elif "backing up" in low or "backup" in low and "step" in low:
            self._status.setText("Backing up partitions...")
            self._status.setStyleSheet(
                "color: #7ec8e3; font-size: 13px; padding: 8px; font-weight: bold;"
            )
        elif "unlock" in low and ("success" in low or "done" in low or "wrote" in low):
            self._status.setText("Bootloader unlocked!")
            self._status.setStyleSheet(
                "color: #4ecca3; font-size: 13px; padding: 8px; font-weight: bold;"
            )
        elif "stock image ready" in low or "magisk patch" in low:
            self._status.setText("Patching with Magisk...")
            self._status.setStyleSheet(
                "color: #7ec8e3; font-size: 13px; padding: 8px; font-weight: bold;"
            )
        elif "flash" in low and ("slot" in low or "wrote" in low):
            self._status.setText("Flashing patched image to device...")
            self._status.setStyleSheet(
                "color: #f0a030; font-size: 13px; padding: 8px; font-weight: bold;"
            )

    def _on_done(self, success: bool) -> None:
        self._done = success
        self._frp_checkbox.setEnabled(True)
        if success:
            self._status.setText(
                "UNLOCK + ROOT COMPLETE!\n"
                "Reboot device and HOLD Power button during orange state warning.\n"
                "Install Magisk APK > try 'Direct Install' first, otherwise 'Install to Inactive Slot'."
            )
            self._status.setStyleSheet(
                "color: #4ecca3; font-size: 16px; padding: 8px; font-weight: bold;"
            )
            self._animation.set_state("connected")
            self._retry_btn.setVisible(False)
        else:
            self._status.setText(
                "Failed. Check log for details. Click Retry to try again."
            )
            self._status.setStyleSheet(
                "color: #e94560; font-size: 14px; padding: 8px;"
            )
            self._animation.set_state("failed")
            self._retry_btn.setVisible(True)
            self._started = False
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._done
