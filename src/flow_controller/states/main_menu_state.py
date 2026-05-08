from typing import override
import yaml

from src.gui.gui_manager import MainMenuEvent
from src.eeg_headset.headset_config import HeadsetConfig, HeadsetModel
from src.eeg_headset.eeg_headset import EEGHeadset
from src.eeg_headset.drivers import MockDriver, BrainAccessDriver
from .experiment_state import ExperimentState
from .calibration_state import CalibrationState

from . import FlowState


HEADSET_CONFIG_PATH = "brainaccess.config.yaml"


class MainMenuState(FlowState):
    """Handles main menu interactions: headset selection and session entry."""

    @override
    def enter(self, **kwargs):
        self.gui_manager.show_main_menu()
        self.gui_manager.set_main_menu_available_models(self._load_available_models())

    @override
    def tick(self):
        headset_connected = self.eeg_headset is not None and self.eeg_headset.is_connected()

        self.gui_manager.update_main_menu(headset_connected)

        for event in self.gui_manager.get_main_menu_events():
            if isinstance(event, tuple) and event[0] == MainMenuEvent.EXPERIMENT_BTN_CLICKED:
                if self._try_start_session(ExperimentState, alt_pressed=event[1], headset_connected=headset_connected, label="Experiment"):
                    return

            elif isinstance(event, tuple) and event[0] == MainMenuEvent.CALIBRATION_BTN_CLICKED:
                if self._try_start_session(CalibrationState, alt_pressed=event[1], headset_connected=headset_connected, label="Calibration"):
                    return

            elif isinstance(event, tuple) and event[0] == MainMenuEvent.HEADSET_CONNECT_REQUESTED:
                _, model_name, use_mock = event
                self._connect_headset(model_name, use_mock)

            elif event == MainMenuEvent.HEADSET_DISCONNECT_REQUESTED:
                self._disconnect_headset()

            elif event == MainMenuEvent.QUIT:
                self.flow_controller.running = False

    @override
    def exit(self):
        pass

    @staticmethod
    def _load_available_models() -> list[str]:
        """Return enum models that have a matching yaml entry. Order follows the enum."""
        try:
            with open(HEADSET_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            return []
        yaml_models = set((data.get("headsets") or {}).keys())
        return [m.value for m in HeadsetModel if m.value in yaml_models]

    def _try_start_session(self, state_cls, alt_pressed: bool, headset_connected: bool, label: str) -> bool:
        """Validate preconditions and transition to session state. Returns True if state changed."""
        if alt_pressed:
            print(f"Starting {label} State (no_eeg_mode=True, alt-forced)")
            self.flow_controller.change_state(state_cls, no_eeg_mode=True)
            return True
        if headset_connected:
            print(f"Starting {label} State with EEG")
            self.flow_controller.change_state(state_cls, no_eeg_mode=False)
            return True
        print(f"Cannot start {label.lower()}: headset not connected. Hold Alt to start without EEG.")
        return False

    def _connect_headset(self, model_name: str, use_mock: bool) -> None:
        """Build driver from model+mock flag, attach to flow_controller, connect."""
        if self.eeg_headset is not None and self.eeg_headset.is_connected():
            print("[MainMenuState] Connect ignored: headset already connected")
            return

        try:
            model = HeadsetModel(model_name)
            config = HeadsetConfig(model=model, config_path=HEADSET_CONFIG_PATH)
            driver = MockDriver(config=config) if use_mock else BrainAccessDriver(config=config)
            headset = EEGHeadset(driver)
            headset.connect()
        except Exception as e:
            print(f"[MainMenuState] Connect failed: {e}")
            return

        self.flow_controller.eeg_headset = headset
        if headset.is_connected():
            print(f"[MainMenuState] Connected: model={model_name}, mock={use_mock}")
        else:
            print(f"[MainMenuState] Connect call returned but driver reports disconnected (model={model_name})")

    def _disconnect_headset(self) -> None:
        """Disconnect current headset and clear it from flow_controller."""
        if self.eeg_headset is None:
            return
        try:
            self.eeg_headset.disconnect()
        except Exception as e:
            print(f"[MainMenuState] Disconnect failed: {e}")
        self.flow_controller.eeg_headset = None
        print("[MainMenuState] Headset disconnected")
