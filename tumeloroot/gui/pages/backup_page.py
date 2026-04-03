"""Backup Page - partition backup with progress and verification."""

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QGroupBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from tumeloroot.core.platform_utils import get_default_backup_dir


class BackupWorker(QThread):
    progress = Signal(str, int, int)
    finished = Signal(bool, str)

    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        self._orig_progress_cb = engine._progress_cb

    def run(self):
        self._engine._progress_cb = lambda c, t, m: self.progress.emit(m, c, t)
        try:
            ok = self._engine.run_step("backup")
            path = self._engine._backup_dir or ""
            self.finished.emit(ok, path)
        finally:
            self._engine._progress_cb = self._orig_progress_cb


class BackupPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Backup Partitions")
        self._done = False
        self._engine = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Backup critical partitions before making any changes."))
        layout.addSpacing(10)

        dir_row = QHBoxLayout()
        self._dir_label = QLabel(get_default_backup_dir())
        self._dir_label.setStyleSheet("color: #a0a0b0;")
        dir_row.addWidget(QLabel("Backup to:"))
        dir_row.addWidget(self._dir_label, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._browse)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)
        layout.addSpacing(10)

        self._start_btn = QPushButton("Start Backup")
        self._start_btn.clicked.connect(self._start_backup)
        layout.addWidget(self._start_btn)

        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self._status)

        self._details = QLabel("")
        self._details.setStyleSheet("color: #a0a0b0;")
        self._details.setWordWrap(True)
        layout.addWidget(self._details)
        layout.addStretch()

    def set_engine(self, engine):
        self._engine = engine

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        if d:
            self._dir_label.setText(d)

    def _start_backup(self) -> None:
        self._start_btn.setEnabled(False)
        self._status.setText("Backing up partitions...")
        self._status.setStyleSheet("color: #f0a030; font-size: 14px; padding: 8px;")

        self._worker = BackupWorker(self._engine)
        self._worker.progress.connect(
            lambda m, c, t: self._status.setText(f"[{c+1}/{t}] Backing up {m}...")
        )
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success: bool, path: str) -> None:
        self._done = success
        self._start_btn.setEnabled(True)
        if success:
            self._status.setText("Backup completed and verified!")
            self._status.setStyleSheet("color: #4ecca3; font-size: 14px; padding: 8px;")
            self._details.setText(f"Saved to: {path}")
        else:
            self._status.setText("Backup failed!")
            self._status.setStyleSheet("color: #e94560; font-size: 14px; padding: 8px;")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._done
