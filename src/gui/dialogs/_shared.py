from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QFrame
from PyQt6.QtGui import QFont


DIALOG_STYLE = """
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
    QLineEdit {
        background-color: rgb(40, 40, 58);
        color: rgb(220, 220, 240);
        border: 1px solid rgba(100, 100, 150, 120);
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 14px;
        font-family: 'Segoe UI', Arial;
    }
    QCheckBox {
        color: rgb(200, 200, 220);
        font-family: 'Segoe UI', Arial;
        font-size: 12px;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid rgba(100, 100, 150, 120);
        border-radius: 3px;
        background-color: rgb(40, 40, 58);
    }
    QCheckBox::indicator:checked {
        background-color: rgba(70, 90, 180, 200);
        border-color: rgba(100, 120, 220, 150);
    }
    QCheckBox::indicator:hover {
        border-color: rgba(120, 140, 200, 180);
    }
"""

CANCEL_STYLE = """
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

START_STYLE = """
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


def make_spinbox(min_val: int, max_val: int, step: int, default: int, width: int = 90) -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(min_val, max_val)
    sb.setSingleStep(step)
    sb.setValue(default)
    sb.setFixedWidth(width)
    return sb


def make_row(label_text: str, widget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    lbl = QLabel(label_text)
    lbl.setFont(QFont("Segoe UI", 11))
    row.addWidget(lbl)
    row.addStretch()
    row.addWidget(widget)
    return row


def separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color: rgba(100, 100, 150, 80);")
    return sep
