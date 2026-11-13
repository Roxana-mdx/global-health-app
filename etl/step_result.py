"""Typed result of one pipeline step (a download or an import of one indicator)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StepStatus(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class StepResult:
    source: str
    item: str
    status: StepStatus
    detail: str = ""

    @classmethod
    def ok(cls, source: str, item: str, detail: str = "") -> "StepResult":
        return cls(source, item, StepStatus.OK, detail)

    @classmethod
    def skipped(cls, source: str, item: str, detail: str = "") -> "StepResult":
        return cls(source, item, StepStatus.SKIPPED, detail)

    @classmethod
    def from_error(cls, source: str, item: str, error: Exception) -> "StepResult":
        return cls(source, item, StepStatus.FAILED, f"{type(error).__name__}: {error}")

    @property
    def is_failed(self) -> bool:
        return self.status is StepStatus.FAILED
