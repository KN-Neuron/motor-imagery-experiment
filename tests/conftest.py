from pathlib import Path

import pytest

# from src.data_manager import DataManager
from eeg_headset.eeg_headset import EEGHeadset
from src.gui import GUIManager


@pytest.fixture
def sample_gui_manager() -> GUIManager:
    """Sample GUI manager for testing."""

    return GUIManager()


@pytest.fixture
def sample_eeg_headset() -> EEGHeadset:
    """Sample egg headset for testing."""

    return EEGHeadset(device_address="mock_device")


# @pytest.fixture
# def sample_data_manager(tmp_path: Path) -> DataManager:
#     """Sample data manager for testing with temporary directory."""

#     return DataManager(data_dir=str(tmp_path))
