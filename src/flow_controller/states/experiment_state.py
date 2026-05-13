from typing import override
from PyQt6.QtCore import QElapsedTimer
from pathlib import Path

from src.sample_manager.sample_manager import SampleManager, ExperimentStep
from src.gui.gui_manager import ExperimentEvent
from src.session_saver.session_saver import SessionSaver
from . import FlowState


class ExperimentState(FlowState):
    """Handles experiment procedures and phase transitions."""

    def __init__(self, flow_controller):
        super().__init__(flow_controller)
        self.sample_manager: SampleManager = None
        self.current_step: ExperimentStep = None
        self.step_timer: QElapsedTimer = QElapsedTimer()
        self.no_eeg_mode: bool = False
        self.total_steps: int = 0
        self.completed_steps: int = 0
        self.is_paused: bool = False
        self.step_was_paused: bool = False
        self.session_saver: SessionSaver = None

    @override
    def enter(self, **kwargs):
        """Initialize experiment with SampleManager."""
        self.no_eeg_mode = kwargs.get("no_eeg_mode", False)

        config = self._show_config_or_abort()
        if config is None:
            return

        if not self._setup_session(config):
            return

        self._begin_first_step()

    @override
    def tick(self):
        """Handle experiment phase transitions."""
        if self._handle_disconnect():
            return

        if not self.current_step:
            print("[ExperimentState] Experiment completed!")
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

        self._update_gui()

        if self._handle_events():
            return

        if self.is_paused:
            return

        if self.step_timer.elapsed() >= self.current_step.duration_ms:
            self._advance_to_next_step()

    def _handle_disconnect(self) -> bool:
        """If running with EEG and headset went away, mark it and bail to menu."""
        if self.no_eeg_mode:
            return False
        if self.flow_controller.headset_connected:
            return False

        from .main_menu_state import MainMenuState

        print("[ExperimentState] EEG headset disconnected — aborting session")
        if self.session_saver is not None:
            self.session_saver.add_marker("DISCONNECTED")

        self.flow_controller.change_state(MainMenuState)

        return True

    @override
    def exit(self):
        """Cleanup experiment resources and finalize EDF."""
        self._teardown_session()

        self.sample_manager = None
        self.current_step = None
        self.total_steps = 0
        self.completed_steps = 0
        self.session_saver = None
        self.no_eeg_mode = False
        self.is_paused = False
        print("[ExperimentState] Experiment state exited")

    def _show_config_or_abort(self):
        from .main_menu_state import MainMenuState

        config = self.gui_manager.show_experiment_config_dialog()
        if config is None:
            self.flow_controller.change_state(MainMenuState)
            return None

        return config

    def _setup_session(self, config) -> bool:
        from .main_menu_state import MainMenuState

        self.sample_manager = SampleManager(
            strategy=config.strategy,
            trials_per_class=config.trials_per_class,
            fixation_ms=config.fixation_ms,
            cue_ms=config.cue_ms,
            rest_ms=config.rest_ms,
            cues=config.cues,
        )
        self.total_steps = len(self.sample_manager.step_queue)
        self.completed_steps = 0
        self.is_paused = False

        if not self.no_eeg_mode:
            if not self._setup_headset(config):
                self.flow_controller.change_state(MainMenuState)
                return False

        return True

    def _setup_headset(self, config) -> bool:
        try:
            self.eeg_headset.start()
        except Exception as e:
            print(f"[ExperimentState] Error starting EEG headset: {e}")
            return False

        self.session_saver = SessionSaver(
            channel_labels=self.eeg_headset.channel_labels,
            sample_rate=self.eeg_headset.sample_rate,
            output_dir=Path("sessions/experiments"),
            session_name=config.session_name,
        )
        self.session_saver.start_session()
        self.eeg_headset.add_subscriber(self.session_saver.on_chunk)

        return True

    def _begin_first_step(self):
        self.current_step = self.sample_manager.get_next()
        self.step_timer.start()

        if not self.no_eeg_mode:
            self.session_saver.add_marker("experiment_start")

        self.gui_manager.show_experiment()

    def _update_gui(self):
        progress_percent = (
            self.completed_steps / self.total_steps if self.total_steps > 0 else 0.0
        )
        self.gui_manager.update_experiment(
            self.current_step.step_type,
            self.no_eeg_mode,
            self.is_paused,
            progress_percent,
        )

    def _handle_events(self) -> bool:
        from .main_menu_state import MainMenuState

        for event in self.gui_manager.get_experiment_events():
            if event == ExperimentEvent.ABORT:
                print("[ExperimentState] Experiment aborted by user (ESC)")
                self.flow_controller.change_state(MainMenuState)
                return True
            elif event == ExperimentEvent.PAUSE:
                self._handle_pause_event()

        return False

    def _handle_pause_event(self):
        self.is_paused = not self.is_paused
        self.step_was_paused = True
        if not self.no_eeg_mode:
            self.session_saver.add_marker("PAUSED" if self.is_paused else "RESUMED")

        print("Experiment PAUSED" if self.is_paused else "Experiment RESUMED")

    def _advance_to_next_step(self):
        self.completed_steps += 1
        self.current_step = self.sample_manager.get_next()
        self.step_timer.restart()
        self.step_was_paused = False

        if self.current_step and not self.no_eeg_mode:
            self.session_saver.add_marker(self.current_step.step_type.value.upper())

        if self.current_step:
            print(
                f"[ExperimentState] Next step: {self.current_step.step_type.value} "
                f"for {self.current_step.duration_ms}ms "
                f"(Progress: {self.completed_steps}/{self.total_steps})"
            )

    def _teardown_session(self):
        if self.session_saver is not None:
            self._teardown_headset()

        if not self.no_eeg_mode:
            try:
                self.eeg_headset.stop()
            except Exception as e:
                print(f"[ExperimentState] Error stopping EEG headset: {e}")

    def _teardown_headset(self):
        try:
            self.eeg_headset.remove_subscriber(self.session_saver.on_chunk)
            self.session_saver.stop_session()
        except Exception as e:
            print(f"[ExperimentState] Error stopping session: {e}")
