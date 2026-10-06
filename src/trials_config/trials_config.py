"""
Loads experiment/calibration configuration from trials.config.yaml located in
the project root (next to pyproject.toml).  Returns typed dataclass instances,
or None if the file is missing, malformed, or the requested section is absent.
"""

import warnings
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, TypeVar

import yaml

from src.signal_quality.thresholds import QualityThresholds

_CONFIG_PATH = Path(__file__).parent.parent.parent / "trials.config.yaml"

FEEDBACK_MODES = ("none", "model", "demo")

# Keys that earlier versions accepted; ignored with a warning.
_DEPRECATED_KEYS = {
    "rest_ms": "use iti_min_ms / iti_max_ms (jittered inter-trial interval)",
    "strategy": "blocks are always class-balanced with a max run length",
}


# Public dataclasses (imported by the dialog modules and the flow-controller states)


@dataclass
class SessionConfig:
    # Block structure (MI blocks: left/right classes, balanced per block)
    n_blocks: int = 4
    trials_per_class_per_block: int = 20
    max_consecutive_same_class: int = 3
    practice_trials_per_class: int = 2

    # Trial timing. cue_ms: instruction on screen; task_ms: imagery/execution
    # window that follows (0 = a single step of cue_ms). The ITI is drawn
    # uniformly per trial.
    fixation_ms: int = 1500
    cue_ms: int = 1000
    task_ms: int = 4000
    iti_min_ms: int = 2000
    iti_max_ms: int = 3500

    # Resting-state block at the start of the session (0 disables)
    rest_eyes_open_ms: int = 120_000
    rest_eyes_closed_ms: int = 0

    # Classes. MI/execution/ssvep cues form the main blocks; artifacts are
    # recorded in their own block (condition=artifact), never mixed with MI.
    cues: list[str] = field(
        default_factory=lambda: ["left_hand_imagery", "right_hand_imagery"]
    )
    artifact_cues: list[str] = field(
        default_factory=lambda: ["double_blink", "jaw_clench", "head_movement"]
    )
    artifact_trials_per_class: int = 10
    ssvep_trials: int = 10
    ssvep_frequency_hz: float = 10.0

    seed: int | None = None  # None = draw a fresh seed (always stored in metadata)
    feedback: str = "none"  # none | model | demo
    instruction_text: str | None = None

    # Signal-quality screen and optional blink/jaw/alpha check procedure
    qc_duration_s: float = 10.0
    qc_procedure: bool = False
    quality: QualityThresholds = field(default_factory=QualityThresholds)

    def validate(self) -> None:
        if self.feedback not in FEEDBACK_MODES:
            raise ValueError(f"feedback must be one of {FEEDBACK_MODES}")
        if self.n_blocks < 1 or self.trials_per_class_per_block < 1:
            raise ValueError("n_blocks and trials_per_class_per_block must be >= 1")
        if self.max_consecutive_same_class < 1:
            raise ValueError("max_consecutive_same_class must be >= 1")
        if not 0 <= self.iti_min_ms <= self.iti_max_ms:
            raise ValueError("need 0 <= iti_min_ms <= iti_max_ms")
        if self.ssvep_frequency_hz <= 0:
            raise ValueError("ssvep_frequency_hz must be > 0")


@dataclass
class ExperimentConfig(SessionConfig):
    pass


@dataclass
class CalibrationConfig(SessionConfig):
    result_ms: int = 2000  # duration of the feedback screen (if feedback != none)


# Loader helpers

C = TypeVar("C", bound=SessionConfig)


def _load_raw() -> dict:
    """Return the parsed YAML dict, or an empty dict on any error."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}


def build_config(cls: type[C], section: dict[str, Any]) -> C:
    """Build a validated config from a YAML section (raises ValueError)."""
    section = dict(section)
    for key, hint in _DEPRECATED_KEYS.items():
        if key in section:
            warnings.warn(f"Config key '{key}' is ignored: {hint}", FutureWarning)
            section.pop(key)
    if "trials_per_class" in section:
        warnings.warn(
            "Config key 'trials_per_class' is deprecated; read as "
            "trials_per_class_per_block (a single block unless n_blocks is set)",
            FutureWarning,
        )
        legacy = section.pop("trials_per_class")
        section.setdefault("trials_per_class_per_block", legacy)
        section.setdefault("n_blocks", 1)

    known = {f.name for f in fields(cls)}
    unknown = set(section) - known
    if unknown:
        raise ValueError(f"Unknown config keys: {sorted(unknown)}")

    if "quality" in section:
        section["quality"] = QualityThresholds(**(section["quality"] or {}))
    for key in ("cues", "artifact_cues"):
        if section.get(key) is not None:
            section[key] = [str(c).lower() for c in section[key]]

    config = cls(**section)
    config.validate()
    return config


def _load_section(cls: type[C], name: str) -> C | None:
    section = _load_raw().get(name)
    if not section:
        return None
    try:
        return build_config(cls, section)
    except (TypeError, ValueError) as e:
        print(f"[trials_config] Invalid '{name}' section: {e}")
        return None


def load_experiment_config() -> ExperimentConfig | None:
    """Return the 'experiment' section as ExperimentConfig, or None."""
    return _load_section(ExperimentConfig, "experiment")


def load_calibration_config() -> CalibrationConfig | None:
    """Return the 'calibration' section as CalibrationConfig, or None."""
    return _load_section(CalibrationConfig, "calibration")
