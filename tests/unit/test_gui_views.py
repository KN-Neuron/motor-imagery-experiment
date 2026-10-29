import time
from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtGui import QPixmap

from src.eeg_headset.drivers import MockDriver
from src.eeg_headset.eeg_headset import EEGHeadset
from src.eeg_headset.headset_config import HeadsetConfig
from src.gui.dialogs.participant_dialog import ParticipantDialog
from src.gui.dialogs.quality_dialog import QualityDialog
from src.gui.dialogs.session_config_dialog import (
    CalibrationConfigDialog,
    ExperimentConfigDialog,
)
from src.gui.views.session_view import DEMO_BANNER, SessionEvent, SessionView
from src.gui.views.ssvep import refresh_warning, ssvep_visible
from src.sample_manager.experiment_step_type import ExperimentStepType as T
from src.sample_manager.sample_manager import ExperimentStep
from src.sample_manager.texts import CUE_TEXT
from src.signal_quality.thresholds import QualityThresholds
from src.trials_config.trials_config import CalibrationConfig, ExperimentConfig


def render(view: SessionView) -> None:
    view.resize(800, 600)
    view.grab()  # forces a paint event offscreen


def test_ssvep_depends_on_time_not_on_paint_count() -> None:
    # 10 Hz: 100 ms period, visible for the first 50 ms regardless of frame rate
    assert ssvep_visible(0.0, 10) and ssvep_visible(0.049, 10)
    assert not ssvep_visible(0.051, 10) and not ssvep_visible(0.099, 10)
    assert ssvep_visible(0.101, 10)
    # same instants, any "frame rate": the answer only depends on elapsed time
    visible = [ssvep_visible(i / 144, 12) for i in range(144)]
    assert 0.45 < sum(visible) / 144 < 0.55


def test_refresh_warning() -> None:
    assert refresh_warning(60, 10) is None  # 6 frames per cycle: fine
    assert refresh_warning(60, 8) is not None  # 7.5 frames
    assert refresh_warning(60, 12) is not None  # 5 frames: odd, unequal duty
    assert refresh_warning(0, 10) is not None  # unknown refresh rate


def test_every_cue_has_polish_and_english_text() -> None:
    for step_type in (
        T.LEFT_HAND_IMAGERY,
        T.RIGHT_HAND_IMAGERY,
        T.LEFT_HAND_EXECUTION,
        T.RIGHT_HAND_EXECUTION,
    ):
        pl, en = CUE_TEXT[step_type]
        assert pl and en
    assert "WYOBRAŹ" in CUE_TEXT[T.LEFT_HAND_IMAGERY][0]
    assert "nie ruszaj" in CUE_TEXT[T.LEFT_HAND_IMAGERY][0]
    assert "WYOBRAŹ" not in CUE_TEXT[T.LEFT_HAND_EXECUTION][0]
    assert "ZACIŚNIJ LEWĄ" in CUE_TEXT[T.LEFT_HAND_EXECUTION][0]


@pytest.mark.parametrize(
    "step_type,phase",
    [
        (T.INSTRUCTION, "screen"),
        (T.FIXATION, "fixation"),
        (T.ITI, "iti"),
        (T.REST_EYES_OPEN, "rest"),
        (T.REST_EYES_CLOSED, "rest"),
        (T.LEFT_HAND_IMAGERY, "cue"),
        (T.RIGHT_HAND_EXECUTION, "task"),
        (T.SSVEP_FOCUS, "task"),
        (T.DOUBLE_BLINK, "task"),
    ],
)
def test_view_paints_every_step_kind(step_type: T, phase: str) -> None:
    view = SessionView()
    step = ExperimentStep(step_type, 1000, phase=phase, text="x")
    view.update_content(step, None, False, False, 0.5, "none", 1)
    render(view)
    view.update_content(step, step_type, True, True, 0.5, "demo", 2)
    render(view)


def test_first_paint_is_reported_once_per_step() -> None:
    view = SessionView()
    step = ExperimentStep(T.FIXATION, 1000, phase="fixation")
    view.update_content(step, token=1)
    before = time.perf_counter_ns()
    render(view)
    token, ns = view.pop_first_paint() or (0, 0)
    assert token == 1 and ns >= before
    render(view)
    assert view.pop_first_paint() is None
    view.update_content(step, token=2)
    render(view)
    assert (view.pop_first_paint() or (0, 0))[0] == 2


