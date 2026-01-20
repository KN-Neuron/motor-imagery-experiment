from typing import override, TYPE_CHECKING
import pygame

from src.sample_manager.sample_manager import SampleManager, ExperimentStep
from src.sample_manager.experiment_step_type import ExperimentStepType
from src.gui.gui_manager import ExperimentEvent

from . import FlowState

if TYPE_CHECKING:
    from .main_menu_state import MainMenuState


# Experiment state for the flow controller handling experiment procedures
class ExperimentState(FlowState):
    def __init__(self, flow_controller):
        super().__init__(flow_controller)
        self.sample_manager: SampleManager = None
        self.current_step: ExperimentStep = None
        self.step_start_time: int = 0
        self.no_eeg_mode: bool = False
        self.total_steps: int = 0
        self.completed_steps: int = 0

    @override
    def enter(self):
        """Initialize experiment with SampleManager"""
        # Check if running without EEG
        self.no_eeg_mode = not self.eeg_headset.connected

        # Create sample manager with stratified strategy (hardcoded for now)
        self.sample_manager = SampleManager(
            strategy="stratified",
            trials_per_class=5
        )

        # Track total steps for progress calculation
        self.total_steps = len(self.sample_manager.step_queue)
        self.completed_steps = 0

        # Get first step
        self.current_step = self.sample_manager.get_next()
        self.step_start_time = pygame.time.get_ticks()

        print(f"Experiment started (no_eeg_mode={self.no_eeg_mode})")
        print(f"Total steps: {self.total_steps}")
        if self.current_step:
            print(f"First step: {self.current_step.step_type.value} for {self.current_step.duration_ms}ms")

    @override
    def iter(self):
        """Handle experiment phase transitions"""
        if not self.current_step:
            # Experiment finished, return to main menu
            print("Experiment completed!")
            # Import here to avoid circular import
            from .main_menu_state import MainMenuState
            self.flow_controller.change_state(MainMenuState)
            return

        # Calculate progress percentage
        progress_percent = self.completed_steps / self.total_steps if self.total_steps > 0 else 0.0

        # Render current experiment phase
        self.gui_manager.render(
            self.gui_manager.display_experiment,
            self.current_step.step_type,
            self.no_eeg_mode,
            progress_percent
        )

        # Process events
        events = self.gui_manager.process_experiment_events()

        # Handle experiment events
        for event in events:
            if event == ExperimentEvent.ABORT:
                print("Experiment aborted by user (ESC)")
                # Import here to avoid circular import
                from .main_menu_state import MainMenuState
                self.flow_controller.change_state(MainMenuState)
                return
            elif event == ExperimentEvent.QUIT:
                print("Quit requested")
                self.flow_controller.running = False
                return

        # Check if current step duration has elapsed
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.step_start_time

        if elapsed >= self.current_step.duration_ms:
            # Move to next step
            self.completed_steps += 1
            self.current_step = self.sample_manager.get_next()
            self.step_start_time = current_time

            if self.current_step:
                print(f"Next step: {self.current_step.step_type.value} for {self.current_step.duration_ms}ms (Progress: {self.completed_steps}/{self.total_steps})")

    @override
    def exit(self):
        """Cleanup experiment resources"""
        self.sample_manager = None
        self.current_step = None
        self.total_steps = 0
        self.completed_steps = 0
        print("Experiment state exited")
