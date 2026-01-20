import pygame
import sys

from src.flow_controller.state.main_menu_state import MainMenuState
from src.flow_controller.state.experiment_state import ExperimentState 
from src.flow_controller.state.calibration_state import CalibrationState


# Flow controller managing the overall application flow and state transitions
class FlowController:
    def __init__(self, gui_manager, eeg_headset, data_manager) -> None:
        self.gui_manager = gui_manager
        self.eeg_headset = eeg_headset
        self.data_manager = data_manager
        self.state = None
        self.clock = pygame.time.Clock()
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
            self.flow_loop()

        except Exception as e:
            print(f"\nUnhandled exception occurred: {e}")

        finally:
            self.shutdown()

    # Main loop of the flow controller
    def flow_loop(self):
        self.running = True
        
        while self.running:
            # Handle global events and logic
            self.state.iter()
            # Wait for next tick
            self.clock.tick(60)

    # Shutdown procedure for the flow controller
    def shutdown(self):
        if self.eeg_headset.connected:
            self.eeg_headset.disconnect()

        export_file = self.data_manager.export_current_session("final_session")
        print(f"Session data exported to: {export_file}")

        pygame.quit()

        sys.exit(0)
