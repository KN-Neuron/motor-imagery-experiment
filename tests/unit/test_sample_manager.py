import random
from itertools import groupby

import pytest

from src.sample_manager import ExperimentStep, SampleManager
from src.sample_manager.experiment_step_type import (
    ExperimentStepType as T,
    parse_step_type,
)
from src.sample_manager.sample_manager import balanced_sequence
from src.trials_config.trials_config import SessionConfig, build_config


def drain(manager: SampleManager) -> list[ExperimentStep]:
    steps = []
    while (step := manager.get_next()) is not None:
        steps.append(step)
    return steps


def class_steps(steps: list[ExperimentStep], **kw: object) -> list[ExperimentStep]:
    return [
        s
        for s in steps
        if s.phase == "task"
        and all(getattr(s, k) == v for k, v in kw.items())
        and s.step_type not in (T.FIXATION, T.ITI)
    ]


def test_defaults_are_a_sane_research_protocol() -> None:
    cfg = SessionConfig()
    assert 4 <= cfg.n_blocks <= 6
    assert cfg.trials_per_class_per_block == 20
    assert (cfg.iti_min_ms, cfg.iti_max_ms) == (2000, 3500)
    assert cfg.feedback == "none"
    assert cfg.cues == ["left_hand_imagery", "right_hand_imagery"]


def test_blocks_are_balanced_per_block() -> None:
    cfg = SessionConfig(n_blocks=3, trials_per_class_per_block=6, seed=1)
    steps = drain(SampleManager(cfg))
    real = class_steps(steps, condition="imagery", practice=False)
    block_ids = {s.block_id for s in real}
    assert len(block_ids) == 3
    for block_id in block_ids:
        block = [s.step_type for s in real if s.block_id == block_id]
        assert block.count(T.LEFT_HAND_IMAGERY) == 6
        assert block.count(T.RIGHT_HAND_IMAGERY) == 6


def test_max_consecutive_same_class() -> None:
    rng = random.Random(0)
    for _ in range(50):
        seq = balanced_sequence(rng, [T.LEFT_HAND_IMAGERY, T.RIGHT_HAND_IMAGERY], 20, 3)
        assert len(seq) == 40
        assert max(len(list(g)) for _, g in groupby(seq)) <= 3


def test_single_class_cannot_exceed_max_run() -> None:
    with pytest.raises(ValueError):
        balanced_sequence(random.Random(0), [T.LEFT_HAND_IMAGERY], 5, 3)


def test_iti_is_jittered_within_range() -> None:
    cfg = SessionConfig(iti_min_ms=2000, iti_max_ms=3500, seed=3)
    itis = [s.duration_ms for s in drain(SampleManager(cfg)) if s.phase == "iti"]
    assert len(itis) > 50
    assert all(2000 <= d <= 3500 for d in itis)
    assert len(set(itis)) > 10  # not a constant gap


def test_same_seed_reproduces_session_different_seed_does_not() -> None:
    def layout(seed: int) -> list[tuple[str, int]]:
        manager = SampleManager(SessionConfig(), seed=seed)
        return [(s.marker, s.duration_ms) for s in drain(manager)]

    assert layout(42) == layout(42)
    assert layout(42) != layout(43)


def test_seed_is_recorded_even_when_not_configured() -> None:
    manager = SampleManager(SessionConfig(seed=None))
    assert isinstance(manager.describe()["seed"], int)
    assert SampleManager(SessionConfig(seed=7)).describe()["seed"] == 7


def test_artifacts_live_in_their_own_block_not_in_mi_blocks() -> None:
    steps = drain(SampleManager(SessionConfig(seed=1)))
    artifact = [s for s in steps if s.condition == "artifact"]
    assert {s.step_type for s in class_steps(artifact)} == {
        T.DOUBLE_BLINK,
        T.JAW_CLENCH,
        T.HEAD_MOVEMENT,
    }
    artifact_blocks = {s.block_id for s in artifact}
    mi_blocks = {s.block_id for s in steps if s.condition == "imagery"}
    assert len(artifact_blocks) == 1 and not artifact_blocks & mi_blocks
    last_mi = max(i for i, s in enumerate(steps) if s.condition == "imagery")
    first_art = min(i for i, s in enumerate(steps) if s.condition == "artifact")
    assert first_art > last_mi


def test_session_order_and_screens() -> None:
    steps = drain(SampleManager(SessionConfig(n_blocks=2, seed=1)))
    markers = [s.marker for s in steps if s.phase in ("screen", "rest")]
    assert markers[0] == "INSTRUCTION"
    assert markers[1] == "REST_EYES_OPEN"
    assert markers[2] == "PRACTICE"
    assert markers.count("BREAK") == 2  # between 2 MI blocks + before artifacts
    assert markers[-1] == "END"
    assert all(s.wait_for_key for s in steps if s.phase == "screen")


def test_practice_trials_are_flagged() -> None:
    steps = drain(SampleManager(SessionConfig(practice_trials_per_class=2, seed=1)))
    practice = [s for s in steps if s.practice]
    assert practice and len(class_steps(practice)) == 4
    assert all(s.condition == "imagery" for s in practice)


def test_cue_then_task_markers() -> None:
    steps = drain(SampleManager(SessionConfig(seed=1)))
    trial = [s.marker for s in steps if s.trial_id == 1 and s.block_id == 3]
    assert trial[0] == "FIXATION"
    assert trial[1].startswith("CUE_") and trial[2] == trial[1][4:]


def test_task_ms_zero_gives_single_class_step() -> None:
    cfg = SessionConfig(task_ms=0, seed=1)
    steps = drain(SampleManager(cfg))
    assert not [s for s in steps if s.phase == "cue"]


def test_legacy_clench_name_maps_to_execution_with_warning() -> None:
    with pytest.warns(FutureWarning, match="deprecated"):
        assert parse_step_type("left_hand_clench") is T.LEFT_HAND_EXECUTION
    cfg = SessionConfig(cues=["left_hand_clench", "right_hand_clench"], seed=1)
    with pytest.warns(FutureWarning):
        steps = drain(SampleManager(cfg))
    assert class_steps(steps, condition="execution")
    assert not class_steps(steps, condition="imagery")


def test_legacy_artifact_cues_in_cues_list_move_to_artifact_block() -> None:
    cfg = SessionConfig(cues=["left_hand_imagery", "right_hand_imagery", "jaw_clench"])
    steps = drain(SampleManager(cfg))
    assert {s.step_type for s in class_steps(steps, condition="imagery")} == {
        T.LEFT_HAND_IMAGERY,
        T.RIGHT_HAND_IMAGERY,
    }


def test_legacy_config_keys_are_translated_with_warning() -> None:
    with pytest.warns(FutureWarning):
        cfg = build_config(
            SessionConfig,
            {"trials_per_class": 3, "rest_ms": 700, "strategy": "random"},
        )
    assert cfg.trials_per_class_per_block == 3 and cfg.n_blocks == 1


def test_unknown_config_key_and_bad_feedback_rejected() -> None:
    with pytest.raises(ValueError):
        build_config(SessionConfig, {"nonsense": 1})
    with pytest.raises(ValueError):
        build_config(SessionConfig, {"feedback": "always"})
