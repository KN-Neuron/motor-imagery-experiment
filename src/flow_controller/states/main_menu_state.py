from typing import override

from src.gui.gui_manager import MainMenuEvent
from .experiment_state import ExperimentState
from .calibration_state import CalibrationState

from . import FlowState


class MainMenuState(FlowState):
    """Handles main menu interactions: session entry."""

    @override
    def enter(self, **kwargs):
        self.gui_manager.show_main_menu()

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

            elif event == MainMenuEvent.QUIT:
                self.flow_controller.running = False

    @override
    def exit(self):
        pass

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
