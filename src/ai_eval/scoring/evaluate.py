"""Evaluate one case: run every assertion's scorer, then derive the case-execution state.

Guarantees invariant #8: *every* assertion yields exactly one result (pass / fail /
unevaluable / error) — an unknown scorer or a scorer exception becomes an explicit
``SCORER_ERROR`` result, never a silent omission.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_eval.domain import (
    AssertionResultStatus,
    CaseExecutionState,
    Criticality,
    EvalCase,
    FailureCode,
    Severity,
)
from ai_eval.parsing import ParseOutcome, ParseStatus

from .context import ScoringContext
from .result import AssertionResult
from .scorers import get_scorer


@dataclass
class CaseScore:
    """The scored outcome for one case execution."""

    case_id: str
    case_version: int
    criticality: Criticality
    state: CaseExecutionState
    parse_status: ParseStatus
    results: list[AssertionResult]

    @property
    def passed(self) -> bool:
        return self.state is CaseExecutionState.PASSED

    @property
    def is_critical_failure(self) -> bool:
        """A critical case that did not pass, or any failed critical-severity assertion."""
        if self.criticality is Criticality.CRITICAL and not self.passed:
            return True
        return any(
            r.status is AssertionResultStatus.FAIL and r.severity is Severity.CRITICAL
            for r in self.results
        )


def _error_result(assertion_id: str, scorer_ref: str, reason: str) -> AssertionResult:
    return AssertionResult(
        assertion_id=assertion_id,
        scorer_ref=scorer_ref,
        status=AssertionResultStatus.ERROR,
        failure_codes=[str(FailureCode.SCORER_ERROR)],
        metadata={"reason": reason},
    )


def _derive_state(
    parse: ParseOutcome,
    results: list[AssertionResult],
    required: dict[str, bool],
) -> CaseExecutionState:
    if parse.status in (ParseStatus.EMPTY, ParseStatus.PARSE_ERROR):
        return CaseExecutionState.PARSE_ERROR
    if parse.status is ParseStatus.SCHEMA_ERROR:
        return CaseExecutionState.SCHEMA_ERROR
    if any(r.status is AssertionResultStatus.ERROR for r in results):
        return CaseExecutionState.SCORING_ERROR
    by_id = {r.assertion_id: r for r in results}
    required_failed = any(
        aid in by_id and by_id[aid].status is AssertionResultStatus.FAIL
        for aid, is_req in required.items()
        if is_req
    )
    return CaseExecutionState.FAILED_ASSERTIONS if required_failed else CaseExecutionState.PASSED


def evaluate_case(case: EvalCase, parse: ParseOutcome) -> CaseScore:
    ctx = ScoringContext.build(case, parse)
    results: list[AssertionResult] = []
    for assertion in case.assertions:
        scorer = get_scorer(assertion.scorer_ref)
        if scorer is None:
            results.append(
                _error_result(assertion.assertion_id, assertion.scorer_ref, "unknown scorer_ref")
            )
            continue
        try:
            results.append(scorer(assertion, ctx))
        except Exception as exc:  # a scorer bug is an evaluator error, never a target failure
            results.append(
                _error_result(assertion.assertion_id, assertion.scorer_ref, repr(exc))
            )
    required = {a.assertion_id: a.required for a in case.assertions}
    state = _derive_state(parse, results, required)
    return CaseScore(
        case_id=case.case_id,
        case_version=case.case_version,
        criticality=case.criticality,
        state=state,
        parse_status=parse.status,
        results=results,
    )
