from src.gui.gui_manager import GUIManager
from src.gui.views.main_menu_view import MainMenuEvent

__all__ = ["GUIManager", "MainMenuEvent", "ExperimentEvent"]
class GUIManager:
    def __init__(self, width: int = 800, height: int = 600) -> None:
        self.width = width
        self.height = height

    def initialize(self) -> None:
        pass

    def handle_events(self) -> bool:
        return True

    def update(self) -> None:
        pass

    def render(self) -> None:
        pass
