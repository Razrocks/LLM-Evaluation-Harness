"""Candidate-vs-baseline comparison.

Produces metric deltas, newly failing / recovered cases, and failure-code deltas — plus
explicit **compatibility warnings**. Comparing runs that used different dataset releases or
workflows is not silently allowed: the report says so, and the gate can treat it as INVALID.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.evaluation import RunEvaluation
from ai_eval.failures import failure_code_counts

from .models import Baseline


class MetricDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    baseline_value: float | None
    candidate_value: float | None
    delta: float | None


class ComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_id: str
    baseline_run_id: str
    candidate_run_id: str
    compatible: bool
    warnings: list[str] = Field(default_factory=list)
    deltas: list[MetricDelta] = Field(default_factory=list)
    newly_failing_cases: list[str] = Field(default_factory=list)
    recovered_cases: list[str] = Field(default_factory=list)
    failure_code_deltas: dict[str, int] = Field(default_factory=dict)
    critical_case_failure_delta: int = 0

    def delta_for(self, metric: str) -> float | None:
        for d in self.deltas:
            if d.metric == metric:
                return d.delta
        return None


def compare_to_baseline(
    baseline: Baseline,
    evaluation: RunEvaluation,
    *,
    candidate_run_id: str,
    candidate_workflow_ref: str,
    candidate_dataset_release_id: str,
    candidate_dataset_release_hash: str,
) -> ComparisonReport:
    """Compare a live evaluation against a baseline."""
    return compare_snapshots(
        baseline,
        candidate_metrics={m.name: m.value for m in evaluation.summary.metrics},
        candidate_case_passed={s.case_id: s.passed for s in evaluation.scores},
        candidate_critical_failures=evaluation.summary.critical_case_failures,
        candidate_failure_codes=failure_code_counts(evaluation.failures),
        candidate_run_id=candidate_run_id,
        candidate_workflow_ref=candidate_workflow_ref,
        candidate_dataset_release_id=candidate_dataset_release_id,
        candidate_dataset_release_hash=candidate_dataset_release_hash,
    )


def compare_snapshots(
    baseline: Baseline,
    *,
    candidate_metrics: dict[str, float | None],
    candidate_case_passed: dict[str, bool],
    candidate_critical_failures: int,
    candidate_failure_codes: dict[str, int],
    candidate_run_id: str,
    candidate_workflow_ref: str,
    candidate_dataset_release_id: str,
    candidate_dataset_release_hash: str,
) -> ComparisonReport:
    """Compare from plain snapshots, so a stored run's artifacts can be compared later."""
    warnings: list[str] = []
    if not baseline.is_usable:
        warnings.append(f"baseline '{baseline.baseline_id}' is not approved (state={baseline.state})")
    if baseline.workflow_ref != candidate_workflow_ref:
        warnings.append(
            f"workflow mismatch: baseline '{baseline.workflow_ref}' vs candidate "
            f"'{candidate_workflow_ref}'"
        )
    if baseline.dataset_release_id != candidate_dataset_release_id:
        warnings.append(
            f"dataset release mismatch: baseline '{baseline.dataset_release_id}' vs candidate "
            f"'{candidate_dataset_release_id}'"
        )
    elif baseline.dataset_release_hash != candidate_dataset_release_hash:
        warnings.append("dataset release hash differs for the same release id (content drift)")

    names = sorted(set(baseline.metrics) | set(candidate_metrics))
    deltas = []
    for name in names:
        b, c = baseline.metrics.get(name), candidate_metrics.get(name)
        delta = (c - b) if (b is not None and c is not None) else None
        deltas.append(MetricDelta(metric=name, baseline_value=b, candidate_value=c, delta=delta))

    newly_failing = sorted(
        cid for cid, passed in candidate_case_passed.items()
        if not passed and baseline.case_passed.get(cid, False)
    )
    recovered = sorted(
        cid for cid, passed in candidate_case_passed.items()
        if passed and cid in baseline.case_passed and not baseline.case_passed[cid]
    )

    return ComparisonReport(
        baseline_id=baseline.baseline_id,
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate_run_id,
        compatible=not warnings,
        warnings=warnings,
        deltas=deltas,
        newly_failing_cases=newly_failing,
        recovered_cases=recovered,
        failure_code_deltas=candidate_failure_codes,
        critical_case_failure_delta=(
            candidate_critical_failures - baseline.critical_case_failures
        ),
    )


def render_comparison_markdown(report: ComparisonReport) -> str:
    lines = ["# Baseline Comparison", ""]
    lines.append(f"- Baseline: `{report.baseline_id}` (run `{report.baseline_run_id}`)")
    lines.append(f"- Candidate run: `{report.candidate_run_id}`")
    lines.append(f"- Compatible: **{report.compatible}**")
    if report.warnings:
        lines += ["", "## ⚠ Compatibility warnings", ""]
        lines += [f"- {w}" for w in report.warnings]
    lines += ["", "## Metric deltas", "", "| metric | baseline | candidate | delta |", "|---|---|---|---|"]
    for d in report.deltas:
        lines.append(f"| {d.metric} | {d.baseline_value} | {d.candidate_value} | {d.delta} |")
    lines += ["", "## Case movement", ""]
    lines.append(f"- Newly failing: {report.newly_failing_cases or '—'}")
    lines.append(f"- Recovered: {report.recovered_cases or '—'}")
    lines.append(f"- Critical-case failure delta: {report.critical_case_failure_delta}")
    return "\n".join(lines) + "\n"
