import pygame
from typing import Callable, Optional, Tuple

class Button:
    def __init__(self, 
        rect: pygame.Rect, text: str, 
        callback: Callable[[], None],
        base_color: Tuple[int, int, int, int] = (40, 120, 220, 255),
        hover_color: Tuple[int, int, int, int] = (60, 150, 240, 255),
        text_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> None:
        self.rect = rect
        self.text = text
        self.callback = callback
        self.base_color = base_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.hover = False

    def draw(self, 
        surface: pygame.Surface, 
        font: Optional[pygame.font.Font]
    ) -> None:
        color = self.hover_color if self.hover else self.base_color

        # Create a transparent surface for the button
        button_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        
        # Draw button with transparency
        pygame.draw.rect(button_surface, color, button_surface.get_rect(), border_radius=12)
        
        # Blit the button surface
        surface.blit(button_surface, self.rect.topleft)

        # Text
        try:
            if font is None:
                font = pygame.font.SysFont('Arial', 22)
            text_surf = font.render(self.text, True, self.text_color)
            tx = self.rect.x + (self.rect.width - text_surf.get_width()) // 2
            ty = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
            surface.blit(text_surf, (tx, ty))
        except Exception:
            # In headless/test envs font rendering might fail; silently skip
            pass
