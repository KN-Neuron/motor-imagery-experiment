"""Export recorded sessions to a BIDS-EEG layout (the original files stay as is).

    python tools/export_bids.py sessions/experiments bids_out [--power-line-hz 50]

Reads <root>/sub-XXX/ses-YY/{session.edf,events.tsv,session_metadata.json,...}
and writes <out>/sub-XXX/ses-YY/eeg/sub-XXX_ses-YY_task-<task>_{eeg.edf,
events.tsv,channels.tsv,electrodes.tsv,eeg.json}. Extra files (sync_log.tsv,
session_metadata.json, qc_rest.npy) go to <out>/sourcedata/.

Unknown values are written as "n/a" (electrode positions, EEG reference,
software filters): nothing is invented. Only the standard library is used.
"""

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

BIDS_VERSION = "1.9.0"
TASK_LABELS = {"experiment": "motorimagery", "calibration": "calibration"}
SOURCE_FILES = ("sync_log.tsv", "session_metadata.json", "qc_rest.npy")
PARTICIPANTS_JSON = {
    "age": {"Description": "Age in years, or a range (e.g. 20-25)"},
    "sex": {"Description": "Optional self-reported sex"},
    "handedness": {"Description": "Self-reported handedness"},
    "ehi_sf_score": {"Description": "Edinburgh Handedness Inventory short form"},
    "cap_size": {"Description": "EEG cap size"},
    "bci_experience": {"Description": "Prior BCI experience"},
    "consent_given": {"Description": "Informed consent confirmed"},
    "consent_date": {"Description": "Date of consent (ISO 8601)"},
}


def write_tsv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def find_sessions(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("sub-*/ses-*/session.edf"))


def export_session(session: Path, out: Path, power_line_hz: float) -> Path:
    meta = json.loads((session / "session_metadata.json").read_text())
    sub, ses = session.parent.name, session.name
    task = TASK_LABELS.get(meta.get("task", ""), "motorimagery")
    stem = f"{sub}_{ses}_task-{task}"
    eeg_dir = out / sub / ses / "eeg"
    eeg_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(session / "session.edf", eeg_dir / f"{stem}_eeg.edf")
    shutil.copy2(session / "events.tsv", eeg_dir / f"{stem}_events.tsv")

    fs = meta["sample_rate_hz"]
    labels = meta["channel_labels"]
    write_tsv(
        eeg_dir / f"{stem}_channels.tsv",
        ["name", "type", "units", "sampling_frequency", "status"],
        [
            {
                "name": label,
                "type": "EEG",
                "units": "uV",
                "sampling_frequency": fs,
                "status": "good",
            }
            for label in labels
        ],
    )
    # Electrode positions are not measured by the application.
    write_tsv(
        eeg_dir / f"{stem}_electrodes.tsv",
        ["name", "x", "y", "z"],
        [{"name": label, "x": "n/a", "y": "n/a", "z": "n/a"} for label in labels],
    )
    sidecar = {
        "TaskName": task,
        "SamplingFrequency": fs,
        "EEGChannelCount": len(labels),
        "EEGReference": "n/a",
        "PowerLineFrequency": power_line_hz,
        "SoftwareFilters": "n/a",
        "RecordingType": "continuous",
        "RecordingDuration": meta["recording_duration_s"],
        "InstitutionName": "n/a",
        "Manufacturer": "BrainAccess",
        "ManufacturersModelName": (meta.get("headset") or {}).get("model") or "n/a",
        "SoftwareVersions": (meta.get("app") or {}).get("commit", "n/a"),
        "SamplesInEDF": meta["n_samples_in_edf"],
        "SamplesReal": meta["n_samples_real"],
        "Note": "EDF samples after SamplesReal are zero padding (END_OF_DATA "
        "event), not signal. Exclude events with practice=true and "
        "interrupted=true from the default analysis.",
    }
    (eeg_dir / f"{stem}_eeg.json").write_text(json.dumps(sidecar, indent=2) + "\n")

    source = out / "sourcedata" / sub / ses
    source.mkdir(parents=True, exist_ok=True)
    for name in SOURCE_FILES:
        if (session / name).exists():
            shutil.copy2(session / name, source / name)
    return eeg_dir


def copy_tables(root: Path, out: Path, sessions: list[Path]) -> None:
    participants = root / "participants.tsv"
    if participants.exists():
        shutil.copy2(participants, out / "participants.tsv")
        (out / "participants.json").write_text(
            json.dumps(PARTICIPANTS_JSON, indent=2) + "\n"
        )
    all_sessions = root / "sessions.tsv"
    if not all_sessions.exists():
        return
    with open(all_sessions, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for sub in {s.parent.name for s in sessions}:
        mine = [r for r in rows if r["participant_id"] == sub]
        if mine:
            columns = [c for c in mine[0] if c != "participant_id"]
            write_tsv(
                out / sub / f"{sub}_sessions.tsv",
                columns,
                [{c: r[c] for c in columns} for r in mine],
            )


def export(root: Path, out: Path, power_line_hz: float = 50.0) -> list[Path]:
    sessions = find_sessions(root)
    if not sessions:
        raise SystemExit(f"No sub-*/ses-*/session.edf found under {root}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "dataset_description.json").write_text(
        json.dumps(
            {
                "Name": "Motor imagery experiment (left/right hand)",
                "BIDSVersion": BIDS_VERSION,
                "DatasetType": "raw",
                "Authors": ["n/a"],
                "License": "n/a",
            },
            indent=2,
        )
        + "\n"
    )
    exported = [export_session(s, out, power_line_hz) for s in sessions]
    copy_tables(root, out, sessions)
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="data directory with sub-*/ses-*")
    parser.add_argument("out", type=Path, help="output BIDS directory")
    parser.add_argument("--power-line-hz", type=float, default=50.0)
    args = parser.parse_args()
    for path in export(args.root, args.out, args.power_line_hz):
        print(f"exported {path}")


if __name__ == "__main__":
    main()
