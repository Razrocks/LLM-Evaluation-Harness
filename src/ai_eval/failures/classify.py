"""Turn scored results into a controlled failure inventory.

Every failed or errored assertion becomes one ``FailureRecord`` carrying its taxonomy codes,
severity, expected/observed values, and evidence — so a report can always resolve an aggregate
back to the exact case and assertion, and never hides an unknown failure in a generic bucket.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import AssertionResultStatus, Severity
from ai_eval.scoring import CaseScore


class FailureRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    case_version: int
    assertion_id: str
    scorer_ref: str
    status: AssertionResultStatus
    severity: Severity | None
    failure_codes: list[str] = Field(default_factory=list)
    expected: object = None
    observed: object = None
    evidence: list[dict] = Field(default_factory=list)


def build_failures(scores: list[CaseScore]) -> list[FailureRecord]:
    """One record per failed/errored assertion, most-severe first within each case."""
    order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2, Severity.INFORMATIONAL: 3}
    records: list[FailureRecord] = []
    for score in scores:
        for r in score.results:
            if r.status in (AssertionResultStatus.FAIL, AssertionResultStatus.ERROR):
                records.append(
                    FailureRecord(
                        case_id=score.case_id,
                        case_version=score.case_version,
                        assertion_id=r.assertion_id,
                        scorer_ref=r.scorer_ref,
                        status=r.status,
                        severity=r.severity,
                        failure_codes=r.failure_codes,
                        expected=r.expected,
                        observed=r.observed,
                        evidence=r.evidence,
                    )
                )
    records.sort(key=lambda x: order.get(x.severity, 9) if x.severity else 9)
    return records


def failure_code_counts(records: list[FailureRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rec in records:
        for code in rec.failure_codes:
            counts[code] = counts.get(code, 0) + 1
    return counts
