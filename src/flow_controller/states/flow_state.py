# State base class for flow controller states (e.g., main menu, experiment, calibration)
from abc import abstractmethod


class FlowState:
    def __init__(self, flow_controller):
        self.flow_controller = flow_controller
        self.gui_manager = flow_controller.gui_manager
        self.eeg_headset = flow_controller.eeg_headset

    # Setup when entering the state
    @abstractmethod
    def enter(self): pass

    # Main loop iteration for the state
    @abstractmethod
    def tick(self): pass

    # Cleanup when exiting the state
    @abstractmethod
    def exit(self): pass
