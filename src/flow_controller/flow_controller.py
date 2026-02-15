from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
import sys

from .states import MainMenuState, ExperimentState, CalibrationState

# Flow controller managing the overall application flow and state transitions
class FlowController:
    def __init__(self, gui_manager, eeg_headset) -> None:
        self.gui_manager = gui_manager
        self.eeg_headset = eeg_headset
        self.state = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick) # Connect timer to 
        self.running = True

    # Method to change the current state of the flow controller
    def change_state(self, state):
        # Exit current state if exists (cleanup)
        if self.state:
            self.state.exit()

        # Instantiate new state based on provided state class
        if state is MainMenuState:
            self.state = MainMenuState(self)
        elif state is ExperimentState:
            self.state = ExperimentState(self)
        elif state is CalibrationState:
            self.state = CalibrationState(self)
        else:
            raise ValueError(f"Unknown FlowController state: {state}")

        # Enter the new state (setup)
        self.state.enter()

    # Function to start the flow controller (wrapper for main loop)
    def start(self):
        self.gui_manager.initialize()

        if self.eeg_headset.connect():
            print("Connected to EEG headset")
        else:
            print("Warning: Could not connect to EEG headset")

        self.change_state(MainMenuState) # Set initial state

        try:
            # Start the timer for 100 FPS
            self.timer.start(10)
            
            # Run Qt event loop
            QApplication.instance().exec()

        except Exception as e:
            print(f"\nUnhandled exception occurred: {e}")

        finally:
            self.shutdown()

    # Tick method called by QTimer
    def _tick(self):
        if not self.running:
            self.timer.stop()
            QApplication.instance().quit()
            return
        
        # Handle global events and logic
        self.state.tick()

    # Shutdown procedure for the flow controller
    def shutdown(self):
        if self.eeg_headset.connected:
            self.eeg_headset.disconnect()

        sys.exit(0)
