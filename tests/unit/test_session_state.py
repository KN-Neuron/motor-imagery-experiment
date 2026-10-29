"""Session flow without hardware: MOCK driver, fake GUI, fake clock."""

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from src.eeg_headset.drivers import MockDriver
from src.eeg_headset.eeg_headset import EEGHeadset
from src.eeg_headset.headset_config import HeadsetConfig
from src.feedback.feedback import make_classifier
from src.flow_controller.states import ExperimentState
from src.flow_controller.states.calibration_state import CalibrationState
from src.flow_controller.states.session_state import SessionState
from src.flow_controller.step_timer import StepTimer
from src.gui.dialogs.quality_dialog import QualityResult
from src.gui.views.session_view import SessionEvent
from src.sample_manager.experiment_step_type import ExperimentStepType as T
from src.session_metadata.participant import ParticipantInfo
from src.signal_quality.quality import assess_channels
from src.trials_config.trials_config import (
    CalibrationConfig,
    ExperimentConfig,
    SessionConfig,
)

FS = 100


class FakeClock:
    def __init__(self) -> None:
        self.ns = 0

    def advance_ms(self, ms: float) -> None:
        self.ns += int(ms * 1e6)

    def __call__(self) -> int:
        return self.ns


class FakeGui:
    def __init__(self, config: SessionConfig, headset: EEGHeadset) -> None:
        self.config = config
        self.headset = headset
        self.events: list[SessionEvent] = []
        self.updates: list[tuple[Any, ...]] = []

    def show_experiment_config_dialog(self) -> SessionConfig:
        return self.config

    show_calibration_config_dialog = show_experiment_config_dialog

    def show_participant_dialog(self, root: Path) -> ParticipantInfo:
        return ParticipantInfo(
            code="sub-001", consent_given=True, consent_date="2026-01-31", age="20-25"
        )

    def show_quality_dialog(self, headset: Any, th: Any, secs: float) -> QualityResult:
        data = np.random.default_rng(0).normal(0, 20, (2, 2 * FS))
        chans = assess_channels(data, FS, headset.channel_labels, th)
        return QualityResult(chans, False, data)

    def show_experiment(self) -> None:
        pass

    show_calibration = show_experiment

    def get_experiment_events(self) -> list[SessionEvent]:
        events, self.events = self.events, []
        return events

    get_calibration_events = get_experiment_events

    def update_experiment(self, *args: Any) -> None:
        self.updates.append(args)

    update_calibration = update_experiment

    def pop_first_paint(self) -> None:
        return None

    def refresh_rate_hz(self) -> float:
        return 60.0

    def set_ssvep_frequency(self, freq: float) -> None:
        pass


class FakeFlow:
    def __init__(self, gui: FakeGui) -> None:
        self.gui_manager = gui
        self.eeg_headset = gui.headset
        self.headset_connected = True
        self.changed_to: Any = None

    def change_state(self, state: Any, **kw: Any) -> None:
        self.changed_to = state


def small_config(**kw: Any) -> SessionConfig:
    base: dict[str, Any] = dict(
        n_blocks=1,
        trials_per_class_per_block=2,
        practice_trials_per_class=0,
        fixation_ms=100,
        cue_ms=100,
        task_ms=200,
        iti_min_ms=100,
        iti_max_ms=100,
        rest_eyes_open_ms=0,
        artifact_cues=[],
        seed=5,
    )
    base.update(kw)
    return SessionConfig(**base)


@pytest.fixture
def make_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    def build(
        cls: type[SessionState] = ExperimentState, config: SessionConfig | None = None
    ) -> tuple[SessionState, FakeGui, FakeClock]:
        monkeypatch.setattr(cls, "output_root", tmp_path)
        driver = MockDriver(config=HeadsetConfig.mock(2, FS))
        headset = EEGHeadset(driver)
        headset.connect()
        cfg = config or small_config()
        if cls is CalibrationState:
            cfg = CalibrationConfig(**vars(cfg))
        gui = FakeGui(cfg, headset)
        state = cls(FakeFlow(gui))
        clock = FakeClock()
        state.timer = StepTimer(clock)
        state.enter()
        assert state._ready
        return state, gui, clock

    return build


