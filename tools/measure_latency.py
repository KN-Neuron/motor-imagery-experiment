"""Measure marker -> screen -> EEG latency (needs hardware for real numbers).

Two steps, see docs/latency.md for the full procedure:

1. Record: show a flashing square (photodiode target) and write a FLASH marker
   for every flash into a normal session directory while the EEG stream runs.
       python tools/measure_latency.py record --mock
       python tools/measure_latency.py record --model MAXI_32CH --flashes 100

2. Analyse: with a photodiode (or a test signal) wired to one EEG channel,
   find the edges in that channel and compare them with the FLASH markers.
       python tools/measure_latency.py analyze sessions/latency/<dir> \
           --channel Fp1

No latency values are built in: every number comes from your recording. With
--mock the "photodiode" does not exist, so analyze only works on real data.
"""

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def record(args: argparse.Namespace) -> None:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QColor, QPainter
    from PyQt6.QtWidgets import QApplication, QWidget

    from src.eeg_headset.drivers import MockDriver
    from src.eeg_headset.eeg_headset import EEGHeadset
    from src.eeg_headset.headset_config import HeadsetConfig, HeadsetModel
    from src.session_saver.session_saver import SessionSaver

    app = QApplication(sys.argv)
    if args.mock:
        driver = MockDriver(config=HeadsetConfig.mock())
    else:
        from src.eeg_headset.drivers import BrainAccessDriver

        config = HeadsetConfig(HeadsetModel(args.model), args.config)
        driver = BrainAccessDriver(config=config)
    headset = EEGHeadset(driver)
    headset.connect()
    headset.start()

    stamp = time.strftime("%Y%m%d_%H%M%S")
    saver = SessionSaver(
        headset.channel_labels,
        headset.sample_rate,
        Path(args.out),
        session_name=f"latency_{stamp}",
    )
    saver.start_session()
    headset.add_subscriber(saver.on_chunk)

    class Flash(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.on = False
            self.pending: int | None = None
            self.shown = 0

        def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(0, 0, 0))
            if self.on:
                painter.fillRect(0, 0, 200, 200, QColor(255, 255, 255))
            painter.end()
            if self.on and self.pending is not None:
                saver.set_display_time(self.pending, time.perf_counter_ns())
                self.pending = None

    widget = Flash()
    widget.showFullScreen()
    state = {"n": 0}

    def tick() -> None:
        headset.poll()
        if widget.on:
            widget.on = False
        else:
            if state["n"] >= args.flashes:
                finish()
                return
            state["n"] += 1
            widget.pending = saver.add_marker("FLASH")
            widget.on = True
        widget.update()

    def finish() -> None:
        timer.stop()
        headset.remove_subscriber(saver.on_chunk)
        saver.stop_session()
        headset.stop()
        print(f"Recorded {args.flashes} flashes in {saver.session_dir}")
        app.quit()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(int(args.interval_ms / 2))
    app.exec()


def load_signal(session: Path, channel: str) -> tuple[list[float], float]:
    import pyedflib

    reader = pyedflib.EdfReader(str(session / "session.edf"))
    try:
        labels = reader.getSignalLabels()
        if channel not in labels:
            raise SystemExit(f"Channel {channel!r} not in {labels}")
        index = labels.index(channel)
        fs = reader.getSampleFrequency(index)
        return list(reader.readSignal(index)), float(fs)
    finally:
        reader.close()


def rising_edges(signal: list[float], fs: float, refractory_s: float) -> list[int]:
    """Sample indices where the signal crosses the midpoint of its range upwards."""
    ordered = sorted(signal)
    low = ordered[int(0.05 * len(ordered))]
    high = ordered[int(0.95 * len(ordered))]
    if high - low <= 0:
        raise SystemExit("Flat channel: is the photodiode connected to it?")
    threshold = (low + high) / 2
    gap = int(refractory_s * fs)
    edges: list[int] = []
    for i in range(1, len(signal)):
        if signal[i - 1] < threshold <= signal[i]:
            if not edges or i - edges[-1] > gap:
                edges.append(i)
    return edges


def analyze(args: argparse.Namespace) -> None:
    session = Path(args.session)
    signal, fs = load_signal(session, args.channel)
    with open(session / "sync_log.tsv", newline="") as f:
        sync = list(csv.DictReader(f, delimiter="\t"))
    flashes = [r for r in sync if r["label"] == "FLASH"]
    edges = rising_edges(signal, fs, args.refractory_s)

    rows = []
    for row in flashes:
        marker_sample = int(row["sample_index"])
        edge = next((e for e in edges if e >= marker_sample), None)
        shown = row["display_perf_counter_ns"]
        rows.append(
            {
                "marker_sample": marker_sample,
                "edge_sample": edge,
                "marker_to_edge_ms": (
                    None if edge is None else (edge - marker_sample) / fs * 1000
                ),
                "marker_to_paint_ms": (
                    None
                    if shown == "n/a"
                    else (int(shown) - int(row["perf_counter_ns"])) / 1e6
                ),
            }
        )
    values = [
        r["marker_to_edge_ms"] for r in rows if r["marker_to_edge_ms"] is not None
    ]
    summary = {
        "n_flashes": len(flashes),
        "n_edges": len(edges),
        "n_paired": len(values),
        "sample_period_ms": 1000 / fs,
    }
    if values:
        quantiles = statistics.quantiles(values, n=20) if len(values) > 1 else values
        summary.update(
            median_ms=statistics.median(values),
            p5_ms=quantiles[0],
            p95_ms=quantiles[-1],
            min_ms=min(values),
            max_ms=max(values),
        )
    out = session / "latency_results.json"
    out.write_text(json.dumps({"summary": summary, "flashes": rows}, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"Per-flash results: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record", help="flash the screen and write FLASH markers")
    rec.add_argument("--mock", action="store_true", help="use the mock driver")
    rec.add_argument("--model", default="MAXI_32CH")
    rec.add_argument("--config", default="brainaccess.config.yaml")
    rec.add_argument("--flashes", type=int, default=100)
    rec.add_argument("--interval-ms", type=int, default=1000)
    rec.add_argument("--out", default="sessions/latency")
    rec.set_defaults(func=record)

    ana = sub.add_parser("analyze", help="compare photodiode edges with markers")
    ana.add_argument("session", help="session directory from `record`")
    ana.add_argument("--channel", required=True, help="channel with the photodiode")
    ana.add_argument("--refractory-s", type=float, default=0.2)
    ana.set_defaults(func=analyze)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
