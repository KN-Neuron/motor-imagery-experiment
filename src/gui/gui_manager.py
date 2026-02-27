from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt

from .views.main_menu_view import MainMenuView, MainMenuEvent
from .views.experiment_view import ExperimentView, ExperimentEvent
from .views.calibration_view import CalibrationView
from .shared.sidebar import Sidebar


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

# Main menu methods

    def show_main_menu(self) -> None:
        self.current_view = self.main_menu_view
        self.stacked_widget.setCurrentWidget(self.main_menu_view)
        self.sidebar.set_buttons_visibility(show_pause=False, show_back=False)

    def update_main_menu(self, headset_connected: bool = False) -> None:
        self.main_menu_view.update_content(headset_connected)

    def process_main_menu_events(self) -> list[MainMenuEvent]:
        """Handle TOGGLE_FULLSCREEN internally, pass rest to state."""
        menu_events = self.main_menu_view.get_pending_events()

        i = 0
        while i < len(menu_events):
            event = menu_events[i]
            event_type = event[0] if isinstance(event, tuple) else event

            if event_type == MainMenuEvent.TOGGLE_FULLSCREEN:
                self.toggle_fullscreen()
                menu_events.pop(i)
            else:
                i += 1

        return menu_events

# Experiment methods

    def show_experiment(self) -> None:
        self.current_view = self.experiment_view
        self.stacked_widget.setCurrentWidget(self.experiment_view)
        self.sidebar.set_buttons_visibility(show_pause=True, show_back=False)

    def update_experiment(self, step_type=None, no_eeg_mode=False, progress_percent=0.0) -> None:
        self.experiment_view.update_content(step_type, no_eeg_mode, progress_percent)

    def process_experiment_events(self) -> list[ExperimentEvent]:
        """Handle TOGGLE_FULLSCREEN internally, pass rest to state."""
        experiment_events = self.experiment_view.get_pending_events()

        i = 0
        while i < len(experiment_events):
            event = experiment_events[i]
            if event == ExperimentEvent.TOGGLE_FULLSCREEN:
                self.toggle_fullscreen()
                experiment_events.pop(i)
            else:
                i += 1

        return experiment_events

# Calibration methods

    def show_calibration(self) -> None:
        self.current_view = self.calibration_view
        self.stacked_widget.setCurrentWidget(self.calibration_view)

    def process_calibration_events(self) -> list:
        return self.calibration_view.get_pending_events()
