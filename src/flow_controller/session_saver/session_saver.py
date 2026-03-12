from pathlib import Path
from datetime import datetime

import numpy as np


class SessionSaver:
    """Saves labeled EEG epochs to disk incrementally — one .npy file per trial.

    Directory layout:
        <output_dir>/
            <YYYYMMDD_HHMMSS>_<session_type>/
                trial_000_LEFT_HAND.npy
                trial_001_RIGHT_HAND.npy
                ...
    Each .npy file contains a single epoch of shape (n_channels, n_samples).
    """

    def __init__(self, session_type: str, output_dir: Path = Path("sessions")):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = output_dir / f"{timestamp}_{session_type}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._trial_count = 0
        print(f"[SessionSaver] Saving to: {self.session_dir}")

    def save_trial(self, data: np.ndarray, label: str) -> None:
        """Save a single epoch. data must have shape (n_channels, n_samples)."""
        filename = self.session_dir / f"trial_{self._trial_count:03d}_{label}.npy"
        np.save(filename, data)
        self._trial_count += 1

    @property
    def trial_count(self) -> int:
        return self._trial_count
