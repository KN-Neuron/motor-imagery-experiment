import time
import numpy as np

from ..headset_config import HeadsetConfig


class MockDriver:
    """
    A mock headset driver for testing.
    Generates deterministic data streams.
    """

    def __init__(
        self,
        config: HeadsetConfig | None = None,
        sampling_rate: int = 250,
        channel_count: int = 4,
    ) -> None:
        if config is not None:
            # If a config is provided, use its settings
            # session_saver relies on the config for metadata, so set it here too
            self._config = config
            self._sampling_rate = config.sample_rate_hz
            self._channel_count = config.n_channels
        else:
            # Testing only: in practice MockDriver should always get a config.
            self._config = None  # type: ignore[assignment]
            self._sampling_rate = sampling_rate
            self._channel_count = channel_count
        self._init_state()

    def _init_state(self) -> None:
        # State tracking required by the Protocol
        self._is_connected = False
        self._is_streaming = False
        self._total_generated_samples = 0
        self._last_read_time = 0.0
        self._pending_dropped = 0

    @property
    def sampling_rate(self) -> int:
        return self._sampling_rate

    @property
    def channel_count(self) -> int:
        return self._channel_count

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    @property
    def config(self) -> HeadsetConfig:
        return self._config

    def connect(self) -> None:
        if not self._is_connected:
            self._is_connected = True
            print("[MockDriver] Hardware connected.")

    def disconnect(self) -> None:
        self._is_connected = False
        self._is_streaming = False
        print("[MockDriver] Hardware disconnected.")

    def start_stream(self) -> None:
        if not self._is_connected:
            raise RuntimeError("Cannot start stream: Mock headset not connected.")

        if not self._is_streaming:
            self._is_streaming = True
            # Anchor the simulation time to exactly when the stream starts
            self._last_read_time = time.perf_counter()
            print("[MockDriver] Stream started.")

    def stop_stream(self) -> None:
        if not self._is_connected:
            raise RuntimeError("Cannot stop stream: Mock headset not connected.")

        if self._is_streaming:
            self._is_streaming = False
            print("[MockDriver] Stream stopped.")

    def annotate(self, text: str) -> None:
        if not self._is_connected or not self._is_streaming:
            raise RuntimeError(
                "Cannot annotate: Mock headset is not actively streaming."
            )

        print(f"[MockDriver] Annotation injected into hardware stream: '{text}'")

    def inject_gap(self, n_samples: int) -> None:
        """Test hook: simulate `n_samples` lost in transit before the next read."""
        self._pending_dropped += n_samples

    def pop_dropped_samples(self) -> int:
        dropped, self._pending_dropped = self._pending_dropped, 0
        return dropped

    def read_available_samples(self) -> np.ndarray:
        if not self._is_connected or not self._is_streaming:
            raise RuntimeError(
                "Cannot read samples: Mock headset is not actively streaming."
            )

        now = time.perf_counter()
        elapsed = now - self._last_read_time

        n_samples = int(elapsed * self._sampling_rate)

        if n_samples <= 0:
            return np.empty((self._channel_count, 0), dtype=float)

        # Advance the "last read time" by exactly the amount of time those
        # samples represent. This prevents fractional-sample time drift
        self._last_read_time += n_samples / self._sampling_rate

        # Generate realistic EEG-like data: sine waves + noise, in µV range
        t = (
            np.arange(
                self._total_generated_samples,
                self._total_generated_samples + n_samples,
                dtype=float,
            )
            / self._sampling_rate
        )
        self._total_generated_samples += n_samples

        channels = []
        for ch in range(self._channel_count):
            freq = 8.0 + ch * 2.0  # alpha-band frequencies per channel
            signal = 50.0 * np.sin(2 * np.pi * freq * t)  # ~50 µV sine
            noise = np.random.default_rng(seed=None).normal(
                0, 10.0, n_samples
            )  # ~10 µV noise
            channels.append(signal + noise)

        return np.vstack(channels)
