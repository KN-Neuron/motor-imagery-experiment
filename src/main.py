from PyQt6.QtWidgets import QApplication, QDialog
import sys

from src.gui import GUIManager
from src.gui.dialogs import HeadsetSelectionDialog
from src.flow_controller import FlowController


def main() -> None:
    app = QApplication(sys.argv)  # saved as variable to prevent GC

    dialog = HeadsetSelectionDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    headset = dialog.get_headset()

    gui_manager = GUIManager()
    flow_controller = FlowController(gui_manager)
    flow_controller.eeg_headset = headset
    flow_controller.start()


if __name__ == "__main__":
    main()
