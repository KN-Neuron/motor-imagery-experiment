from enum import Enum


class ExperimentStepType(Enum):
    FIXATION = "fixation"
    REST = "rest"

    DOUBLE_BLINK = "double_blink"  # Podwójne/mocne mrugnięcie
    LEFT_HAND = "left_hand_clench"  # Zaciśnięcie lewej dłoni
    RIGHT_HAND = "right_hand_clench"  # Zaciśnięcie prawej dłoni
    JAW_CLENCH = "jaw_clench"  # Zaciśnięcie szczęki
    HEAD_MOVEMENT = "head_movement"  # Ruch głową
    SSVEP_FOCUS = "ssvep_focus"  # Skupienie na migającym punkcie

CLASSIFIABLE = [s for s in ExperimentStepType
                 if s not in (ExperimentStepType.FIXATION, ExperimentStepType.REST)]
