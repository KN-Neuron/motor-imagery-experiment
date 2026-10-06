import csv
from pathlib import Path

import pytest

from src.session_metadata.participant import (
    ParticipantInfo,
    validate_participant,
    validate_participant_code,
    validate_session_name,
)
from src.session_metadata.tables import update_tables


def info(**kw: object) -> ParticipantInfo:
    base = dict(code="sub-001", consent_given=True, consent_date="2026-01-31")
    base.update(kw)
    return ParticipantInfo(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize("code", ["sub-001", "sub-A12", "sub-042"])
def test_valid_codes(code: str) -> None:
    result = validate_participant_code(code)
    assert result.ok and not result.warnings


@pytest.mark.parametrize(
    "code", ["Jan Kowalski", "sub-001 ", "sub-Łukasz1", "001", "sub-", "sub-a/b"]
)
def test_invalid_codes_rejected(code: str) -> None:
    assert not validate_participant_code(code).ok


@pytest.mark.parametrize("code", ["sub-JanKowalski", "sub-Anna"])
def test_name_like_codes_warn(code: str) -> None:
    result = validate_participant_code(code)
    assert result.ok and result.warnings


def test_session_name_validation() -> None:
    assert validate_session_name("").ok
    assert validate_session_name("pilot_1").ok
    assert not validate_session_name("moja sesja").ok
    assert not validate_session_name("sesja_żółć").ok
    assert not validate_session_name("../x").ok


def test_participant_requires_consent_and_valid_fields() -> None:
    assert validate_participant(info()).ok
    assert not validate_participant(info(consent_given=False)).ok
    assert not validate_participant(info(consent_date="yesterday")).ok
    assert not validate_participant(info(age="abc")).ok
    assert validate_participant(info(age="20-25")).ok
    assert not validate_participant(info(age="25-20")).ok
    assert not validate_participant(info(fatigue=6)).ok
    assert not validate_participant(info(handedness="x")).ok


def test_tables_upsert_participant_and_append_sessions(tmp_path: Path) -> None:
    update_tables(tmp_path, info(age="20-25"), "mi", "none", "2026-01-31T10:00:00")
    update_tables(
        tmp_path,
        info(session_number=2, age="20-25", notes="a\tb\nc"),
        "mi",
        "none",
        "2026-02-07T10:00:00",
    )
    with open(tmp_path / "participants.tsv") as f:
        participants = list(csv.DictReader(f, delimiter="\t"))
    with open(tmp_path / "sessions.tsv") as f:
        sessions = list(csv.DictReader(f, delimiter="\t"))
    assert len(participants) == 1 and participants[0]["age"] == "20-25"
    assert [s["session_id"] for s in sessions] == ["ses-01", "ses-02"]
    assert sessions[1]["notes"] == "a b c"
    assert sessions[0]["path"] == "sub-001/ses-01"
