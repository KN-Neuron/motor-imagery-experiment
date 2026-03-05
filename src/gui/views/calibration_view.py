from enum import Enum
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QKeySequence, QShortcut

from src.sample_manager.experiment_step_type import ExperimentStepType


class CalibrationEvent(Enum):
    ABORT = "abort"
    PAUSE = "pause"
    QUIT = "quit"

STEP_DISPLAY = {
    ExperimentStepType.DOUBLE_BLINK:   (QColor(100, 200, 255), "DOUBLE BLINK"),
    ExperimentStepType.LEFT_HAND:      (QColor(255, 150, 150), "LEFT HAND CLENCH"),
    ExperimentStepType.RIGHT_HAND:     (QColor(150, 255, 150), "RIGHT HAND CLENCH"),
    ExperimentStepType.JAW_CLENCH:     (QColor(255, 200, 100), "JAW CLENCH"),
    ExperimentStepType.HEAD_MOVEMENT:  (QColor(200, 150, 255), "HEAD MOVEMENT"),
    ExperimentStepType.SSVEP_FOCUS:    (QColor(255, 255, 150), "SSVEP FOCUS"),
}

class CalibrationView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pending_events = []
        self.step_type: ExperimentStepType | None = None
        self.classified_as: ExperimentStepType | None = None
        self.no_eeg_mode: bool = False
        self.is_paused = False
        self.progress_percent: float = 0.0

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: rgb(20, 20, 35);")

        # ESC shortcut enabled/disabled via showEvent/hideEvent
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.esc_shortcut.activated.connect(
            lambda: self.pending_events.append(CalibrationEvent.ABORT)
        )
        self.esc_shortcut.setEnabled(False)

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

        color, label = STEP_DISPLAY.get(self.step_type, (QColor(255, 255, 255), self.step_type.value.upper()))

        # Action label
        action_font = QFont("Arial", 48, QFont.Weight.Bold)
        painter.setFont(action_font)
        painter.setPen(color)
        action_w = painter.fontMetrics().horizontalAdvance(label)
        painter.drawText((w - action_w) // 2, int(h * 0.42) + painter.fontMetrics().ascent(), label)

    def _draw_fixation_cross(self, painter: QPainter, w: int, h: int):
        cx, cy = w // 2, int(h * 0.42) + 24
        arm, thick = 45, 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(cx - arm, cy - thick // 2, arm * 2, thick)
        painter.drawRect(cx - thick // 2, cy - arm, thick, arm * 2)

    def _draw_result(self, painter: QPainter, w: int, h: int):
        prompted_color, prompted_label = STEP_DISPLAY.get(
            self.step_type, (QColor(200, 200, 200), self.step_type.value.upper())
        ) if self.step_type else (QColor(200, 200, 200), "—")

        classified_color, classified_label = STEP_DISPLAY.get(
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

        # ✓ / ✗ indicator
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

    def get_pending_events(self) -> list[CalibrationEvent]:
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events

    def showEvent(self, event):
        """Called by Qt when this view becomes visible. Enables the ESC shortcut."""
        super().showEvent(event)
        self.esc_shortcut.setEnabled(True)

    def hideEvent(self, event):
        """Called by Qt when this view is hidden. Disables the ESC shortcut to prevent it from firing in the background."""
        super().hideEvent(event)
        self.esc_shortcut.setEnabled(False)
