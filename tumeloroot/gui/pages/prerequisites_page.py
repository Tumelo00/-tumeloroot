"""Prerequisites Page - check and install dependencies."""

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout,
)
from PySide6.QtCore import Qt, QThread, Signal

from tumeloroot.core.prerequisite_checker import PrerequisiteChecker


class CheckWorker(QThread):
    finished = Signal(list)

    def __init__(self):
        super().__init__()
        self._checker = PrerequisiteChecker()

    def run(self):
        results = self._checker.check_all()
        self.finished.emit(results)


class PrerequisitesPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Prerequisites")
        self._all_ok = False
        self._results = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Checking required tools and drivers..."))
        layout.addSpacing(10)

        self._group = QGroupBox("Dependencies")
        self._grid = QGridLayout()
        self._group.setLayout(self._grid)
        layout.addWidget(self._group)

        self._status_labels: list[tuple[QLabel, QLabel]] = []

        btn_row = QHBoxLayout()
        self._check_btn = QPushButton("Check All")
        self._check_btn.clicked.connect(self._run_check)
        btn_row.addWidget(self._check_btn)

        self._install_btn = QPushButton("Install Missing")
        self._install_btn.setObjectName("secondary")
        self._install_btn.setEnabled(False)
        self._install_btn.clicked.connect(self._install_missing)
        btn_row.addWidget(self._install_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()

    def initializePage(self) -> None:
        self._run_check()

    def _run_check(self) -> None:
        self._check_btn.setEnabled(False)
        self._worker = CheckWorker()
        self._worker.finished.connect(self._on_check_done)
        self._worker.start()

    def _on_check_done(self, results) -> None:
        self._results = results
        # Clear grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._status_labels.clear()

        has_missing = False
        for i, r in enumerate(results):
            icon = QLabel("  OK  " if r.available else " MISS ")
            icon.setStyleSheet(
                f"color: {'#4ecca3' if r.available else '#e94560'}; font-weight: bold; "
                f"background-color: {'#1a3a2e' if r.available else '#3a1a1e'}; "
                f"border-radius: 3px; padding: 4px 8px;"
            )
            name = QLabel(r.name)
            name.setStyleSheet("font-weight: bold;")
            ver = QLabel(r.version)
            ver.setStyleSheet("color: #a0a0b0;")
            self._grid.addWidget(icon, i, 0)
            self._grid.addWidget(name, i, 1)
            self._grid.addWidget(ver, i, 2)
            self._status_labels.append((name, ver))
            if r.required and not r.available:
                has_missing = True

        self._all_ok = not has_missing
        self._check_btn.setEnabled(True)
        self._install_btn.setEnabled(has_missing)
        self.completeChanged.emit()

    def _install_missing(self) -> None:
        for r in self._results:
            if not r.available and r.install_func:
                r.install_func()
        self._run_check()

    def isComplete(self) -> bool:
        return self._all_ok
