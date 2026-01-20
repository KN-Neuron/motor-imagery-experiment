from enum import Enum
import pygame
from ..shared.button import Button


class MainMenuEvent(Enum):
    TOGGLE_FULLSCREEN = "toggle_fullscreen"
    TOGGLE_FRAME = "toggle_frame"
    EXPERIMENT_BTN_CLICKED = "experiment_btn_clicked"
    CALIBRATION_BTN_CLICKED = "calibration_btn_clicked"
    QUIT = "quit"


class MainMenuView:
    def __init__(self) -> None:
        self.experiment_btn: Button = None
        self.calibration_btn: Button = None
        self.fullscreen_btn_rect: pygame.Rect = None
        self.frameless_btn_rect: pygame.Rect = None

    def render(
        self,
        window: pygame.Surface,
        width: int,
        height: int,
        is_fullscreen: bool,
        is_frameless: bool = False,
        headset_connected: bool = False
    ) -> None:
        """Render the main menu view"""
        # window.fill((30, 30, 40))  # Dark background
        try:
            btn_width = 50
            btn_height = 35
            btn_margin = 10
            btn_spacing = 5

            # Fullscreen toggle button
            self.fullscreen_btn_rect = pygame.Rect(btn_margin, btn_margin, btn_width, btn_height)

            # Draw button background
            btn_surface = pygame.Surface((btn_width, btn_height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surface, (60, 60, 80, 180), btn_surface.get_rect(), border_radius=8)
            window.blit(btn_surface, self.fullscreen_btn_rect.topleft)

            # Draw text label (FS = fullscreen, WIN = windowed)
            icon_font = pygame.font.SysFont('Arial', 14, bold=True)
            icon_text = "FS" if not is_fullscreen else "WIN"
            icon_surface = icon_font.render(icon_text, True, (255, 255, 255))
            icon_x = btn_margin + (btn_width - icon_surface.get_width()) // 2
            icon_y = btn_margin + (btn_height - icon_surface.get_height()) // 2
            window.blit(icon_surface, (icon_x, icon_y))

            # Frameless toggle button (positioned to the right of fullscreen button)
            self.frameless_btn_rect = pygame.Rect(
                btn_margin + btn_width + btn_spacing,
                btn_margin,
                btn_width,
                btn_height
            )

            # Draw button background
            btn_surface2 = pygame.Surface((btn_width, btn_height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surface2, (60, 60, 80, 180), btn_surface2.get_rect(), border_radius=8)
            window.blit(btn_surface2, self.frameless_btn_rect.topleft)

            # Draw text label (NF = no frame, FR = frame)
            icon_text2 = "NF" if not is_frameless else "FR"
            icon_surface2 = icon_font.render(icon_text2, True, (255, 255, 255))
            icon_x2 = self.frameless_btn_rect.x + (btn_width - icon_surface2.get_width()) // 2
            icon_y2 = self.frameless_btn_rect.y + (btn_height - icon_surface2.get_height()) // 2
            window.blit(icon_surface2, (icon_x2, icon_y2))
        except Exception:
            pass

        # Draw title - centered
        try:
            title_font = pygame.font.SysFont('Arial', 56, bold=True)
            title_text = title_font.render("Hex-O-Spell Experiment", True, (255, 255, 255))
            title_x = (width - title_text.get_width()) // 2
            title_y = height * 0.1  # 10% from top
            window.blit(title_text, (title_x, title_y))
        except Exception:
            pass

        # Draw KN NEURON logo and text - centered
        try:
            import os
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'imgs', 'kn_neuron_logo.png')
            logo_img = pygame.image.load(logo_path)
            # Scale logo to appropriate size (e.g., 40x40)
            logo_img = pygame.transform.scale(logo_img, (40, 40))

            kn_font = pygame.font.SysFont('Arial', 24, bold=True)
            kn_text = kn_font.render("KN NEURON", True, (200, 200, 200))

            # Calculate total width and center
            total_width = logo_img.get_width() + 10 + kn_text.get_width()
            logo_x = (width - total_width) // 2
            logo_y = height * 0.21  # 21% from top

            window.blit(logo_img, (logo_x, logo_y))
            window.blit(kn_text, (logo_x + logo_img.get_width() + 10, logo_y + 8))
        except Exception:
            pass

        # Display headset status - centered
        try:
            status_font = pygame.font.SysFont('Arial', 28)
            status_text_1 = status_font.render("Headset: ", True, (255, 255, 255))
            status_color = (50, 200, 50) if headset_connected else (220, 50, 50)
            status_text_2 = status_font.render(
                "Connected" if headset_connected else "Disconnected",
                True,
                status_color
            )
            # Calculate total width and center
            total_status_width = status_text_1.get_width() + status_text_2.get_width()
            status_x = (width - total_status_width) // 2
            status_y = height * 0.29  # 29% from top

            window.blit(status_text_1, (status_x, status_y))
            window.blit(status_text_2, (status_x + status_text_1.get_width(), status_y))
        except Exception:
            pass

        # Modern, smaller, transparent buttons - centered
        btn_w, btn_h = 200, 50
        spacing = 20
        btn_x = (width - btn_w) // 2  # Center horizontally
        btn_y = height * 0.5  # 50% from top

        rect1 = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        rect2 = pygame.Rect(btn_x, btn_y + btn_h + spacing, btn_w, btn_h)

        # Create modern transparent buttons
        self.experiment_btn = Button(
            rect1, "Start Experiment", lambda: None,
            base_color=(60, 60, 80, 180),
            hover_color=(80, 80, 120, 200)
        )
        self.calibration_btn = Button(
            rect2, "Start Calibration", lambda: None,
            base_color=(60, 60, 80, 180),
            hover_color=(80, 80, 120, 200)
        )

        # Draw the buttons
        try:
            font = pygame.font.SysFont('Arial', 22)
        except Exception:
            font = None

        self.experiment_btn.draw(window, font)
        self.calibration_btn.draw(window, font)

    def process_events(self, events: list) -> list[MainMenuEvent]:
        """Process events for main menu"""
        menu_events = []

        for event in events:
            # Button clicks
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Get keyboard modifiers
                keys = pygame.key.get_mods()
                alt_pressed = keys & pygame.KMOD_ALT

                # Check fullscreen button
                if self.fullscreen_btn_rect and self.fullscreen_btn_rect.collidepoint(event.pos):
                    menu_events.append(MainMenuEvent.TOGGLE_FULLSCREEN)
                # Check frameless button
                elif self.frameless_btn_rect and self.frameless_btn_rect.collidepoint(event.pos):
                    menu_events.append(MainMenuEvent.TOGGLE_FRAME)
                # Check experiment (returns tuple with alt state)
                elif self.experiment_btn and self.experiment_btn.rect.collidepoint(event.pos):
                    menu_events.append((MainMenuEvent.EXPERIMENT_BTN_CLICKED, alt_pressed))
                # Check calibration
                elif self.calibration_btn and self.calibration_btn.rect.collidepoint(event.pos):
                    menu_events.append(MainMenuEvent.CALIBRATION_BTN_CLICKED)

            # Quit application
            elif event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                menu_events.append(MainMenuEvent.QUIT)

        return menu_events
