from PyQt6.QtWidgets import QApplication
import sys

from src.gui import GUIManager
from src.eeg_headset.eeg_headset import EEGHeadset
from src.eeg_headset.drivers import MockDriver
from src.flow_controller import FlowController


def main() -> None:
    app = QApplication(sys.argv) # QApplication is saved as variable to prevent garbage collection clearing it out

    gui_manager = GUIManager()
    
    driver = MockDriver()
    headset = EEGHeadset(driver)

    flow_controller = FlowController(gui_manager, headset)
    flow_controller.start()

if __name__ == "__main__":
    main()
