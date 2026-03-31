"""
Loads experiment/calibration configuration from config.json located in the
project root (next to pyproject.toml).  Returns typed dataclass instances, or
None if the file is missing, malformed, or the requested section is absent.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path


_CONFIG_PATH = Path(__file__).parent.parent.parent / "trials_config.yaml"

# Public dataclasses (imported by config_dialog and the flow-controller states)

@dataclass
class ExperimentConfig:
    trials_per_class: int
    strategy: str
    fixation_ms: int
    cue_ms: int
    rest_ms: int
    cues: list[str] | None = None
    session_name: str | None = None

@dataclass
class CalibrationConfig:
    trials_per_class: int
    strategy: str
    fixation_ms: int
    cue_ms: int
    rest_ms: int
    result_ms: int
    cues: list[str] | None = None
    session_name: str | None = None

# Loader helpers

def _load_raw() -> dict:
    """Return the parsed YAML dict, or an empty dict on any error."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}

def load_experiment_config() -> ExperimentConfig | None:
    """
    Return an ExperimentConfig populated from the 'experiment' section of
    config.json, or None if the file / section is unavailable.
    """
    section = _load_raw().get("experiment")
    if not section:
        return None
    try:
        cues = section.get("cues")
        if cues is not None:
            cues = [str(c).lower() for c in cues]
        return ExperimentConfig(
            trials_per_class=int(section["trials_per_class"]),
            strategy=str(section["strategy"]),
            fixation_ms=int(section["fixation_ms"]),
            cue_ms=int(section["cue_ms"]),
            rest_ms=int(section["rest_ms"]),
            cues=cues,
        )
    except (KeyError, TypeError, ValueError):
        return None

def load_calibration_config() -> CalibrationConfig | None:
    """
    Return a CalibrationConfig populated from the 'calibration' section of
    config.json, or None if the file / section is unavailable.
    """
    section = _load_raw().get("calibration")
    if not section:
        return None
    try:
        cues = section.get("cues")
        if cues is not None:
            cues = [str(c).lower() for c in cues]
        return CalibrationConfig(
            trials_per_class=int(section["trials_per_class"]),
            strategy=str(section["strategy"]),
            fixation_ms=int(section["fixation_ms"]),
            cue_ms=int(section["cue_ms"]),
            rest_ms=int(section["rest_ms"]),
            result_ms=int(section["result_ms"]),
            cues=cues,
        )
    except (KeyError, TypeError, ValueError):
        return None
