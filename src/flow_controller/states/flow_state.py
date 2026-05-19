from abc import abstractmethod


class FlowState():
    """State base class for flow controller states (e.g., main menu, experiment, calibration)"""

    def __init__(self, flow_controller):
        self.flow_controller = flow_controller
        self.gui_manager = flow_controller.gui_manager

    @property
    def eeg_headset(self):
        """Live reference to the current headset; can be None or swapped out via main menu."""
        return self.flow_controller.eeg_headset

    @abstractmethod
    def enter(self, **kwargs):
        """Setup when entering the state. Accepts arbitrary kwargs forwarded by change_state."""
        ...

    @abstractmethod
    def tick(self):
        """Main loop iteration for the state"""
        ...

    @abstractmethod
    def exit(self):
        """Cleanup when exiting the state"""
        ...