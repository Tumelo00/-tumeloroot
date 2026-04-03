"""Step Illustrations - painted visual guides for OEM unlock steps."""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient


class PhoneSettingsIllustration(QWidget):
    """Shows a phone screen with settings menu and build number tap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Phone outline
        px, py, pw, ph = 20, 10, 100, 140
        p.setPen(QPen(QColor("#4a4a6e"), 2))
        p.setBrush(QBrush(QColor("#16213e")))
        p.drawRoundedRect(px, py, pw, ph, 8, 8)

        # Screen
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#0f0f1e")))
        p.drawRoundedRect(px + 5, py + 12, pw - 10, ph - 24, 4, 4)

        # Settings icon (gear) on screen
        p.setPen(QPen(QColor("#4ecca3"), 2))
        cx, cy = px + pw // 2, py + 30
        p.drawEllipse(cx - 6, cy - 6, 12, 12)
        p.drawEllipse(cx - 3, cy - 3, 6, 6)

        # Menu items
        font = QFont("Segoe UI", 5)
        p.setFont(font)
        p.setPen(QPen(QColor("#6a6a8e"), 1))
        for i, txt in enumerate(["About", "Build No.", "Tap x7"]):
            y = py + 50 + i * 16
            p.drawRoundedRect(px + 8, y, pw - 16, 12, 2, 2)
            p.drawText(px + 12, y + 9, txt)

        # Highlight "Build Number"
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#e94560")))
        p.setOpacity(0.3)
        p.drawRoundedRect(px + 8, py + 66, pw - 16, 12, 2, 2)
        p.setOpacity(1.0)

        # Tap finger icon
        p.setPen(QPen(QColor("#e94560"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        finger_x, finger_y = px + pw + 10, py + 68
        p.drawEllipse(finger_x, finger_y, 16, 16)
        p.drawLine(finger_x + 8, finger_y + 16, finger_x + 8, finger_y + 30)

        # Arrow
        p.setPen(QPen(QColor("#e94560"), 1))
        p.drawLine(finger_x - 4, finger_y + 8, px + pw + 2, finger_y + 8)

        # Text on right
        font = QFont("Segoe UI", 9)
        p.setFont(font)
        p.setPen(QPen(QColor("#e0e0e0"), 1))
        p.drawText(155, 35, "Settings")
        p.drawText(155, 52, "> About Tablet")
        p.setPen(QPen(QColor("#e94560"), 1))
        font.setBold(True)
        p.setFont(font)
        p.drawText(155, 72, "> Build Number")
        p.drawText(155, 89, "  Tap 7 times!")

        p.setPen(QPen(QColor("#4ecca3"), 1))
        font.setBold(False)
        p.setFont(font)
        p.drawText(155, 115, '"You are now')
        p.drawText(155, 130, ' a developer!"')

        p.end()


class OemToggleIllustration(QWidget):
    """Shows Developer Options with OEM Unlock toggle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Phone
        px, py, pw, ph = 20, 10, 100, 140
        p.setPen(QPen(QColor("#4a4a6e"), 2))
        p.setBrush(QBrush(QColor("#16213e")))
        p.drawRoundedRect(px, py, pw, ph, 8, 8)

        # Screen
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#0f0f1e")))
        p.drawRoundedRect(px + 5, py + 12, pw - 10, ph - 24, 4, 4)

        # Title bar on screen
        font = QFont("Segoe UI", 5)
        p.setFont(font)
        p.setPen(QPen(QColor("#e94560"), 1))
        p.drawText(px + 10, py + 22, "Developer Options")

        # Toggle items
        items = [
            ("OEM Unlock", True, "#4ecca3"),
            ("USB Debug", False, "#6a6a8e"),
            ("Stay awake", False, "#6a6a8e"),
        ]
        for i, (name, on, color) in enumerate(items):
            y = py + 32 + i * 22

            # Label
            p.setPen(QPen(QColor("#a0a0b0"), 1))
            p.drawText(px + 10, y + 10, name)

            # Toggle
            toggle_x = px + pw - 28
            p.setPen(Qt.PenStyle.NoPen)
            bg_color = QColor(color) if on else QColor("#3a3a5e")
            p.setBrush(QBrush(bg_color))
            p.drawRoundedRect(toggle_x, y + 2, 20, 10, 5, 5)

            # Toggle knob
            knob_x = toggle_x + 11 if on else toggle_x + 1
            p.setBrush(QBrush(QColor("white")))
            p.drawEllipse(knob_x, y + 3, 8, 8)

        # Highlight OEM Unlock
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#4ecca3")))
        p.setOpacity(0.15)
        p.drawRoundedRect(px + 7, py + 30, pw - 14, 20, 3, 3)
        p.setOpacity(1.0)

        # Arrow pointing to OEM toggle
        p.setPen(QPen(QColor("#4ecca3"), 2))
        arrow_x = px + pw + 8
        arrow_y = py + 42
        p.drawLine(arrow_x, arrow_y, arrow_x + 15, arrow_y)
        p.drawLine(arrow_x, arrow_y, arrow_x + 5, arrow_y - 4)
        p.drawLine(arrow_x, arrow_y, arrow_x + 5, arrow_y + 4)

        # Text on right
        font = QFont("Segoe UI", 9)
        p.setFont(font)
        p.setPen(QPen(QColor("#e0e0e0"), 1))
        p.drawText(155, 35, "Developer Options")
        p.setPen(QPen(QColor("#4ecca3"), 1))
        font.setBold(True)
        p.setFont(font)
        p.drawText(155, 55, "OEM Unlocking")
        p.drawText(155, 72, "  Turn ON")

        p.setPen(QPen(QColor("#f0a030"), 1))
        font.setBold(False)
        font.setPointSize(8)
        p.setFont(font)
        p.drawText(155, 95, "A warning popup")
        p.drawText(155, 110, "will appear.")
        p.setPen(QPen(QColor("#e0e0e0"), 1))
        p.drawText(155, 130, 'Tap "Enable"')

        p.end()


