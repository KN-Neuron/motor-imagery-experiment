from PyQt6.QtWidgets import QApplication
import sys

from src.gui import GUIManager
from src.flow_controller import FlowController


def main() -> None:
    app = QApplication(sys.argv)  # saved as variable to prevent GC

    gui_manager = GUIManager()
    flow_controller = FlowController(gui_manager)
    flow_controller.start()


if __name__ == "__main__":
    main()
