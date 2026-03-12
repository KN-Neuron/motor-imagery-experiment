from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QPushButton, QFrame
)
from PyQt6.QtGui import QFont

from src.config.config import CalibrationConfig, ExperimentConfig

_DIALOG_STYLE = """
    QDialog {
        background-color: rgb(25, 25, 38);
    }
    QLabel {
        color: rgb(200, 200, 220);
        font-family: 'Segoe UI', Arial;
    }
    QSpinBox {
        background-color: rgb(40, 40, 58);
        color: rgb(220, 220, 240);
        border: 1px solid rgba(100, 100, 150, 120);
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 14px;
        font-family: 'Segoe UI', Arial;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        width: 20px;
        background-color: rgb(55, 55, 78);
        border: none;
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background-color: rgb(80, 80, 120);
    }
    QComboBox {
        background-color: rgb(40, 40, 58);
        color: rgb(220, 220, 240);
        border: 1px solid rgba(100, 100, 150, 120);
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 14px;
        font-family: 'Segoe UI', Arial;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox QAbstractItemView {
        background-color: rgb(40, 40, 58);
        color: rgb(220, 220, 240);
        selection-background-color: rgb(70, 90, 160);
    }
"""

_CANCEL_STYLE = """
    QPushButton {
        background-color: rgba(60, 60, 80, 180);
        color: rgb(180, 180, 200);
        border-radius: 8px;
        font-size: 13px;
        font-family: 'Segoe UI', Arial;
        border: 1px solid rgba(80, 80, 110, 120);
    }
    QPushButton:hover {
        background-color: rgba(80, 80, 110, 220);
        color: white;
    }
"""

_START_STYLE = """
    QPushButton {
        background-color: rgba(70, 90, 180, 200);
        color: white;
        border-radius: 8px;
        font-size: 13px;
        font-weight: bold;
        font-family: 'Segoe UI', Arial;
        border: 1px solid rgba(100, 120, 220, 150);
    }
    QPushButton:hover {
        background-color: rgba(90, 110, 210, 230);
    }
"""


def _make_spinbox(min_val: int, max_val: int, step: int, default: int, width: int = 90) -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(min_val, max_val)
    sb.setSingleStep(step)
    sb.setValue(default)
    sb.setFixedWidth(width)
    return sb