def test_demo_banner_is_drawn_only_in_demo_mode() -> None:
    def pixels(mode: str) -> bytes:
        view = SessionView()
        view.update_content(None, feedback_mode=mode)
        view.resize(1000, 400)
        pixmap: QPixmap = view.grab()
        return bytes(pixmap.toImage().constBits().asarray(1000 * 400 * 4))

    assert pixels("demo") != pixels("none")
    assert pixels("none") == pixels("model")
    assert "NIE PRAWDZIWY KLASYFIKATOR" in DEMO_BANNER


def test_space_and_esc_events() -> None:
    view = SessionView()
    view._on_space_pressed()
    assert view.get_pending_events() == [SessionEvent.CONTINUE]
    view._on_esc_pressed()  # ignored unless paused
    assert view.get_pending_events() == []
    view.is_paused = True
    view._on_esc_pressed()
    assert view.get_pending_events() == [SessionEvent.ABORT]


def test_config_dialogs_roundtrip_defaults() -> None:
    dialog = ExperimentConfigDialog(ExperimentConfig())
    dialog._on_start()
    assert dialog.get_config() == ExperimentConfig()

    dialog2 = CalibrationConfigDialog(CalibrationConfig(feedback="demo"))
    dialog2._on_start()
    assert dialog2.get_config() == CalibrationConfig(feedback="demo")


def test_config_dialog_rejects_invalid_iti() -> None:
    dialog = ExperimentConfigDialog(ExperimentConfig())
    dialog.iti_min.setValue(5000)
    dialog.iti_max.setValue(2000)
    dialog._on_start()
    assert dialog.get_config() is None and dialog.error_label.text()


def test_participant_dialog_validates_and_warns_on_name_like_code(
    tmp_path: Path,
) -> None:
    dialog = ParticipantDialog(tmp_path)
    dialog.code.setText("sub-001")
    dialog._on_start()  # consent missing
    assert dialog.get_info() is None and "Consent" in dialog.message.text()

    dialog.consent.setChecked(True)
    dialog.age.setText("20-25")
    dialog._on_start()
    info = dialog.get_info()
    assert info is not None and info.code == "sub-001" and info.age == "20-25"
    assert info.consent_date and info.ehi_score is None

    dialog = ParticipantDialog(tmp_path)
    dialog.consent.setChecked(True)
    dialog.code.setText("sub-JanKowalski")
    dialog._on_start()  # first click: warning only
    assert dialog.get_info() is None and "name" in dialog.message.text()
    dialog._on_start()
    assert dialog.get_info() is not None

    dialog = ParticipantDialog(tmp_path)
    dialog.consent.setChecked(True)
    dialog.code.setText("Jan Kowalski")
    dialog._on_start()
    assert dialog.get_info() is None


def test_participant_dialog_blocks_overwriting_existing_session(tmp_path: Path) -> None:
    (tmp_path / "sub-001" / "ses-01").mkdir(parents=True)
    (tmp_path / "sub-001" / "ses-01" / "session.edf").write_bytes(b"x")
    dialog = ParticipantDialog(tmp_path)
    dialog.code.setText("sub-001")
    dialog.consent.setChecked(True)
    dialog._on_start()
    assert dialog.get_info() is None and "already exists" in dialog.message.text()


def test_quality_dialog_collects_and_flags_ignored_warnings() -> None:
    fs = 100
    headset = EEGHeadset(MockDriver(config=HeadsetConfig.mock(2, fs)))
    dialog = QualityDialog(headset, QualityThresholds(), duration_s=2)
    rng = np.random.default_rng(0)
    good = rng.normal(0, 20, (2, 3 * fs))
    good[1] = 0  # channel CH1 is flat
    dialog._on_data(good)
    dialog._collected = good.shape[1]
    dialog.finish_collecting()
    dialog._on_continue()

    result = dialog.get_result()
    assert result is not None
    assert result.rest_data.shape == (2, 2 * fs)
    assert result.ignored_warnings is True
    meta = result.to_metadata()
    assert meta["warnings_ignored"] is True
    assert meta["channels"]["CH1"]["warnings"] == ["flat"]  # type: ignore[index]
    assert meta["channels"]["CH0"]["warnings"] == []  # type: ignore[index]
