import time
from typing import Callable


class StepTimer:
    """Step timer that stops counting while paused.

    `elapsed_ms` excludes paused time; `wall_elapsed_s` includes it. `was_paused`
    stays True for the rest of the step once a pause happened in it, so the step
    can be flagged `interrupted` in events.tsv.
    """

    def __init__(self, clock: Callable[[], int] = time.perf_counter_ns) -> None:
        self._clock = clock
        self.start()

    def start(self) -> None:
        self._start_ns = self._clock()
        self._paused_total_ns = 0
        self._pause_started_ns: int | None = None
        self.was_paused = False

    restart = start

    @property
    def start_ns(self) -> int:
        return self._start_ns

    @property
    def is_paused(self) -> bool:
        return self._pause_started_ns is not None

    def pause(self) -> None:
        if self._pause_started_ns is None:
            self._pause_started_ns = self._clock()
            self.was_paused = True

    def resume(self) -> None:
        if self._pause_started_ns is not None:
            self._paused_total_ns += self._clock() - self._pause_started_ns
            self._pause_started_ns = None

    def elapsed_ms(self) -> float:
        now = self._pause_started_ns if self.is_paused else self._clock()
        assert now is not None
        return (now - self._start_ns - self._paused_total_ns) / 1e6

    def wall_elapsed_s(self) -> float:
        return (self._clock() - self._start_ns) / 1e9
