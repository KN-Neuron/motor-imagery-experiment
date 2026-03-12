import random
from typing import override, TYPE_CHECKING
from PyQt6.QtCore import QTime

from src.sample_manager.sample_manager import SampleManager, ExperimentStep
from src.sample_manager.experiment_step_type import ExperimentStepType
from src.gui.views.calibration_view import CalibrationEvent
from src.flow_controller.session_saver.session_saver import SessionSaver

from . import FlowState

if TYPE_CHECKING:
    from .main_menu_state import MainMenuState

_CLASSIFIABLE = [s for s in ExperimentStepType
                 if s not in (ExperimentStepType.FIXATION, ExperimentStepType.REST)]


class CalibrationState(FlowState):
    """Handles calibration: shows cue → classifies → shows result."""

    def __init__(self, flow_controller):
        super().__init__(flow_controller)
        self.sample_manager: SampleManager = None
        self.current_step: ExperimentStep = None
        self.step_start_time: QTime = None
        self.classified_as: ExperimentStepType | None = None
        self.no_eeg_mode: bool = False
        self.is_paused: bool = False
        self.pause_elapsed_time: int = 0
        self.total_steps: int = 0
        self.completed_steps: int = 0
        self.cue_duration_ms: int = 4000
        self.result_duration_ms: int = 2000
        self.session_saver: SessionSaver = None

    @override
    def enter(self):
        self.no_eeg_mode = not self.eeg_headset.is_connected()

        config = self.gui_manager.show_calibration_config_dialog()
        if config is None:
            # Import here to avoid circular import
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

        self.cue_duration_ms = config.cue_ms
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
        self.classified_as = None

        if not self.no_eeg_mode:
            self.session_saver = SessionSaver(session_type="calibration")
            try:
                self.eeg_headset.start()
            except Exception as e:
                print(f"[CalibrationState] Error starting EEG headset: {e}")
                self.flow_controller.change_state(MainMenuState)
                return

        self.current_step = self.sample_manager.get_next()
        self.step_start_time = QTime.currentTime()

        # Annotate first step if it is classifiable (it is not but just in case the strategy changes)
        if self.current_step and self.current_step.step_type in _CLASSIFIABLE:
            self.eeg_headset.annotate(self.current_step.step_type.value)

        self.gui_manager.show_calibration()
        self.gui_manager.update_calibration(self.current_step.step_type, None, 0.0, self.no_eeg_mode)
        print(f"[CalibrationState] Calibration started — {self.total_steps} steps, {config.trials_per_class} trials/class, strategy={config.strategy}, no_eeg_mode={self.no_eeg_mode}")

    @override
    def tick(self):
        if not self.current_step:
            print("[CalibrationState] Calibration completed!")
            # Import here to avoid circular import
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
                # Import here to avoid circular import
                from .main_menu_state import MainMenuState
                self.flow_controller.change_state(MainMenuState)
                return
            elif event == CalibrationEvent.PAUSE:
                self.is_paused = not self.is_paused
                if self.is_paused:
                    self.pause_elapsed_time = self.step_start_time.msecsTo(QTime.currentTime())
                else:
                    self.step_start_time = QTime.currentTime().addMSecs(-self.pause_elapsed_time)

        if self.is_paused:
            return

        elapsed = self.step_start_time.msecsTo(QTime.currentTime())

        if self.classified_as is None:
            # CUE/FIXATION/REST phase — wait then classify (if classifiable) and move to RESULT
            cue_duration = self.cue_duration_ms \
                if self.current_step.step_type in _CLASSIFIABLE \
                else self.current_step.duration_ms
            
            if elapsed >= cue_duration:
                if self.current_step.step_type in _CLASSIFIABLE:
                    # CUE phase done — classify and show result
                    self.classified_as = self._classify()
                    self.step_start_time = QTime.currentTime()
                    print(f"[CalibrationState] Classified: {self.classified_as.value}")
                else:
                    # FIXATION/REST — no classification, move directly to next step
                    self.completed_steps += 1
                    self.current_step = self.sample_manager.get_next()
                    self.step_start_time = QTime.currentTime()
                    if self.current_step and self.current_step.step_type in _CLASSIFIABLE:
                        self.eeg_headset.annotate(self.current_step.step_type.value)
        else:
            # RESULT phase — wait then move to next step
            if elapsed >= self.result_duration_ms:
                self.completed_steps += 1
                self.current_step = self.sample_manager.get_next()
                self.classified_as = None
                self.step_start_time = QTime.currentTime()
                if self.current_step and self.current_step.step_type in _CLASSIFIABLE:
                    self.eeg_headset.annotate(self.current_step.step_type.value)

    def _classify(self) -> ExperimentStepType:
        if self.no_eeg_mode:
            return random.choice(_CLASSIFIABLE)

        eeg_data = self.eeg_headset.get_output(seconds=self.cue_duration_ms // 1000)
        self.session_saver.save_trial(eeg_data, self.current_step.step_type.value)
        # TODO: pass eeg_data to actual classifier
        return self.current_step.step_type

    @override
    def exit(self):
        self.sample_manager = None
        self.current_step = None
        self.classified_as = None
        self.no_eeg_mode = False
        self.is_paused = False
        self.pause_elapsed_time = 0
        self.total_steps = 0
        self.completed_steps = 0
        self.cue_duration_ms = 4000
        self.result_duration_ms = 2000
        self.session_saver = None

        if not self.no_eeg_mode:
            try:
                self.eeg_headset.stop()
            except Exception as e:
                print(f"[CalibrationState] Error stopping EEG headset: {e}")

        print("[CalibrationState] Calibration state exited")
