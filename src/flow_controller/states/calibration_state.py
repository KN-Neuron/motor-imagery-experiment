import random
from typing import override, TYPE_CHECKING
from PyQt6.QtCore import QElapsedTimer
from pathlib import Path

from src.sample_manager.sample_manager import SampleManager, ExperimentStep
from src.sample_manager.experiment_step_type import ExperimentStepType, CLASSIFIABLE
from src.gui.views.calibration_view import CalibrationEvent
from src.flow_controller.session_saver.session_saver import SessionSaver
from . import FlowState


if TYPE_CHECKING:
    from .main_menu_state import MainMenuState

class CalibrationState(FlowState):
    """Handles calibration: shows cue → classifies → shows result."""

    def __init__(self, flow_controller):
        super().__init__(flow_controller)
        self.sample_manager: SampleManager = None
        self.current_step: ExperimentStep = None
        self.step_timer: QElapsedTimer = QElapsedTimer()
        self.classified_as: ExperimentStepType | None = None
        self.no_eeg_mode: bool = False
        self.is_paused: bool = False
        self.step_was_paused: bool = False
        self._in_result_phase: bool = False
        self.total_steps: int = 0
        self.completed_steps: int = 0
        self.result_duration_ms: int = 2000
        self.session_saver: SessionSaver = None

    @override
    def enter(self):
        self.no_eeg_mode = not self.eeg_headset.is_connected()

        config = self.gui_manager.show_calibration_config_dialog()
        if config is None:
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

        self.result_duration_ms = config.result_ms

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
        self.classified_as = None
        self._in_result_phase = False

        if not self.no_eeg_mode:
            channel_labels = list(self.eeg_headset._driver._config.channel_map.values())
            sample_rate = self.eeg_headset._driver.sampling_rate
            self.session_saver = SessionSaver(channel_labels=channel_labels, sample_rate=sample_rate, output_dir=Path("sessions/calibrations"))
            try:
                self.eeg_headset.start()
            except Exception as e:
                print(f"[CalibrationState] Error starting EEG headset: {e}")
                self.flow_controller.change_state(MainMenuState)
                return

        self.current_step = self.sample_manager.get_next()
        self.step_timer.start()

        if not self.no_eeg_mode:
            self.eeg_headset.annotate("calibration_start")

        self.gui_manager.show_calibration()
        self.gui_manager.update_calibration(self.current_step.step_type, None, 0.0, self.no_eeg_mode)
        print(f"[CalibrationState] Calibration started — {self.total_steps} steps, {config.trials_per_class} trials/class, strategy={config.strategy}, no_eeg_mode={self.no_eeg_mode}")

    @override
    def tick(self):
        if not self.current_step:
            print("[CalibrationState] Calibration completed!")
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

        progress_percent = self.completed_steps / self.total_steps if self.total_steps > 0 else 0.0

        self.gui_manager.update_calibration(
            self.current_step.step_type,
            self.classified_as,
            self.no_eeg_mode,
            self.is_paused,
            progress_percent,
        )

        events = self.gui_manager.get_calibration_events()
        for event in events:
            if event == CalibrationEvent.ABORT:
                print("[CalibrationState] Calibration aborted")
                from .main_menu_state import MainMenuState
                self.flow_controller.change_state(MainMenuState)
                return
            elif event == CalibrationEvent.PAUSE:
                self.is_paused = not self.is_paused
                self.step_was_paused = True
                print("Calibration PAUSED" if self.is_paused else "Calibration RESUMED")

        if self.is_paused:
            if not self.no_eeg_mode and self.step_timer.elapsed() > self.eeg_headset.buffer_size_seconds * 1000:
                # If paused for too long, we risk overflowing the EEG buffer since we're not reading data during the pause. To prevent this, we can end the calibration if the pause exceeds the buffer size
                print("[CalibrationState] Buffer overflow during pause — ending calibration")
                from .main_menu_state import MainMenuState
                self.flow_controller.change_state(MainMenuState)
            return

        elapsed = self.step_timer.elapsed()

        if not self._in_result_phase:
            # Active step phase: CUE / FIXATION / REST
            if elapsed >= self.current_step.duration_ms:
                label = self.current_step.step_type.value.upper() if not self.step_was_paused else "PAUSED" # Mark paused steps in the data
                self._save_and_annotate(label, elapsed)
                if self.current_step.step_type in CLASSIFIABLE:
                    self.classified_as = self._classify()
                    self._in_result_phase = True
                    self.step_timer.restart()
                    print(f"[CalibrationState] Classified: {self.classified_as.value}")
                else:
                    self._advance_to_next_step()
        else:
            # Result display phase (only for classifiable steps)
            if elapsed >= self.result_duration_ms:
                self._save_and_annotate("RESULT", elapsed)
                self.classified_as = None
                self._in_result_phase = False
                self._advance_to_next_step()

    def _save_and_annotate(self, label: str, duration_ms: int) -> None:
        if not self.no_eeg_mode:
            eeg_data = self.eeg_headset.get_output(seconds=duration_ms / 1000)
            self.session_saver.save_step(eeg_data, label, duration_ms / 1000)
            self.eeg_headset.annotate("border")

    def _advance_to_next_step(self) -> None:
        self.completed_steps += 1
        self.current_step = self.sample_manager.get_next()
        self.step_timer.restart()
        self.step_was_paused = False
        if self.current_step and self.current_step.step_type in CLASSIFIABLE:
            self.eeg_headset.annotate(self.current_step.step_type.value)

    def _classify(self) -> ExperimentStepType:
        # TODO: pass eeg_data to actual classifier
        return random.choice(CLASSIFIABLE) if self.no_eeg_mode else self.current_step.step_type

    @override
    def exit(self):
        if self.session_saver is not None:
            try:
                self.session_saver.export_to_edf()
            except Exception as e:
                print(f"[CalibrationState] Error exporting EDF: {e}")
        self.sample_manager = None
        self.current_step = None
        self.classified_as = None
        self._in_result_phase = False
        self.total_steps = 0
        self.completed_steps = 0
        self.result_duration_ms = 2000
        self.session_saver = None

        if not self.no_eeg_mode:
            try:
                self.eeg_headset.stop()
            except Exception as e:
                print(f"[CalibrationState] Error stopping EEG headset: {e}")

        self.no_eeg_mode = False
        self.is_paused = False
        print("[CalibrationState] Calibration state exited")
