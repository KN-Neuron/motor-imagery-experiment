from typing import override

from src.gui.gui_manager import MainMenuEvent

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
        
        # Handle events
        change_state_event = self.gui_manager.handle_main_menu_events()

        if change_state_event == MainMenuEvent.EXPERIMENT_BTN_CLICKED:
            print("Starting Experiment State")
        elif change_state_event == MainMenuEvent.CALIBRATION_BTN_CLICKED:
            print("Starting Calibration State")
        elif change_state_event == MainMenuEvent.QUIT:
            self.flow_controller.running = False

    @override
    def exit(self):
        pass
