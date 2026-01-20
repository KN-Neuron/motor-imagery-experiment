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
        
        # Process events
        events = self.gui_manager.process_main_menu_events()

        for event in events:
            if event == MainMenuEvent.EXPERIMENT_BTN_CLICKED:
                print("Starting Experiment State")
            elif event == MainMenuEvent.CALIBRATION_BTN_CLICKED:
                print("Starting Calibration State")
            elif event == MainMenuEvent.QUIT:
                self.flow_controller.running = False

    @override
    def exit(self):
        pass
