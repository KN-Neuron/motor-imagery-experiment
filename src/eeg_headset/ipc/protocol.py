from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict


DriverKind = Literal["brainaccess", "mock"]


class DriverRecipe(TypedDict):
    version: int
    driver: DriverKind
    params: dict[str, Any]


@dataclass(frozen=True)
class WorkerError(Exception):
    message: str
    traceback: str | None = None

    def __str__(self) -> str:  # pragma: no cover
        if self.traceback:
            return f"{self.message}\n\n{self.traceback}"
        return self.message
