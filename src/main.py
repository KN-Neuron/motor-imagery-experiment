import sys


def _suppress_qt_warnings(msg_type, context, message):
    """Filter out noisy Qt warnings."""
    if "QFont::setPointSize" in message:
        return


def main() -> None:
    # IMPORTANT (Windows + multiprocessing spawn): keep PyQt imports inside main().
    # Child processes created via spawn will import this module, and importing PyQt
    # in the worker process can trigger the BrainAccess native crash.
    from PyQt6.QtWidgets import QApplication, QDialog
    from PyQt6.QtCore import qInstallMessageHandler

    qInstallMessageHandler(_suppress_qt_warnings)

    from src.gui import GUIManager
    from src.gui.dialogs import HeadsetSelectionDialog
    from src.flow_controller import FlowController

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
