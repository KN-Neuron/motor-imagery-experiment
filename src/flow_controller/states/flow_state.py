from abc import abstractmethod
from typing import Any


class FlowState:
    """Base class for flow controller states (main menu, experiment, calibration)."""

    def __init__(self, flow_controller: Any) -> None:
        self.flow_controller = flow_controller
        self.gui_manager = flow_controller.gui_manager

    @property
    def eeg_headset(self) -> Any:
        """Live reference to the current headset (None or swapped via main menu)."""
        return self.flow_controller.eeg_headset

    @abstractmethod
    def enter(self, **kwargs: Any) -> None:
        """Setup when entering the state; receives the kwargs of change_state."""
        ...

    @abstractmethod
    def tick(self) -> None:
        """Main loop iteration for the state"""
        ...

    @abstractmethod
    def exit(self) -> None:
        """Cleanup when exiting the state"""
        ...
