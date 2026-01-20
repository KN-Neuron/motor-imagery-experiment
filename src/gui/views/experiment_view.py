import pygame
from enum import Enum
from src.sample_manager.experiment_step_type import ExperimentStepType


class ExperimentEvent(Enum):
    TOGGLE_FULLSCREEN = "toggle_fullscreen"
    TOGGLE_FRAME = "toggle_frame"
    ABORT = "abort"
    QUIT = "quit"


class ExperimentView:
    def __init__(self) -> None:
        self.fullscreen_btn_rect: pygame.Rect = None
        self.frameless_btn_rect: pygame.Rect = None

    def render(
        self,
        window: pygame.Surface,
        width: int,
        height: int,
        step_type: ExperimentStepType = None,
        no_eeg_mode: bool = False,
        is_fullscreen: bool = False,
        is_frameless: bool = False,
        progress_percent: float = 0.0
    ) -> None:
        """Render the experiment view with deep purple background"""
        # Deep purple background (instead of dark blue)
        deep_purple = (25, 15, 40)
        window.fill(deep_purple)

        # Draw fullscreen/frameless toggle buttons (same as main menu)
        self._draw_window_controls(window, is_fullscreen, is_frameless)

        # Draw NO EEG MODE label in top-right corner
        if no_eeg_mode:
            self._draw_no_eeg_label(window, width)

        # Draw progress bar at bottom
        self._draw_progress_bar(window, width, height, progress_percent)

        # Draw current experiment step info
        if step_type:
            self._draw_step_info(window, width, height, step_type)

    def _draw_window_controls(self, window: pygame.Surface, is_fullscreen: bool, is_frameless: bool) -> None:
        """Draw window control buttons in top-left corner"""
        try:
            btn_width = 50
            btn_height = 35
            btn_margin = 10
            btn_spacing = 5

            # Fullscreen toggle button
            self.fullscreen_btn_rect = pygame.Rect(btn_margin, btn_margin, btn_width, btn_height)
            btn_surface = pygame.Surface((btn_width, btn_height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surface, (60, 60, 80, 180), btn_surface.get_rect(), border_radius=8)
            window.blit(btn_surface, self.fullscreen_btn_rect.topleft)

            icon_font = pygame.font.SysFont('Arial', 14, bold=True)
            icon_text = "FS" if not is_fullscreen else "WIN"
            icon_surface = icon_font.render(icon_text, True, (255, 255, 255))
            icon_x = btn_margin + (btn_width - icon_surface.get_width()) // 2
            icon_y = btn_margin + (btn_height - icon_surface.get_height()) // 2
            window.blit(icon_surface, (icon_x, icon_y))

            # Frameless toggle button
            self.frameless_btn_rect = pygame.Rect(
                btn_margin + btn_width + btn_spacing,
                btn_margin,
                btn_width,
                btn_height
            )
            btn_surface2 = pygame.Surface((btn_width, btn_height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surface2, (60, 60, 80, 180), btn_surface2.get_rect(), border_radius=8)
            window.blit(btn_surface2, self.frameless_btn_rect.topleft)

            icon_text2 = "NF" if not is_frameless else "FR"
            icon_surface2 = icon_font.render(icon_text2, True, (255, 255, 255))
            icon_x2 = self.frameless_btn_rect.x + (btn_width - icon_surface2.get_width()) // 2
            icon_y2 = self.frameless_btn_rect.y + (btn_height - icon_surface2.get_height()) // 2
            window.blit(icon_surface2, (icon_x2, icon_y2))
        except Exception:
            pass

    def _draw_no_eeg_label(self, window: pygame.Surface, width: int) -> None:
        """Draw NO EEG MODE label in top-right corner"""
        try:
            mode_font = pygame.font.SysFont('Arial', 16)
            mode_surface = mode_font.render("NO EEG MODE", True, (180, 100, 100))
            mode_x = width - mode_surface.get_width() - 15
            mode_y = 15
            window.blit(mode_surface, (mode_x, mode_y))
        except Exception:
            pass

    def _draw_progress_bar(self, window: pygame.Surface, width: int, height: int, progress_percent: float) -> None:
        """Draw progress bar at bottom of screen"""
        try:
            bar_height = 8
            bar_y = height - bar_height
            bar_width = width

            # Background (darker)
            bg_rect = pygame.Rect(0, bar_y, bar_width, bar_height)
            pygame.draw.rect(window, (40, 40, 60), bg_rect)

            # Progress fill (blue)
            if progress_percent > 0:
                fill_width = int(bar_width * progress_percent)
                fill_rect = pygame.Rect(0, bar_y, fill_width, bar_height)
                pygame.draw.rect(window, (80, 120, 200), fill_rect)
        except Exception:
            pass

    def _draw_step_info(
        self,
        window: pygame.Surface,
        width: int,
        height: int,
        step_type: ExperimentStepType
    ) -> None:
        """Draw current experiment step information"""
        try:
            # Title showing current phase
            title_font = pygame.font.SysFont('Arial', 48, bold=True)

            # Map step types to display text and colors
            step_colors = {
                ExperimentStepType.FIXATION: ((200, 200, 200), "FIXATION"),
                ExperimentStepType.REST: ((150, 150, 200), "REST"),
                ExperimentStepType.DOUBLE_BLINK: ((100, 200, 255), "DOUBLE BLINK"),
                ExperimentStepType.LEFT_HAND: ((255, 150, 150), "LEFT HAND CLENCH"),
                ExperimentStepType.RIGHT_HAND: ((150, 255, 150), "RIGHT HAND CLENCH"),
                ExperimentStepType.JAW_CLENCH: ((255, 200, 100), "JAW CLENCH"),
                ExperimentStepType.HEAD_MOVEMENT: ((200, 150, 255), "HEAD MOVEMENT"),
                ExperimentStepType.SSVEP_FOCUS: ((255, 255, 150), "SSVEP FOCUS"),
            }

            color, text = step_colors.get(step_type, ((255, 255, 255), step_type.value.upper()))

            title_surface = title_font.render(text, True, color)
            title_x = (width - title_surface.get_width()) // 2
            title_y = height * 0.4
            window.blit(title_surface, (title_x, title_y))

            # Show ESC hint
            hint_font = pygame.font.SysFont('Arial', 18)
            hint_surface = hint_font.render("Press ESC to abort experiment", True, (150, 150, 150))
            hint_x = (width - hint_surface.get_width()) // 2
            hint_y = height * 0.92
            window.blit(hint_surface, (hint_x, hint_y))

        except Exception:
            pass

    def process_events(self, events: list) -> list[ExperimentEvent]:
        """Process events for experiment view"""
        experiment_events = []

        for event in events:
            # Button clicks
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check fullscreen button
                if self.fullscreen_btn_rect and self.fullscreen_btn_rect.collidepoint(event.pos):
                    experiment_events.append(ExperimentEvent.TOGGLE_FULLSCREEN)
                # Check frameless button
                elif self.frameless_btn_rect and self.frameless_btn_rect.collidepoint(event.pos):
                    experiment_events.append(ExperimentEvent.TOGGLE_FRAME)

            # Abort experiment (ESC key)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                experiment_events.append(ExperimentEvent.ABORT)

            # Quit application
            elif event.type == pygame.QUIT:
                experiment_events.append(ExperimentEvent.QUIT)

        return experiment_events
