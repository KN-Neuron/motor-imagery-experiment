import pygame

from .views.main_menu_view import MainMenuView, MainMenuEvent
from .views.experiment_view import ExperimentView, ExperimentEvent
from .views.calibration_view import CalibrationView


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

        # Initialize views
        self.main_menu_view = MainMenuView()
        self.experiment_view = ExperimentView()
        self.calibration_view = CalibrationView()

    def initialize(self) -> None:
        """Initialize the GUI system"""
        pygame.init()
        self.window = pygame.display.set_mode(
            (self.width, self.height),
            pygame.RESIZABLE
        )
        pygame.display.set_caption("Hex-O-Spell Experiment")

    def toggle_frame(self) -> None:
        """Toggle window frame (borderless window mode)"""
        self.is_frameless = not self.is_frameless

        if self.is_frameless:
            info = pygame.display.Info()
            self.width, self.height = info.current_w, info.current_h

            self.window = pygame.display.set_mode(
                (self.width, self.height),
                pygame.NOFRAME
            )
        else:
            self.window = pygame.display.set_mode(
                (self.width, self.height),
                pygame.RESIZABLE
            )

    def toggle_fullscreen(self) -> None:
        """Toggle actual fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            self.window = pygame.display.set_mode(
                (0, 0),
                pygame.FULLSCREEN
            )
            self.width = self.window.get_width()
            self.height = self.window.get_height()
        else:
            self.width = self.default_width
            self.height = self.default_height
            self.window = pygame.display.set_mode(
                (self.width, self.height),
                pygame.RESIZABLE
            )
            self.is_frameless = False  # Going windowed disables frameless
            
    def _handle_window_resize(self, event: pygame.event.Event) -> None:
        """Handle window resize event"""
        if not self.is_fullscreen:
            new_width = max(event.w, self.min_width)
            new_height = max(event.h, self.min_height)
            self.width = new_width
            self.height = new_height
            self.window = pygame.display.set_mode(
                (new_width, new_height),
                pygame.RESIZABLE
            )

    def _process_events(self) -> list:
        """Gather pygame events, and process window resize internally"""
        events_to_process = []

        # Go through all events, separate and process resize internally
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                self._handle_window_resize(event)
            else:
                events_to_process.append(event)

        return events_to_process

# Main menu facade methods

    def display_main_menu(self, headset_connected: bool = False) -> None:
        """Display the main menu"""
        self.main_menu_view.render(
            self.window,
            self.width,
            self.height,
            self.is_fullscreen,
            self.is_frameless,
            headset_connected
        )

    def process_main_menu_events(self) -> list[MainMenuEvent]:
        """Gather main menu events and handle some internally"""
        events_to_process = self._process_events()

        # Delegate to view
        menu_events = self.main_menu_view.process_events(events_to_process)

        # Separate and process some events internally
        i = 0
        while i < len(menu_events):
            event = menu_events[i]
            if event == MainMenuEvent.TOGGLE_FULLSCREEN:
                self.toggle_fullscreen()
                menu_events.pop(i)
            elif event == MainMenuEvent.TOGGLE_FRAME:
                self.toggle_frame()
                menu_events.pop(i)
            else:
                i += 1

        return menu_events

# Experiment facade methods

    def display_experiment(self, step_type=None, no_eeg_mode=False, progress_percent=0.0) -> None:
        """Display the experiment view"""
        self.experiment_view.render(
            self.window,
            self.width,
            self.height,
            step_type,
            no_eeg_mode,
            self.is_fullscreen,
            self.is_frameless,
            progress_percent
        )

    def process_experiment_events(self) -> list[ExperimentEvent]:
        """Gather experiment events and handle some internally"""
        events_to_process = self._process_events()

        # Delegate to view
        experiment_events = self.experiment_view.process_events(events_to_process)

        # Separate and process some events internally
        i = 0
        while i < len(experiment_events):
            event = experiment_events[i]
            if event == ExperimentEvent.TOGGLE_FULLSCREEN:
                self.toggle_fullscreen()
                experiment_events.pop(i)
            elif event == ExperimentEvent.TOGGLE_FRAME:
                self.toggle_frame()
                experiment_events.pop(i)
            else:
                i += 1

        return experiment_events

# Calibration facade methods

    def display_calibration(self) -> None:
        """Display the calibration view"""
        self.calibration_view.render(
            self.window,
            self.width,
            self.height
        )

    def process_calibration_events(self) -> list:
        """Gather calibration events and handle some internally"""
        events = self._process_events()
        return self.calibration_view.process_events(events)

# Common rendering method

    def render(self, display_function, *args, **kwargs) -> None:
        """Render the current GUI state using the provided display function"""
        self.window.fill((15, 15, 25))
        display_function(*args, **kwargs)
        pygame.display.flip()
