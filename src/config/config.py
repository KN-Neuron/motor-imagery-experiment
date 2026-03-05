"""
Loads experiment/calibration configuration from config.json located in the
project root (next to pyproject.toml).  Returns typed dataclass instances, or
None if the file is missing, malformed, or the requested section is absent.
"""

import json
from dataclasses import dataclass
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"


# ---------------------------------------------------------------------------
# Public dataclasses (imported by config_dialog and the flow-controller states)
# ---------------------------------------------------------------------------

@dataclass
class CalibrationConfig:
    trials_per_class: int
    strategy: str
    fixation_ms: int
    cue_ms: int
    rest_ms: int
    result_ms: int


@dataclass
class ExperimentConfig:
    trials_per_class: int
    strategy: str
    fixation_ms: int
    cue_ms: int
    rest_ms: int


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------

def _load_raw() -> dict:
    """Return the parsed JSON dict, or an empty dict on any error."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_calibration_config() -> CalibrationConfig | None:
    """
    Return a CalibrationConfig populated from the 'calibration' section of
    config.json, or None if the file / section is unavailable.
    """
    section = _load_raw().get("calibration")
    if not section:
        return None
    try:
        return CalibrationConfig(
            trials_per_class=int(section["trials_per_class"]),
            strategy=str(section["strategy"]),
            fixation_ms=int(section["fixation_ms"]),
            cue_ms=int(section["cue_ms"]),
            rest_ms=int(section["rest_ms"]),
            result_ms=int(section["result_ms"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def load_experiment_config() -> ExperimentConfig | None:
    """
    Return an ExperimentConfig populated from the 'experiment' section of
    config.json, or None if the file / section is unavailable.
    """
    section = _load_raw().get("experiment")
    if not section:
        return None
    try:
        return ExperimentConfig(
            trials_per_class=int(section["trials_per_class"]),
            strategy=str(section["strategy"]),
            fixation_ms=int(section["fixation_ms"]),
            cue_ms=int(section["cue_ms"]),
            rest_ms=int(section["rest_ms"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
