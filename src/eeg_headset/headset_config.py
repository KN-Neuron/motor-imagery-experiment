from enum import Enum
import yaml


class HeadsetModel(Enum):
    HALO_4CH = "HALO_4CH"
    MIDI_16CH_BASE = "MIDI_16CH_BASE"
    MAXI_32CH = "MAXI_32CH"
    SAMPLE_64CH = "SAMPLE_64CH"


class HeadsetConfig:
    def __init__(self, model: HeadsetModel, config_path: str = "headsets.yaml"):
        self.model = model

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration file expected at {config_path} not found."
            )

        headsets_config = yaml_data.get("headsets", {})

        model_name = self.model.value
        if model_name not in headsets_config:
            raise ValueError(
                f"Model {model_name} nie posiada konfiguracji w pliku {config_path}."
            )

        config = headsets_config[model_name]

        # Extract type-safe fields
        self.device_name: str = config.get("device_name", "")
        self.n_channels: int = config.get("n_channels", 0)
        self.sample_rate_hz: int = config.get("sample_rate_hz", 0)

        # Cast the channel map to avoid type issues
        raw_map = config.get("channel_map", {})
        self.channel_map: dict[int, str] = {int(k): str(v) for k, v in raw_map.items()}

        # Validate that the config matches the channel count
        if len(self.channel_map) != self.n_channels:
            raise ValueError(
                f"Channel map size and n_channels mismatch for {model_name}"
            )

    @classmethod
    def mock(cls, n_channels: int = 4, sample_rate_hz: int = 250) -> "HeadsetConfig":
        """Create a dummy config for use with MockDriver (no YAML required)."""
        obj = object.__new__(cls)
        obj.model = None
        obj.device_name = "MOCK"
        obj.n_channels = n_channels
        obj.sample_rate_hz = sample_rate_hz
        obj.channel_map = {i: f"CH{i}" for i in range(n_channels)}
        return obj
