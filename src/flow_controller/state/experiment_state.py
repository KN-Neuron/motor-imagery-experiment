from typing import override

from . import FlowState


# Experiment state for the flow controller handling experiment procedures
class ExperimentState(FlowState):
    def __init__(self, flow_controller):
        super().__init__(flow_controller)

    @override
    def enter(self): 
        pass

    @override
    def iter(self): 
        pass

    @override
    def exit(self): 
        pass
