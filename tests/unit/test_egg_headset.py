from egg_headset.drivers.mock import MockDriver
from egg_headset.model import HeadsetConfiguration, HeadsetModel
from egg_headset import EggHeadset

import numpy as np


class TestEggHeadset:
    def test_initialization(self) -> None:
        config = HeadsetConfiguration(
            config_path="brainaccess_headsets_config.yaml",
            model=HeadsetModel.MIDI_16CH_BASE,
        )
        headset = EggHeadset(driver=MockDriver(config=config))

        assert headset is not None

    def test_get_output(self) -> None:
        config = HeadsetConfiguration(
            config_path="brainaccess_headsets_config.yaml",
            model=HeadsetModel.MIDI_16CH_BASE,
        )
        headset = EggHeadset(driver=MockDriver(config=config))

        headset.connect()
        headset.start()
        headset.annotate("A")

        out = headset.get_output()
        assert isinstance(out, np.ndarray)
        assert out.shape == (config.n_channels, config.sample_rate_hz)
