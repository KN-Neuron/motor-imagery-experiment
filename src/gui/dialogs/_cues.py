from PyQt6.QtWidgets import QVBoxLayout, QCheckBox

from src.sample_manager.experiment_step_type import (
    ARTIFACTS,
    CLASSIFIABLE,
    ExperimentStepType,
    parse_step_type,
)

MAIN_CUES = [*CLASSIFIABLE, ExperimentStepType.SSVEP_FOCUS]
ARTIFACT_CUES = list(ARTIFACTS)


def _display_name(cue_value: str) -> str:
    return cue_value.replace("_", " ").capitalize()


def make_cue_checkboxes(
    layout: QVBoxLayout,
    enabled_cues: list[str] | None,
    cue_types: list[ExperimentStepType] = MAIN_CUES,
) -> dict[str, QCheckBox]:
    """Create checkboxes for the given cue types. Returns {cue_value: checkbox}."""
    enabled = {
        parse_step_type(c) for c in enabled_cues or []
    }  # legacy names are mapped
    checkboxes = {}
    for cue_type in cue_types:
        cb = QCheckBox(_display_name(cue_type.value))
        cb.setChecked(cue_type in enabled)
        layout.addWidget(cb)
        checkboxes[cue_type.value] = cb

    return checkboxes


def get_selected_cues(checkboxes: dict[str, QCheckBox]) -> list[str]:
    """Return list of cue values for checked checkboxes."""
    return [value for value, cb in checkboxes.items() if cb.isChecked()]
