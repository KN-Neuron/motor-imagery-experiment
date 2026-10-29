from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QHBoxLayout

from .views.main_menu_view import MainMenuView, MainMenuEvent
from .views.experiment_view import ExperimentView, ExperimentEvent
from .views.calibration_view import CalibrationView, CalibrationEvent
from .views.session_view import SessionView
from .views.view import View
from .shared.sidebar import Sidebar
from .dialogs import CalibrationConfigDialog, ExperimentConfigDialog
from .dialogs.participant_dialog import ParticipantDialog
from .dialogs.quality_dialog import QualityDialog, QualityResult
from src.eeg_headset.eeg_headset import EEGHeadset
from src.sample_manager.experiment_step_type import ExperimentStepType
from src.sample_manager.sample_manager import ExperimentStep
from src.session_metadata.participant import ParticipantInfo
from src.signal_quality.thresholds import QualityThresholds
from src.trials_config.trials_config import (
    CalibrationConfig,
    ExperimentConfig,
    load_calibration_config,
    load_experiment_config,
)


class GUIManager:
    def __init__(self, width: int = 1200, height: int = 800) -> None:
        self.width = width
        self.height = height
        self.min_width = width
        self.min_height = height
        self.default_width = width
        self.default_height = height
        self.is_fullscreen = False
        self.is_frameless = False

        self.main_menu_view = MainMenuView()
        self.experiment_view = ExperimentView()
        self.calibration_view = CalibrationView()

        self.sidebar = Sidebar()

        self.window: QMainWindow
        self.stacked_widget: QStackedWidget
        self.current_view: View | None = None

    def initialize(self) -> None:
        """Create the main window, layout and connect sidebar signals."""
        self.window = QMainWindow()
        self.window.setWindowTitle("Motor Imagery Experiment")
        self.window.setMinimumSize(self.min_width, self.min_height)
        self.window.resize(self.width, self.height)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.sidebar)

        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        self.stacked_widget.addWidget(self.main_menu_view)
        self.stacked_widget.addWidget(self.experiment_view)
        self.stacked_widget.addWidget(self.calibration_view)

        # Connect sidebar signals
        self.sidebar.fullscreen_toggled.connect(self.toggle_fullscreen)
        self.sidebar.pause_toggled.connect(self.toggle_pause)
        self.sidebar.quit_requested.connect(self.on_quit_requested)

        self.window.setCentralWidget(container)
        self.window.show()

    def toggle_fullscreen(self) -> None:
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            self.window.showFullScreen()
        else:
            self.window.showNormal()
            self.window.resize(self.default_width, self.default_height)

        self.sidebar.update_states(self.is_fullscreen)

    def toggle_pause(self) -> None:
        if self.current_view == self.experiment_view:
            self.experiment_view.pending_events.append(ExperimentEvent.PAUSE)
        elif self.current_view == self.calibration_view:
            self.calibration_view.pending_events.append(CalibrationEvent.PAUSE)

    def on_quit_requested(self) -> None:
        if self.current_view == self.main_menu_view:
            self.main_menu_view.pending_events.append(MainMenuEvent.QUIT)

    # Main menu methods

    def show_main_menu(self) -> None:
        self.current_view = self.main_menu_view
        self.stacked_widget.setCurrentWidget(self.main_menu_view)
        self.sidebar.set_buttons_visibility(
            show_pause=False, show_back=False, show_quit=True
        )

    def update_main_menu(self, headset_connected: bool = False) -> None:
        self.main_menu_view.update_content(headset_connected)

    def get_main_menu_events(self) -> list[MainMenuEvent]:
        return self.main_menu_view.get_pending_events()

    # Experiment / calibration methods (both use SessionView)

    def show_experiment(self) -> None:
        self.current_view = self.experiment_view
        self.stacked_widget.setCurrentWidget(self.experiment_view)
        self.experiment_view.is_paused = False
        self.sidebar.reset_pause()
        self.sidebar.set_buttons_visibility(show_pause=True, show_back=False)

    def update_experiment(
        self,
        step: ExperimentStep | None = None,
        classified_as: ExperimentStepType | None = None,
        no_eeg_mode: bool = False,
        is_paused: bool = False,
        progress_percent: float = 0.0,
        feedback_mode: str = "none",
        token: int = 0,
    ) -> None:
        self.experiment_view.update_content(
            step,
            classified_as,
            no_eeg_mode,
            is_paused,
            progress_percent,
            feedback_mode,
            token,
        )

    def get_experiment_events(self) -> list[ExperimentEvent]:
        return self.experiment_view.get_pending_events()

    def show_calibration(self) -> None:
        self.current_view = self.calibration_view
        self.stacked_widget.setCurrentWidget(self.calibration_view)
        self.calibration_view.is_paused = False
        self.sidebar.reset_pause()
        self.sidebar.set_buttons_visibility(show_pause=True)

    def update_calibration(
        self,
        step: ExperimentStep | None = None,
        classified_as: ExperimentStepType | None = None,
        no_eeg_mode: bool = False,
        is_paused: bool = False,
        progress_percent: float = 0.0,
        feedback_mode: str = "none",
        token: int = 0,
    ) -> None:
        self.calibration_view.update_content(
            step,
            classified_as,
            no_eeg_mode,
            is_paused,
            progress_percent,
            feedback_mode,
            token,
        )

    def get_calibration_events(self) -> list[CalibrationEvent]:
        return self.calibration_view.get_pending_events()

    def set_ssvep_frequency(self, freq_hz: float) -> None:
        self.experiment_view.ssvep_frequency_hz = freq_hz
        self.calibration_view.ssvep_frequency_hz = freq_hz

    def pop_first_paint(self) -> tuple[int, int] | None:
        """(step token, perf_counter_ns) when the current step was first painted."""
        view = self.current_view
        return view.pop_first_paint() if isinstance(view, SessionView) else None

    def refresh_rate_hz(self) -> float:
        return self.experiment_view.refresh_rate_hz()

    def show_calibration_config_dialog(self) -> CalibrationConfig | None:
        initial = load_calibration_config() or CalibrationConfig()
        dialog = CalibrationConfigDialog(initial=initial, parent=self.window)
        dialog.exec()
        config = dialog.get_config()
        return config if isinstance(config, CalibrationConfig) else None

    def show_experiment_config_dialog(self) -> ExperimentConfig | None:
        initial = load_experiment_config() or ExperimentConfig()
        dialog = ExperimentConfigDialog(initial=initial, parent=self.window)
        dialog.exec()
        config = dialog.get_config()
        return config if isinstance(config, ExperimentConfig) else None

    def show_participant_dialog(self, data_root: Path) -> ParticipantInfo | None:
        dialog = ParticipantDialog(data_root, parent=self.window)
        dialog.exec()
        return dialog.get_info()

    def show_quality_dialog(
        self, headset: EEGHeadset, thresholds: QualityThresholds, duration_s: float
    ) -> QualityResult | None:
        dialog = QualityDialog(headset, thresholds, duration_s, parent=self.window)
        dialog.exec()
        return dialog.get_result()
