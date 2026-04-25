from PyQt6.QtWidgets import QApplication
import sys

from src.gui import GUIManager
from src.eeg_headset.headset_config import HeadsetConfig, HeadsetModel
from src.eeg_headset.eeg_headset import EEGHeadset
# from src.eeg_headset.drivers import MockDriver
from src.eeg_headset.drivers import MockDriver, BrainAccessDriver
from src.flow_controller import FlowController


def main() -> None:
    app = QApplication(sys.argv) # QApplication is saved as variable to prevent garbage collection clearing it out
    gui_manager = GUIManager()
    
    driver_config = HeadsetConfig(
        model=HeadsetModel.HALO_4CH, 
        config_path="brainaccess.config.yaml")
    driver = MockDriver(config=driver_config)
    # driver = BrainAccessDriver(config=driver_config)
    headset = EEGHeadset(driver)

    flow_controller = FlowController(gui_manager, headset)
    flow_controller.start()

if __name__ == "__main__":
    main()
