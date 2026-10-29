from pathlib import Path

from src.trials_config.trials_config import SessionConfig

from .session_state import SessionState


class ExperimentState(SessionState):
    """Motor-imagery experiment: rest block, practice, MI blocks, artifact block."""

    kind = "experiment"
    output_root = Path("sessions/experiments")

    def _show_config(self) -> SessionConfig | None:
        config: SessionConfig | None = self.gui_manager.show_experiment_config_dialog()
        return config
