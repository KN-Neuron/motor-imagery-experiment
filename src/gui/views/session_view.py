import os
import time
from enum import Enum

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter

from src.sample_manager.experiment_step_type import ExperimentStepType as T
from src.sample_manager.sample_manager import ExperimentStep
from src.sample_manager.texts import CUE_TEXT, PAUSE_HINT

from .ssvep import ssvep_visible
from .utils.pixmap_cache import get_pixmap_cache
from .view import View

DEMO_BANNER = "FEEDBACK DEMO, NIE PRAWDZIWY KLASYFIKATOR"


class SessionEvent(Enum):
    ABORT = "abort"
    PAUSE = "pause"
    CONTINUE = "continue"  # SPACE on instruction / break / end screens


IMG_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "../../res/imgs")
)


def _img(name: str) -> str:
    return os.path.join(IMG_DIR, name)


# step type -> (colour, short label, image)
STEP_DISPLAY = {
    T.FIXATION: (QColor(200, 200, 200), "FIXATION", None),
    T.REST_EYES_OPEN: (QColor(150, 150, 200), "REST", _img("rest.png")),
    T.REST_EYES_CLOSED: (QColor(150, 150, 200), "REST (EYES CLOSED)", None),
    T.DOUBLE_BLINK: (QColor(100, 200, 255), "DOUBLE BLINK", _img("double_blink.png")),
    T.LEFT_HAND_IMAGERY: (
        QColor(255, 150, 150),
        "LEFT HAND IMAGERY",
        _img("left_hand_clench.png"),
    ),
    T.RIGHT_HAND_IMAGERY: (
        QColor(150, 255, 150),
        "RIGHT HAND IMAGERY",
        _img("right_hand_clench.png"),
    ),
    T.LEFT_HAND_EXECUTION: (
        QColor(255, 150, 150),
        "LEFT HAND EXECUTION",
        _img("left_hand_clench.png"),
    ),
    T.RIGHT_HAND_EXECUTION: (
        QColor(150, 255, 150),
        "RIGHT HAND EXECUTION",
        _img("right_hand_clench.png"),
    ),
    T.JAW_CLENCH: (QColor(255, 200, 100), "JAW CLENCH", _img("jaw_clench.png")),
    T.HEAD_MOVEMENT: (
        QColor(200, 150, 255),
        "HEAD MOVEMENT",
        _img("head_movement.png"),
    ),
    T.SSVEP_FOCUS: (QColor(255, 255, 150), "SSVEP FOCUS", None),
}

_WHITE = QColor(255, 255, 255)


