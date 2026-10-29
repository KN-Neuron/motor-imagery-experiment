from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.eeg_headset.eeg_headset import EEGHeadset
from src.signal_quality.quality import ChannelQuality, assess_channels
from src.signal_quality.thresholds import QualityThresholds

from ._shared import CANCEL_STYLE, DIALOG_STYLE, START_STYLE


@dataclass
class QualityResult:
    channels: list[ChannelQuality]
    ignored_warnings: bool  # the operator continued despite warnings
    rest_data: np.ndarray  # the resting fragment, shape (n_channels, n_samples)

    def to_metadata(self) -> dict[str, object]:
        return {
            "warnings_ignored": self.ignored_warnings,
            "n_samples": int(self.rest_data.shape[1]),
            "channels": {
                q.label: {
                    "rms_uv": q.rms_uv,
                    "peak_to_peak_uv": q.peak_to_peak_uv,
                    "dc_offset_uv": q.dc_offset_uv,
                    "line_ratio": q.line_ratio,
                    "drift_uv_per_s": q.drift_uv_per_s,
                    "warnings": q.warnings,
                }
                for q in self.channels
            },
        }


class _Bars(QWidget):
    """RMS per channel; red bars have warnings."""

    def __init__(self, max_uv: float) -> None:
        super().__init__()
        self.max_uv = max_uv
        self.channels: list[ChannelQuality] = []
        self.setMinimumHeight(220)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        n = len(self.channels)
        if n == 0:
            return
        gap = 4
        bar_w = max(4.0, (self.width() - gap * (n + 1)) / n)
        for i, q in enumerate(self.channels):
            frac = min(1.0, q.rms_uv / self.max_uv)
            height = frac * (self.height() - 30)
            x = gap + i * (bar_w + gap)
            color = QColor(220, 80, 80) if q.warnings else QColor(80, 180, 120)
            painter.fillRect(
                QRectF(x, self.height() - 20 - height, bar_w, height), color
            )
            painter.setPen(QColor(200, 200, 220))
            painter.drawText(
                QRectF(x - gap, self.height() - 18, bar_w + 2 * gap, 16),
                int(Qt.AlignmentFlag.AlignCenter),
                q.label,
            )


class QualityDialog(QDialog):
    """Signal-quality check before recording.

    Collects `duration_s` of resting EEG from the live stream, then shows RMS per
    channel with warnings. The operator may re-measure or continue despite
    warnings (recorded in the session metadata).
    """

    def __init__(
        self,
        headset: EEGHeadset,
        thresholds: QualityThresholds,
        duration_s: float,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._headset = headset
        self._th = thresholds
        self._needed = int(duration_s * headset.sample_rate)
        self._chunks: list[np.ndarray] = []
        self._collected = 0
        self._result: QualityResult | None = None
        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._start_collecting()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Signal quality check")
        self.resize(760, 560)
        self.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(self)
        self.status = QLabel("")
        layout.addWidget(self.status)
        self.bars = _Bars(self._th.high_rms_uv * 1.5)
        layout.addWidget(self.bars)
        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.details)

        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(CANCEL_STYLE)
        cancel.clicked.connect(self.reject)
        self.redo_btn = QPushButton("Measure again")
        self.redo_btn.setStyleSheet(CANCEL_STYLE)
        self.redo_btn.clicked.connect(self._start_collecting)
        self.go_btn = QPushButton("Continue")
        self.go_btn.setStyleSheet(START_STYLE)
        self.go_btn.clicked.connect(self._on_continue)
        for btn in (cancel, self.redo_btn, self.go_btn):
            btn.setFixedHeight(36)
            row.addWidget(btn)
        layout.addLayout(row)

    def _start_collecting(self) -> None:
        self._chunks, self._collected, self._result = [], 0, None
        self.bars.channels = []
        self.bars.update()
        self.details.setText("")
        self.go_btn.setEnabled(False)
        self.redo_btn.setEnabled(False)
        self._headset.add_subscriber(self._on_data)
        self._refresh_status()
        if hasattr(self, "_timer"):
            self._timer.start(200)

    def _on_data(self, chunk: np.ndarray) -> None:
        self._chunks.append(chunk.copy())
        self._collected += chunk.shape[1]

    def _refresh_status(self) -> None:
        seconds = self._collected / self._headset.sample_rate
        total = self._needed / self._headset.sample_rate
        self.status.setText(
            f"Sit still, eyes open. Recording rest: {seconds:.1f} / {total:.0f} s"
        )

    def _refresh(self) -> None:
        self._refresh_status()
        if self._collected >= self._needed:
            self.finish_collecting()

    def finish_collecting(self) -> None:
        """Assess the collected fragment and show the result."""
        self._timer.stop()
        self._headset.remove_subscriber(self._on_data)
        data = np.concatenate(self._chunks, axis=1)[:, : self._needed]
        channels = assess_channels(
            data, self._headset.sample_rate, self._headset.channel_labels, self._th
        )
        flagged = [q for q in channels if q.warnings]
        self._result = QualityResult(channels, bool(flagged), data)
        self.bars.channels = channels
        self.bars.update()
        self.details.setText(
            "\n".join(f"{q.label}: {', '.join(q.warnings)}" for q in flagged)
            or "No warnings."
        )
        self.status.setText("Rest recorded. Check the bars (red = warning).")
        self.go_btn.setText("Continue despite warnings" if flagged else "Continue")
        self.go_btn.setEnabled(True)
        self.redo_btn.setEnabled(True)

    def _on_continue(self) -> None:
        self.accept()

    def done(self, r: int) -> None:
        self._timer.stop()
        try:
            self._headset.remove_subscriber(self._on_data)
        except ValueError:
            pass
        super().done(r)

    def get_result(self) -> QualityResult | None:
        return self._result if self.result() == QDialog.DialogCode.Accepted else None
