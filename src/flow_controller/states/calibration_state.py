from typing import override

from . import FlowState


class CalibrationState(FlowState):
    """Handles calibration procedures."""

    def __init__(self, flow_controller):
        super().__init__(flow_controller)

    @override
    def enter(self):
        pass

    @override
    def tick(self):
        pass

    @override
    def exit(self):
        pass
