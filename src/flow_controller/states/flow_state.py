from abc import abstractmethod


class FlowState():
    """State base class for flow controller states (e.g., main menu, experiment, calibration)"""
    
    def __init__(self, flow_controller):
        self.flow_controller = flow_controller
        self.gui_manager = flow_controller.gui_manager
        self.eeg_headset = flow_controller.eeg_headset

    @abstractmethod
    def enter(self): 
        """Setup when entering the state"""
        ...

    @abstractmethod
    def tick(self): 
        """Main loop iteration for the state"""
        ...

    @abstractmethod
    def exit(self): 
        """Cleanup when exiting the state"""
        ...