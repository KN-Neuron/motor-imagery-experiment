from enum import Enum
import os
import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap

from src.sample_manager.experiment_step_type import ExperimentStepType
from .experiment_view import STEP_DISPLAY
from .view import View


class CalibrationEvent(Enum):
    ABORT = "abort"
    PAUSE = "pause"
    QUIT = "quit"

class CalibrationView(View):
    def __init__(self) -> None:
        self.step_type: ExperimentStepType | None = None
        self.classified_as: ExperimentStepType | None = None
        self.no_eeg_mode: bool = False
        self.is_paused = False
        self.progress_percent: float = 0.0
        self.ssvep_display_arg: int = 0
        super().__init__()

    def _setup_ui(self):
        self.setStyleSheet("background-color: rgb(20, 20, 35);")

        self._register_shortcut(Qt.Key.Key_Escape, self._on_esc_pressed)

    def update_content(self, 
        step_type: ExperimentStepType | None,
        classified_as: ExperimentStepType | None,
        no_eeg_mode: bool = False,
        is_paused: bool = False,
        progress_percent: float = 0.0,
    ):
        self.step_type = step_type
        self.classified_as = classified_as
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

        if self.classified_as is None:
            self._draw_cue(painter, w, h)
        else:
            self._draw_result(painter, w, h)

        self._draw_progress_bar(painter, w, h)

        if self.is_paused:
            self._draw_header(painter, w)
            self._draw_esc_hint(painter, w, h)

    def _draw_no_eeg_indicator(self, painter: QPainter, w: int):
        mode_font = QFont("Arial", 16)
        painter.setFont(mode_font)
        painter.setPen(QColor(180, 100, 100))
        mode_text = "NO EEG MODE"
        mode_w = painter.fontMetrics().horizontalAdvance(mode_text)
        painter.drawText(w - mode_w - 15, 15 + painter.fontMetrics().ascent(), mode_text)

    def _draw_esc_hint(self, painter: QPainter, w: int, h: int):
        hint_font = QFont("Arial", 14)
        painter.setFont(hint_font)
        painter.setPen(QColor(80, 80, 100))
        hint = "Press ESC to abort"
        hint_w = painter.fontMetrics().horizontalAdvance(hint)
        painter.drawText((w - hint_w) // 2, int(h * 0.92) + painter.fontMetrics().ascent(), hint)

    def _draw_header(self, painter: QPainter, w: int):
        header_font = QFont("Arial", 18)
        painter.setFont(header_font)
        painter.setPen(QColor(100, 100, 140))
        header = "CALIBRATION"
        header_w = painter.fontMetrics().horizontalAdvance(header)
        painter.drawText((w - header_w) // 2, 15 + painter.fontMetrics().ascent(), header)

    def _draw_cue(self, painter: QPainter, w: int, h: int):
        if not self.step_type:
            return

        if self.step_type == ExperimentStepType.FIXATION:
            self._draw_fixation_cross(painter, w, h)
            return

        color, label, img_path = STEP_DISPLAY.get(
            self.step_type,
            (QColor(255, 255, 255), self.step_type.value.upper(), None)
        )

        # Action label
        action_font = QFont("Arial", 32, QFont.Weight.Bold)
        painter.setFont(action_font)
        painter.setPen(color)
        action_w = painter.fontMetrics().horizontalAdvance(label)
        text_y = int(h * 0.42) + painter.fontMetrics().ascent()
        painter.drawText((w - action_w) // 2, text_y, label)

        if self.step_type == ExperimentStepType.SSVEP_FOCUS:
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
            # Draw image
            if img_path is not None and os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                max_img_w, max_img_h = 300, 180
                img_w = min(pixmap.width(), max_img_w)
                img_h = min(pixmap.height(), max_img_h)
                scaled_pixmap = pixmap.scaled(img_w, img_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_x = (w - scaled_pixmap.width()) // 2
                img_y = text_y + 30
                painter.drawPixmap(img_x, img_y, scaled_pixmap)

    def _draw_fixation_cross(self, painter: QPainter, w: int, h: int):
        cx, cy = w // 2, int(h * 0.42) + 24
        arm, thick = 45, 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(cx - arm, cy - thick // 2, arm * 2, thick)
        painter.drawRect(cx - thick // 2, cy - arm, thick, arm * 2)

    def _draw_result(self, painter: QPainter, w: int, h: int):
        prompted_color, prompted_label, _ = STEP_DISPLAY.get(
            self.step_type, (QColor(200, 200, 200), self.step_type.value.upper())
        ) if self.step_type else (QColor(200, 200, 200), "—")

        classified_color, classified_label, _ = STEP_DISPLAY.get(
            self.classified_as, (QColor(200, 200, 200), self.classified_as.value.upper())
        )

        correct = self.step_type == self.classified_as

        # "RESULT" header
        header_font = QFont("Arial", 18)
        painter.setFont(header_font)
        painter.setPen(QColor(100, 100, 140))
        header = "RESULT"
        header_w = painter.fontMetrics().horizontalAdvance(header)
        painter.drawText((w - header_w) // 2, int(h * 0.22) + painter.fontMetrics().ascent(), header)

        row_font = QFont("Arial", 26)
        label_font = QFont("Arial", 26, QFont.Weight.Bold)

        center_x = w // 2
        row1_y = int(h * 0.36) + painter.fontMetrics().ascent()
        row2_y = int(h * 0.50) + painter.fontMetrics().ascent()

        def draw_row(y, prefix, value_label, value_color):
            painter.setFont(row_font)
            painter.setPen(QColor(140, 140, 170))
            prefix_w = painter.fontMetrics().horizontalAdvance(prefix)

            painter.setFont(label_font)
            value_w = painter.fontMetrics().horizontalAdvance(value_label)

            total_w = prefix_w + 8 + value_w
            start_x = center_x - total_w // 2

            painter.setFont(row_font)
            painter.setPen(QColor(140, 140, 170))
            painter.drawText(start_x, y, prefix)

            painter.setFont(label_font)
            painter.setPen(value_color)
            painter.drawText(start_x + prefix_w + 8, y, value_label)

        draw_row(row1_y, "Prompted:", prompted_label, prompted_color)
        draw_row(row2_y, "Classified:", classified_label, classified_color)

        # Valid ✓ / Invalid ✗ indicator
        indicator_font = QFont("Segoe UI Symbol", 48, QFont.Weight.Bold)
        painter.setFont(indicator_font)
        indicator_color = QColor(60, 210, 100) if correct else QColor(220, 70, 70)
        painter.setPen(indicator_color)
        indicator = "✓" if correct else "✗"
        ind_w = painter.fontMetrics().horizontalAdvance(indicator)
        painter.drawText((w - ind_w) // 2, int(h * 0.68) + painter.fontMetrics().ascent(), indicator)

    def _draw_progress_bar(self, painter: QPainter, w: int, h: int):
        bar_h = 8
        bar_y = h - bar_h
        painter.fillRect(0, bar_y, w, bar_h, QColor(30, 30, 50))
        if self.progress_percent > 0:
            fill_w = int(w * self.progress_percent)
            painter.fillRect(0, bar_y, fill_w, bar_h, QColor(80, 120, 200))

    def _on_esc_pressed(self):
        if self.is_paused:
            print("[CalibrationView] ESC pressed during pause - adding ABORT event")
            self.pending_events.append(CalibrationEvent.ABORT)
