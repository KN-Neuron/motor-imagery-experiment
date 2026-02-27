from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
import sys

from .states import MainMenuState, ExperimentState, CalibrationState


class FlowController:
    """Manages overall application flow and state transitions."""

    def __init__(self, gui_manager, eeg_headset) -> None:
        self.gui_manager = gui_manager
        self.eeg_headset = eeg_headset
        self.state = None
        self.timer = QTimer()
        self.timer.start(10)  # 100 FPS
        self.timer.timeout.connect(self._tick)
        self.running = True

    def change_state(self, state):
        """Exit current state and enter the new one."""
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

        self.state.enter()

    def start(self):
        """Initialize GUI, connect headset and run the Qt event loop."""
        self.gui_manager.initialize()

        if self.eeg_headset.connect():
            print("Connected to EEG headset")
        else:
            print("Warning: Could not connect to EEG headset")

        self.change_state(MainMenuState)

        try:
            QApplication.instance().exec()

        except Exception as e:
            print(f"\nUnhandled exception occurred: {e}")

        finally:
            self.shutdown()

    def _tick(self):
        """Called by QTimer every 10ms."""
        if not self.running:
            self.timer.stop()
            QApplication.instance().quit()
            return

        self.state.tick()

    def shutdown(self):
        """Disconnect headset and exit the process."""
        if self.eeg_headset.connected:
            self.eeg_headset.disconnect()

        sys.exit(0)
