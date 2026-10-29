import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pyedflib

# Physical range of the EDF signal in µV (BrainAccess outputs µV).
# Samples outside are clipped by the EDF digital range, so we count and warn.
PHYS_MIN = -3200.0
PHYS_MAX = 3200.0

NA = "n/a"

EVENTS_COLUMNS = [
    "onset",
    "duration",
    "trial_type",
    "block_id",
    "trial_id",
    "condition",
    "planned_duration",
    "actual_duration",
    "interrupted",
    "practice",
    "feedback_mode",
]

SYNC_COLUMNS = [
    "marker_idx",
    "label",
    "sample_index",
    "perf_counter_ns",
    "last_packet_perf_counter_ns",
    "planned_start_perf_counter_ns",
    "display_perf_counter_ns",
]


@dataclass
class Marker:
    sample_idx: int
    label: str
    perf_ns: int
    last_packet_ns: int | None
    block_id: int | None = None
    trial_id: int | None = None
    condition: str | None = None
    planned_duration: float | None = None
    actual_duration: float | None = None
    interrupted: bool = False
    practice: bool = False
    planned_start_ns: int | None = None
    display_ns: int | None = None
    duration_override: float | None = None  # e.g. DATA_GAP length in seconds


def _fmt(value: Any) -> str:
    if value is None:
        return NA
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