def feed(state: SessionState, n: int = 10) -> None:
    assert state.session_saver is not None
    state.session_saver.on_chunk(np.zeros((2, n)))


def run_to_end(state: SessionState, clock: FakeClock, step_ms: float = 50) -> None:
    for _ in range(100_000):
        if state.current_step is None:
            state.tick()  # leaves the session, as FlowController would
            return
        clock.advance_ms(step_ms)
        feed(state, 5)
        state.tick()
        if state.current_step is not None and state.current_step.wait_for_key:
            state.gui_manager.events.append(SessionEvent.CONTINUE)  # type: ignore
    raise AssertionError("session did not finish")


def read_events(root: Path) -> list[dict[str, str]]:
    with open(root / "sub-001" / "ses-01" / "events.tsv") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def test_pause_mid_trial_does_not_end_the_step_and_flags_it(
    tmp_path: Path, make_state: Any
) -> None:
    state, gui, clock = make_state()
    state.gui_manager.events.append(SessionEvent.CONTINUE)  # instruction screen
    state.tick()
    assert state.current_step.phase == "fixation"  # type: ignore[union-attr]

    clock.advance_ms(60)  # 60 of 100 ms
    state.tick()
    gui.events.append(SessionEvent.PAUSE)
    state.tick()
    assert state.is_paused

    clock.advance_ms(10_000)  # long pause
    state.tick()
    assert state.current_step.phase == "fixation"  # type: ignore[union-attr]

    gui.events.append(SessionEvent.PAUSE)  # resume
    state.tick()
    assert not state.is_paused
    assert state.current_step.phase == "fixation"  # type: ignore[union-attr]
    assert state.timer.elapsed_ms() == pytest.approx(60)  # pause not counted

    clock.advance_ms(45)  # 105 ms of active time in total
    state.tick()
    assert state.current_step.phase == "cue"  # type: ignore[union-attr]

    run_to_end(state, clock)
    state.exit()
    rows = read_events(tmp_path)
    fixation = next(r for r in rows if r["trial_type"] == "FIXATION")
    assert fixation["interrupted"] == "true"
    others = [r for r in rows if r["trial_type"] == "ITI"]
    assert all(r["interrupted"] == "false" for r in others)
    assert {"PAUSED", "RESUMED"} <= {r["trial_type"] for r in rows}


def test_step_timer_excludes_pause() -> None:
    clock = FakeClock()
    timer = StepTimer(clock)
    clock.advance_ms(30)
    timer.pause()
    clock.advance_ms(500)
    assert timer.elapsed_ms() == pytest.approx(30)
    timer.resume()
    clock.advance_ms(20)
    assert timer.elapsed_ms() == pytest.approx(50)
    assert timer.was_paused and timer.wall_elapsed_s() == pytest.approx(0.55)


def test_default_feedback_is_none_and_writes_no_result_markers(
    tmp_path: Path, make_state: Any
) -> None:
    state, gui, clock = make_state(CalibrationState)
    run_to_end(state, clock)
    assert all(update[1] is None for update in gui.updates)  # nothing shown
    state.exit()
    rows = read_events(tmp_path)
    assert not [r for r in rows if r["trial_type"].startswith("RESULT_")]
    assert {r["feedback_mode"] for r in rows} == {"none"}


