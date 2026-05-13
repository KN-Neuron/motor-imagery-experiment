from pathlib import Path
from datetime import datetime

import numpy as np
import pyedflib


# Standard physical range for EEG signals in µV.
# BrainAccess outputs data in µV; this range covers typical EEG amplitudes.
PHYS_MIN = -3200.0
PHYS_MAX = 3200.0


class SessionSaver:
    """
    Continuously saves EEG data directly to EDF+ format.

    Usage:
        saver = SessionSaver(channel_labels, sample_rate, output_dir)
        saver.start_session()
        headset.add_subscriber(saver.on_chunk)   # called every poll()
        saver.add_marker("LEFT_HAND")            # called by state on step transitions
        ...
        headset.remove_subscriber(saver.on_chunk)
        saver.stop_session()                     # finalizes EDF + writes events TSV
    """

    def __init__(self, channel_labels: list[str], sample_rate: int, output_dir: Path = Path("sessions"), session_name: str | None = None) -> None:
        self.channel_labels = channel_labels
        self.sample_rate = sample_rate
        self.n_channels = len(channel_labels)

        folder_name = session_name if session_name else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.session_dir = output_dir / folder_name
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self._writer: pyedflib.EdfWriter | None = None
        self._total_samples: int = 0
        self._markers: list[tuple[int, str]] = []

        # Internal buffer to accumulate samples until a full data record is ready.
        # EDF writes data in fixed-size records (1 second = sample_rate samples).
        self._chunk_buffer: np.ndarray | None = None
        self._buffer_pos: int = 0

    def start_session(self) -> None:
        """Open EDF+ file and write channel headers."""
        edf_path = self.session_dir / "session.edf"
        self._writer = pyedflib.EdfWriter(str(edf_path), self.n_channels, file_type=pyedflib.FILETYPE_EDFPLUS)

        headers = []
        for label in self.channel_labels:
            headers.append({
                "label": label,
                "dimension": "uV",
                "sample_frequency": self.sample_rate,
                "physical_min": PHYS_MIN,
                "physical_max": PHYS_MAX,
                "digital_min": -32768,
                "digital_max": 32767,
                "transducer": "",
                "prefilter": "",
            })

        self._writer.setSignalHeaders(headers)
        self._chunk_buffer = np.zeros((self.n_channels, self.sample_rate), dtype=float)
        self._buffer_pos = 0
        self._total_samples = 0
        self._markers = []

        print(f"[SessionSaver] Session started, saving to: {self.session_dir}")

    def on_chunk(self, chunk: np.ndarray) -> None:
        """
        Subscriber callback — receives each chunk from EEGHeadset.poll().

        Args:
            chunk: EEG data of shape (n_channels, n_samples).
        """
        if self._writer is None:
            return

        n_samples = chunk.shape[1]
        written = 0

        while written < n_samples:
            space_left = self.sample_rate - self._buffer_pos
            to_copy = min(space_left, n_samples - written)

            self._chunk_buffer[:, self._buffer_pos:self._buffer_pos + to_copy] = chunk[:, written:written + to_copy]
            self._buffer_pos += to_copy
            written += to_copy

            if self._buffer_pos >= self.sample_rate:
                self._flush_record()

    def add_marker(self, label: str) -> None:
        """Record a marker at the current sample position."""
        self._markers.append((self._total_samples + self._buffer_pos, label))

    def stop_session(self) -> None:
        """Flush remaining data, write annotations, close EDF, and generate events TSV."""
        if self._writer is None:
            return

        # Flush any remaining buffered samples as a partial record
        if self._buffer_pos > 0:
            self._flush_partial_record()

        # Write all markers as EDF+ annotations
        for sample_idx, label in self._markers:
            onset_sec = sample_idx / self.sample_rate
            self._writer.writeAnnotation(onset_sec, -1, label)

        self._writer.close()
        self._writer = None

        total_seconds = self._total_samples / self.sample_rate
        print(f"[SessionSaver] EDF saved: {self._total_samples} samples ({total_seconds:.1f}s), {len(self._markers)} markers")

        self._write_events_tsv()

    def _flush_record(self) -> None:
        """Write one full data record (1 second) to EDF."""
        self._writer.writeSamples(
            [self._chunk_buffer[ch, :] for ch in range(self.n_channels)]
        )
        self._total_samples += self.sample_rate
        self._buffer_pos = 0

    def _flush_partial_record(self) -> None:
        """Write remaining samples (less than one full record) to EDF."""
        # writeSamples expects exactly sample_rate samples per channel per record.
        # Pad with zeros to fill the record, but track real sample count.
        real_samples = self._buffer_pos
        if real_samples < self.sample_rate:
            self._chunk_buffer[:, real_samples:] = 0.0

        self._writer.writeSamples(
            [self._chunk_buffer[ch, :] for ch in range(self.n_channels)]
        )
        self._total_samples += real_samples
        self._buffer_pos = 0

    def _write_events_tsv(self) -> None:
        """Generate BIDS-style events TSV from markers."""
        if not self._markers:
            return

        events_path = self.session_dir / "events.tsv"
        with open(events_path, "w") as f:
            f.write("onset\tduration\ttrial_type\n")
            for i, (sample_idx, label) in enumerate(self._markers):
                onset = sample_idx / self.sample_rate
                # Duration = time until next marker, or until end of recording
                if i + 1 < len(self._markers):
                    next_sample_idx = self._markers[i + 1][0]
                else:
                    next_sample_idx = self._total_samples
                duration = (next_sample_idx - sample_idx) / self.sample_rate
                f.write(f"{onset:.3f}\t{duration:.3f}\t{label}\n")

        print(f"[SessionSaver] Events TSV saved: {events_path}")
