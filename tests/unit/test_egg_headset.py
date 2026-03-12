from eeg_headset.eeg_headset import EEGHeadset

import numpy as np


class TestEEGHeadset:
    def test_initialization(self) -> None:
        headset = EEGHeadset()
        assert headset is not None

    def test_get_output(self) -> None:
        headset = EEGHeadset()
        assert headset.connect() is True
        headset.start()
        headset.annotate("A")

        out = headset.get_output()
        assert isinstance(out, np.ndarray)
        assert out.shape == (4, 250)
