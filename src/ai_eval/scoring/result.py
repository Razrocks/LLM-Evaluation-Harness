"""The assertion-result model — one evidence-backed outcome per assertion.

Mirrors ``schemas/assertion_result.v1.json``. Every scorer returns one of these; none are
silently omitted. ``evidence`` and ``normalization`` are free-form dict notes so a reader can
always see *why* the status is what it is.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import AssertionResultStatus, FailureCode, Severity


class AssertionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str
    scorer_ref: str
    status: AssertionResultStatus
    score: float | None = None
    threshold: float | None = None
    expected: Any = None
    observed: Any = None
    normalization: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    failure_codes: list[str] = Field(default_factory=list)
    severity: Severity | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status is AssertionResultStatus.PASS


def failure(codes: list[FailureCode]) -> list[str]:
    """Convert failure-code enums to their string values for a result payload."""
    return [str(c) for c in codes]