def _make_row(label_text: str, widget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    lbl = QLabel(label_text)
    lbl.setFont(QFont("Segoe UI", 11))
    row.addWidget(lbl)
    row.addStretch()
    row.addWidget(widget)
    return row


def _separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color: rgba(100, 100, 150, 80);")
    return sep

class ExperimentConfigDialog(QDialog):
    """Dialog for configuring an experiment session; pre-fills fields from ExperimentConfig if provided."""

    def __init__(self, initial: ExperimentConfig | None = None, parent=None):
        super().__init__(parent)
        self._initial = initial
        self._config: ExperimentConfig | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Build and lay out all widgets."""
        self.setWindowTitle("Experiment Setup")
        self.setFixedSize(390, 390)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Experiment Configuration")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: rgb(180, 190, 255);")
        layout.addWidget(title)
        layout.addWidget(_separator())

        ini = self._initial

        self.trials_spinbox = _make_spinbox(1, 50, 1, ini.trials_per_class if ini else 5)
        layout.addLayout(_make_row("Trials per class:", self.trials_spinbox))

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Stratified", "stratified")
        self.strategy_combo.addItem("Random", "random")
        self.strategy_combo.setFixedWidth(130)
        if ini:
            idx = self.strategy_combo.findData(ini.strategy)
            if idx >= 0:
                self.strategy_combo.setCurrentIndex(idx)
        layout.addLayout(_make_row("Sampling strategy:", self.strategy_combo))

        layout.addWidget(_separator())

        self.fixation_ms = _make_spinbox(100, 10000, 100, ini.fixation_ms if ini else 2000)
        layout.addLayout(_make_row("Fixation duration (ms):", self.fixation_ms))

        self.cue_ms = _make_spinbox(100, 10000, 100, ini.cue_ms if ini else 4000)
        layout.addLayout(_make_row("Cue duration (ms):", self.cue_ms))

        self.rest_ms = _make_spinbox(100, 10000, 100, ini.rest_ms if ini else 1500)
        layout.addLayout(_make_row("Rest duration (ms):", self.rest_ms))

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(_CANCEL_STYLE)
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("Start Experiment")
        start_btn.setFixedHeight(36)
        start_btn.setStyleSheet(_START_STYLE)
        start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(start_btn)
        layout.addLayout(btn_row)

    def _on_start(self):
        """Collect widget values into an ExperimentConfig and accept the dialog."""
        self._config = ExperimentConfig(
            trials_per_class=self.trials_spinbox.value(),
            strategy=self.strategy_combo.currentData(),
            fixation_ms=self.fixation_ms.value(),
            cue_ms=self.cue_ms.value(),
            rest_ms=self.rest_ms.value(),
            cues=self._initial.cues if self._initial else None
        )
        self.accept()

    def get_config(self) -> ExperimentConfig | None:
        """Return the confirmed config, or None if the dialog was cancelled."""
        return self._config

class CalibrationConfigDialog(QDialog):
    """Dialog for configuring a calibration session; pre-fills fields from CalibrationConfig if provided."""

    def __init__(self, initial: CalibrationConfig | None = None, parent=None):
        super().__init__(parent)
        self._initial = initial
        self._config: CalibrationConfig | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Build and lay out all widgets."""
        self.setWindowTitle("Calibration Setup")
        self.setFixedSize(390, 430)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Calibration Configuration")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: rgb(180, 190, 255);")
        layout.addWidget(title)
        layout.addWidget(_separator())

        ini = self._initial

        self.trials_spinbox = _make_spinbox(1, 20, 1, ini.trials_per_class if ini else 2)
        layout.addLayout(_make_row("Trials per class:", self.trials_spinbox))

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Stratified", "stratified")
        self.strategy_combo.addItem("Random", "random")
        self.strategy_combo.setFixedWidth(130)
        if ini:
            idx = self.strategy_combo.findData(ini.strategy)
            if idx >= 0:
                self.strategy_combo.setCurrentIndex(idx)
        layout.addLayout(_make_row("Sampling strategy:", self.strategy_combo))

        layout.addWidget(_separator())

        self.fixation_ms = _make_spinbox(100, 10000, 100, ini.fixation_ms if ini else 2000)
        layout.addLayout(_make_row("Fixation duration (ms):", self.fixation_ms))

        self.cue_ms = _make_spinbox(100, 10000, 100, ini.cue_ms if ini else 4000)
        layout.addLayout(_make_row("Cue duration (ms):", self.cue_ms))

        self.rest_ms = _make_spinbox(100, 10000, 100, ini.rest_ms if ini else 1500)
        layout.addLayout(_make_row("Rest duration (ms):", self.rest_ms))

        self.result_ms = _make_spinbox(100, 10000, 100, ini.result_ms if ini else 2000)
        layout.addLayout(_make_row("Result duration (ms):", self.result_ms))

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(_CANCEL_STYLE)
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("Start Calibration")
        start_btn.setFixedHeight(36)
        start_btn.setStyleSheet(_START_STYLE)
        start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(start_btn)
        layout.addLayout(btn_row)

    def _on_start(self):
        """Collect widget values into a CalibrationConfig and accept the dialog."""
        self._config = CalibrationConfig(
            trials_per_class=self.trials_spinbox.value(),
            strategy=self.strategy_combo.currentData(),
            fixation_ms=self.fixation_ms.value(),
            cue_ms=self.cue_ms.value(),
            rest_ms=self.rest_ms.value(),
            result_ms=self.result_ms.value(),
            cues=self._initial.cues if self._initial else None
        )
        self.accept()

    def get_config(self) -> CalibrationConfig | None:
        """Return the confirmed config, or None if the dialog was cancelled."""
        return self._config
