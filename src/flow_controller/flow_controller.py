from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
import sys

from src.eeg_headset.eeg_headset import EEGHeadset
from .states import MainMenuState, ExperimentState, CalibrationState


class FlowController:
    """Manages overall application flow and state transitions."""

    def __init__(self, gui_manager) -> None:
        self.gui_manager = gui_manager
        self.eeg_headset: EEGHeadset | None = None
        self.state = None
        self.timer = QTimer()
        self.timer.start(10)  # 100 FPS
        self.timer.timeout.connect(self._tick)
        self.running = True

    def change_state(self, state, **kwargs):
        """Exit current state and enter the new one. kwargs are forwarded to enter()."""
        if self.state:
            self.state.exit()

        if state is MainMenuState:
            self.state = MainMenuState(self)
        elif state is ExperimentState:
            self.state = ExperimentState(self)
        elif state is CalibrationState:
            self.state = CalibrationState(self)
        else:
            raise ValueError(f"Unknown FlowController state: {state}")

        self.state.enter(**kwargs)

    def start(self):
        """Initialize GUI and run the Qt event loop. Headset is pre-connected before this call."""
        self.gui_manager.initialize()
        self.change_state(MainMenuState)

        try:
            QApplication.instance().exec()

        except Exception as e:
            print(f"[FlowController] Unhandled exception occurred: {e}")

        finally:
            self.shutdown()

    def _tick(self):
        """Called by QTimer every 10ms."""
        if not self.running:
            self.timer.stop()
            QApplication.instance().quit()
            return

        if self.eeg_headset is not None and self.eeg_headset.is_connected() and self.eeg_headset.is_streaming():
            self.eeg_headset.poll()

        self.state.tick()

    def shutdown(self):
        """Disconnect headset and exit the process."""
        if self.eeg_headset is not None and self.eeg_headset.is_connected():
            self.eeg_headset.disconnect()

        sys.exit(0)
