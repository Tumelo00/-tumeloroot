"""Progress Panel widget - step progress with status display."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt


class ProgressPanel(QWidget):
    """Shows step name, progress bar, and status text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._step_label = QLabel("Ready")
        self._step_label.setStyleSheet("font-size: 15px; font-weight: bold;")

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #a0a0b0; font-size: 12px;")

        layout.addWidget(self._step_label)
        layout.addWidget(self._progress)
        layout.addWidget(self._status)

    def set_step(self, name: str) -> None:
        self._step_label.setText(name)
        self._progress.setValue(0)
        self._status.setText("Running...")

    def set_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setValue(int(current / total * 100))

    def set_status(self, text: str, color: str = "#a0a0b0") -> None:
        self._status.setText(text)
        self._status.setStyleSheet(f"color: {color}; font-size: 12px;")

    def set_completed(self, success: bool) -> None:
        if success:
            self._progress.setValue(100)
            self.set_status("Completed", "#4ecca3")
        else:
            self.set_status("Failed", "#e94560")
