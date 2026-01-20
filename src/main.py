import sys

from src.data_manager import DataManager
from src.egg_headset import EggHeadset
from src.gui import GUIManager
from src.flow_controller import FlowController


def main() -> None:
    gui_manager = GUIManager()
    headset = EggHeadset()
    data_manager = DataManager()

    flow_controller = FlowController(gui_manager, headset, data_manager)
    flow_controller.start()

if __name__ == "__main__":
    main()
