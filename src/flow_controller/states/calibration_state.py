from pathlib import Path
from typing import Any

from src.trials_config.trials_config import CalibrationConfig, SessionConfig

from .session_state import SessionState


class CalibrationState(SessionState):
    """Calibration: same protocol as the experiment (feedback shown if enabled)."""

    kind = "calibration"
    output_root = Path("sessions/calibrations")

    def _show_config(self) -> SessionConfig | None:
        config: SessionConfig | None = self.gui_manager.show_calibration_config_dialog()
        if isinstance(config, CalibrationConfig):
            self.result_ms = config.result_ms
        return config

    def _metadata(self, *args: Any) -> dict[str, Any]:
        data = super()._metadata(*args)
        data["result_ms"] = self.result_ms
        return data
