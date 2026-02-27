from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


@dataclass
class CalibrationConfig:
    trials_per_class: int
    strategy: str


class CalibrationConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config: CalibrationConfig | None = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Calibration Setup")
        self.setFixedSize(340, 240)
        self.setStyleSheet("""
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
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Calibration Configuration")
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: rgb(180, 190, 255);")
        layout.addWidget(title)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: rgba(100, 100, 150, 80);")
        layout.addWidget(separator)

        row = QHBoxLayout()
        row.setSpacing(12)

        label = QLabel("Trials per class:")
        label.setFont(QFont("Segoe UI", 11))
        row.addWidget(label)

        row.addStretch()

        self.trials_spinbox = QSpinBox()
        self.trials_spinbox.setRange(1, 10)
        self.trials_spinbox.setValue(2)
        self.trials_spinbox.setFixedWidth(80)
        row.addWidget(self.trials_spinbox)

        layout.addLayout(row)

        strategy_row = QHBoxLayout()
        strategy_row.setSpacing(12)

        strategy_label = QLabel("Sampling strategy:")
        strategy_label.setFont(QFont("Segoe UI", 11))
        strategy_row.addWidget(strategy_label)

        strategy_row.addStretch()

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Stratified", "stratified")
        self.strategy_combo.addItem("Random", "random")
        self.strategy_combo.setFixedWidth(120)
        strategy_row.addWidget(self.strategy_combo)

        layout.addLayout(strategy_row)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("""
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
        """)
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("Start Calibration")
        start_btn.setFixedHeight(36)
        start_btn.setStyleSheet("""
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
        """)
        start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(start_btn)
        layout.addLayout(btn_row)

    def _on_start(self):
        self._config = CalibrationConfig(
            trials_per_class=self.trials_spinbox.value(),
            strategy=self.strategy_combo.currentData()
        )
        self.accept()

    def get_config(self) -> CalibrationConfig | None:
        return self._config
