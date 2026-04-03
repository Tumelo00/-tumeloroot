"""Theme manager for Tumeloroot GUI."""

from pathlib import Path

from PySide6.QtWidgets import QApplication


def get_styles_dir() -> Path:
    return Path(__file__).parent / "resources" / "styles"


def load_dark_theme(app: QApplication) -> None:
    """Apply the dark theme stylesheet to the application."""
    qss_path = get_styles_dir() / "dark.qss"
    if qss_path.is_file():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
