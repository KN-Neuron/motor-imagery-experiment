from typing import override

from src.gui.gui_manager import MainMenuEvent
from .experiment_state import ExperimentState

from . import FlowState


# Main menu state for the flow controller handling main menu interactions
class MainMenuState(FlowState):
    def __init__(self, flow_controller):
        super().__init__(flow_controller)

    @override
    def enter(self):
        self.gui_manager.render(self.gui_manager.display_main_menu)

    @override   
    def iter(self):
        # Check headset connection status
        headset_connected = self.eeg_headset.connected
        
        # Render the main menu with headset status
        self.gui_manager.render(self.gui_manager.display_main_menu, headset_connected)
        
        # Process events
        events = self.gui_manager.process_main_menu_events()

        for event in events:
            # Handle experiment button (can be tuple with alt state or just enum)
            if isinstance(event, tuple) and event[0] == MainMenuEvent.EXPERIMENT_BTN_CLICKED:
                alt_pressed = event[1]
                if alt_pressed or self.eeg_headset.connected:
                    print(f"Starting Experiment State (no_eeg_mode={not self.eeg_headset.connected})")
                    self.flow_controller.change_state(ExperimentState)
                    return # Exit to avoid further processing fater state change
                else:
                    print("Cannot start experiment: EEG headset not connected. Hold Alt to start without EEG.")
            elif event == MainMenuEvent.CALIBRATION_BTN_CLICKED:
                print("Starting Calibration State")
            elif event == MainMenuEvent.QUIT:
                self.flow_controller.running = False

    @override
    def exit(self):
        pass
