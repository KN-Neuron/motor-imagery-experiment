import json
from pathlib import Path

import numpy as np
import pyedflib
import pytest

from src.eeg_headset.drivers import MockDriver
from src.eeg_headset.eeg_headset import EEGHeadset
from src.eeg_headset.headset_config import HeadsetConfig
from src.session_saver.session_saver import EVENTS_COLUMNS, SessionSaver

FS = 100


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000_000

    def __call__(self) -> int:
        self.now += 1_000
        return self.now


def make_saver(tmp_path: Path, **kwargs: object) -> SessionSaver:
    saver = SessionSaver(
        channel_labels=["C3", "C4"],
        sample_rate=FS,
        output_dir=tmp_path,
        session_name="s",
        clock=FakeClock(),
        **kwargs,  # type: ignore[arg-type]
    )
    saver.start_session()
    return saver


def read_tsv(path: Path) -> list[dict[str, str]]:
    lines = path.read_text().splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:]]


def chunk(n: int, value: float = 10.0) -> np.ndarray:
    return np.full((2, n), value)


def test_marker_onsets_match_sample_indices(tmp_path: Path) -> None:
    saver = make_saver(tmp_path)
    saver.on_chunk(chunk(37))
    saver.add_marker("A")
    saver.on_chunk(chunk(190))  # crosses two record boundaries
    saver.add_marker("B")
    saver.on_chunk(chunk(5))
    saver.stop_session()

    rows = read_tsv(tmp_path / "s" / "events.tsv")
    onsets = {r["trial_type"]: float(r["onset"]) for r in rows}
    assert onsets["A"] == pytest.approx(0.37)
    assert onsets["B"] == pytest.approx(2.27)
    assert onsets["END_OF_DATA"] == pytest.approx(2.32)

    reader = pyedflib.EdfReader(str(tmp_path / "s" / "session.edf"))
    ann = dict(zip(reader.readAnnotations()[2], reader.readAnnotations()[0]))
    reader.close()
    assert ann["A"] == pytest.approx(0.37)
    assert ann["B"] == pytest.approx(2.27)


def test_events_tsv_keeps_old_columns_first_and_adds_new(tmp_path: Path) -> None:
    saver = make_saver(tmp_path, feedback_mode="demo")
    saver.on_chunk(chunk(10))
    idx = saver.add_marker(
        "CUE", block_id=1, trial_id=3, condition="imagery", planned_duration=4.0
    )
    saver.on_chunk(chunk(10))
    saver.finish_marker(idx, actual_duration=4.01, interrupted=True)
    saver.stop_session()

    header = (tmp_path / "s" / "events.tsv").read_text().splitlines()[0].split("\t")
    assert header[:3] == ["onset", "duration", "trial_type"]
    assert header == EVENTS_COLUMNS
    row = read_tsv(tmp_path / "s" / "events.tsv")[0]
    assert row["block_id"] == "1" and row["trial_id"] == "3"
    assert row["condition"] == "imagery"
    assert row["planned_duration"] == "4.000"
    assert row["actual_duration"] == "4.010"
    assert row["interrupted"] == "true"
    assert row["feedback_mode"] == "demo"


def test_partial_last_record_is_flagged_not_silent(tmp_path: Path) -> None:
    saver = make_saver(tmp_path)
    data = np.vstack([np.arange(250.0), -np.arange(250.0)])
    saver.on_chunk(data)
    saver.stop_session()

    meta = json.loads((tmp_path / "s" / "session_metadata.json").read_text())
    assert meta["n_samples_real"] == 250
    assert meta["n_samples_in_edf"] == 300

    reader = pyedflib.EdfReader(str(tmp_path / "s" / "session.edf"))
    sig = reader.readSignal(0)
    ann = reader.readAnnotations()
    reader.close()
    end = ann[0][list(ann[2]).index("END_OF_DATA")]
    assert end == pytest.approx(2.5)
    # real signal is intact, zeros only after the END_OF_DATA marker
    np.testing.assert_allclose(sig[:250], data[0], atol=0.2)
    assert np.all(np.abs(sig[250:]) < 0.1)  # padding (quantised zero)


def test_data_gap_marker_and_alignment(tmp_path: Path) -> None:
    saver = make_saver(tmp_path)
    saver.on_chunk(chunk(50))
    saver.on_gap(30)
    saver.on_chunk(chunk(20))
    saver.add_marker("AFTER")
    saver.stop_session()

    rows = read_tsv(tmp_path / "s" / "events.tsv")
    gap = next(r for r in rows if r["trial_type"] == "DATA_GAP")
    assert float(gap["onset"]) == pytest.approx(0.5)
    assert float(gap["duration"]) == pytest.approx(0.3)
    after = next(r for r in rows if r["trial_type"] == "AFTER")
    assert float(after["onset"]) == pytest.approx(1.0)  # timeline not shifted
    meta = json.loads((tmp_path / "s" / "session_metadata.json").read_text())
    assert meta["data_gap_samples"] == 30


def test_headset_reports_gap_from_driver(tmp_path: Path) -> None:
    driver = MockDriver(config=HeadsetConfig.mock(n_channels=2, sample_rate_hz=FS))
    headset = EEGHeadset(driver)
    headset.connect()
    headset.start()
    saver = make_saver(tmp_path)
    headset.add_gap_subscriber(saver.on_gap)
    driver.inject_gap(25)
    headset.poll()
    saver.stop_session()
    rows = read_tsv(tmp_path / "s" / "events.tsv")
    assert any(r["trial_type"] == "DATA_GAP" for r in rows)


def test_sync_log_records_monotonic_times(tmp_path: Path) -> None:
    saver = make_saver(tmp_path)
    saver.on_chunk(chunk(10))
    first = saver.add_marker("A", planned_start_ns=123)
    saver.set_display_time(first, 999)
    saver.add_marker("B")
    saver.stop_session()

    rows = read_tsv(tmp_path / "s" / "sync_log.tsv")
    a, b = rows[0], rows[1]
    assert int(b["perf_counter_ns"]) > int(a["perf_counter_ns"]) > 0
    assert a["planned_start_perf_counter_ns"] == "123"
    assert a["display_perf_counter_ns"] == "999"
    assert a["last_packet_perf_counter_ns"] != "n/a"
    assert a["sample_index"] == "10"


def test_clipping_warning_and_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    saver = make_saver(tmp_path)
    big = chunk(10)
    big[1, :4] = 5000.0
    saver.on_chunk(big)
    saver.stop_session()

    assert "exceeds the EDF range" in capsys.readouterr().out
    meta = json.loads((tmp_path / "s" / "session_metadata.json").read_text())
    assert meta["clipped_samples_per_channel"] == {"C3": 0, "C4": 4}


def test_refuses_overwrite_and_path_traversal(tmp_path: Path) -> None:
    make_saver(tmp_path)
    with pytest.raises(FileExistsError):
        make_saver(tmp_path)
    with pytest.raises(ValueError):
        SessionSaver(["C3"], FS, tmp_path, session_name="../evil")
