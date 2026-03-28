from typing import override, TYPE_CHECKING
from PyQt6.QtCore import QElapsedTimer
from pathlib import Path

from src.sample_manager.sample_manager import SampleManager, ExperimentStep
from src.sample_manager.experiment_step_type import CLASSIFIABLE
from src.gui.gui_manager import ExperimentEvent
from src.flow_controller.session_saver.session_saver import SessionSaver
from . import FlowState


if TYPE_CHECKING:
    from .main_menu_state import MainMenuState

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
    def enter(self):
        """Initialize experiment with SampleManager."""

        self.no_eeg_mode = not self.eeg_headset.is_connected()

        config = self.gui_manager.show_experiment_config_dialog()
        if config is None:
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

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
            channel_labels = list(self.eeg_headset._driver._config.channel_map.values())
            sample_rate = self.eeg_headset._driver.sampling_rate
            self.session_saver = SessionSaver(channel_labels=channel_labels, sample_rate=sample_rate, output_dir=Path("sessions/experiments"))
            try:
                self.eeg_headset.start()
            except Exception as e:
                print(f"[ExperimentState] Error starting EEG headset: {e}")
                self.flow_controller.change_state(MainMenuState)
                return

        self.current_step = self.sample_manager.get_next()
        self.step_timer.start()

        # Annotate first start so we have a clear marker in the buffer
        if not self.no_eeg_mode:
            self.eeg_headset.annotate("experiment_start")

        self.gui_manager.show_experiment()

        print(f"[ExperimentState]Experiment started — {self.total_steps} steps, {config.trials_per_class} trials/class, strategy={config.strategy}, no_eeg_mode={self.no_eeg_mode}")
        if self.current_step:
            print(f"[ExperimentState] First step: {self.current_step.step_type.value} for {self.current_step.duration_ms}ms")

    @override
    def tick(self):
        """Handle experiment phase transitions."""
        if not self.current_step:
            print("[ExperimentState] Experiment completed!")
            # Import here to avoid circular import
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

        progress_percent = self.completed_steps / self.total_steps if self.total_steps > 0 else 0.0

        self.gui_manager.update_experiment(
            self.current_step.step_type,
            self.no_eeg_mode,
            self.is_paused,
            progress_percent
        )

        events = self.gui_manager.get_experiment_events()

        for event in events:
            if event == ExperimentEvent.ABORT:
                print("[ExperimentState] Experiment aborted by user (ESC)")
                # Import here to avoid circular import
                from .main_menu_state import MainMenuState
                self.flow_controller.change_state(MainMenuState)
                return
            
            elif event == ExperimentEvent.QUIT:
                print("[ExperimentState] Quit requested")
                self.flow_controller.running = False
                return
            
            elif event == ExperimentEvent.PAUSE:
                self.is_paused = not self.is_paused
                self.step_was_paused = True
                print("Experiment PAUSED" if self.is_paused else "Experiment RESUMED")

        if self.is_paused:
            if not self.no_eeg_mode and self.step_timer.elapsed() > self.eeg_headset.buffer_size_seconds * 1000:
                # If paused for too long, we risk overflowing the EEG buffer since we're not reading data during the pause. To prevent this, we can end the experiment if the pause exceeds the buffer size
                print("[ExperimentState] Buffer overflow during pause — ending experiment")
                from .main_menu_state import MainMenuState
                self.flow_controller.change_state(MainMenuState)
            return

        elapsed = self.step_timer.elapsed()

        if elapsed >= self.current_step.duration_ms:
            if not self.no_eeg_mode:
                step_data = self.eeg_headset.get_output(seconds=self.current_step.duration_ms // 1000)
                label = self.current_step.step_type.value.upper() if not self.step_was_paused else "PAUSED" # Mark paused steps in the data
                self.session_saver.save_step(step_data, label, elapsed / 1000)
                self.eeg_headset.annotate("border")

            self.completed_steps += 1
            self.current_step = self.sample_manager.get_next()
            self.step_timer.restart()
            self.step_was_paused = False

            if self.current_step and self.current_step.step_type in CLASSIFIABLE:
                self.eeg_headset.annotate(self.current_step.step_type.value)

            if self.current_step:
                print(f"[ExperimentState] Next step: {self.current_step.step_type.value} for {self.current_step.duration_ms}ms (Progress: {self.completed_steps}/{self.total_steps})")

    @override
    def exit(self):
        """Cleanup experiment resources and export data to EDF"""
        if self.session_saver is not None:
            try:
                self.session_saver.export_to_edf()
            except Exception as e:
                print(f"[ExperimentState] Error exporting EDF: {e}")
        self.sample_manager = None
        self.current_step = None
        self.total_steps = 0
        self.completed_steps = 0
        self.session_saver = None
        if not self.no_eeg_mode:
            try:
                self.eeg_headset.stop()
            except Exception as e:
                print(f"[ExperimentState] Error stopping EEG headset: {e}")
        print("[ExperimentState] Experiment state exited")
