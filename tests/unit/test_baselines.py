"""Baseline approval semantics and candidate-vs-baseline comparison."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_eval.baselines import (
    approve_baseline,
    build_baseline_candidate,
    compare_to_baseline,
    render_comparison_markdown,
)
from ai_eval.datasets import load_cases_dir
from ai_eval.domain import BaselineState
from ai_eval.evaluation import evaluate_raw_outputs
from ai_eval.targets import InvocationContext, get_recorded_target

REPO = Path(__file__).resolve().parents[2]
CASES = load_cases_dir(REPO / "datasets/reference/request_triage/v1/cases")
NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def _evaluate(target_name: str):
    adapter = get_recorded_target(target_name)
    items = []
    for case in CASES:
        ctx = InvocationContext(run_id="t", case_execution_id=f"t:{case.case_id}")
        res = adapter.invoke(case, ctx)
        items.append((case, res.raw_output, res.succeeded))
    return evaluate_raw_outputs(items)


def _baseline(evaluation, release_id: str = "rel_v1", release_hash: str = "sha256:rel"):
    return build_baseline_candidate(
        baseline_id="b1",
        workflow_ref="reference.request_triage.v1",
        run_id="run_base",
        dataset_release_id=release_id,
        dataset_release_hash=release_hash,
        evaluation=evaluation,
    )


def test_candidate_starts_unapproved_and_unusable() -> None:
    baseline = _baseline(_evaluate("recorded_pass"))
    assert baseline.state is BaselineState.CANDIDATE
    assert not baseline.is_usable


def test_approval_is_explicit() -> None:
    baseline = _baseline(_evaluate("recorded_pass"))
    approved = approve_baseline(baseline, approver="alice", rationale="reference", approved_at=NOW)
    assert approved.state is BaselineState.ACTIVE
    assert approved.is_usable
    assert approved.approved_by == "alice"
    # Re-approving an already-active baseline is rejected.
    with pytest.raises(ValueError):
        approve_baseline(approved, approver="bob", rationale="again", approved_at=NOW)


def test_baseline_snapshots_metrics_and_case_outcomes() -> None:
    baseline = _baseline(_evaluate("recorded_pass"))
    assert baseline.metrics["missing_information_recall"] == 1.0
    assert all(baseline.case_passed.values())
    assert baseline.critical_case_failures == 0


def test_regression_shows_newly_failing_cases_and_negative_delta() -> None:
    baseline = approve_baseline(
        _baseline(_evaluate("recorded_pass")), approver="a", rationale="r", approved_at=NOW
    )
    degraded = _evaluate("recorded_missing_information_regression")
    report = compare_to_baseline(
        baseline, degraded,
        candidate_run_id="run_cand",
        candidate_workflow_ref="reference.request_triage.v1",
        candidate_dataset_release_id="rel_v1",
        candidate_dataset_release_hash="sha256:rel",
    )
    assert report.compatible
    assert report.newly_failing_cases  # cases that passed on baseline now fail
    assert report.recovered_cases == []
    assert report.delta_for("missing_information_recall") == -1.0
    assert report.critical_case_failure_delta > 0
    assert "Baseline Comparison" in render_comparison_markdown(report)


def test_dataset_mismatch_is_flagged_incompatible() -> None:
    baseline = approve_baseline(
        _baseline(_evaluate("recorded_pass")), approver="a", rationale="r", approved_at=NOW
    )
    report = compare_to_baseline(
        baseline, _evaluate("recorded_pass"),
        candidate_run_id="run_cand",
        candidate_workflow_ref="reference.request_triage.v1",
        candidate_dataset_release_id="rel_v2",  # different release
        candidate_dataset_release_hash="sha256:other",
    )
    assert not report.compatible
    assert any("dataset release mismatch" in w for w in report.warnings)


def test_unapproved_baseline_is_flagged() -> None:
    candidate = _baseline(_evaluate("recorded_pass"))  # never approved
    report = compare_to_baseline(
        candidate, _evaluate("recorded_pass"),
        candidate_run_id="run_cand",
        candidate_workflow_ref="reference.request_triage.v1",
        candidate_dataset_release_id="rel_v1",
        candidate_dataset_release_hash="sha256:rel",
    )
    assert not report.compatible
    assert any("not approved" in w for w in report.warnings)
