import dataclasses
import time
from datetime import datetime
from pathlib import Path
from typing import Any, override

import numpy as np

from src.feedback.feedback import Classifier, make_classifier
from src.flow_controller.step_timer import StepTimer
from src.gui.views.session_view import SessionEvent
from src.gui.views.ssvep import refresh_warning
from src.sample_manager.experiment_step_type import ExperimentStepType as T
from src.sample_manager.sample_manager import (
    ExperimentStep,
    SampleManager,
    resolve_classes,
)
from src.session_metadata import tables
from src.session_metadata.environment import app_version, system_info
from src.session_metadata.participant import ParticipantInfo
from src.session_saver.session_saver import SessionSaver
from src.trials_config.trials_config import SessionConfig

from . import FlowState


class SessionState(FlowState):
    """Shared logic of experiment and calibration sessions.

    Runs the block/step queue from SampleManager with a pause-aware step timer,
    writes markers (with block/trial/condition metadata) through SessionSaver,
    optionally shows classifier feedback, and writes participant/session tables.
    """

    kind = "experiment"  # task label, log prefix and GUIManager method suffix
    output_root = Path("sessions/experiments")
    result_ms = 2000

    def __init__(self, flow_controller: Any) -> None:
        super().__init__(flow_controller)
        self.sample_manager: SampleManager | None = None
        self.current_step: ExperimentStep | None = None
        self.timer = StepTimer()
        self.no_eeg_mode = False
        self.is_paused = False
        self.total_steps = 0
        self.completed_steps = 0
        self.session_saver: SessionSaver | None = None
        self.config: SessionConfig | None = None
        self.classifier: Classifier | None = None
        self.classified_as: T | None = None
        self.completed = False

        self._ready = False
        self._in_result_phase = False
        self._token = 0
        self._marker_idx: int | None = None
        self._token_markers: dict[int, int] = {}
        self._planned_end_ns: int | None = None
        self._pause_started_ns = 0

    # --- hooks for subclasses ---------------------------------------------

    def _show_config(self) -> SessionConfig | None:
        raise NotImplementedError

    def _show_view(self) -> None:
        getattr(self.gui_manager, f"show_{self.kind}")()

    def _get_events(self) -> list[SessionEvent]:
        events: list[SessionEvent] = getattr(
            self.gui_manager, f"get_{self.kind}_events"
        )()
        return events

    def _update_gui(self) -> None:
        progress = self.completed_steps / self.total_steps if self.total_steps else 0.0
        getattr(self.gui_manager, f"update_{self.kind}")(
            self.current_step,
            self.classified_as,
            self.no_eeg_mode,
            self.is_paused,
            progress,
            self.config.feedback if self.config else "none",
            self._token,
        )

    # --- lifecycle --------------------------------------------------------

    @override
    def enter(self, **kwargs: Any) -> None:
        self.no_eeg_mode = kwargs.get("no_eeg_mode", False)

        config = self._show_config()
        if config is None:
            return self._to_menu()
        self.config = config

        participant: ParticipantInfo | None = None
        if not self.no_eeg_mode:
            participant = self.gui_manager.show_participant_dialog(self.output_root)
            if participant is None:
                return self._to_menu()

        if not self._setup_session(config, participant):
            return self._to_menu()

        self._begin()

    def _to_menu(self) -> None:
        from .main_menu_state import MainMenuState

        self.flow_controller.change_state(MainMenuState)

    @override
    def tick(self) -> None:
        if not self._ready:
            return
        if self._handle_disconnect():
            return

        if self.current_step is None:
            print(f"[{self.kind}] Session completed!")
            self.completed = True
            self._to_menu()
            return

        self._update_gui()
        self._log_display_time()

        if self._handle_events():
            return
        if self.is_paused or self.current_step is None:
            return
        self._progress()

    def _handle_disconnect(self) -> bool:
        """If running with EEG and headset went away, mark it and bail to menu."""
        if self.no_eeg_mode or self.flow_controller.headset_connected:
            return False

        print(f"[{self.kind}] EEG headset disconnected — aborting session")
        if self.session_saver is not None:
            self.session_saver.add_marker("DISCONNECTED")
        self._to_menu()
        return True

    @override
    def exit(self) -> None:
        self._ready = False
        self._teardown_session()

        self.sample_manager = None
        self.current_step = None
        self.total_steps = 0
        self.completed_steps = 0
        self.session_saver = None
        self.no_eeg_mode = False
        self.is_paused = False
        self.classified_as = None
        self._in_result_phase = False
        print(f"[{self.kind}] State exited")

    # --- setup ------------------------------------------------------------

    def _setup_session(
        self, config: SessionConfig, participant: ParticipantInfo | None
    ) -> bool:
        try:
            self.sample_manager = SampleManager(config)
            classes = resolve_classes(config)[0]
            self.classifier = make_classifier(config.feedback, classes)
        except (ValueError, NotImplementedError) as e:
            print(f"[{self.kind}] Cannot start: {e}")
            return False

        self.total_steps = len(self.sample_manager.step_queue)
        self.completed_steps = 0
        self.is_paused = False
        self.classified_as = None
        self._in_result_phase = False

        ssvep_warning = self._check_ssvep(config)

        if self.no_eeg_mode:
            return True
        assert participant is not None
        return self._setup_headset(config, participant, ssvep_warning)

    def _check_ssvep(self, config: SessionConfig) -> str | None:
        _, ssvep, _ = resolve_classes(config)
        if not ssvep or config.ssvep_trials <= 0:
            return None
        self.gui_manager.set_ssvep_frequency(config.ssvep_frequency_hz)
        warning = refresh_warning(
            self.gui_manager.refresh_rate_hz(), config.ssvep_frequency_hz
        )
        if warning:
            print(f"[{self.kind}] SSVEP WARNING: {warning}")
        return warning

    def _setup_headset(
        self,
        config: SessionConfig,
        participant: ParticipantInfo,
        ssvep_warning: str | None,
    ) -> bool:
        assert self.sample_manager is not None
        headset = self.eeg_headset
        try:
            headset.start()
        except Exception as e:
            print(f"[{self.kind}] Error starting EEG headset: {e}")
            return False

        quality = self.gui_manager.show_quality_dialog(
            headset, config.quality, config.qc_duration_s
        )
        if quality is None:
            print(f"[{self.kind}] Signal quality check cancelled")
            return False

        try:
            self.session_saver = SessionSaver(
                channel_labels=headset.channel_labels,
                sample_rate=headset.sample_rate,
                output_dir=self.output_root,
                session_name=participant.session_path,
                feedback_mode=config.feedback,
            )
            self.session_saver.start_session()
        except (OSError, ValueError) as e:
            print(f"[{self.kind}] Cannot create session files: {e}")
            self.session_saver = None
            return False

        saver = self.session_saver
        np.save(saver.session_dir / "qc_rest.npy", quality.rest_data)
        saver.set_metadata(
            self._metadata(config, participant, quality.to_metadata(), ssvep_warning)
        )
        tables.update_tables(
            self.output_root,
            participant,
            self.kind,
            config.feedback,
            datetime.now().isoformat(timespec="seconds"),
        )
        headset.add_subscriber(saver.on_chunk)
        headset.add_gap_subscriber(saver.on_gap)
        return True

    def _metadata(
        self,
        config: SessionConfig,
        participant: ParticipantInfo,
        quality: dict[str, object],
        ssvep_warning: str | None,
    ) -> dict[str, Any]:
        assert self.sample_manager is not None
        headset_config = self.eeg_headset.config
        model = getattr(headset_config, "model", None)
        return {
            "task": self.kind,
            "app": app_version(),
            "system": system_info(self.gui_manager.refresh_rate_hz()),
            "headset": {
                "model": getattr(model, "value", None),
                "device_name": getattr(headset_config, "device_name", None),
                "channel_map": {
                    str(k): v for k, v in headset_config.channel_map.items()
                },
            },
            "participant": dataclasses.asdict(participant),
            "randomisation": self.sample_manager.describe(),
            "trial_config": dataclasses.asdict(config),
            "feedback_mode": config.feedback,
            "quality_check": quality,
            "ssvep": {
                "frequency_hz": config.ssvep_frequency_hz,
                "refresh_warning": ssvep_warning,
                "validated": False,
            },
        }

    def _begin(self) -> None:
        assert self.sample_manager is not None
        self._show_view()
        if self.session_saver is not None:
            self.session_saver.add_marker(f"{self.kind}_start")
        self._start_step(self.sample_manager.get_next())
        self._ready = True

    # --- step handling ----------------------------------------------------

    def _step_meta(self, step: ExperimentStep) -> dict[str, Any]:
        return {
            "block_id": step.block_id,
            "trial_id": step.trial_id,
            "condition": step.condition,
            "practice": step.practice,
        }

    def _start_step(self, step: ExperimentStep | None) -> None:
        self.current_step = step
        self.timer.restart()
        self.classified_as = None
        self._in_result_phase = False
        if step is None:
            return

        planned_start = self._planned_end_ns
        self._planned_end_ns = (
            None
            if step.wait_for_key
            else self.timer.start_ns + int(step.duration_ms * 1e6)
        )
        self._token += 1
        if self.session_saver is not None:
            self._marker_idx = self.session_saver.add_marker(
                step.marker,
                planned_duration=None if step.wait_for_key else step.duration_ms / 1e3,
                planned_start_ns=planned_start,
                **self._step_meta(step),
            )
            self._token_markers[self._token] = self._marker_idx

    def _finish_marker(self) -> None:
        if self.session_saver is not None and self._marker_idx is not None:
            self.session_saver.finish_marker(
                self._marker_idx, self.timer.wall_elapsed_s(), self.timer.was_paused
            )

    def _advance(self) -> None:
        assert self.sample_manager is not None
        self._finish_marker()
        self.completed_steps += 1
        self._start_step(self.sample_manager.get_next())

    def _progress(self) -> None:
        step = self.current_step
        assert step is not None
        if step.wait_for_key:
            return
        limit = self.result_ms if self._in_result_phase else step.duration_ms
        if self.timer.elapsed_ms() < limit:
            return
        if self._in_result_phase or not self._start_feedback(step):
            self._advance()

    def _start_feedback(self, step: ExperimentStep) -> bool:
        """Show the classifier's answer after a trial. False if no feedback."""
        if self.classifier is None or not step.is_feedback_class:
            return False
        self.classified_as = self.classifier.predict(self._recent_eeg())
        self._finish_marker()
        self.timer.restart()
        self._in_result_phase = True
        if self.session_saver is not None:
            self._marker_idx = self.session_saver.add_marker(
                f"RESULT_{self.classified_as.value.upper()}",
                planned_duration=self.result_ms / 1e3,
                **self._step_meta(step),
            )
        print(f"[{self.kind}] Feedback ({self.config and self.config.feedback})")
        return True

    def _recent_eeg(self) -> np.ndarray:
        if self.no_eeg_mode or self.config is None:
            return np.empty((0, 0))
        n = int(self.eeg_headset.sample_rate * self.config.task_ms / 1e3)
        recent: np.ndarray = self.eeg_headset.get_last(n)
        return recent

    # --- events -----------------------------------------------------------

    def _handle_events(self) -> bool:
        for event in self._get_events():
            if event == SessionEvent.ABORT:
                print(f"[{self.kind}] Aborted by user (ESC)")
                if self.session_saver is not None:
                    self._finish_marker()
                    self._marker_idx = None
                    self.session_saver.add_marker("ABORTED")
                self._to_menu()
                return True
            if event == SessionEvent.PAUSE:
                self._handle_pause_event()
            elif event == SessionEvent.CONTINUE:
                step = self.current_step
                if step is not None and step.wait_for_key and not self.is_paused:
                    self._advance()
        return False

    def _handle_pause_event(self) -> None:
        self.is_paused = not self.is_paused
        now = time.perf_counter_ns()
        if self.is_paused:
            self.timer.pause()
            self._pause_started_ns = now
        else:
            self.timer.resume()
            if self._planned_end_ns is not None:
                self._planned_end_ns += now - self._pause_started_ns
        if self.session_saver is not None:
            self.session_saver.add_marker("PAUSED" if self.is_paused else "RESUMED")
        print(f"[{self.kind}] {'PAUSED' if self.is_paused else 'RESUMED'}")

    def _log_display_time(self) -> None:
        paint = self.gui_manager.pop_first_paint()
        if paint is None or self.session_saver is None:
            return
        token, display_ns = paint
        idx = self._token_markers.pop(token, None)
        if idx is not None:
            self.session_saver.set_display_time(idx, display_ns)

    # --- teardown ---------------------------------------------------------

    def _teardown_session(self) -> None:
        saver = self.session_saver
        if saver is not None:
            try:
                self.eeg_headset.remove_subscriber(saver.on_chunk)
                self.eeg_headset.remove_gap_subscriber(saver.on_gap)
                self._finish_marker()
                saver.set_metadata({"session_completed": self.completed})
                saver.stop_session()
            except Exception as e:
                print(f"[{self.kind}] Error stopping session: {e}")

        if not self.no_eeg_mode and self.eeg_headset is not None:
            try:
                self.eeg_headset.stop()
            except Exception as e:
                print(f"[{self.kind}] Error stopping EEG headset: {e}")