class UsbDebugIllustration(QWidget):
    """Shows USB debugging toggle and PC connection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Phone
        px, py, pw, ph = 15, 15, 70, 110
        p.setPen(QPen(QColor("#4a4a6e"), 2))
        p.setBrush(QBrush(QColor("#16213e")))
        p.drawRoundedRect(px, py, pw, ph, 6, 6)

        # Screen with toggle
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#0f0f1e")))
        p.drawRoundedRect(px + 4, py + 10, pw - 8, ph - 18, 3, 3)

        # USB Debug toggle on screen
        font = QFont("Segoe UI", 5)
        p.setFont(font)
        p.setPen(QPen(QColor("#a0a0b0"), 1))
        p.drawText(px + 8, py + 28, "USB Debug")

        # Toggle ON
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#4ecca3")))
        p.drawRoundedRect(px + pw - 24, py + 20, 16, 8, 4, 4)
        p.setBrush(QBrush(QColor("white")))
        p.drawEllipse(px + pw - 15, py + 21, 6, 6)

        # USB cable from phone bottom
        cable_y = py + ph
        p.setPen(QPen(QColor("#6a6a8e"), 3))
        cx = px + pw // 2
        p.drawLine(cx, cable_y, cx, cable_y + 12)

        # Cable going right to PC
        p.drawLine(cx, cable_y + 12, 115, cable_y + 12)
        p.drawLine(115, cable_y + 12, 115, py + 60)

        # PC/Monitor
        pc_x, pc_y = 105, py + 15
        p.setPen(QPen(QColor("#4a4a6e"), 2))
        p.setBrush(QBrush(QColor("#16213e")))
        p.drawRoundedRect(pc_x, pc_y, 55, 40, 4, 4)

        # PC screen
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#0f0f1e")))
        p.drawRoundedRect(pc_x + 4, pc_y + 4, 47, 28, 2, 2)

        # PC stand
        p.setPen(QPen(QColor("#4a4a6e"), 2))
        p.drawLine(pc_x + 27, pc_y + 40, pc_x + 27, pc_y + 48)
        p.drawLine(pc_x + 17, pc_y + 48, pc_x + 37, pc_y + 48)

        # "Connected" on PC screen
        font = QFont("Segoe UI", 5)
        p.setFont(font)
        p.setPen(QPen(QColor("#4ecca3"), 1))
        p.drawText(pc_x + 8, pc_y + 18, "ADB")
        p.drawText(pc_x + 8, pc_y + 27, "Ready")

        # Popup on phone "Allow USB Debugging?"
        popup_y = py + 45
        p.setPen(QPen(QColor("#4a4a6e"), 1))
        p.setBrush(QBrush(QColor("#1a1a2e")))
        p.drawRoundedRect(px + 6, popup_y, pw - 12, 30, 3, 3)
        p.setPen(QPen(QColor("#e0e0e0"), 1))
        font = QFont("Segoe UI", 4)
        p.setFont(font)
        p.drawText(px + 9, popup_y + 10, "Allow USB")
        p.drawText(px + 9, popup_y + 17, "Debugging?")

        # Allow button
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#4ecca3")))
        p.drawRoundedRect(px + pw - 28, popup_y + 20, 18, 7, 2, 2)
        p.setPen(QPen(QColor("#0f0f1e"), 1))
        font = QFont("Segoe UI", 3)
        p.setFont(font)
        p.drawText(px + pw - 26, popup_y + 26, "Allow")

        # Text on right
        font = QFont("Segoe UI", 9)
        p.setFont(font)
        p.setPen(QPen(QColor("#e0e0e0"), 1))
        p.drawText(175, 35, "USB Debugging")
        p.setPen(QPen(QColor("#4ecca3"), 1))
        font.setBold(True)
        p.setFont(font)
        p.drawText(175, 55, "Turn ON")

        p.setPen(QPen(QColor("#e0e0e0"), 1))
        font.setBold(False)
        p.setFont(font)
        p.drawText(175, 80, "Connect USB")
        p.drawText(175, 95, "to your PC")

        p.setPen(QPen(QColor("#f0a030"), 1))
        font.setPointSize(8)
        p.setFont(font)
        p.drawText(175, 120, 'Tap "Allow"')
        p.drawText(175, 135, "when prompted")

        p.end()
