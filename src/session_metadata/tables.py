import csv
from pathlib import Path

from .participant import ParticipantInfo

NA = "n/a"

PARTICIPANT_COLUMNS = [
    "participant_id",
    "age",
    "sex",
    "handedness",
    "ehi_sf_score",
    "cap_size",
    "bci_experience",
    "consent_given",
    "consent_date",
]

SESSION_COLUMNS = [
    "participant_id",
    "session_id",
    "session_name",
    "acq_time",
    "task",
    "feedback_mode",
    "fatigue_1_5",
    "sleep_quality_1_5",
    "notes",
    "path",
]


def _read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _write(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _na(value: object) -> str:
    return NA if value in (None, "") else str(value)


def participant_row(info: ParticipantInfo) -> dict[str, str]:
    return {
        "participant_id": info.code,
        "age": _na(info.age),
        "sex": _na(info.sex),
        "handedness": info.handedness,
        "ehi_sf_score": _na(info.ehi_score),
        "cap_size": _na(info.cap_size),
        "bci_experience": info.bci_experience,
        "consent_given": "true" if info.consent_given else "false",
        "consent_date": _na(info.consent_date),
    }


def session_row(
    info: ParticipantInfo, task: str, feedback_mode: str, acq_time: str
) -> dict[str, str]:
    # notes may hold free text: tabs/newlines would corrupt the TSV
    notes = " ".join(info.notes.split())
    return {
        "participant_id": info.code,
        "session_id": info.session_id,
        "session_name": _na(info.session_name),
        "acq_time": acq_time,
        "task": task,
        "feedback_mode": feedback_mode,
        "fatigue_1_5": _na(info.fatigue),
        "sleep_quality_1_5": _na(info.sleep_quality),
        "notes": _na(notes),
        "path": info.session_path,
    }


def update_tables(
    root: Path, info: ParticipantInfo, task: str, feedback_mode: str, acq_time: str
) -> None:
    """Upsert the participant row and append the session row (participants.tsv,
    sessions.tsv in the data directory `root`)."""
    root.mkdir(parents=True, exist_ok=True)

    path = root / "participants.tsv"
    rows = [r for r in _read(path) if r["participant_id"] != info.code]
    rows.append(participant_row(info))
    _write(path, PARTICIPANT_COLUMNS, sorted(rows, key=lambda r: r["participant_id"]))

    path = root / "sessions.tsv"
    rows = _read(path)
    rows.append(session_row(info, task, feedback_mode, acq_time))
    _write(path, SESSION_COLUMNS, rows)
