from enum import Enum
import pygame
from .main_menu.button import Button

# Possible main menu events
class MainMenuEvent(Enum):
    EXPERIMENT_BTN_CLICKED = "experiment_btn_clicked"
    CALIBRATION_BTN_CLICKED = "calibration_btn_clicked"
    QUIT = "quit"

# GUI manager for handling GUI rendering and events
class GUIManager:
    def __init__(self, width: int = 1200, height: int = 800) -> None:
        self.width = width
        self.height = height
        self.min_width = width  # Minimum window width
        self.min_height = height  # Minimum window height
        self.default_width = width  # Default windowed width
        self.default_height = height  # Default windowed height
        self.is_fullscreen = False
        self.main_menu_btns: dict[str, Button] = {}
        self.fullscreen_btn_rect = None

    # Initialize the GUI system
    def initialize(self) -> None:
        # Initialize pygame and create the main window with RESIZABLE flag
        pygame.init()
        self.window = pygame.display.set_mode(
            (self.width, self.height), 
            pygame.RESIZABLE
        )
        pygame.display.set_caption("Hex-O-Spell Experiment")
    
    # Toggle fullscreen mode
    def toggle_fullscreen(self) -> None:
        if self.is_fullscreen:
            # Exit fullscreen - return to default size
            self.is_fullscreen = False
            self.width = self.default_width
            self.height = self.default_height
            self.window = pygame.display.set_mode(
                (self.width, self.height),
                pygame.RESIZABLE
            )
        else:
            # Enter fullscreen
            self.is_fullscreen = True
            self.window = pygame.display.set_mode(
                (0, 0),  # Use native resolution
                pygame.FULLSCREEN
            )
            # Update dimensions to fullscreen size
            self.width = self.window.get_width()
            self.height = self.window.get_height()

    # Display the main menu
    def display_main_menu(self, headset_connected: bool = False) -> None:
        # Draw fullscreen toggle button in top-left corner
        try:
            fs_btn_width = 50
            fs_btn_height = 35
            fs_btn_margin = 10
            self.fullscreen_btn_rect = pygame.Rect(fs_btn_margin, fs_btn_margin, fs_btn_width, fs_btn_height)
            
            # Draw button background
            btn_surface = pygame.Surface((fs_btn_width, fs_btn_height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surface, (60, 60, 80, 180), btn_surface.get_rect(), border_radius=8)
            self.window.blit(btn_surface, self.fullscreen_btn_rect.topleft)
            
            # Draw text label (FS = fullscreen, WIN = windowed)
            icon_font = pygame.font.SysFont('Arial', 14, bold=True)
            icon_text = "FS" if not self.is_fullscreen else "WIN"
            icon_surface = icon_font.render(icon_text, True, (255, 255, 255))
            icon_x = fs_btn_margin + (fs_btn_width - icon_surface.get_width()) // 2
            icon_y = fs_btn_margin + (fs_btn_height - icon_surface.get_height()) // 2
            self.window.blit(icon_surface, (icon_x, icon_y))
        except Exception:
            pass
        
        # Draw title - centered
        try:
            title_font = pygame.font.SysFont('Arial', 56, bold=True)
            title_text = title_font.render("Hex-O-Spell Experiment", True, (255, 255, 255))
            title_x = (self.width - title_text.get_width()) // 2
            title_y = self.height * 0.1  # 10% from top
            self.window.blit(title_text, (title_x, title_y))
        except Exception:
            pass
        
        # Draw KN NEURON logo and text - centered
        try:
            import os
            logo_path = os.path.join(os.path.dirname(__file__), 'imgs', 'kn_neuron_logo.png')
            logo_img = pygame.image.load(logo_path)
            # Scale logo to appropriate size (e.g., 40x40)
            logo_img = pygame.transform.scale(logo_img, (40, 40))
            
            kn_font = pygame.font.SysFont('Arial', 24, bold=True)
            kn_text = kn_font.render("KN NEURON", True, (200, 200, 200))
            
            # Calculate total width and center
            total_width = logo_img.get_width() + 10 + kn_text.get_width()
            logo_x = (self.width - total_width) // 2
            logo_y = self.height * 0.21  # 21% from top
            
            self.window.blit(logo_img, (logo_x, logo_y))
            self.window.blit(kn_text, (logo_x + logo_img.get_width() + 10, logo_y + 8))
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
            status_x = (self.width - total_status_width) // 2
            status_y = self.height * 0.29  # 29% from top
            
            self.window.blit(status_text_1, (status_x, status_y))
            self.window.blit(status_text_2, (status_x + status_text_1.get_width(), status_y))
        except Exception:
            pass
        
        # Modern, smaller, transparent buttons - centered
        btn_w, btn_h = 200, 50
        spacing = 20
        btn_x = (self.width - btn_w) // 2  # Center horizontally
        btn_y = self.height * 0.5  # 50% from top

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

        self.experiment_btn.draw(self.window, font)
        self.calibration_btn.draw(self.window, font)

    # Handle events in the main menu
    def handle_main_menu_events(self) -> str:
        # Handle events in the main menu
        for event in pygame.event.get():
            # Handle window resize
            if event.type == pygame.VIDEORESIZE:
                # Only handle resize if not in fullscreen
                if not self.is_fullscreen:
                    # Enforce minimum window size
                    new_width = max(event.w, self.min_width)
                    new_height = max(event.h, self.min_height)
                    self.width = new_width
                    self.height = new_height
                    self.window = pygame.display.set_mode(
                        (new_width, new_height), 
                        pygame.RESIZABLE
                    )
            
            # Button clicks
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check fullscreen button first
                if self.fullscreen_btn_rect and self.fullscreen_btn_rect.collidepoint(event.pos):
                    self.toggle_fullscreen()
                    return None  # Don't process other buttons during mode change
                
                # Check menu buttons
                if self.experiment_btn.rect.collidepoint(event.pos):
                    return MainMenuEvent.EXPERIMENT_BTN_CLICKED
                
                elif self.calibration_btn.rect.collidepoint(event.pos):
                    return MainMenuEvent.CALIBRATION_BTN_CLICKED
                    
            # Quit application
            elif event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                return MainMenuEvent.QUIT
            
        return None # No relevant event
            
    # Render the current GUI state using the provided display function
    def render(self, display_function, *args, **kwargs) -> None:
        self.window.fill((15, 15, 25))  # Fill with dark blue-gray background
        display_function(*args, **kwargs) # Call the provided display function to draw GUI elements
        pygame.display.flip() # Update the full display surface to the screen
