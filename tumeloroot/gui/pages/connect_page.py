"""Connect & Unlock Page - single page that does BROM connect + bootloader unlock."""

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QLabel, QPushButton, QGroupBox, QCheckBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from tumeloroot.gui.widgets.device_animation import BromAnimation


class UnlockWorker(QThread):
    """Runs mtkclient bootloader unlock as subprocess — same as terminal."""
    log = Signal(str, str)
    finished = Signal(bool)

    def __init__(self, mtk_bridge, clear_frp: bool = False):
        super().__init__()
        self._mtk = mtk_bridge
        self._clear_frp = clear_frp

    def run(self):
        self._mtk._log_cb = lambda msg, lvl: self.log.emit(msg, lvl)
        self.log.emit("Starting bootloader unlock...", "INFO")
        if self._clear_frp:
            self.log.emit("FRP clear enabled", "INFO")
        ok = self._mtk.unlock_bootloader(clear_frp=self._clear_frp)
        self.finished.emit(ok)


class ConnectPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Bootloader Unlock")
        self._done = False
        self._engine = None

        layout = QVBoxLayout(self)

        # Animation
        self._animation = BromAnimation()
        layout.addWidget(self._animation, alignment=Qt.AlignmentFlag.AlignCenter)

        # Instructions
        info = QGroupBox("How to enter BROM mode")
        info_layout = QVBoxLayout()
        steps = [
            "1.  Power OFF the tablet completely",
            "2.  Hold Power + Vol Up + Vol Down together",
            "3.  While holding, plug in USB cable",
            "4.  Release ONLY Power (keep Vol Up + Vol Down held)",
            "5.  Wait 3-5 seconds, then release all buttons",
        ]
        for step in steps:
            lbl = QLabel(step)
            lbl.setStyleSheet("padding: 6px 12px; font-size: 13px;")
            info_layout.addWidget(lbl)
        info.setLayout(info_layout)
        layout.addWidget(info)

        layout.addSpacing(8)

        # FRP checkbox
        self._frp_checkbox = QCheckBox("  Clear FRP (skip Google account setup after factory reset)")
        self._frp_checkbox.setChecked(True)
        self._frp_checkbox.setStyleSheet(
            "QCheckBox { color: #c0c0d0; font-size: 13px; padding: 8px 4px; }"
            "QCheckBox::indicator { width: 20px; height: 20px; }"
        )
        layout.addWidget(self._frp_checkbox)

        layout.addSpacing(4)

        # Retry button (hidden initially — auto-starts on page open)
        self._unlock_btn = QPushButton("Retry")
        self._unlock_btn.setObjectName("secondary")
        self._unlock_btn.setVisible(False)
        self._unlock_btn.clicked.connect(self._start_unlock)
        layout.addWidget(self._unlock_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status
        self._status = QLabel("Waiting for device...")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("color: #a0a0b0; font-size: 13px; padding: 8px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Result
        self._result = QLabel("")
        self._result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._result)

    def set_engine(self, engine):
        self._engine = engine

    def initializePage(self):
        """Auto-start unlock when page opens."""
        self._start_unlock()

    def _start_unlock(self):
        if not self._engine:
            return

        self._unlock_btn.setEnabled(False)
        self._frp_checkbox.setEnabled(False)
        self._status.setText("Waiting for device in BROM mode... Plug in now!")
        self._status.setStyleSheet("color: #f0a030; font-size: 14px; font-weight: bold; padding: 8px;")
        self._animation.set_state("connecting")
        self._result.setText("")

        from tumeloroot.core.mtk_bridge import MtkBridge
        mtk = MtkBridge(log_callback=self._on_log)

        clear_frp = self._frp_checkbox.isChecked()
        self._worker = UnlockWorker(mtk, clear_frp=clear_frp)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_log(self, msg: str, level: str = "INFO"):
        # Update status with latest message
        if "waiting" in msg.lower() or "plug" in msg.lower():
            self._status.setText(msg)
            self._status.setStyleSheet("color: #f0a030; font-size: 13px; font-weight: bold; padding: 8px;")
        elif "detected" in msg.lower():
            self._status.setText(msg)
            self._status.setStyleSheet("color: #4ecca3; font-size: 13px; font-weight: bold; padding: 8px;")
            self._animation.set_state("detected")
        elif "success" in msg.lower() or "wrote" in msg.lower():
            self._animation.set_state("connected")

        # Forward to wizard log
        wizard = self.wizard()
        if wizard and hasattr(wizard, '_log'):
            wizard._log.append_log(msg, level)

    def _on_done(self, success: bool):
        self._done = success
        if success:
            self._animation.set_state("connected")
            self._status.setText("")
            self._unlock_btn.setVisible(False)
            self._result.setText("BOOTLOADER UNLOCKED!")
            self._result.setStyleSheet("color: #4ecca3; font-size: 24px; font-weight: bold; padding: 16px;")
        else:
            self._animation.set_state("failed")
            self._status.setText("Failed — reconnect device, then click Retry")
            self._status.setStyleSheet("color: #e94560; font-size: 13px; font-weight: bold; padding: 8px;")
            self._unlock_btn.setVisible(True)
            self._unlock_btn.setEnabled(True)
            self._frp_checkbox.setEnabled(True)
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._done
