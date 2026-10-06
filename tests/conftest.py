import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.eeg_headset.drivers import MockDriver  # noqa: E402
from src.eeg_headset.eeg_headset import EEGHeadset  # noqa: E402
from src.eeg_headset.headset_config import HeadsetConfig  # noqa: E402
from src.gui import GUIManager  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def qapp() -> QApplication:
    """Single QApplication (offscreen) shared by all tests."""
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    return app


@pytest.fixture
def sample_gui_manager() -> GUIManager:
    """Sample GUI manager for testing."""

    return GUIManager()


@pytest.fixture
def sample_eeg_headset() -> EEGHeadset:
    """Headset backed by the mock driver (no hardware needed)."""

    return EEGHeadset(MockDriver(config=HeadsetConfig.mock()))
