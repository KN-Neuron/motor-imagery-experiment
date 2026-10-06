import random
import secrets
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

from src.trials_config.trials_config import SessionConfig

from . import texts
from .experiment_step_type import (
    ARTIFACTS,
    CLASSIFIABLE,
    ExperimentStepType as T,
    condition_of,
    parse_step_type,
)

# Optional signal-check procedure (blink / jaw / eyes open / eyes closed)
QC_TRIALS_PER_CLASS = 3
QC_TASK_MS = 3000
QC_REST_MS = 15_000


@dataclass
class ExperimentStep:
    step_type: T
    duration_ms: int  # 0 together with wait_for_key: waits for SPACE
    phase: str = "task"  # fixation | cue | task | iti | rest | screen
    block_id: int | None = None
    trial_id: int | None = None
    condition: str | None = None
    practice: bool = False
    wait_for_key: bool = False
    text: str | None = None

    @property
    def marker(self) -> str:
        """Label written to EDF / events.tsv when the step starts."""
        if self.phase == "cue":
            return f"CUE_{self.step_type.value.upper()}"
        return self.step_type.value.upper()

    @property
    def is_feedback_class(self) -> bool:
        return self.phase == "task" and self.step_type in CLASSIFIABLE


def balanced_sequence(
    rng: random.Random, classes: list[T], n_per_class: int, max_run: int
) -> list[T]:
    """Shuffle `n_per_class` of each class so no class repeats > max_run times."""
    if len(classes) == 1:
        if n_per_class > max_run:
            raise ValueError("A single class cannot satisfy max_consecutive")
        return classes * n_per_class

    for _ in range(1000):
        remaining = {c: n_per_class for c in classes}
        seq: list[T] = []
        while sum(remaining.values()):
            options = [
                c
                for c, left in remaining.items()
                if left > 0 and not (seq[-max_run:] == [c] * max_run)
            ]
            if not options:
                break
            # weights by remaining count make dead ends (only one class left) rare
            choice = rng.choices(options, weights=[remaining[o] for o in options])[0]
            seq.append(choice)
            remaining[choice] -= 1
        else:
            return seq
    raise ValueError("Could not build a sequence satisfying max_consecutive")


def resolve_classes(
    config: SessionConfig,
) -> tuple[list[T], list[T], list[T]]:
    """Split configured cue names into (MI/execution, ssvep, artifact) classes."""
    main: list[T] = []
    ssvep: list[T] = []
    artifacts: list[T] = []
    for name in [*config.cues, *config.artifact_cues]:
        step_type = parse_step_type(name)
        if step_type is None:
            raise ValueError(f"Unknown cue name: {name!r}")
        if step_type in ARTIFACTS:
            target = artifacts
        elif step_type == T.SSVEP_FOCUS:
            target = ssvep
        elif step_type in CLASSIFIABLE:
            target = main
        else:
            raise ValueError(f"'{name}' cannot be used as a cue")
        if step_type not in target:
            target.append(step_type)
    return main, ssvep, artifacts


