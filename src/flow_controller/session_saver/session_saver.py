from pathlib import Path
from datetime import datetime

import numpy as np


class SessionSaver:
    """
    A class to save session data and labels to a specified directory.
    All trial data is appended to a single data.csv file, with labels in labels.csv.
    """

    def __init__(self, channel_labels: list[str], output_dir: Path = Path("sessions")):
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
