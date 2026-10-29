import dataclasses
from typing import Any

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.trials_config.trials_config import (
    CalibrationConfig,
    SessionConfig,
)

from ._cues import ARTIFACT_CUES, MAIN_CUES, get_selected_cues, make_cue_checkboxes
from ._shared import (
    CANCEL_STYLE,
    DIALOG_STYLE,
    START_STYLE,
    make_row,
    make_spinbox,
    separator,
)

FEEDBACK_LABELS = [
    ("None (no feedback)", "none"),
    ("Model (needs a trained classifier)", "model"),
    ("Demo (random, NOT a real classifier)", "demo"),
]


class SessionConfigDialog(QDialog):
    """Dialog for the main session parameters.

    Parameters not shown here (rest block length, practice trials, seed, SSVEP
    frequency, quality thresholds, ...) are kept from the loaded config.
    """

    title = "Session Setup"
    start_label = "Start"

    def __init__(self, initial: SessionConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._initial = initial
        self._config: SessionConfig | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle(self.title)
        self.setFixedSize(430, 640)
        self.setStyleSheet(DIALOG_STYLE)
        outer = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setSpacing(10)
        scroll.setWidget(body)
        outer.addWidget(scroll)

        title = QLabel(self.title)
        title_font = QFont("Segoe UI", 13)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: rgb(180, 190, 255);")
        layout.addWidget(title)
        layout.addWidget(separator())

        ini = self._initial
        self.n_blocks = make_spinbox(1, 20, 1, ini.n_blocks)
        layout.addLayout(make_row("Blocks:", self.n_blocks))
        self.trials = make_spinbox(1, 100, 1, ini.trials_per_class_per_block)
        layout.addLayout(make_row("Trials per class per block:", self.trials))
        self.max_run = make_spinbox(1, 20, 1, ini.max_consecutive_same_class)
        layout.addLayout(make_row("Max same class in a row:", self.max_run))

        layout.addWidget(separator())
        self.fixation_ms = make_spinbox(100, 10000, 100, ini.fixation_ms)
        layout.addLayout(make_row("Fixation (ms):", self.fixation_ms))
        self.cue_ms = make_spinbox(100, 10000, 100, ini.cue_ms)
        layout.addLayout(make_row("Cue (ms):", self.cue_ms))
        self.task_ms = make_spinbox(0, 20000, 100, ini.task_ms)
        layout.addLayout(make_row("Imagery/execution window (ms):", self.task_ms))
        self.iti_min = make_spinbox(0, 20000, 100, ini.iti_min_ms)
        layout.addLayout(make_row("ITI min (ms):", self.iti_min))
        self.iti_max = make_spinbox(0, 20000, 100, ini.iti_max_ms)
        layout.addLayout(make_row("ITI max (ms):", self.iti_max))

        layout.addWidget(separator())
        self.feedback_combo = QComboBox()
        for label, value in FEEDBACK_LABELS:
            self.feedback_combo.addItem(label, value)
        self.feedback_combo.setCurrentIndex(
            max(0, self.feedback_combo.findData(ini.feedback))
        )
        layout.addLayout(make_row("Feedback:", self.feedback_combo))
        self._add_extra_fields(layout)

        layout.addWidget(separator())
        layout.addWidget(QLabel("MI / execution / SSVEP cues (main blocks):"))
        self._cue_checkboxes = make_cue_checkboxes(layout, ini.cues, MAIN_CUES)
        layout.addWidget(QLabel("Artifact cues (separate block):"))
        self._artifact_checkboxes = make_cue_checkboxes(
            layout, ini.artifact_cues, ARTIFACT_CUES
        )
        layout.addStretch()

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(CANCEL_STYLE)
        cancel_btn.clicked.connect(self.reject)
        start_btn = QPushButton(self.start_label)
        start_btn.setFixedHeight(36)
        start_btn.setStyleSheet(START_STYLE)
        start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(start_btn)
        outer.addLayout(btn_row)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: rgb(220, 80, 80);")
        outer.addWidget(self.error_label)

    def _add_extra_fields(self, layout: QVBoxLayout) -> None:
        """Hook for subclass-specific fields."""

    def _extra_values(self) -> dict[str, Any]:
        return {}

    def _on_start(self) -> None:
        try:
            config = dataclasses.replace(
                self._initial,
                n_blocks=self.n_blocks.value(),
                trials_per_class_per_block=self.trials.value(),
                max_consecutive_same_class=self.max_run.value(),
                fixation_ms=self.fixation_ms.value(),
                cue_ms=self.cue_ms.value(),
                task_ms=self.task_ms.value(),
                iti_min_ms=self.iti_min.value(),
                iti_max_ms=self.iti_max.value(),
                feedback=self.feedback_combo.currentData(),
                cues=get_selected_cues(self._cue_checkboxes),
                artifact_cues=get_selected_cues(self._artifact_checkboxes),
                **self._extra_values(),
            )
            config.validate()
        except ValueError as e:
            self.error_label.setText(str(e))
            return
        self._config = config
        self.accept()

    def get_config(self) -> SessionConfig | None:
        return self._config


class ExperimentConfigDialog(SessionConfigDialog):
    title = "Experiment Setup"
    start_label = "Start Experiment"


class CalibrationConfigDialog(SessionConfigDialog):
    title = "Calibration Setup"
    start_label = "Start Calibration"

    def _add_extra_fields(self, layout: QVBoxLayout) -> None:
        assert isinstance(self._initial, CalibrationConfig)
        self.result_ms = make_spinbox(100, 10000, 100, self._initial.result_ms)
        layout.addLayout(make_row("Result screen (ms):", self.result_ms))

    def _extra_values(self) -> dict[str, Any]:
        return {"result_ms": self.result_ms.value()}
