import re
from dataclasses import dataclass
from datetime import date

CODE_RE = re.compile(r"^sub-[A-Za-z0-9]{1,16}$")
LABEL_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
# two capitalised words glued together, e.g. "sub-JanKowalski"
NAME_LIKE_RE = re.compile(r"^[A-Z][a-z]{2,}[ _-]?[A-Z][a-z]{2,}$")
AGE_RE = re.compile(r"^(\d{1,3})(-(\d{1,3}))?$")

SEX_VALUES = ("", "F", "M", "other")
HANDEDNESS_VALUES = ("right", "left", "ambidextrous")
BCI_VALUES = ("none", "some", "experienced")


@dataclass
class ParticipantInfo:
    """Pseudonymised participant data. Never put a name or contact data here."""

    code: str  # e.g. sub-001
    session_number: int = 1
    age: str = ""  # "23" or a range "20-25" (a range is preferred)
    sex: str = ""  # optional
    handedness: str = "right"
    ehi_score: int | None = None  # optional EHI short form laterality quotient
    cap_size: str = ""
    bci_experience: str = "none"
    fatigue: int | None = None  # 1 (rested) .. 5 (very tired), optional
    sleep_quality: int | None = None  # 1 (bad) .. 5 (good), optional
    notes: str = ""
    consent_given: bool = False
    consent_date: str = ""  # ISO date
    session_name: str = ""  # optional technical label

    @property
    def session_id(self) -> str:
        return f"ses-{self.session_number:02d}"

    @property
    def session_path(self) -> str:
        return f"{self.code}/{self.session_id}"


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_participant_code(code: str) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if any(c.isspace() for c in code):
        errors.append("Participant code must not contain spaces")
    if not code.isascii():
        errors.append("Participant code must be ASCII (no Polish letters)")
    if not errors and not CODE_RE.match(code):
        errors.append("Participant code must look like sub-001 (letters/digits)")
    label = code[4:] if code.startswith("sub-") else code
    if not errors and (
        NAME_LIKE_RE.match(label) or not any(c.isdigit() for c in label)
    ):
        warnings.append(
            "Code looks like a name; use a numeric pseudonym such as sub-001"
        )
    return ValidationResult(errors, warnings)


def validate_session_name(name: str) -> ValidationResult:
    if not name:
        return ValidationResult([], [])
    errors: list[str] = []
    warnings: list[str] = []
    if any(c.isspace() for c in name):
        errors.append("Session name must not contain spaces")
    if not name.isascii():
        errors.append("Session name must be ASCII (no Polish letters)")
    if not errors and not LABEL_RE.match(name):
        errors.append("Session name: letters, digits, '_' and '-' only (max 40)")
    if not errors and NAME_LIKE_RE.match(name):
        warnings.append("Session name looks like a person's name")
    return ValidationResult(errors, warnings)


def validate_participant(info: ParticipantInfo) -> ValidationResult:
    result = validate_participant_code(info.code)
    errors, warnings = list(result.errors), list(result.warnings)

    name_result = validate_session_name(info.session_name)
    errors += name_result.errors
    warnings += name_result.warnings

    if info.session_number < 1:
        errors.append("Session number must be >= 1")
    if info.age:
        match = AGE_RE.match(info.age)
        if not match:
            errors.append("Age: a number (23) or a range (20-25)")
        else:
            low = int(match.group(1))
            high = int(match.group(3)) if match.group(3) else low
            if not 5 <= low <= high <= 120:
                errors.append("Age out of range")
    if info.sex not in SEX_VALUES:
        errors.append(f"Sex must be one of {SEX_VALUES}")
    if info.handedness not in HANDEDNESS_VALUES:
        errors.append(f"Handedness must be one of {HANDEDNESS_VALUES}")
    if info.ehi_score is not None and not -100 <= info.ehi_score <= 100:
        errors.append("EHI score must be in -100..100")
    if info.bci_experience not in BCI_VALUES:
        errors.append(f"BCI experience must be one of {BCI_VALUES}")
    for label, value in (("Fatigue", info.fatigue), ("Sleep", info.sleep_quality)):
        if value is not None and not 1 <= value <= 5:
            errors.append(f"{label} must be 1..5")
    if not info.consent_given:
        errors.append("Consent must be confirmed before recording")
    else:
        try:
            date.fromisoformat(info.consent_date)
        except ValueError:
            errors.append("Consent date must be an ISO date (YYYY-MM-DD)")
    return ValidationResult(errors, warnings)
