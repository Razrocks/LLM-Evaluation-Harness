"""Evaluate raw target outputs into a complete, reportable run evaluation.

This is the seam that runs *after* raw capture (M2) and *before* reporting/gating (M4). For each
case it parses the raw output (no repair), scores every assertion, builds metric inputs, then
aggregates metrics and the failure inventory. It imports the scoring, metrics, and failures
layers but none import it — keeping the dependency flow one-directional.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_eval.domain import CaseExecutionState, EvalCase, FailureCode
from ai_eval.failures import FailureRecord, build_failures
from ai_eval.metrics import CaseMetricInput, MetricSummary, aggregate_metrics, build_metric_input
from ai_eval.parsing import ParseOutcome, ParseStatus, parse_triage_output
from ai_eval.scoring import CaseScore, evaluate_case


@dataclass
class ExecutionObservation:
    """Operational facts captured at invocation time, carried into metrics."""

    latency_ms: float | None = None
    cost_usd: float | None = None


@dataclass
class RunEvaluation:
    scores: list[CaseScore]
    inputs: list[CaseMetricInput]
    summary: MetricSummary
    failures: list[FailureRecord]
    parsed: list[dict[str, Any]]


def _no_output() -> ParseOutcome:
    return ParseOutcome(
        ParseStatus.EMPTY,
        failure_code=FailureCode.OUTPUT_EMPTY,
        message="no output captured (invocation error)",
    )


def evaluate_raw_outputs(
    items: list[tuple[EvalCase, str | None, bool]],
    observations: dict[str, ExecutionObservation] | None = None,
) -> RunEvaluation:
    """Score a run from ``(case, raw_output, invoked_ok)`` triples.

    ``observations`` optionally supplies per-case latency/cost (keyed by ``case_id``) so
    operational metrics can be aggregated alongside quality metrics.
    """
    obs_by_case = observations or {}
    scores: list[CaseScore] = []
    inputs: list[CaseMetricInput] = []
    parsed: list[dict[str, Any]] = []

    for case, raw, invoked_ok in items:
        parse = parse_triage_output(raw) if (invoked_ok and raw is not None) else _no_output()
        score = evaluate_case(case, parse)
        if not invoked_ok:
            score.state = CaseExecutionState.INVOCATION_ERROR

        observed_risk = parse.value.get("risk_level") if (parse.ok and parse.value) else None
        expected_risk = case.expected.get("risk_level") if isinstance(case.expected, dict) else None

        obs = obs_by_case.get(case.case_id, ExecutionObservation())
        scores.append(score)
        inputs.append(
            build_metric_input(
                case.case_id,
                case.criticality,
                invoked_ok=invoked_ok,
                expected_risk=expected_risk,
                observed_risk=observed_risk,
                score=score,
                latency_ms=obs.latency_ms,
                cost_usd=obs.cost_usd,
            )
        )
        parsed.append(
            {
                "case_id": case.case_id,
                "case_version": case.case_version,
                "parse_status": str(parse.status),
                "state": str(score.state),
                "output": parse.value if parse.ok else None,
            }
        )

    return RunEvaluation(
        scores=scores,
        inputs=inputs,
        summary=aggregate_metrics(inputs),
        failures=build_failures(scores),
        parsed=parsed,
    )
