"""Log Console widget - colored read-only log display."""

from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QTextCharFormat, QColor, QFont


LEVEL_COLORS = {
    "INFO": "#c0c0d0",
    "WARNING": "#f0a030",
    "ERROR": "#e94560",
    "SUCCESS": "#4ecca3",
    "DEBUG": "#6a6a8e",
}


class LogConsole(QPlainTextEdit):
    """Read-only colored log display widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setStyleSheet(
            "QPlainTextEdit { background-color: #0a0a18; color: #b0b0c0; "
            "border: 1px solid #2a2a4e; border-radius: 0; padding: 4px; }"
        )

    def append_log(self, message: str, level: str = "INFO") -> None:
        """Append a colored log message."""
        color = LEVEL_COLORS.get(level, LEVEL_COLORS["INFO"])
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        prefix_map = {"INFO": "INFO", "WARNING": "WARN", "ERROR": "ERR!", "SUCCESS": " OK ", "DEBUG": "DBG"}
        prefix = prefix_map.get(level, level[:4])

        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"[{prefix}] {message}\n", fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def save_log(self, filepath: str) -> None:
        """Export log content to a text file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.toPlainText())

    def clear_log(self) -> None:
        self.clear()