class SessionView(View):
    """Full-screen view for experiment and calibration sessions."""

    background = "background-color: rgb(25, 15, 40);"

    def __init__(self) -> None:
        self.step: ExperimentStep | None = None
        self.classified_as: T | None = None
        self.no_eeg_mode = False
        self.is_paused = False
        self.progress_percent = 0.0
        self.feedback_mode = "none"
        self.ssvep_frequency_hz = 10.0
        self._token = 0
        self._token_start_ns = 0
        self._painted_token = 0
        self._first_paint: tuple[int, int] | None = None
        super().__init__()

    def _setup_ui(self) -> None:
        self.setStyleSheet(self.background)
        self._register_shortcut(Qt.Key.Key_Escape, self._on_esc_pressed)
        self._register_shortcut(Qt.Key.Key_Space, self._on_space_pressed)

    def update_content(  # type: ignore[override]
        self,
        step: ExperimentStep | None,
        classified_as: T | None = None,
        no_eeg_mode: bool = False,
        is_paused: bool = False,
        progress_percent: float = 0.0,
        feedback_mode: str = "none",
        token: int = 0,
    ) -> None:
        if token != self._token:
            self._token = token
            self._token_start_ns = time.perf_counter_ns()
        self.step = step
        self.classified_as = classified_as
        self.no_eeg_mode = no_eeg_mode
        self.is_paused = is_paused
        self.progress_percent = progress_percent
        self.feedback_mode = feedback_mode
        self.update()

    def pop_first_paint(self) -> tuple[int, int] | None:
        """(token, perf_counter_ns) of the first paint of a new step, once."""
        result, self._first_paint = self._first_paint, None
        return result

    def refresh_rate_hz(self) -> float:
        screen = self.screen()
        return float(screen.refreshRate()) if screen is not None else 0.0

    # --- painting ---------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self.no_eeg_mode:
            self._text(painter, "NO EEG MODE", 0, 0.01, 16, QColor(180, 100, 100), w)

        if self.feedback_mode == "demo":
            self._text(painter, DEMO_BANNER, 0, 0.06, 22, QColor(255, 80, 80), w, True)

        if self.step is not None:
            if self.classified_as is not None:
                self._draw_result(painter, w, h)
            else:
                self._draw_step(painter, w, h, self.step)

        self._draw_progress_bar(painter, w, h)

        if self.is_paused:
            self._text(painter, PAUSE_HINT, 0, 0.15, 30, QColor(100, 100, 140), w)
            self._text(
                painter, "Press ESC to abort", 0, 0.88, 14, QColor(120, 120, 150), w
            )

        painter.end()
        if self._painted_token != self._token:
            self._painted_token = self._token
            self._first_paint = (self._token, time.perf_counter_ns())

    def _text(
        self,
        painter: QPainter,
        text: str,
        x: int,
        y_frac: float,
        size: int,
        color: QColor,
        w: int,
        bold: bool = False,
        height_frac: float = 0.2,
    ) -> None:
        font = QFont("Arial", size)
        if bold:
            font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(color)
        rect = QRectF(w * 0.08, self.height() * y_frac, w * 0.84, self.height() * 0.5)
        painter.drawText(
            rect,
            int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            | int(Qt.TextFlag.TextWordWrap),
            text,
        )

    def _draw_step(
        self, painter: QPainter, w: int, h: int, step: ExperimentStep
    ) -> None:
        if step.phase == "screen":
            self._text(painter, step.text or "", 0, 0.2, 20, _WHITE, w)
        elif step.phase == "fixation":
            self._draw_cross(painter, w, h)
        elif step.phase == "iti":
            pass  # blank screen between trials
        elif step.phase == "rest":
            self._cue_text(painter, step.step_type, w, 0.2)
            if step.step_type == T.REST_EYES_OPEN:
                self._draw_cross(painter, w, h)
        else:
            self._draw_cue(painter, w, h, step)

    def _cue_text(self, painter: QPainter, step_type: T, w: int, y: float) -> None:
        color = STEP_DISPLAY.get(step_type, (_WHITE, "", None))[0]
        pl, en = CUE_TEXT.get(step_type, (step_type.value.upper(), ""))
        self._text(painter, pl, 0, y, 28, color, w, True)
        self._text(painter, en, 0, y + 0.16, 18, QColor(190, 190, 210), w)

    def _draw_cue(
        self, painter: QPainter, w: int, h: int, step: ExperimentStep
    ) -> None:
        self._cue_text(painter, step.step_type, w, 0.15)

        if step.step_type == T.SSVEP_FOCUS and not self.is_paused:
            elapsed_s = (time.perf_counter_ns() - self._token_start_ns) / 1e9
            if ssvep_visible(elapsed_s, self.ssvep_frequency_hz):
                radius = 24
                painter.setBrush(_WHITE)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(
                    w // 2 - radius, int(h * 0.62) - radius, radius * 2, radius * 2
                )
            return

        pixmap = get_pixmap_cache(STEP_DISPLAY).get(step.step_type)
        if pixmap is not None:
            painter.drawPixmap((w - pixmap.width()) // 2, int(h * 0.50), pixmap)

    def _draw_cross(self, painter: QPainter, w: int, h: int) -> None:
        cx, cy = w // 2, int(h * 0.55)
        arm, thick = 45, 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(cx - arm, cy - thick // 2, arm * 2, thick)
        painter.drawRect(cx - thick // 2, cy - arm, thick, arm * 2)

    def _draw_result(self, painter: QPainter, w: int, h: int) -> None:
        """Feedback screen (calibration only, when feedback != none)."""
        assert self.step is not None and self.classified_as is not None
        prompted = STEP_DISPLAY.get(self.step.step_type, (_WHITE, "", None))
        classified = STEP_DISPLAY.get(self.classified_as, (_WHITE, "", None))
        correct = self.step.step_type == self.classified_as

        self._text(painter, "RESULT", 0, 0.2, 18, QColor(100, 100, 140), w)
        self._text(painter, f"Prompted: {prompted[1]}", 0, 0.34, 24, prompted[0], w)
        self._text(
            painter, f"Classified: {classified[1]}", 0, 0.48, 24, classified[0], w
        )
        color = QColor(60, 210, 100) if correct else QColor(220, 70, 70)
        self._text(painter, "✓" if correct else "✗", 0, 0.62, 48, color, w, True)

    def _draw_progress_bar(self, painter: QPainter, w: int, h: int) -> None:
        bar_h = 8
        bar_y = h - bar_h
        painter.fillRect(0, bar_y, w, bar_h, QColor(40, 40, 60))
        if self.progress_percent > 0:
            painter.fillRect(
                0, bar_y, int(w * self.progress_percent), bar_h, QColor(80, 120, 200)
            )

    # --- input ------------------------------------------------------------

    def _on_esc_pressed(self) -> None:
        if self.is_paused:
            self.pending_events.append(SessionEvent.ABORT)

    def _on_space_pressed(self) -> None:
        self.pending_events.append(SessionEvent.CONTINUE)
