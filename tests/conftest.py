from pathlib import Path

import pytest

# from src.data_manager import DataManager
from src.egg_headset import EggHeadset
from src.gui import GUIManager


@pytest.fixture
def sample_gui_manager() -> GUIManager:
    """Sample GUI manager for testing."""

    return GUIManager()


@pytest.fixture
def sample_egg_headset() -> EggHeadset:
    """Sample egg headset for testing."""

    return EggHeadset(device_address="mock_device")


# @pytest.fixture
# def sample_data_manager(tmp_path: Path) -> DataManager:
#     """Sample data manager for testing with temporary directory."""

#     return DataManager(data_dir=str(tmp_path))
