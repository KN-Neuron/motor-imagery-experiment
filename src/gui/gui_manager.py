from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt

from .views.main_menu_view import MainMenuView, MainMenuEvent
from .views.experiment_view import ExperimentView, ExperimentEvent
from .views.calibration_view import CalibrationView, CalibrationEvent
from .shared.sidebar import Sidebar
from .shared.config_dialog import CalibrationConfigDialog, ExperimentConfigDialog
from src.config.config import (
    CalibrationConfig, ExperimentConfig,
    load_calibration_config, load_experiment_config,
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

        self.window = None
        self.stacked_widget = None
        self.current_view = None

    def initialize(self) -> None:
        """Create the main window, layout and connect sidebar signals."""
        self.window = QMainWindow()
        self.window.setWindowTitle("Hex-O-Spell Experiment")
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
        elif self.current_view == self.experiment_view:
            self.experiment_view.pending_events.append(ExperimentEvent.QUIT)
        elif self.current_view == self.calibration_view:
            self.calibration_view.pending_events.append(CalibrationEvent.QUIT)

# Main menu methods

    def show_main_menu(self) -> None:
        self.current_view = self.main_menu_view
        self.stacked_widget.setCurrentWidget(self.main_menu_view)
        self.sidebar.set_buttons_visibility(show_pause=False, show_back=False, show_quit=True)

    def update_main_menu(self, headset_connected: bool = False) -> None:
        self.main_menu_view.update_content(headset_connected)

    def get_main_menu_events(self) -> list[MainMenuEvent]:
        return self.main_menu_view.get_pending_events()

# Experiment methods

    def show_experiment(self) -> None:
        self.current_view = self.experiment_view
        self.stacked_widget.setCurrentWidget(self.experiment_view)
        self.sidebar.reset_pause()
        self.sidebar.set_buttons_visibility(show_pause=True, show_back=False)

    def update_experiment(self, 
        step_type=None, 
        no_eeg_mode=False, 
        is_paused=False,
        progress_percent=0.0
    ) -> None:
        self.experiment_view.update_content(step_type, no_eeg_mode, is_paused, progress_percent)

    def get_experiment_events(self) -> list[ExperimentEvent]:
        return self.experiment_view.get_pending_events()

# Calibration methods

    def show_calibration(self) -> None:
        self.current_view = self.calibration_view
        self.stacked_widget.setCurrentWidget(self.calibration_view)
        self.sidebar.reset_pause()
        self.sidebar.set_buttons_visibility(show_pause=True)

    def update_calibration(self, 
        step_type=None, 
        classified_as=None, 
        no_eeg_mode=False,
        is_paused=False,
        progress_percent=0.0
    ) -> None:
        self.calibration_view.update_content(step_type, classified_as, no_eeg_mode, is_paused, progress_percent)

    def get_calibration_events(self) -> list[CalibrationEvent]:
        return self.calibration_view.get_pending_events()

    def show_calibration_config_dialog(self) -> CalibrationConfig | None:
        initial = load_calibration_config()
        dialog = CalibrationConfigDialog(initial=initial, parent=self.window)
        dialog.exec()
        return dialog.get_config()

    def show_experiment_config_dialog(self) -> ExperimentConfig | None:
        initial = load_experiment_config()
        dialog = ExperimentConfigDialog(initial=initial, parent=self.window)
        dialog.exec()
        return dialog.get_config()
