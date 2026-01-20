from typing import List, Any
import random
from .experiment_step_type import ExperimentStepType


class BaseSampler:
    def generate_session_sequence(
        self, commands: List[Any], trials_per_command: int
    ) -> List[Any]:
        raise NotImplementedError

    def _expand_to_triplets(self, tasks: List[Any]) -> List[Any]:
        full_sequence = []
        for cmd in tasks:
            full_sequence.append(ExperimentStepType.FIXATION)
            full_sequence.append(cmd)
            full_sequence.append(ExperimentStepType.REST)
        return full_sequence


class RandomSampler(BaseSampler):
    def generate_session_sequence(
        self, commands: List[Any], trials_per_command: int
    ) -> List[Any]:
        total_trials = len(commands) * trials_per_command
        tasks = [random.choice(commands) for _ in range(total_trials)]
        return self._expand_to_triplets(tasks)


class StratifiedSampler(BaseSampler):
    def generate_session_sequence(
        self, commands: List[Any], trials_per_command: int
    ) -> List[Any]:
        tasks = []
        for cmd in commands:
            tasks.extend([cmd] * trials_per_command)
        random.shuffle(tasks)
        return self._expand_to_triplets(tasks)