def test_demo_feedback_marks_results_with_mode_and_never_uses_true_class(
    tmp_path: Path, make_state: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    class AlwaysLeft:
        def predict(self, eeg: np.ndarray) -> T:
            return T.LEFT_HAND_IMAGERY

    monkeypatch.setattr(
        "src.flow_controller.states.session_state.make_classifier",
        lambda mode, classes, model=None: AlwaysLeft(),
    )
    state, gui, clock = make_state(
        CalibrationState, small_config(feedback="demo", trials_per_class_per_block=5)
    )
    run_to_end(state, clock)
    shown = [u for u in gui.updates if u[1] is not None]
    assert shown and all(u[5] == "demo" for u in shown)  # banner flag passed to view
    state.exit()
    rows = read_events(tmp_path)
    results = [r for r in rows if r["trial_type"].startswith("RESULT_")]
    assert len(results) == 10
    assert {r["feedback_mode"] for r in results} == {"demo"}
    # Right-hand trials get the (wrong) predicted answer: the screen shows the
    # classifier output, not the prompted class.
    assert {r["trial_type"] for r in results} == {"RESULT_LEFT_HAND_IMAGERY"}


def test_make_classifier_modes() -> None:
    classes = [T.LEFT_HAND_IMAGERY, T.RIGHT_HAND_IMAGERY]
    assert make_classifier("none", classes) is None
    demo = make_classifier("demo", classes)
    assert demo is not None and demo.predict(np.zeros((1, 1))) in classes
    with pytest.raises(NotImplementedError):
        make_classifier("model", classes)


def test_model_feedback_without_model_refuses_to_start(make_state: Any) -> None:
    driver = MockDriver(config=HeadsetConfig.mock(2, FS))
    headset = EEGHeadset(driver)
    headset.connect()
    gui = FakeGui(small_config(feedback="model"), headset)
    flow = FakeFlow(gui)
    state = ExperimentState(flow)
    state.enter()
    assert not state._ready


def test_full_mock_session_produces_all_outputs(
    tmp_path: Path, make_state: Any
) -> None:
    cfg = small_config(
        practice_trials_per_class=1,
        rest_eyes_open_ms=200,
        artifact_cues=["double_blink"],
        artifact_trials_per_class=2,
        n_blocks=2,
        qc_procedure=True,
    )
    state, gui, clock = make_state(ExperimentState, cfg)
    run_to_end(state, clock)
    state.exit()

    session = tmp_path / "sub-001" / "ses-01"
    for name in (
        "session.edf",
        "events.tsv",
        "sync_log.tsv",
        "session_metadata.json",
        "qc_rest.npy",
    ):
        assert (session / name).exists(), name
    assert (tmp_path / "participants.tsv").exists()
    assert (tmp_path / "sessions.tsv").exists()

    rows = read_events(tmp_path)
    markers = [r["trial_type"] for r in rows]
    assert markers[1] == "INSTRUCTION"
    for needed in ("REST_EYES_OPEN", "PRACTICE", "BREAK", "ITI", "END", "DOUBLE_BLINK"):
        assert needed in markers, needed
    practice = [r for r in rows if r["practice"] == "true"]
    assert practice and all(r["condition"] == "imagery" for r in practice)
    conditions = {r["condition"] for r in rows}
    assert {"imagery", "artifact", "rest", "qc"} <= conditions
    artifact_blocks = {r["block_id"] for r in rows if r["condition"] == "artifact"}
    imagery_blocks = {r["block_id"] for r in rows if r["condition"] == "imagery"}
    assert not artifact_blocks & imagery_blocks

    meta = json.loads((session / "session_metadata.json").read_text())
    assert meta["session_completed"] is True
    assert meta["randomisation"]["seed"] == 5
    assert meta["feedback_mode"] == "none"
    assert meta["trial_config"]["n_blocks"] == 2
    assert meta["headset"]["channel_map"] == {"0": "CH0", "1": "CH1"}
    for key in ("app", "system", "participant", "quality_check", "units"):
        assert key in meta
    assert "name" not in meta["participant"]

    sync = (session / "sync_log.tsv").read_text().splitlines()
    assert sync[0].split("\t")[3] == "perf_counter_ns" and len(sync) > 10


def test_experiment_defaults_use_experiment_config_type() -> None:
    assert isinstance(ExperimentConfig(), SessionConfig)
    assert T.ITI.value == "iti"
