from pathlib import Path

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.session_metadata.participant import (
    BCI_VALUES,
    HANDEDNESS_VALUES,
    ParticipantInfo,
    validate_participant,
)

from ._shared import CANCEL_STYLE, DIALOG_STYLE, START_STYLE, make_row, separator

# Edinburgh Handedness Inventory (Oldfield 1971). Verify the link before use.
EHI_LINK = "https://doi.org/10.1016/0028-3932(71)90067-4"
NO_SCALE = "n/a"


class ParticipantDialog(QDialog):
    """Entry screen: pseudonymised participant data and consent confirmation.

    Do NOT enter names or other direct identifiers anywhere (notes included).
    """

    def __init__(self, data_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data_root = data_root
        self._info: ParticipantInfo | None = None
        self._shown_warnings: list[str] | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Participant")
        self.setFixedSize(460, 680)
        self.setStyleSheet(DIALOG_STYLE)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setSpacing(8)
        scroll.setWidget(body)
        outer.addWidget(scroll)

        title = QLabel("Participant and session")
        font = QFont("Segoe UI", 13)
        font.setWeight(QFont.Weight.Bold)
        title.setFont(font)
        layout.addWidget(title)
        warn = QLabel("Use a pseudonym only. Never enter a name or contact data.")
        warn.setStyleSheet("color: rgb(200, 170, 70);")
        warn.setWordWrap(True)
        layout.addWidget(warn)
        layout.addWidget(separator())

        self.code = QLineEdit("sub-")
        self.code.setFixedWidth(150)
        layout.addLayout(make_row("Participant code:", self.code))
        self.session_number = QSpinBox()
        self.session_number.setRange(1, 99)
        layout.addLayout(make_row("Session number:", self.session_number))
        self.session_name = QLineEdit()
        self.session_name.setPlaceholderText("optional technical label")
        self.session_name.setFixedWidth(180)
        layout.addLayout(make_row("Session label:", self.session_name))

        layout.addWidget(separator())
        self.age = QLineEdit()
        self.age.setPlaceholderText("23 or 20-25")
        self.age.setFixedWidth(120)
        layout.addLayout(make_row("Age (number or range):", self.age))
        self.sex = QComboBox()
        for label, value in (("n/a", ""), ("F", "F"), ("M", "M"), ("other", "other")):
            self.sex.addItem(label, value)
        layout.addLayout(make_row("Sex (optional):", self.sex))
        self.handedness = QComboBox()
        self.handedness.addItems(list(HANDEDNESS_VALUES))
        layout.addLayout(make_row("Handedness:", self.handedness))
        self.ehi = QSpinBox()
        self.ehi.setRange(-101, 100)
        self.ehi.setSpecialValueText(NO_SCALE)
        self.ehi.setValue(-101)
        layout.addLayout(make_row("EHI short form score (-100..100):", self.ehi))
        link = QLabel(f'<a href="{EHI_LINK}">Full Edinburgh Handedness Inventory</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)
        self.cap_size = QLineEdit()
        self.cap_size.setFixedWidth(80)
        layout.addLayout(make_row("Cap size:", self.cap_size))
        self.bci = QComboBox()
        self.bci.addItems(list(BCI_VALUES))
        layout.addLayout(make_row("BCI experience:", self.bci))
        self.fatigue = self._scale_combo()
        layout.addLayout(make_row("Fatigue (1 rested .. 5 tired):", self.fatigue))
        self.sleep = self._scale_combo()
        layout.addLayout(make_row("Sleep quality (1 bad .. 5 good):", self.sleep))

        layout.addWidget(separator())
        layout.addWidget(QLabel("Experimenter notes (no identifying data):"))
        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(70)
        layout.addWidget(self.notes)

        self.consent = QCheckBox("Informed consent given")
        layout.addWidget(self.consent)
        self.consent_date = QDateEdit(QDate.currentDate())
        self.consent_date.setCalendarPopup(True)
        self.consent_date.setDisplayFormat("yyyy-MM-dd")
        layout.addLayout(make_row("Consent date:", self.consent_date))
        layout.addStretch()

        self.message = QLabel("")
        self.message.setWordWrap(True)
        outer.addWidget(self.message)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(36)
        cancel.setStyleSheet(CANCEL_STYLE)
        cancel.clicked.connect(self.reject)
        self.start_btn = QPushButton("Continue")
        self.start_btn.setFixedHeight(36)
        self.start_btn.setStyleSheet(START_STYLE)
        self.start_btn.clicked.connect(self._on_start)
        row.addWidget(cancel)
        row.addWidget(self.start_btn)
        outer.addLayout(row)

    @staticmethod
    def _scale_combo() -> QComboBox:
        combo = QComboBox()
        combo.addItem(NO_SCALE, None)
        for i in range(1, 6):
            combo.addItem(str(i), i)
        return combo

    def collect(self) -> ParticipantInfo:
        ehi = self.ehi.value()
        return ParticipantInfo(
            code=self.code.text().strip(),
            session_number=self.session_number.value(),
            age=self.age.text().strip(),
            sex=self.sex.currentData(),
            handedness=self.handedness.currentText(),
            ehi_score=None if ehi < -100 else ehi,
            cap_size=self.cap_size.text().strip(),
            bci_experience=self.bci.currentText(),
            fatigue=self.fatigue.currentData(),
            sleep_quality=self.sleep.currentData(),
            notes=self.notes.toPlainText().strip(),
            consent_given=self.consent.isChecked(),
            consent_date=(
                self.consent_date.date().toString(Qt.DateFormat.ISODate)
                if self.consent.isChecked()
                else ""
            ),
            session_name=self.session_name.text().strip(),
        )

    def _on_start(self) -> None:
        info = self.collect()
        result = validate_participant(info)
        errors = list(result.errors)
        if (self._data_root / info.session_path / "session.edf").exists():
            errors.append(f"{info.session_path} already exists; use a new session no.")
        if errors:
            self.message.setStyleSheet("color: rgb(220, 80, 80);")
            self.message.setText("\n".join(errors))
            self._shown_warnings = None
            return
        if result.warnings and self._shown_warnings != result.warnings:
            # first click only shows the warning; clicking again accepts
            self._shown_warnings = result.warnings
            self.message.setStyleSheet("color: rgb(200, 170, 70);")
            self.message.setText(
                "\n".join(result.warnings) + "\nClick again to accept."
            )
            return
        self._info = info
        self.accept()

    def get_info(self) -> ParticipantInfo | None:
        return self._info
