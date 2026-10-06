import warnings
from enum import Enum


class ExperimentStepType(Enum):
    FIXATION = "fixation"
    ITI = "iti"  # inter-trial interval (jittered blank screen)

    REST_EYES_OPEN = "rest_eyes_open"
    REST_EYES_CLOSED = "rest_eyes_closed"

    # Motor imagery: the participant imagines the movement and does NOT move.
    LEFT_HAND_IMAGERY = "left_hand_imagery"
    RIGHT_HAND_IMAGERY = "right_hand_imagery"
    # Motor execution: the participant really clenches the hand.
    LEFT_HAND_EXECUTION = "left_hand_execution"
    RIGHT_HAND_EXECUTION = "right_hand_execution"

    # Artifact classes (recorded in a separate block, never mixed with MI).
    DOUBLE_BLINK = "double_blink"
    JAW_CLENCH = "jaw_clench"
    HEAD_MOVEMENT = "head_movement"

    SSVEP_FOCUS = "ssvep_focus"  # Focus on a flashing dot (not validated)

    # Screens without a task
    INSTRUCTION = "instruction"
    PRACTICE = "practice"
    BREAK = "break"
    END = "end"


IMAGERY = (
    ExperimentStepType.LEFT_HAND_IMAGERY,
    ExperimentStepType.RIGHT_HAND_IMAGERY,
)
EXECUTION = (
    ExperimentStepType.LEFT_HAND_EXECUTION,
    ExperimentStepType.RIGHT_HAND_EXECUTION,
)
ARTIFACTS = (
    ExperimentStepType.DOUBLE_BLINK,
    ExperimentStepType.JAW_CLENCH,
    ExperimentStepType.HEAD_MOVEMENT,
)
REST_STEPS = (
    ExperimentStepType.REST_EYES_OPEN,
    ExperimentStepType.REST_EYES_CLOSED,
)

# Left/right hand classes: the only ones a classifier may give feedback on.
CLASSIFIABLE = [*IMAGERY, *EXECUTION]

# Cue names that existed before imagery/execution were split.
LEGACY_NAMES = {
    "left_hand_clench": ExperimentStepType.LEFT_HAND_EXECUTION,
    "right_hand_clench": ExperimentStepType.RIGHT_HAND_EXECUTION,
}


def parse_step_type(name: str) -> ExperimentStepType | None:
    """Config name -> step type. Legacy `*_hand_clench` maps to execution."""
    name = name.lower()
    if name in LEGACY_NAMES:
        mapped = LEGACY_NAMES[name]
        warnings.warn(
            f"Cue name '{name}' is deprecated; interpreted as '{mapped.value}' "
            "(real movement). Use *_imagery or *_execution explicitly.",
            FutureWarning,
            stacklevel=2,
        )
        return mapped
    try:
        return ExperimentStepType(name)
    except ValueError:
        return None


def condition_of(step_type: ExperimentStepType) -> str | None:
    """imagery / execution / artifact / rest / ssvep (None for plain screens)."""
    if step_type in IMAGERY:
        return "imagery"
    if step_type in EXECUTION:
        return "execution"
    if step_type in ARTIFACTS:
        return "artifact"
    if step_type in REST_STEPS:
        return "rest"
    if step_type == ExperimentStepType.SSVEP_FOCUS:
        return "ssvep"
    return None
