import random
from typing import Protocol

import numpy as np

from src.sample_manager.experiment_step_type import ExperimentStepType


class Classifier(Protocol):
    """Interface for a real motor-imagery classifier (no implementation yet)."""

    def predict(self, eeg: np.ndarray) -> ExperimentStepType:
        """Classify one trial. `eeg` has shape (n_channels, n_samples)."""
        ...


class DemoClassifier:
    """Random answers. For demos only: it does NOT look at the signal."""

    def __init__(self, classes: list[ExperimentStepType], seed: int | None = None):
        self._classes = classes
        self._rng = random.Random(seed)

    def predict(self, eeg: np.ndarray) -> ExperimentStepType:
        return self._rng.choice(self._classes)


def make_classifier(
    mode: str,
    classes: list[ExperimentStepType],
    model: Classifier | None = None,
) -> Classifier | None:
    """Classifier for a feedback mode (none -> no feedback at all)."""
    if mode == "none":
        return None
    if mode == "demo":
        return DemoClassifier(classes)
    if mode == "model":
        if model is None:
            raise NotImplementedError(
                "feedback=model needs a trained Classifier; none is available yet"
            )
        return model
    raise ValueError(f"Unknown feedback mode: {mode!r}")
