"""Connect Page - BROM mode device connection with auto-detection and animation."""

from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from tumeloroot.gui.widgets.device_animation import BromAnimation, InstructionPanel


class BromScanner(QThread):
    """Background thread that continuously scans for MediaTek device in BROM mode."""
    device_found = Signal()
    log = Signal(str, str)

    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        """Scan for USB device with VID 0x0E8D."""
        self.log.emit("Scanning USB for MediaTek device...", "INFO")
        try:
            import usb.core
            while self._running:
                devs = list(usb.core.find(find_all=True, idVendor=0x0E8D))
                if devs:
                    self.log.emit(f"MediaTek USB device detected! ({len(devs)} device(s))", "SUCCESS")
                    self.device_found.emit()
                    return
                self.msleep(500)
        except ImportError:
            self.log.emit("pyusb not available, using manual connection", "WARNING")
        except Exception as e:
            self.log.emit(f"USB scan error: {e}", "WARNING")


class ConnectWorker(QThread):
    """Worker thread for BROM connection."""
    finished = Signal(bool, dict)
    log = Signal(str, str)

    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        # Store original callback and restore after
        self._orig_log_cb = engine._log_cb

    def run(self):
        # Thread-safe: emit signals instead of direct UI calls
        log_emitter = lambda msg, lvl: self.log.emit(msg, lvl)
        self._engine._log_cb = log_emitter
        try:
            ok = self._engine.run_step("connect")
            info = self._engine._mtk.get_device_info() if ok else {}
            self.finished.emit(ok, info)
        finally:
            self._engine._log_cb = self._orig_log_cb


class ConnectPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Connect Device")
        self._connected = False
        self._engine = None
        self._scanner = None

        layout = QVBoxLayout(self)

        # Animation
        self._animation = BromAnimation()
        layout.addWidget(self._animation, alignment=Qt.AlignmentFlag.AlignCenter)

        # Default instructions (overridden by device profile)
        self._instructions = InstructionPanel()
        self._instructions.set_instructions([
            "Power OFF the tablet completely",
            "Hold Power + Vol Up + Vol Down all together",
            "While holding ALL 3 buttons, plug in USB cable",
            "Release ONLY the Power button (keep Vol Up + Vol Down held!)",
            "Wait 3-5 seconds, then release Vol Up + Vol Down",
            "Auto-detection will connect automatically",
        ])
        layout.addWidget(self._instructions)
        layout.addSpacing(8)

        # Status
        btn_row = QHBoxLayout()
        self._status = QLabel("Plug in your device — auto-detection is active")
        self._status.setStyleSheet("color: #f0a030; font-size: 13px; font-weight: bold; padding: 4px;")
        btn_row.addWidget(self._status, 1)

        self._retry_btn = QPushButton("Retry")
        self._retry_btn.setObjectName("secondary")
        self._retry_btn.setVisible(False)
        self._retry_btn.clicked.connect(self._start_scan)
        btn_row.addWidget(self._retry_btn)
        layout.addLayout(btn_row)

        # Device info
        self._device_info = QLabel("")
        self._device_info.setStyleSheet("color: #a0a0b0; font-size: 12px;")
        layout.addWidget(self._device_info)

    def set_engine(self, engine):
        self._engine = engine

    def initializePage(self) -> None:
        """Start auto-scanning when page opens."""
        if self._engine:
            steps = self._engine.profile.brom_instructions.steps + ["Auto-detection will connect automatically"]
            self._instructions.set_instructions(steps)

        self._instructions.highlight_step(0)
        self._animation.set_state("waiting")
        self._start_scan()

    def _start_scan(self) -> None:
        """Start background USB scanning."""
        self._retry_btn.setVisible(False)
        self._status.setText("Scanning USB for device... Plug in now!")
        self._status.setStyleSheet("color: #f0a030; font-size: 13px; font-weight: bold; padding: 4px;")
        self._animation.set_state("waiting")
        self._instructions.highlight_step(0)

        if self._scanner and self._scanner.isRunning():
            self._scanner.stop()
            self._scanner.wait()

        self._scanner = BromScanner()
        self._scanner.device_found.connect(self._on_device_found)
        self._scanner.log.connect(self._on_log)
        self._scanner.start()

    def _on_device_found(self) -> None:
        """Device USB detected — now connect via mtkclient."""
        self._animation.set_state("detected")
        self._instructions.highlight_step(3)
        self._status.setText("Device detected! Connecting via BROM...")
        self._status.setStyleSheet("color: #4ecca3; font-size: 13px; font-weight: bold; padding: 4px;")

        # Auto-start BROM connection
        self._animation.set_state("connecting")
        self._worker = ConnectWorker(self._engine)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_connected)
        self._worker.start()

    def _on_connected(self, success: bool, info: dict) -> None:
        self._connected = success
        if success:
            self._animation.set_state("connected")
            self._instructions.highlight_step(5)
            self._status.setText("CONNECTED! Device ready.")
            self._status.setStyleSheet("color: #4ecca3; font-size: 14px; font-weight: bold; padding: 4px;")
            info_text = " | ".join(f"{k}: {v}" for k, v in info.items()) if info else "Connected"
            self._device_info.setText(info_text)
        else:
            self._animation.set_state("failed")
            self._status.setText("Connection failed. Disconnect USB, retry BROM mode.")
            self._status.setStyleSheet("color: #e94560; font-size: 13px; font-weight: bold; padding: 4px;")
            self._retry_btn.setVisible(True)
        self.completeChanged.emit()

    def _on_log(self, msg: str, level: str = "INFO") -> None:
        wizard = self.wizard()
        if wizard and hasattr(wizard, '_log'):
            wizard._log.append_log(msg, level)

    def cleanupPage(self) -> None:
        if self._scanner and self._scanner.isRunning():
            self._scanner.stop()

    def isComplete(self) -> bool:
        return self._connected
