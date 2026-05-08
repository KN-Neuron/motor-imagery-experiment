from PyQt6.QtWidgets import QVBoxLayout, QCheckBox

from src.sample_manager.experiment_step_type import CLASSIFIABLE


_CUE_DISPLAY_NAMES = {
    "double_blink": "Double blink",
    "left_hand_clench": "Left hand clench",
    "right_hand_clench": "Right hand clench",
    "jaw_clench": "Jaw clench",
    "head_movement": "Head movement",
    "ssvep_focus": "SSVEP focus",
}


def make_cue_checkboxes(layout: QVBoxLayout, enabled_cues: list[str] | None) -> dict[str, QCheckBox]:
    """Create checkboxes for all classifiable cue types. Returns {cue_value: checkbox}."""
    all_cue_values = [step.value for step in CLASSIFIABLE]
    enabled_set = set(c.lower() for c in enabled_cues) if enabled_cues is not None else set(all_cue_values)

    checkboxes = {}
    for cue_value in all_cue_values:
        display_name = _CUE_DISPLAY_NAMES.get(cue_value, cue_value)
        cb = QCheckBox(display_name)
        cb.setChecked(cue_value in enabled_set)
        layout.addWidget(cb)
        checkboxes[cue_value] = cb

    return checkboxes


def get_selected_cues(checkboxes: dict[str, QCheckBox]) -> list[str]:
    """Return list of cue values for checked checkboxes."""
    return [value for value, cb in checkboxes.items() if cb.isChecked()]
