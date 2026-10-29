import numpy as np

from src.eeg_headset.drivers import MockDriver
from src.eeg_headset.eeg_headset import EEGHeadset
from src.eeg_headset.headset_config import HeadsetConfig


class TestEEGHeadset:
    def test_initialization(self, sample_eeg_headset: EEGHeadset) -> None:
        assert sample_eeg_headset is not None

    def test_get_output(self) -> None:
        headset = EEGHeadset(MockDriver(config=HeadsetConfig.mock()))
        headset.connect()
        assert headset.is_connected()
        headset.start()
        headset.annotate("A")

        out = headset.get_output()
        assert isinstance(out, np.ndarray)
        assert out.shape == (4, 250)
