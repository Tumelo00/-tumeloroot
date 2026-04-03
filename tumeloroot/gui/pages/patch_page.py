"""Patch Page - vbmeta disable + Magisk patch + flash with explanations."""

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from tumeloroot.gui.widgets.progress_panel import ProgressPanel


class PatchWorker(QThread):
    step_update = Signal(str, str)  # step_name, status
    log = Signal(str, str)
    finished = Signal(bool)

    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        self._orig_log_cb = engine._log_cb

    def run(self):
        self._engine._log_cb = lambda msg, lvl: self.log.emit(msg, lvl)
        try:
            # Step 1: Patch vbmeta
            self.step_update.emit("vbmeta", "running")
            if not self._engine.run_step("patch_vbmeta"):
                self.step_update.emit("vbmeta", "failed")
                self.finished.emit(False)
                return
            self.step_update.emit("vbmeta", "done")

            # Step 2: Magisk patch (needs device booted to Android)
            self.step_update.emit("magisk", "running")
            if not self._engine.run_step("patch_magisk"):
                self.step_update.emit("magisk", "failed")
                self.finished.emit(False)
                return
            self.step_update.emit("magisk", "done")

            # Step 3: Flash (needs BROM reconnection)
            self.step_update.emit("flash", "running")
            if not self._engine.run_step("flash"):
                self.step_update.emit("flash", "failed")
                self.finished.emit(False)
                return
            self.step_update.emit("flash", "done")

            self.finished.emit(True)
        finally:
            self._engine._log_cb = self._orig_log_cb


class PatchPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Patch & Flash")
        self._done = False
        self._engine = None

        layout = QVBoxLayout(self)

        # Explanation
        explain = QLabel(
            "This is the main rooting step. Three things will happen:"
        )
        explain.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px;")
        layout.addWidget(explain)

        # Sub-step panels with explanations
        # 1. vbmeta
        vb_group = QGroupBox("1. Disable Verified Boot (vbmeta)")
        vb_layout = QVBoxLayout()
        vb_desc = QLabel(
            "Android checks if boot files are modified. We disable this check\n"
            "so the device accepts our modified files without blocking boot."
        )
        vb_desc.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        vb_desc.setWordWrap(True)
        vb_layout.addWidget(vb_desc)
        self._vbmeta_panel = ProgressPanel()
        self._vbmeta_panel.set_step("Disable vbmeta verification")
        vb_layout.addWidget(self._vbmeta_panel)
        vb_group.setLayout(vb_layout)
        layout.addWidget(vb_group)

        # 2. Magisk
        mg_group = QGroupBox("2. Patch with Magisk (root)")
        mg_layout = QVBoxLayout()
        mg_desc = QLabel(
            "Magisk patches the vendor_boot image to inject root access.\n"
            "The device needs to be booted to Android for this step.\n"
            "Magisk app will be installed and will patch the image automatically."
        )
        mg_desc.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        mg_desc.setWordWrap(True)
        mg_layout.addWidget(mg_desc)
        self._magisk_panel = ProgressPanel()
        self._magisk_panel.set_step("Patch vendor_boot with Magisk")
        mg_layout.addWidget(self._magisk_panel)
        mg_group.setLayout(mg_layout)
        layout.addWidget(mg_group)

        # 3. Flash
        fl_group = QGroupBox("3. Flash to Device")
        fl_layout = QVBoxLayout()
        fl_desc = QLabel(
            "Write the patched image back to the device (both A and B slots).\n"
            "This requires reconnecting in BROM mode."
        )
        fl_desc.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        fl_desc.setWordWrap(True)
        fl_layout.addWidget(fl_desc)
        self._flash_panel = ProgressPanel()
        self._flash_panel.set_step("Flash patched vendor_boot")
        fl_layout.addWidget(self._flash_panel)
        fl_group.setLayout(fl_layout)
        layout.addWidget(fl_group)

        layout.addSpacing(8)

        # Start button
        self._start_btn = QPushButton("Start Patching")
        self._start_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 12px 28px; }")
        self._start_btn.clicked.connect(self._start)
        layout.addWidget(self._start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Final status
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self._status)

    def set_engine(self, engine):
        self._engine = engine

    def _start(self) -> None:
        self._start_btn.setEnabled(False)
        self._status.setText("Patching in progress... Do not disconnect!")
        self._status.setStyleSheet("color: #f0a030; font-size: 14px; padding: 8px; font-weight: bold;")

        self._panels = {
            "vbmeta": self._vbmeta_panel,
            "magisk": self._magisk_panel,
            "flash": self._flash_panel,
        }

        self._worker = PatchWorker(self._engine)
        self._worker.step_update.connect(self._on_step_update)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_step_update(self, step: str, status: str) -> None:
        panel = self._panels.get(step)
        if not panel:
            return
        if status == "running":
            panel.set_status("Running...", "#f0a030")
        elif status == "done":
            panel.set_completed(True)
        elif status == "failed":
            panel.set_completed(False)

    def _on_log(self, msg: str, level: str) -> None:
        wizard = self.wizard()
        if wizard and hasattr(wizard, '_log'):
            wizard._log.append_log(msg, level)

    def _on_done(self, success: bool) -> None:
        self._done = success
        self._start_btn.setEnabled(True)
        if success:
            self._status.setText("All patches applied and flashed!")
            self._status.setStyleSheet("color: #4ecca3; font-size: 16px; padding: 8px; font-weight: bold;")
        else:
            self._status.setText("Patching failed. Check log for details. You can retry.")
            self._status.setStyleSheet("color: #e94560; font-size: 14px; padding: 8px;")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._done
