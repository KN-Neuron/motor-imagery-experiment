from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QApplication
)
from PyQt6.QtGui import QFont
import yaml
import sys

from src.eeg_headset.headset_config import HeadsetConfig, HeadsetModel
from src.eeg_headset.eeg_headset import EEGHeadset
from src.eeg_headset.drivers import MockDriver, BrainAccessDriver
from src.eeg_headset.ipc import IpcHeadsetDriver, make_brainaccess_recipe

from ._shared import DIALOG_STYLE, CANCEL_STYLE, START_STYLE, make_row, separator


class HeadsetSelectionDialog(QDialog):
    MOCK_SENTINEL = "__MOCK__"
    CONFIG_PATH = "brainaccess.config.yaml"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._headset: EEGHeadset | None = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("EEG Headset Setup")
        self.setFixedSize(380, 300)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Select EEG Headset")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: rgb(180, 190, 255);")
        layout.addWidget(title)
        layout.addWidget(separator())

        models = self._load_available_models()

        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: rgb(40, 40, 58);
                color: rgb(220, 220, 240);
                border: 1px solid rgba(100, 100, 150, 120);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 14px;
                font-family: 'Segoe UI', Arial;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background-color: rgb(40, 40, 58);
                color: rgb(220, 220, 240);
                selection-background-color: rgb(70, 90, 160);
                font-size: 14px;
                font-family: 'Segoe UI', Arial;
            }
        """)
        self.model_combo.addItem("MOCK (no hardware)", self.MOCK_SENTINEL)
        for m in models:
            self.model_combo.addItem(m, m)
        layout.addLayout(make_row("Headset model:", self.model_combo))

        if not models:
            warn = QLabel("No hardware models found in brainaccess.config.yaml.\nOnly mock driver is available.")
            warn.setStyleSheet("color: rgb(200, 170, 70); font-size: 11px;")
            warn.setWordWrap(True)
            layout.addWidget(warn)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: rgb(220, 80, 80); font-size: 11px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        layout.addStretch()
        layout.addWidget(separator())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.quit_btn = QPushButton("Quit")
        self.quit_btn.setFixedHeight(36)
        self.quit_btn.setStyleSheet(CANCEL_STYLE)
        self.quit_btn.clicked.connect(self._on_quit)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedHeight(36)
        self.connect_btn.setStyleSheet(START_STYLE)
        self.connect_btn.clicked.connect(self._on_connect)

        btn_row.addWidget(self.quit_btn)
        btn_row.addWidget(self.connect_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _load_available_models() -> list[str]:
        try:
            with open(HeadsetSelectionDialog.CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            return []
        yaml_models = set((data.get("headsets") or {}).keys())
        return [m.value for m in HeadsetModel if m.value in yaml_models]

    def _on_connect(self) -> None:
        self.error_label.setText("")
        selected = self.model_combo.currentData()

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")
        QApplication.processEvents()

        try:
            if selected == self.MOCK_SENTINEL:
                driver = MockDriver(config=HeadsetConfig.mock())
            else:
                config = HeadsetConfig(model=HeadsetModel(selected), config_path=self.CONFIG_PATH)
                if sys.platform == "win32":
                    recipe = make_brainaccess_recipe(model=selected, config_path=self.CONFIG_PATH)
                    driver = IpcHeadsetDriver(recipe=recipe, config=config)
                else:
                    driver = BrainAccessDriver(config=config)

            headset = EEGHeadset(driver)
            headset.connect()

            if not headset.is_connected():
                raise RuntimeError("Driver reported disconnected after connect().")

        except Exception as e:
            self.error_label.setText(f"Connection failed: {e}")
            self.model_combo.setEnabled(False)
            self.connect_btn.setVisible(False)
            return

        self._headset = headset
        self.accept()

    def _on_quit(self) -> None:
        self.reject()

    def get_headset(self) -> EEGHeadset | None:
        return self._headset
