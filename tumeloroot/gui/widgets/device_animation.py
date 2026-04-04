"""Device Animation Widget - visual step-by-step instructions with animated indicators."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient


class PulsingDot(QWidget):
    """Animated pulsing dot indicator."""

    def __init__(self, color: str = "#e94560", size: int = 16, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self._opacity = 1.0
        self.setFixedSize(size + 8, size + 8)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._pulse_up = False
        self._active = False

    def start(self):
        self._active = True
        self._timer.start(50)
        self.update()

    def stop(self):
        self._active = False
        self._timer.stop()
        self._opacity = 1.0
        self.update()

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def _pulse(self):
        if self._pulse_up:
            self._opacity += 0.05
            if self._opacity >= 1.0:
                self._opacity = 1.0
                self._pulse_up = False
        else:
            self._opacity -= 0.05
            if self._opacity <= 0.3:
                self._opacity = 0.3
                self._pulse_up = True
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._opacity if self._active else 0.3)
        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.PenStyle.NoPen)
        center = self.rect().center()
        painter.drawEllipse(center, self._size // 2, self._size // 2)
        painter.end()


class StepIndicator(QWidget):
    """Visual step indicator showing current progress through the wizard."""

    STEPS = [
        ("Select", "device"),
        ("Check", "prereqs"),
        ("Connect", "BROM"),
        ("Backup", "partitions"),
        ("Unlock", "bootloader"),
        ("Patch", "& flash"),
        ("Verify", "root"),
        ("Done", "!"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_step = 0
        self.setFixedHeight(70)

    def set_step(self, index: int):
        self._current_step = index
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        n = len(self.STEPS)
        step_w = w / n

        for i, (label, sub) in enumerate(self.STEPS):
            cx = int(step_w * i + step_w / 2)
            cy = 22

            # Line between dots
            if i > 0:
                prev_cx = int(step_w * (i - 1) + step_w / 2)
                color = QColor("#4ecca3") if i <= self._current_step else QColor("#2a2a4e")
                painter.setPen(QPen(color, 2))
                painter.drawLine(prev_cx + 12, cy, cx - 12, cy)

            # Dot
            if i < self._current_step:
                painter.setBrush(QBrush(QColor("#4ecca3")))
                painter.setPen(Qt.PenStyle.NoPen)
            elif i == self._current_step:
                painter.setBrush(QBrush(QColor("#e94560")))
                painter.setPen(Qt.PenStyle.NoPen)
            else:
                painter.setBrush(QBrush(QColor("#2a2a4e")))
                painter.setPen(QPen(QColor("#3a3a5e"), 1))

            painter.drawEllipse(cx - 10, cy - 10, 20, 20)

            # Checkmark for completed
            if i < self._current_step:
                painter.setPen(QPen(QColor("#1a1a2e"), 2))
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(cx - 6, cy + 5, "✓")

            # Step number for current/future
            if i >= self._current_step:
                painter.setPen(QPen(QColor("white" if i == self._current_step else "#5a5a7e"), 1))
                font = QFont("Segoe UI", 8, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(cx - 4, cy + 4, str(i + 1))

            # Label
            painter.setPen(QPen(QColor("#e0e0e0" if i == self._current_step else "#6a6a8e"), 1))
            font = QFont("Segoe UI", 9, QFont.Weight.Bold if i == self._current_step else QFont.Weight.Normal)
            painter.setFont(font)
            text_rect = painter.fontMetrics().boundingRect(label)
            painter.drawText(int(cx - text_rect.width() / 2), cy + 28, label)

            # Sub label
            painter.setPen(QPen(QColor("#a0a0b0" if i == self._current_step else "#4a4a6e"), 1))
            font = QFont("Segoe UI", 7)
            painter.setFont(font)
            sub_rect = painter.fontMetrics().boundingRect(sub)
            painter.drawText(int(cx - sub_rect.width() / 2), cy + 42, sub)

        painter.end()


class BromAnimation(QWidget):
    """Visual animation showing BROM connection with tablet, buttons, and USB cable."""

    STATES = {
        "waiting": ("Scanning for device... Enter BROM mode now", "#f0a030", True),
        "detected": ("MediaTek device detected!", "#4ecca3", False),
        "connecting": ("Connecting to BROM...", "#e94560", True),
        "connected": ("BROM connection established!", "#4ecca3", False),
        "failed": ("Connection failed - try BROM mode again", "#e94560", False),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "waiting"
        self._scan_angle = 0
        self._brom_step = 0  # 0-5 for the BROM entry steps
        self.setFixedHeight(220)
        self.setMinimumWidth(500)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

        # Auto-cycle BROM steps when waiting
        self._step_timer = QTimer(self)
        self._step_timer.timeout.connect(self._cycle_step)
        self._step_timer.start(2000)

    def set_state(self, state: str):
        self._state = state
        _, _, animate = self.STATES.get(state, ("", "#e0e0e0", False))
        if animate:
            self._timer.start(30)
        else:
            self._timer.stop()
        if state in ("connected", "detected"):
            self._step_timer.stop()
        self.update()

    def _animate(self):
        self._scan_angle = (self._scan_angle + 3) % 360
        self.update()

    def _cycle_step(self):
        if self._state == "waiting":
            self._brom_step = (self._brom_step + 1) % 6
            self.update()

    def paintEvent(self, event):
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        # === LEFT SIDE: Tablet with buttons ===
        tab_cx = w // 3
        tab_cy = h // 2 - 5

        # Tablet body (landscape orientation for better button visibility)
        tw, th = 100, 140
        tx = tab_cx - tw // 2
        ty = tab_cy - th // 2

        painter.setPen(QPen(QColor("#4a4a6e"), 2))
        painter.setBrush(QBrush(QColor("#16213e")))
        painter.drawRoundedRect(tx, ty, tw, th, 10, 10)

        # Screen
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#0f0f1e")))
        painter.drawRoundedRect(tx + 8, ty + 14, tw - 16, th - 30, 5, 5)

        # Camera
        painter.setBrush(QBrush(QColor("#3a3a5e")))
        painter.drawEllipse(tab_cx - 3, ty + 5, 6, 6)

        # ---- POWER BUTTON on top of tablet ----
        btn_h = 8
        pwr_active = self._brom_step == 0
        pwr_color = "#e94560" if pwr_active else "#3a3a5e"
        painter.setBrush(QBrush(QColor(pwr_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(tx + tw - 30, ty - btn_h - 2, 20, btn_h, 3, 3)

        # Power label
        painter.setPen(QPen(QColor(pwr_color), 1))
        font = QFont("Segoe UI", 7)
        painter.setFont(font)
        painter.drawText(tx + tw - 33, ty - btn_h - 5, "PWR")

        # ---- VOL BUTTONS on right side of tablet ----
        btn_x = tx + tw + 4
        btn_w = 8

        # Vol Up button
        vup_active = self._brom_step in (1, 2, 3, 4)
        vup_color = "#4ecca3" if vup_active else "#3a3a5e"
        painter.setBrush(QBrush(QColor(vup_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(btn_x, ty + 30, btn_w, 22, 3, 3)

        painter.setPen(QPen(QColor(vup_color), 1))
        painter.drawText(btn_x + btn_w + 4, ty + 45, "V+")

        # Vol Down button
        vdn_active = self._brom_step in (1, 2, 3, 4)
        vdn_color = "#4ecca3" if vdn_active else "#3a3a5e"
        painter.setBrush(QBrush(QColor(vdn_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(btn_x, ty + 60, btn_w, 22, 3, 3)

        painter.setPen(QPen(QColor(vdn_color), 1))
        painter.drawText(btn_x + btn_w + 4, ty + 75, "V-")

        # USB port at bottom
        usb_y = ty + th
        painter.setPen(QPen(QColor("#5a5a7e"), 2))
        painter.setBrush(QBrush(QColor("#16213e")))
        painter.drawRoundedRect(tab_cx - 6, usb_y - 2, 12, 6, 2, 2)

        # USB cable (shown when step >= 2)
        cable_plugged = self._brom_step >= 2 or self._state in ("detected", "connecting", "connected")
        if cable_plugged:
            painter.setPen(QPen(QColor("#6a6a8e"), 3))
            painter.drawLine(tab_cx, usb_y + 4, tab_cx, usb_y + 25)
            painter.setBrush(QBrush(QColor("#5a5a7e")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(tab_cx - 6, usb_y + 25, 12, 8)
            # USB label
            painter.setPen(QPen(QColor("#6a6a8e"), 1))
            font = QFont("Segoe UI", 7)
            painter.setFont(font)
            painter.drawText(tab_cx - 8, usb_y + 46, "USB")

        # Screen content based on state
        scr_cx = tab_cx
        scr_cy = tab_cy + 2

        if self._state == "connected" or self._state == "detected":
            # Green checkmark
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#4ecca3")))
            painter.drawEllipse(scr_cx - 15, scr_cy - 15, 30, 30)
            painter.setPen(QPen(QColor("#0f0f1e"), 3))
            painter.drawLine(scr_cx - 8, scr_cy, scr_cx - 3, scr_cy + 7)
            painter.drawLine(scr_cx - 3, scr_cy + 7, scr_cx + 10, scr_cy - 8)
        elif self._state == "failed":
            # Red X
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#e94560")))
            painter.drawEllipse(scr_cx - 15, scr_cy - 15, 30, 30)
            painter.setPen(QPen(QColor("#0f0f1e"), 3))
            painter.drawLine(scr_cx - 7, scr_cy - 7, scr_cx + 7, scr_cy + 7)
            painter.drawLine(scr_cx + 7, scr_cy - 7, scr_cx - 7, scr_cy + 7)
        else:
            # Dark screen with scanning text
            painter.setPen(QPen(QColor("#3a3a5e"), 1))
            font = QFont("Segoe UI", 8)
            painter.setFont(font)
            painter.drawText(scr_cx - 18, scr_cy - 5, "BROM")
            painter.drawText(scr_cx - 18, scr_cy + 10, "MODE")

        # === RIGHT SIDE: Current step instruction ===
        info_x = w // 2 + 20
        info_y = 20

        step_texts = [
            ("Power OFF", "Turn off the device completely", "#a0a0b0"),
            ("Hold Vol+/Vol-", "Press and hold both volume buttons", "#e94560"),
            ("Plug USB", "While holding buttons, plug USB cable", "#f0a030"),
            ("Wait 3-5 sec", "Keep holding volume buttons", "#4ecca3"),
            ("Release", "Release all buttons", "#4ecca3"),
            ("Auto-detect", "App is scanning for device...", "#f0a030"),
        ]

        if self._state in ("connected", "detected"):
            # Show connected info
            painter.setPen(QPen(QColor("#4ecca3"), 1))
            font = QFont("Segoe UI", 14, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(info_x, info_y + 40, "CONNECTED!")

            font = QFont("Segoe UI", 10)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#a0a0b0"), 1))
            painter.drawText(info_x, info_y + 65, "Device is in BROM mode")
            painter.drawText(info_x, info_y + 85, "Click Next to continue")
        else:
            # Show cycling steps
            for i, (title, desc, color) in enumerate(step_texts):
                y_pos = info_y + i * 28
                is_current = (i == self._brom_step)
                is_done = (i < self._brom_step)

                # Step circle
                circle_r = 8
                if is_done:
                    painter.setBrush(QBrush(QColor("#4ecca3")))
                    painter.setPen(Qt.PenStyle.NoPen)
                elif is_current:
                    painter.setBrush(QBrush(QColor("#e94560")))
                    painter.setPen(Qt.PenStyle.NoPen)
                else:
                    painter.setBrush(QBrush(QColor("#2a2a4e")))
                    painter.setPen(QPen(QColor("#3a3a5e"), 1))

                painter.drawEllipse(info_x, y_pos, circle_r * 2, circle_r * 2)

                # Number/check
                painter.setPen(QPen(QColor("white" if is_current else "#1a1a2e" if is_done else "#5a5a7e"), 1))
                font = QFont("Segoe UI", 7, QFont.Weight.Bold)
                painter.setFont(font)
                txt = "✓" if is_done else str(i + 1)
                painter.drawText(info_x + circle_r - 3, y_pos + circle_r + 4, txt)

                # Text
                t_color = color if is_current else "#4ecca3" if is_done else "#5a5a7e"
                painter.setPen(QPen(QColor(t_color), 1))
                font = QFont("Segoe UI", 9, QFont.Weight.Bold if is_current else QFont.Weight.Normal)
                painter.setFont(font)
                painter.drawText(info_x + circle_r * 2 + 8, y_pos + 8, title)

                painter.setPen(QPen(QColor("#6a6a8e" if not is_current else "#a0a0b0"), 1))
                font = QFont("Segoe UI", 7)
                painter.setFont(font)
                painter.drawText(info_x + circle_r * 2 + 8, y_pos + 19, desc)

        # === BOTTOM: Scanning animation ===
        if self._state in ("waiting", "connecting"):
            bar_y = h - 18
            bar_w = w - 40
            bar_x = 20

            # Background bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#16213e")))
            painter.drawRoundedRect(bar_x, bar_y, bar_w, 8, 4, 4)

            # Animated scanning bar
            scan_w = 80
            scan_pos = int((self._scan_angle / 360) * (bar_w - scan_w))
            grad = QLinearGradient(bar_x + scan_pos, 0, bar_x + scan_pos + scan_w, 0)
            grad.setColorAt(0.0, QColor("#1a1a2e"))
            grad.setColorAt(0.5, QColor("#e94560"))
            grad.setColorAt(1.0, QColor("#1a1a2e"))
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(bar_x + scan_pos, bar_y, scan_w, 8, 4, 4)

        # Status text
        msg, color, _ = self.STATES.get(self._state, ("", "#e0e0e0", False))
        painter.setPen(QPen(QColor(color), 1))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = painter.fontMetrics().boundingRect(msg)
        painter.drawText(w // 2 - text_rect.width() // 2, h - 22, msg)

        painter.end()


class InstructionPanel(QWidget):
    """Visual instruction panel with numbered steps and highlight."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)
        self._steps: list[QLabel] = []
        self._current = -1

    def set_instructions(self, steps: list[str]):
        """Set instruction steps."""
        # Clear existing
        for lbl in self._steps:
            lbl.deleteLater()
        self._steps.clear()

        for i, text in enumerate(steps, 1):
            lbl = QLabel(f"  {i}.  {text}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                "padding: 8px 12px; border-radius: 6px; font-size: 13px; "
                "background-color: #16213e; color: #a0a0b0;"
            )
            self._layout.addWidget(lbl)
            self._steps.append(lbl)

    def highlight_step(self, index: int):
        """Highlight the current step (0-based)."""
        self._current = index
        for i, lbl in enumerate(self._steps):
            if i < index:
                lbl.setStyleSheet(
                    "padding: 8px 12px; border-radius: 6px; font-size: 13px; "
                    "background-color: #1a3a2e; color: #4ecca3; font-weight: bold;"
                )
                text = lbl.text()
                if "✓" not in text:
                    lbl.setText(f"  ✓  {text.strip().split('.', 1)[1].strip()}")
            elif i == index:
                lbl.setStyleSheet(
                    "padding: 8px 12px; border-radius: 6px; font-size: 13px; "
                    "background-color: #2a1a2e; color: #e94560; font-weight: bold; "
                    "border: 1px solid #e94560;"
                )
            else:
                lbl.setStyleSheet(
                    "padding: 8px 12px; border-radius: 6px; font-size: 13px; "
                    "background-color: #16213e; color: #6a6a8e;"
                )
