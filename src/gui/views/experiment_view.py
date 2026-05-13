import math
import os
from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont
from src.sample_manager.experiment_step_type import ExperimentStepType
from .utils.pixmap_cache import get_pixmap_cache
from .view import View


class ExperimentEvent(Enum):
    ABORT = "abort"
    PAUSE = "pause"

IMG_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '../../res/imgs'))
STEP_DISPLAY = {
    ExperimentStepType.FIXATION:      (QColor(200, 200, 200), "FIXATION", None),
    ExperimentStepType.REST:          (QColor(150, 150, 200), "REST", os.path.join(IMG_DIR, 'rest.png')),
    ExperimentStepType.DOUBLE_BLINK:  (QColor(100, 200, 255), "DOUBLE BLINK", os.path.join(IMG_DIR, 'double_blink.png')),
    ExperimentStepType.LEFT_HAND:     (QColor(255, 150, 150), "LEFT HAND CLENCH", os.path.join(IMG_DIR, 'left_hand_clench.png')),
    ExperimentStepType.RIGHT_HAND:    (QColor(150, 255, 150), "RIGHT HAND CLENCH", os.path.join(IMG_DIR, 'right_hand_clench.png')),
    ExperimentStepType.JAW_CLENCH:    (QColor(255, 200, 100), "JAW CLENCH", os.path.join(IMG_DIR, 'jaw_clench.png')),
    ExperimentStepType.HEAD_MOVEMENT: (QColor(200, 150, 255), "HEAD MOVEMENT", os.path.join(IMG_DIR, 'head_movement.png')),
    ExperimentStepType.SSVEP_FOCUS:   (QColor(255, 255, 150), "SSVEP FOCUS", None),
}

class ExperimentView(View):
    def __init__(self) -> None:
        self.step_type = None
        self.no_eeg_mode = False
        self.is_paused = False
        self.progress_percent = 0.0
        self.ssvep_display_arg = 0
        super().__init__()

    def _setup_ui(self):
        self.setStyleSheet("background-color: rgb(25, 15, 40);")

        self._register_shortcut(Qt.Key.Key_Escape, self._on_esc_pressed)

    def update_content(self, step_type, no_eeg_mode, is_paused, progress_percent):
        self.step_type = step_type
        self.no_eeg_mode = no_eeg_mode
        self.is_paused = is_paused
        self.progress_percent = progress_percent
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        if self.no_eeg_mode and self.is_paused:
            self._draw_no_eeg_indicator(painter, w)

        if self.is_paused:
            self._draw_header(painter, w)

        self._draw_step(painter, w, h)

        self._draw_progress_bar(painter, w, h)

    def _draw_header(self, painter: QPainter, w: int):
        header_font = QFont('Arial', 18)
        painter.setFont(header_font)
        painter.setPen(QColor(100, 100, 140))
        header = "EXPERIMENT"
        header_w = painter.fontMetrics().horizontalAdvance(header)
        painter.drawText((w - header_w) // 2, 15 + painter.fontMetrics().ascent(), header)

    def _draw_no_eeg_indicator(self, painter: QPainter, w: int):
        mode_font = QFont('Arial', 16)
        painter.setFont(mode_font)
        painter.setPen(QColor(180, 100, 100))
        mode_text = "NO EEG MODE"
        mode_w = painter.fontMetrics().horizontalAdvance(mode_text)
        painter.drawText(w - mode_w - 15, 15 + painter.fontMetrics().ascent(), mode_text)

    def _draw_step(self, painter: QPainter, w: int, h: int):
        if not self.step_type:
            return

        if self.step_type == ExperimentStepType.FIXATION:
            self._draw_fixation_cross(painter, w, h)
        else:
            color, text, _ = STEP_DISPLAY.get(
                self.step_type,
                (QColor(255, 255, 255), self.step_type.value.upper(), None)
            )
            step_font = QFont('Arial', 32)
            step_font.setWeight(QFont.Weight.Bold)
            painter.setFont(step_font)
            painter.setPen(color)
            step_w = painter.fontMetrics().horizontalAdvance(text)
            text_y = int(h * 0.4) + painter.fontMetrics().ascent()
            painter.drawText((w - step_w) // 2, text_y, text)

            if self.step_type == ExperimentStepType.SSVEP_FOCUS and not self.is_paused:
                sin_factor = math.sin(2 * math.pi * 10 * self.ssvep_display_arg / 100)
                sin_factor = 0 if sin_factor < 0.5 else sin_factor # Creates a "blinking" effect where the dot is fully visible for half the time and invisible for the other half
                painter.save()
                painter.setOpacity(sin_factor)
                dot_radius = 24
                cx = w // 2
                cy = int(h * 0.60) + 24
                painter.setBrush(QColor(255, 255, 255))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(cx - dot_radius, cy - dot_radius, dot_radius * 2, dot_radius * 2)
                painter.restore()
                self.ssvep_display_arg = (self.ssvep_display_arg + 1) % 100 # Increment to trigger animation changes

            else:
                scaled_pixmap = get_pixmap_cache(STEP_DISPLAY).get(self.step_type)
                if scaled_pixmap is not None:
                    img_x = (w - scaled_pixmap.width()) // 2
                    img_y = text_y + 30
                    painter.drawPixmap(img_x, img_y, scaled_pixmap)

        if self.is_paused:
            hint_font = QFont('Arial', 18)
            painter.setFont(hint_font)
            painter.setPen(QColor(150, 150, 150))
            hint = "Press ESC to abort experiment"
            hint_w = painter.fontMetrics().horizontalAdvance(hint)
            painter.drawText((w - hint_w) // 2, int(h * 0.92) + painter.fontMetrics().ascent(), hint)

    def _draw_fixation_cross(self, painter: QPainter, w: int, h: int):
        cx, cy = w // 2, int(h * 0.4) + 24
        arm, thick = 45, 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(cx - arm, cy - thick // 2, arm * 2, thick)
        painter.drawRect(cx - thick // 2, cy - arm, thick, arm * 2)

    def _draw_progress_bar(self, painter: QPainter, w: int, h: int):
        bar_h = 8
        bar_y = h - bar_h
        painter.fillRect(0, bar_y, w, bar_h, QColor(40, 40, 60))
        if self.progress_percent > 0:
            fill_w = int(w * self.progress_percent)
            painter.fillRect(0, bar_y, fill_w, bar_h, QColor(80, 120, 200))

    def _on_esc_pressed(self):
        if self.is_paused:
            print("[ExperimentView] ESC pressed during pause - adding ABORT event")
            self.pending_events.append(ExperimentEvent.ABORT)
