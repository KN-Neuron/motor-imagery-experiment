from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit
)
from PyQt6.QtGui import QFont

from src.trials_config.trials_config import CalibrationConfig

from ._shared import DIALOG_STYLE, CANCEL_STYLE, START_STYLE, make_spinbox, make_row, separator
from ._cues import make_cue_checkboxes, get_selected_cues


class CalibrationConfigDialog(QDialog):
    """Dialog for configuring a calibration session; pre-fills fields from CalibrationConfig if provided."""

    def __init__(self, initial: CalibrationConfig | None = None, parent=None):
        super().__init__(parent)
        self._initial = initial
        self._config: CalibrationConfig | None = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Calibration Setup")
        self.setFixedSize(390, 640)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Calibration Configuration")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: rgb(180, 190, 255);")
        layout.addWidget(title)
        layout.addWidget(separator())

        ini = self._initial

        self.trials_spinbox = make_spinbox(1, 20, 1, ini.trials_per_class if ini else 2)
        layout.addLayout(make_row("Trials per class:", self.trials_spinbox))

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Stratified", "stratified")
        self.strategy_combo.addItem("Random", "random")
        self.strategy_combo.setFixedWidth(130)
        if ini:
            idx = self.strategy_combo.findData(ini.strategy)
            if idx >= 0:
                self.strategy_combo.setCurrentIndex(idx)
        layout.addLayout(make_row("Sampling strategy:", self.strategy_combo))

        layout.addWidget(separator())

        self.fixation_ms = make_spinbox(100, 10000, 100, ini.fixation_ms if ini else 2000)
        layout.addLayout(make_row("Fixation duration (ms):", self.fixation_ms))

        self.cue_ms = make_spinbox(100, 10000, 100, ini.cue_ms if ini else 4000)
        layout.addLayout(make_row("Cue duration (ms):", self.cue_ms))

        self.rest_ms = make_spinbox(100, 10000, 100, ini.rest_ms if ini else 1500)
        layout.addLayout(make_row("Rest duration (ms):", self.rest_ms))

        self.result_ms = make_spinbox(100, 10000, 100, ini.result_ms if ini else 2000)
        layout.addLayout(make_row("Result duration (ms):", self.result_ms))

        layout.addWidget(separator())

        cues_label = QLabel("Cues:")
        cues_label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(cues_label)

        self._cue_checkboxes = make_cue_checkboxes(layout, ini.cues if ini else None)

        layout.addWidget(separator())

        self.session_name_edit = QLineEdit()
        self.session_name_edit.setPlaceholderText("auto (timestamp)")
        self.session_name_edit.setFixedWidth(180)
        if ini and ini.session_name:
            self.session_name_edit.setText(ini.session_name)
        layout.addLayout(make_row("Session name:", self.session_name_edit))

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(CANCEL_STYLE)
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("Start Calibration")
        start_btn.setFixedHeight(36)
        start_btn.setStyleSheet(START_STYLE)
        start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(start_btn)
        layout.addLayout(btn_row)

    def _on_start(self):
        name = self.session_name_edit.text().strip() or None
        self._config = CalibrationConfig(
            trials_per_class=self.trials_spinbox.value(),
            strategy=self.strategy_combo.currentData(),
            fixation_ms=self.fixation_ms.value(),
            cue_ms=self.cue_ms.value(),
            rest_ms=self.rest_ms.value(),
            result_ms=self.result_ms.value(),
            cues=get_selected_cues(self._cue_checkboxes),
            session_name=name,
        )
        self.accept()

    def get_config(self) -> CalibrationConfig | None:
        return self._config
