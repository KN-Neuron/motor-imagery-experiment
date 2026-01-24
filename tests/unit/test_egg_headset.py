from src.egg_headset import EggHeadset

import numpy as np


class TestEggHeadset:
    def test_initialization(self) -> None:
        headset = EggHeadset()
        assert headset is not None

    def test_get_output(self) -> None:
        headset = EggHeadset()
        assert headset.connect() is True
        headset.start()
        headset.annotate("A")

        out = headset.get_output()
        assert isinstance(out, np.ndarray)
        assert out.shape == (4, 250)
