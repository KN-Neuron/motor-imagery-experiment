from pathlib import Path
from datetime import datetime

import numpy as np
import pyedflib


class SessionSaver:
    """
    A class to save session data and labels to a specified directory.
    All trial data is appended to a single data.csv file, with labels in labels.csv.
    On finalize(), converts CSV data to EDF + EDF events (MNE/BIDS TSV).
    """

    def __init__(self, channel_labels: list[str], sample_rate: int, output_dir: Path = Path("sessions")):
        self.channel_labels = channel_labels
        self.sample_rate = sample_rate

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.session_dir = output_dir / f"{timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        with open(self.session_dir / "data.csv", "w") as f:
            f.write("# " + ",".join(channel_labels) + "\n")

        print(f"[SessionSaver] Saving to: {self.session_dir}")

    def save_step(self, data: np.ndarray, label: str, duration: float) -> None:
        """Append trial data to data.csv and label+duration to labels.csv."""
        with open(self.session_dir / "data.csv", "a") as f:
            np.savetxt(f, data.T, delimiter=",", fmt="%.6f")
        with open(self.session_dir / "labels.csv", "a") as f:
            f.write(f"{label},{duration}\n")

    def export_to_edf(self) -> None:
        """Convert accumulated CSV data to EDF + events TSV (MNE/BIDS style)."""
        data_path = self.session_dir / "data.csv"
        labels_path = self.session_dir / "labels.csv"

        # Load EEG data: (n_samples, n_channels)
        data = np.loadtxt(data_path, delimiter=",")
        if data.ndim == 1:
            data = data.reshape(1, -1)
        n_samples, n_channels = data.shape

        # Write EDF via pyedflib
        edf_path = self.session_dir / "session.edf"
        writer = pyedflib.EdfWriter(str(edf_path), n_channels, file_type=pyedflib.FILETYPE_EDFPLUS)
        try:
            headers = []
            for i, label in enumerate(self.channel_labels):
                channel_data = data[:, i]
                phys_min = float(channel_data.min())
                phys_max = float(channel_data.max())
                if phys_min == phys_max:
                    phys_max = phys_min + 1.0

                headers.append({
                    "label": label,
                    "dimension": "uV",
                    "sample_frequency": self.sample_rate,
                    "physical_min": phys_min,
                    "physical_max": phys_max,
                    "digital_min": -32768,
                    "digital_max": 32767,
                    "transducer": "",
                    "prefilter": "",
                })

            writer.setSignalHeaders(headers)
            writer.writeSamples([data[:, i] for i in range(n_channels)])
        finally:
            writer.close()

        print(f"[SessionSaver] Exported EDF: {edf_path} ({n_samples} samples, {n_channels} channels)")

        # Write events TSV (MNE/BIDS style)
        if not labels_path.exists():
            return

        events_path = self.session_dir / "session.edf.events"
        onset = 0.0
        with open(events_path, "w") as f:
            f.write("onset\tduration\ttrial_type\n")
            with open(labels_path, "r") as lf:
                for line in lf:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    label = parts[0]
                    duration = float(parts[1])
                    f.write(f"{onset:.3f}\t{duration:.3f}\t{label}\n")
                    onset += duration

        print(f"[SessionSaver] Exported events: {events_path}")
