import random
from typing import override, TYPE_CHECKING
from PyQt6.QtCore import QTime

from src.sample_manager.sample_manager import SampleManager, ExperimentStep
from src.sample_manager.experiment_step_type import ExperimentStepType
from src.gui.views.calibration_view import CalibrationEvent

from . import FlowState

if TYPE_CHECKING:
    from .main_menu_state import MainMenuState

CUE_DURATION_MS = 4000
RESULT_DURATION_MS = 2000

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

    @override
    def enter(self):
        self.no_eeg_mode = not self.eeg_headset.connected

        config = self.gui_manager.show_calibration_config_dialog()
        if config is None:
            # Import here to avoid circular import
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

        self.sample_manager = SampleManager(
            strategy=config.strategy,
            trials_per_class=config.trials_per_class
        )
        self.total_steps = len(self.sample_manager.step_queue)
        self.completed_steps = 0
        self.classified_as = None

        self.current_step = self.sample_manager.get_next()
        self.step_start_time = QTime.currentTime()

        self.gui_manager.show_calibration()
        self.gui_manager.update_calibration(self.current_step.step_type, None, 0.0, self.no_eeg_mode)
        print(f"Calibration started — {self.total_steps} steps, {config.trials_per_class} trials/class, strategy={config.strategy}, no_eeg_mode={self.no_eeg_mode}")

    @override
    def tick(self):
        if not self.current_step:
            print("Calibration completed!")
            # Import here to avoid circular import
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

        progress = self.completed_steps / self.total_steps if self.total_steps > 0 else 0.0

        self.gui_manager.update_calibration(
            self.current_step.step_type,
            self.classified_as,
            progress,
            self.no_eeg_mode
        )

        events = self.gui_manager.process_calibration_events()
        for event in events:
            if event == CalibrationEvent.ABORT:
                print("Calibration aborted")
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
        is_classifiable = self.current_step.step_type in _CLASSIFIABLE

        if self.classified_as is None:
            cue_duration = CUE_DURATION_MS if is_classifiable else self.current_step.duration_ms
            if elapsed >= cue_duration:
                if is_classifiable:
                    # CUE phase done — classify and show result
                    self.classified_as = self._classify()
                    self.step_start_time = QTime.currentTime()
                    print(f"Classified: {self.classified_as.value}")
                else:
                    # FIXATION/REST — no classification, move directly to next step
                    self.completed_steps += 1
                    self.current_step = self.sample_manager.get_next()
                    self.step_start_time = QTime.currentTime()
        else:
            # RESULT phase — wait then move to next step
            if elapsed >= RESULT_DURATION_MS:
                self.completed_steps += 1
                self.current_step = self.sample_manager.get_next()
                self.classified_as = None
                self.step_start_time = QTime.currentTime()

    def _classify(self) -> ExperimentStepType:
        if self.no_eeg_mode:
            return random.choice(_CLASSIFIABLE)
        else:
            # Placeholder for actual classification logic. For now, just return the correct class or a random one if in no-EEG mode.
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
