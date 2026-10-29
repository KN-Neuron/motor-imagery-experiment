import argparse
import csv
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import numpy as np

from src.session_saver.session_saver import SessionSaver

ROOT = Path(__file__).resolve().parent.parent.parent
FS = 250


def load_tool(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_session(root: Path, sub: str = "sub-001", ses: str = "ses-01") -> Path:
    saver = SessionSaver(["C3", "C4"], FS, root, session_name=f"{sub}/{ses}")
    saver.start_session()
    saver.on_chunk(np.zeros((2, 300)))
    saver.add_marker("LEFT_HAND_IMAGERY", block_id=1, trial_id=1, condition="imagery")
    saver.on_chunk(np.zeros((2, 100)))
    saver.set_metadata({"task": "experiment", "headset": {"model": None}, "app": {}})
    saver.stop_session()
    return saver.session_dir


def test_export_bids_layout_and_honest_unknowns(tmp_path: Path) -> None:
    export_bids = load_tool("export_bids")
    root, out = tmp_path / "data", tmp_path / "bids"
    session = make_session(root)
    (root / "participants.tsv").write_text("participant_id\tage\nsub-001\t20-25\n")
    (root / "sessions.tsv").write_text(
        "participant_id\tsession_id\tacq_time\nsub-001\tses-01\t2026-01-31T10:00:00\n"
    )

    export_bids.export(root, out)

    eeg = out / "sub-001" / "ses-01" / "eeg"
    stem = "sub-001_ses-01_task-motorimagery"
    for suffix in (
        "eeg.edf",
        "events.tsv",
        "channels.tsv",
        "electrodes.tsv",
        "eeg.json",
    ):
        assert (eeg / f"{stem}_{suffix}").exists(), suffix
    assert (out / "dataset_description.json").exists()
    assert (out / "participants.tsv").exists()
    assert (out / "sourcedata" / "sub-001" / "ses-01" / "sync_log.tsv").exists()
    # the original recording is untouched
    assert (session / "session.edf").read_bytes() == (
        eeg / f"{stem}_eeg.edf"
    ).read_bytes()

    sidecar = json.loads((eeg / f"{stem}_eeg.json").read_text())
    assert sidecar["SamplesReal"] == 400 and sidecar["SamplesInEDF"] == 500
    assert sidecar["RecordingDuration"] == 400 / FS
    assert sidecar["EEGReference"] == "n/a"  # not invented
    with open(eeg / f"{stem}_electrodes.tsv") as f:
        assert {r["x"] for r in csv.DictReader(f, delimiter="\t")} == {"n/a"}
    with open(eeg / f"{stem}_events.tsv") as f:
        header = f.readline().split("\t")
    assert header[:3] == ["onset", "duration", "trial_type"]


def test_latency_analysis_recovers_known_delay(tmp_path: Path) -> None:
    tool = load_tool("measure_latency")
    saver = SessionSaver(["PD"], FS, tmp_path, session_name="lat")
    saver.start_session()
    delay = 12  # samples between marker and photodiode edge (48 ms at 250 Hz)
    signal = np.zeros(FS * 10)
    for k in range(5):
        marker_at = FS * (1 + 2 * k)
        signal[marker_at + delay : marker_at + delay + 50] = 1000.0
    for k in range(5):
        pos = FS * (1 + 2 * k)
        saver.on_chunk(signal[saver.total_samples : pos].reshape(1, -1))
        saver.add_marker("FLASH")
    saver.on_chunk(signal[saver.total_samples :].reshape(1, -1))
    saver.stop_session()

    tool.analyze(
        argparse.Namespace(session=tmp_path / "lat", channel="PD", refractory_s=0.2)
    )

    result = json.loads((tmp_path / "lat" / "latency_results.json").read_text())
    assert result["summary"]["n_paired"] == 5
    assert abs(result["summary"]["median_ms"] - delay / FS * 1000) <= 1000 / FS
