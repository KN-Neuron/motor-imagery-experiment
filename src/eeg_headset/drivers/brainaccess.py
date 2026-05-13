import numpy as np
from brainaccess.utils import acquisition

from ..headset_config import HeadsetConfig
from brainaccess.core.eeg_manager import EEGManager


class BrainAccessDriver:
    """
    BrainAccess EEG driver for interfacing with the BrainAccess SDK.\n
    Quirks:
    - EEG mode "accumulate" retains all data forever, and
    "roll" only keeps n latest seconds,
    so we have to manually clear the buffer after reading samples
    to achieve dynamic rolling window behavior.
    (the "roll" functionality is achieved later in the RingBuffer, which
    1. is more efficient and 2. keeps the protocol contract)
    """

    def __init__(self, config: HeadsetConfig):
        self._config = config
        self._eeg = acquisition.EEG(mode="accumulate")
        self._mgr = EEGManager()

    @property
    def sampling_rate(self) -> int:
        return self._config.sample_rate_hz

    @property
    def channel_count(self) -> int:
        return self._config.n_channels

    @property
    def is_connected(self) -> bool:
        return self._mgr.is_connected()

    @property
    def is_streaming(self) -> bool:
        return self._mgr.is_streaming()

    @property
    def config(self) -> HeadsetConfig:
        return self._config

    def connect(self) -> None:
        if self.is_connected:
            return

        self._eeg.setup(
            self._mgr,
            device_name=self._config.device_name,
            cap=self._config.channel_map,
            sfreq=self._config.sample_rate_hz,
        )

    def disconnect(self) -> None:
        if not self.is_connected:
            return

        if self.is_streaming:
            self.stop_stream()
        self._mgr.disconnect()

    def start_stream(self) -> None:
        if not self.is_connected:
            raise RuntimeError("Cannot start stream: Headset not connected.")

        if self.is_streaming:
            return

        self._eeg.start_acquisition()

    def stop_stream(self) -> None:
        if not self.is_connected:
            raise RuntimeError("Cannot stop stream: Headset not connected.")

        if not self.is_streaming:
            return

        self._eeg.stop_acquisition()

    def annotate(self, text: str) -> None:
        if not self.is_connected:
            raise RuntimeError("Cannot annotate: Headset not connected.")
        if not self.is_streaming:
            raise RuntimeError("Cannot annotate: Headset not streaming.")

        self._eeg.annotate(text)

    def read_available_samples(self) -> np.ndarray:
        if not self.is_connected:
            raise RuntimeError("Cannot read samples: Headset not connected.")
        if not self.is_streaming:
            raise RuntimeError("Cannot read samples: Headset not streaming.")

        # safely acquire chunks and clear the buffer
        with self._eeg.data.lock:
            chunks = self._eeg.data.data[:]
            self._eeg.data.data.clear()

        if not chunks:
            return np.empty((self.channel_count, 0))

        raw_hw_data = np.concatenate(chunks, axis=1)

        # SDK hw_id (1-based) maps to cap index (0-based) as hw_id = cap_idx + 1.
        # Build row indices in cap order to preserve channel_map ordering.
        eeg_row_indices = [
            self._eeg.channels_indexes[cap_idx + 1]
            for cap_idx in sorted(self._config.channel_map.keys())
            if (cap_idx + 1) in self._eeg.channels_indexes
            and self._eeg.channels_type.get(cap_idx + 1) == "EEG"
        ]

        # SDK data is in nanovolts; convert to µV for EDF and downstream processing.
        eeg_only_data = raw_hw_data[eeg_row_indices, :] * 1e-3

        return eeg_only_data
