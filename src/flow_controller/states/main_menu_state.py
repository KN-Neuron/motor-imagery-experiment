from typing import override
import time

from src.gui.gui_manager import MainMenuEvent
from .experiment_state import ExperimentState
from .calibration_state import CalibrationState

from . import FlowState


class MainMenuState(FlowState):
    """Handles main menu interactions: session entry."""

    def __init__(self, flow_controller):
        super().__init__(flow_controller)
        self._last_ui_connected: bool | None = None
        self._last_ui_update_s = 0.0

    @override
    def enter(self, **kwargs):
        self.gui_manager.show_main_menu()
        self._last_ui_connected = None
        self._last_ui_update_s = 0.0

    @override
    def tick(self):
        headset_connected = self.flow_controller.headset_connected

        # Avoid repainting the main menu at 100 FPS; update only on changes
        # or at a low heartbeat rate.
        now = time.monotonic()
        if self._last_ui_connected is None or headset_connected != self._last_ui_connected or (now - self._last_ui_update_s) > 0.5:
            self.gui_manager.update_main_menu(headset_connected)
            self._last_ui_connected = headset_connected
            self._last_ui_update_s = now

        if self._handle_events(headset_connected):
            return

    @override
    def exit(self):
        pass

    def _handle_events(self, headset_connected: bool) -> bool:
        """Process pending GUI events. Returns True if a state transition occurred."""
        for event in self.gui_manager.get_main_menu_events():
            if isinstance(event, tuple) and event[0] == MainMenuEvent.EXPERIMENT_BTN_CLICKED:
                if self._try_start_session(ExperimentState, alt_pressed=event[1], headset_connected=headset_connected, label="Experiment"):
                    return True

            elif isinstance(event, tuple) and event[0] == MainMenuEvent.CALIBRATION_BTN_CLICKED:
                if self._try_start_session(CalibrationState, alt_pressed=event[1], headset_connected=headset_connected, label="Calibration"):
                    return True

            elif event == MainMenuEvent.RECONNECT_BTN_CLICKED:
                self._try_reconnect(headset_connected)

            elif event == MainMenuEvent.QUIT:
                self.flow_controller.running = False

        return False

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

    def _try_reconnect(self, headset_connected: bool) -> None:
        if headset_connected:
            return

        if self.eeg_headset is None:
            print("[MainMenuState] Cannot reconnect: no headset instance")
            return

        try:
            print("[MainMenuState] Reconnecting EEG headset...")
            self.eeg_headset.connect()
        except Exception as e:
            print(f"[MainMenuState] Reconnect failed: {e}")
