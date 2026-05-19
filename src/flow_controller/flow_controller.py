from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
import sys
import time
from dataclasses import dataclass

from src.eeg_headset.eeg_headset import EEGHeadset
from .states import MainMenuState, ExperimentState, CalibrationState


@dataclass
class HeadsetStatus:
    connected: bool = False
    streaming: bool = False
    last_error: str | None = None
    updated_at_s: float = 0.0


class FlowController:
    """Manages overall application flow and state transitions."""

    def __init__(self, gui_manager) -> None:
        self.gui_manager = gui_manager
        self.eeg_headset: EEGHeadset | None = None
        self.state = None
        self.timer = QTimer()
        self.timer.start(10)  # 100 FPS
        self.timer.timeout.connect(self._tick)
        self.running = True

        self._headset_status = HeadsetStatus()
        self._last_status_check_s = 0.0
        self._last_probe_s = 0.0

    @property
    def headset_connected(self) -> bool:
        return bool(self._headset_status.connected)

    @property
    def headset_streaming(self) -> bool:
        return bool(self._headset_status.streaming)

    @property
    def headset_last_error(self) -> str | None:
        return self._headset_status.last_error

    def change_state(self, state, **kwargs):
        """Exit current state and enter the new one. kwargs are forwarded to enter()."""
        if self.state:
            self.state.exit()

        if state is MainMenuState:
            self.state = MainMenuState(self)
        elif state is ExperimentState:
            self.state = ExperimentState(self)
        elif state is CalibrationState:
            self.state = CalibrationState(self)
        else:
            raise ValueError(f"Unknown FlowController state: {state}")

        self.state.enter(**kwargs)

    def start(self):
        """Initialize GUI and run the Qt event loop. Headset is pre-connected before this call."""
        self.gui_manager.initialize()
        self.change_state(MainMenuState)

        try:
            QApplication.instance().exec()

        except Exception as e:
            print(f"[FlowController] Unhandled exception occurred: {e}")

        finally:
            self.shutdown()

    def _tick(self):
        """Called by QTimer every 10ms."""
        if not self.running:
            self.timer.stop()
            QApplication.instance().quit()
            return

        self._refresh_headset_status()

        if self._headset_status.connected and self._headset_status.streaming:
            try:
                self.eeg_headset.poll()
            except Exception as e:
                # Poll can fail mid-stream; let session states handle disconnect logic.
                print(f"[FlowController] EEG poll failed: {e}")
                self._headset_status.connected = False
                self._headset_status.streaming = False
                self._headset_status.last_error = str(e)
                self._headset_status.updated_at_s = time.monotonic()

        self.state.tick()

    def _refresh_headset_status(self) -> None:
        """Update cached headset status with throttling.

        This is the only place that should call into the driver for status checks.
        """

        now = time.monotonic()
        if (now - self._last_status_check_s) < 0.25:
            return

        self._last_status_check_s = now

        connected = False
        streaming = False
        last_error: str | None = None

        if self.eeg_headset is not None:
            try:
                connected = bool(self.eeg_headset.is_connected())
                streaming = bool(self.eeg_headset.is_streaming()) if connected else False
            except Exception as e:
                # Treat failures (IPC worker crash/timeout) as a disconnect.
                last_error = str(e)
                connected = False
                streaming = False

        # Optional probe: some SDKs only notice a physical disconnect after a real call.
        # Do this only in MainMenu (idle), infrequently.
        if connected and not streaming and (now - self._last_probe_s) >= 5.0:
            if isinstance(self.state, MainMenuState):
                self._last_probe_s = now
                try:
                    self.eeg_headset.start()
                    self.eeg_headset.stop()
                except Exception as e:
                    last_error = str(e)
                    connected = False
                    streaming = False

        if last_error is not None:
            print(f"[FlowController] EEG status check failed: {last_error}")

        self._headset_status.connected = connected
        self._headset_status.streaming = streaming
        self._headset_status.last_error = last_error
        self._headset_status.updated_at_s = now

    def shutdown(self):
        """Disconnect headset and exit the process."""
        if self.eeg_headset is not None:
            try:
                # Prefer cached status to avoid extra IPC/RPC calls during shutdown.
                if self.headset_connected or self.eeg_headset.is_connected():
                    self.eeg_headset.disconnect()
            except Exception as e:
                print(f"[FlowController] Error during headset disconnect: {e}")

        sys.exit(0)