class SessionSaver:
    """
    Continuously saves EEG data directly to EDF+ format.

    Usage:
        saver = SessionSaver(channel_labels, sample_rate, output_dir)
        saver.start_session()
        headset.add_subscriber(saver.on_chunk)   # called every poll()
        saver.add_marker("LEFT_HAND_IMAGERY")    # called by state on step transitions
        ...
        headset.remove_subscriber(saver.on_chunk)
        saver.stop_session()  # finalizes EDF, events.tsv, sync_log.tsv, metadata

    Output files (session.edf and the first three columns of events.tsv keep
    their original format; everything else is additive):
        session.edf, events.tsv, sync_log.tsv, session_metadata.json
    """

    def __init__(
        self,
        channel_labels: list[str],
        sample_rate: int,
        output_dir: Path = Path("sessions"),
        session_name: str | None = None,
        feedback_mode: str = "none",
        clock: Callable[[], int] = time.perf_counter_ns,
    ) -> None:
        self.channel_labels = channel_labels
        self.sample_rate = sample_rate
        self.n_channels = len(channel_labels)
        self.feedback_mode = feedback_mode
        self._clock = clock

        folder_name = (
            session_name
            if session_name
            else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        self.session_dir = output_dir / folder_name
        if ".." in Path(folder_name).parts:
            raise ValueError(f"Invalid session folder name: {folder_name!r}")
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self._writer: pyedflib.EdfWriter | None = None
        self._total_samples: int = 0
        self._markers: list[Marker] = []
        self._last_packet_ns: int | None = None
        self._start_ns: int = 0
        self._start_unix_ns: int = 0
        self._gap_samples: int = 0
        self._clipped: np.ndarray = np.zeros(self.n_channels, dtype=int)
        self._metadata: dict[str, Any] = {}

        # Internal buffer to accumulate samples until a full data record is ready.
        # EDF writes data in fixed-size records (1 second = sample_rate samples).
        self._chunk_buffer: np.ndarray = np.zeros((self.n_channels, sample_rate))
        self._buffer_pos: int = 0

    @property
    def total_samples(self) -> int:
        """Real samples received so far (excluding padding)."""
        return self._total_samples + self._buffer_pos

    def set_metadata(self, metadata: dict[str, Any]) -> None:
        """Extra fields merged into session_metadata.json at stop_session()."""
        self._metadata.update(metadata)

    def start_session(self) -> None:
        """Open EDF+ file and write channel headers."""
        edf_path = self.session_dir / "session.edf"
        if edf_path.exists():
            raise FileExistsError(f"Refusing to overwrite {edf_path}")
        self._writer = pyedflib.EdfWriter(
            str(edf_path), self.n_channels, file_type=pyedflib.FILETYPE_EDFPLUS
        )

        headers: list[dict[str, str | int | float | None]] = []
        for label in self.channel_labels:
            headers.append(
                {
                    "label": label,
                    "dimension": "uV",
                    "sample_frequency": self.sample_rate,
                    "physical_min": PHYS_MIN,
                    "physical_max": PHYS_MAX,
                    "digital_min": -32768,
                    "digital_max": 32767,
                    "transducer": "",
                    "prefilter": "",
                }
            )

        self._writer.setSignalHeaders(headers)
        self._chunk_buffer = np.zeros((self.n_channels, self.sample_rate), dtype=float)
        self._buffer_pos = 0
        self._total_samples = 0
        self._markers = []
        self._gap_samples = 0
        self._clipped = np.zeros(self.n_channels, dtype=int)
        self._start_ns = self._clock()
        self._start_unix_ns = time.time_ns()

        print(f"[SessionSaver] Session started, saving to: {self.session_dir}")

    def on_chunk(self, chunk: np.ndarray) -> None:
        """
        Subscriber callback — receives each chunk from EEGHeadset.poll().

        Args:
            chunk: EEG data of shape (n_channels, n_samples).
        """
        if self._writer is None:
            return

        self._last_packet_ns = self._clock()
        self._check_clipping(chunk)

        n_samples = chunk.shape[1]
        written = 0

        while written < n_samples:
            space_left = self.sample_rate - self._buffer_pos
            to_copy = min(space_left, n_samples - written)

            end = self._buffer_pos + to_copy
            self._chunk_buffer[:, self._buffer_pos : end] = chunk[
                :, written : written + to_copy
            ]
            self._buffer_pos += to_copy
            written += to_copy

            if self._buffer_pos >= self.sample_rate:
                self._flush_record()

    def on_gap(self, n_missing: int) -> None:
        """
        Called when the driver reports `n_missing` lost samples before the next
        chunk. The gap is filled with zeros so the EDF timeline stays aligned
        with wall-clock time, and a DATA_GAP marker (with its duration) flags
        the filled interval: it must be excluded from analysis.
        """
        if self._writer is None or n_missing <= 0:
            return

        idx = self.add_marker("DATA_GAP")
        self._markers[idx].duration_override = n_missing / self.sample_rate
        self._gap_samples += n_missing
        print(f"[SessionSaver] WARNING: DATA_GAP of {n_missing} samples")
        self.on_chunk(np.zeros((self.n_channels, n_missing)))

    def add_marker(
        self,
        label: str,
        *,
        block_id: int | None = None,
        trial_id: int | None = None,
        condition: str | None = None,
        planned_duration: float | None = None,
        practice: bool = False,
        planned_start_ns: int | None = None,
    ) -> int:
        """Record a marker at the current sample position. Returns its index."""
        self._markers.append(
            Marker(
                sample_idx=self.total_samples,
                label=label,
                perf_ns=self._clock(),
                last_packet_ns=self._last_packet_ns,
                block_id=block_id,
                trial_id=trial_id,
                condition=condition,
                planned_duration=planned_duration,
                practice=practice,
                planned_start_ns=planned_start_ns,
            )
        )
        return len(self._markers) - 1

    def finish_marker(
        self, idx: int, actual_duration: float, interrupted: bool = False
    ) -> None:
        """Fill in the measured duration of the step that started with marker `idx`."""
        marker = self._markers[idx]
        marker.actual_duration = actual_duration
        marker.interrupted = interrupted

    def set_display_time(self, idx: int, display_ns: int) -> None:
        """Time (perf_counter_ns) at which the step was first painted."""
        self._markers[idx].display_ns = display_ns

    def stop_session(self) -> None:
        """Flush remaining data, write annotations, close EDF and sidecar files."""
        if self._writer is None:
            return

        real_samples = self.total_samples
        self.add_marker("END_OF_DATA")

        # Flush any remaining buffered samples as a (zero-padded) partial record.
        # The padding is NOT signal: END_OF_DATA and n_samples_real mark its start.
        if self._buffer_pos > 0:
            self._flush_partial_record()

        for marker in self._markers:
            duration = marker.duration_override
            self._writer.writeAnnotation(
                marker.sample_idx / self.sample_rate,
                -1 if duration is None else duration,
                marker.label,
            )

        self._writer.close()
        self._writer = None

        total_seconds = real_samples / self.sample_rate
        print(
            f"[SessionSaver] EDF saved: {real_samples} samples "
            f"({total_seconds:.1f}s), {len(self._markers)} markers"
        )

        self._write_events_tsv(real_samples)
        self._write_sync_log()
        self._write_metadata(real_samples)

    def _check_clipping(self, chunk: np.ndarray) -> None:
        over = np.abs(chunk) > PHYS_MAX
        if not over.any():
            return
        per_channel = over.sum(axis=1)
        for ch in np.nonzero(per_channel)[0]:
            if self._clipped[ch] == 0:
                print(
                    f"[SessionSaver] WARNING: channel {self.channel_labels[ch]} "
                    f"exceeds the EDF range ±{PHYS_MAX:.0f} µV (DC offset?); "
                    "samples will be clipped in session.edf"
                )
        self._clipped += per_channel

    def _flush_record(self) -> None:
        """Write one full data record (1 second) to EDF."""
        assert self._writer is not None
        self._writer.writeSamples(
            [self._chunk_buffer[ch, :] for ch in range(self.n_channels)]
        )
        self._total_samples += self.sample_rate
        self._buffer_pos = 0

    def _flush_partial_record(self) -> None:
        """Write remaining samples (less than one full record) to EDF."""
        assert self._writer is not None
        # writeSamples expects exactly sample_rate samples per channel per record.
        real_samples = self._buffer_pos
        self._chunk_buffer[:, real_samples:] = 0.0

        self._writer.writeSamples(
            [self._chunk_buffer[ch, :] for ch in range(self.n_channels)]
        )
        self._total_samples += real_samples
        self._buffer_pos = 0

    def _write_events_tsv(self, real_samples: int) -> None:
        """Generate BIDS-style events TSV from markers."""
        events_path = self.session_dir / "events.tsv"
        with open(events_path, "w") as f:
            f.write("\t".join(EVENTS_COLUMNS) + "\n")
            for i, m in enumerate(self._markers):
                onset = m.sample_idx / self.sample_rate
                if m.duration_override is not None:
                    duration = m.duration_override
                else:
                    # Duration = time until next marker, or until end of recording
                    if i + 1 < len(self._markers):
                        next_idx = self._markers[i + 1].sample_idx
                    else:
                        next_idx = real_samples
                    duration = (next_idx - m.sample_idx) / self.sample_rate
                row = [
                    f"{onset:.3f}",
                    f"{duration:.3f}",
                    m.label,
                    _fmt(m.block_id),
                    _fmt(m.trial_id),
                    _fmt(m.condition),
                    _fmt(m.planned_duration),
                    _fmt(m.actual_duration),
                    _fmt(m.interrupted),
                    _fmt(m.practice),
                    self.feedback_mode,
                ]
                f.write("\t".join(row) + "\n")

        print(f"[SessionSaver] Events TSV saved: {events_path}")

    def _write_sync_log(self) -> None:
        with open(self.session_dir / "sync_log.tsv", "w") as f:
            f.write("\t".join(SYNC_COLUMNS) + "\n")
            for i, m in enumerate(self._markers):
                row = [
                    str(i),
                    m.label,
                    str(m.sample_idx),
                    str(m.perf_ns),
                    _fmt(m.last_packet_ns),
                    _fmt(m.planned_start_ns),
                    _fmt(m.display_ns),
                ]
                f.write("\t".join(row) + "\n")

    def _write_metadata(self, real_samples: int) -> None:
        elapsed_s = (self._clock() - self._start_ns) / 1e9
        stats = {
            "n_samples_real": real_samples,
            "n_samples_in_edf": int(np.ceil(real_samples / self.sample_rate))
            * self.sample_rate,
            "recording_duration_s": real_samples / self.sample_rate,
            "padding_note": "EDF records are 1 s; samples after n_samples_real "
            "are zero padding (marked by END_OF_DATA), not signal",
            "data_gap_samples": self._gap_samples,
            "clipped_samples_per_channel": {
                label: int(n) for label, n in zip(self.channel_labels, self._clipped)
            },
            "edf_physical_range_uv": [PHYS_MIN, PHYS_MAX],
            "wall_clock_elapsed_s": elapsed_s,
            "expected_samples_from_wall_clock": int(elapsed_s * self.sample_rate),
            "t0_perf_counter_ns": self._start_ns,
            "t0_unix_ns": self._start_unix_ns,
            "feedback_mode": self.feedback_mode,
            "sample_rate_hz": self.sample_rate,
            "channel_labels": self.channel_labels,
            "units": "uV",
        }
        data = {**stats, **self._metadata}
        with open(self.session_dir / "session_metadata.json", "w") as f:
            json.dump(data, f, indent=2, default=str)
            f.write("\n")
