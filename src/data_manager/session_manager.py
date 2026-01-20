from collections import deque
from dataclasses import dataclass
from typing import Optional
from .sampling_strategies import RandomSampler, StratifiedSampler, BaseSampler
from .types import ExperimentStepType


@dataclass
class ExperimentStep:
    step_type: ExperimentStepType
    duration_ms: int


class SessionManager:
    def __init__(
        self,
        strategy: str = "stratified",
        trials_per_class: int = 5,
    ) -> None:
        self.durations = {"fixation": 2000, "cue": 4000, "rest": 1500}

        excluded_steps = (
            ExperimentStepType.FIXATION,
            ExperimentStepType.REST,
        )

        commands = [step for step in ExperimentStepType if step not in excluded_steps]

        self.sampler: BaseSampler
        if strategy == "stratified":
            self.sampler = StratifiedSampler()
        else:
            self.sampler = RandomSampler()

        seq = self.sampler.generate_session_sequence(
            commands,
            trials_per_class,
        )
        full_sequence_types = seq

        self.step_queue: deque[ExperimentStep] = deque()

        for step_type in full_sequence_types:
            duration = self._get_duration(step_type)
            self.step_queue.append(
                ExperimentStep(step_type=step_type, duration_ms=duration)
            )

    def _get_duration(self, step_type: ExperimentStepType) -> int:
        if step_type == ExperimentStepType.FIXATION:
            return self.durations["fixation"]
        elif step_type == ExperimentStepType.REST:
            return self.durations["rest"]
        else:
            return self.durations["cue"]

    def get_next(self) -> Optional[ExperimentStep]:
        if self.step_queue:
            return self.step_queue.popleft()
        return None

    def run_trial(self) -> None:
        pass
