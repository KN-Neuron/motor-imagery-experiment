from PyQt6.QtWidgets import QApplication
import sys

from src.gui import GUIManager
from src.egg_headset import EggHeadset
from src.flow_controller import FlowController


def main() -> None:
    app = QApplication(sys.argv)
    
    gui_manager = GUIManager()
    headset = EggHeadset()

    flow_controller = FlowController(gui_manager, headset)
    flow_controller.start()


if __name__ == "__main__":
    main()