class SampleManager:
    """Builds the whole session as a queue of steps, organised in blocks.

    Order: instruction, [QC procedure], [rest block], [practice], MI blocks
    (separated by BREAK screens), artifact block, [SSVEP block], end screen.
    All randomness (class order and ITI jitter) comes from one seeded RNG, so
    the same seed reproduces the same session.
    """

    def __init__(self, config: SessionConfig, seed: int | None = None) -> None:
        self.config = config
        if seed is None:
            seed = config.seed if config.seed is not None else secrets.randbits(32)
        self.seed = seed
        self._rng = random.Random(seed)
        self._block_id = 0
        self.blocks: list[dict[str, Any]] = []
        self.step_queue: deque[ExperimentStep] = deque()

        self._build()

    # --- construction -----------------------------------------------------

    def _build(self) -> None:
        cfg = self.config
        main, ssvep, artifacts = resolve_classes(cfg)

        self._screen(T.INSTRUCTION, cfg.instruction_text or texts.DEFAULT_INSTRUCTION)

        if cfg.qc_procedure:
            self._qc_block()
        self._rest_block()

        if main and cfg.practice_trials_per_class > 0:
            self._screen(T.PRACTICE, texts.PRACTICE_TEXT)
            self._trial_block(
                "practice", main, cfg.practice_trials_per_class, practice=True
            )
        for index in range(cfg.n_blocks if main else 0):
            if index > 0:
                self._screen(T.BREAK, texts.BREAK_TEXT)
            self._trial_block("mi", main, cfg.trials_per_class_per_block)

        if artifacts and cfg.artifact_trials_per_class > 0:
            self._screen(T.BREAK, texts.BREAK_TEXT)
            self._trial_block("artifact", artifacts, cfg.artifact_trials_per_class)
        if ssvep and cfg.ssvep_trials > 0:
            self._screen(T.BREAK, texts.BREAK_TEXT)
            self._trial_block("ssvep", ssvep, cfg.ssvep_trials)

        self._screen(T.END, texts.END_TEXT)

    def _screen(self, step_type: T, text: str) -> None:
        self.step_queue.append(
            ExperimentStep(step_type, 0, phase="screen", wait_for_key=True, text=text)
        )

    def _new_block(self, kind: str, n_trials: int) -> int:
        self._block_id += 1
        self.blocks.append(
            {"block_id": self._block_id, "kind": kind, "n_trials": n_trials}
        )
        return self._block_id

    def _rest_block(self) -> None:
        for step_type, duration in (
            (T.REST_EYES_OPEN, self.config.rest_eyes_open_ms),
            (T.REST_EYES_CLOSED, self.config.rest_eyes_closed_ms),
        ):
            if duration > 0:
                block_id = self._new_block("rest", 0)
                self.step_queue.append(
                    ExperimentStep(
                        step_type,
                        duration,
                        phase="rest",
                        block_id=block_id,
                        condition="rest",
                    )
                )

    def _qc_block(self) -> None:
        block_id = self._new_block("qc", 2 * QC_TRIALS_PER_CLASS)
        self._trials(
            block_id,
            [T.DOUBLE_BLINK, T.JAW_CLENCH] * QC_TRIALS_PER_CLASS,
            practice=False,
            cue_ms=QC_TASK_MS,
            task_ms=0,
            condition="qc",
        )
        for step_type in (T.REST_EYES_OPEN, T.REST_EYES_CLOSED):
            block_id = self._new_block("qc", 0)
            self.step_queue.append(
                ExperimentStep(
                    step_type,
                    QC_REST_MS,
                    phase="rest",
                    block_id=block_id,
                    condition="qc",
                )
            )

    def _trial_block(
        self, kind: str, classes: list[T], n_per_class: int, practice: bool = False
    ) -> None:
        sequence = balanced_sequence(
            self._rng, classes, n_per_class, self.config.max_consecutive_same_class
        )
        block_id = self._new_block(kind, len(sequence))
        self._trials(
            block_id,
            sequence,
            practice,
            self.config.cue_ms,
            self.config.task_ms,
        )

    def _trials(
        self,
        block_id: int,
        sequence: list[T],
        practice: bool,
        cue_ms: int,
        task_ms: int,
        condition: str | None = None,
    ) -> None:
        cfg = self.config

        def step(step_type: T, duration: int, phase: str, trial_id: int) -> None:
            self.step_queue.append(
                ExperimentStep(
                    step_type,
                    duration,
                    phase=phase,
                    block_id=block_id,
                    trial_id=trial_id,
                    condition=condition or condition_of(sequence[trial_id - 1]),
                    practice=practice,
                )
            )

        for trial_id, step_type in enumerate(sequence, start=1):
            step(T.FIXATION, cfg.fixation_ms, "fixation", trial_id)
            if task_ms > 0:
                step(step_type, cue_ms, "cue", trial_id)
                step(step_type, task_ms, "task", trial_id)
            else:
                step(step_type, cue_ms, "task", trial_id)
            if trial_id < len(sequence):  # a BREAK / next block follows the last
                iti = self._rng.randint(cfg.iti_min_ms, cfg.iti_max_ms)
                step(T.ITI, iti, "iti", trial_id)

    # --- consumption ------------------------------------------------------

    def get_next(self) -> Optional[ExperimentStep]:
        if self.step_queue:
            return self.step_queue.popleft()
        return None

    def describe(self) -> dict[str, Any]:
        """Seed + block layout, stored in session_metadata.json."""
        return {"seed": self.seed, "blocks": self.blocks}
