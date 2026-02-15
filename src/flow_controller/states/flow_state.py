# State base class for flow controller states (e.g., main menu, experiment, calibration)
class FlowState:
    def __init__(self, flow_controller):
        self.flow_controller = flow_controller
        self.gui_manager = flow_controller.gui_manager
        self.eeg_headset = flow_controller.eeg_headset

    # Setup when entering the state
    def enter(self): pass

    # Main loop iteration for the state
    def tick(self): pass

    # Cleanup when exiting the state
    def exit(self): pass
