"""Baseline manifests — an explicitly approved run used as the comparison reference.

A baseline is *not* automatically the best-scoring run. It is a human decision with a scope,
an approver, and declared limitations. It snapshots the approved run's metric values and
per-case outcomes so a later candidate can be compared without re-running it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import BaselineState
from ai_eval.evaluation import RunEvaluation


class Baseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_id: str
    baseline_version: str = "v1"
    workflow_ref: str
    run_id: str
    dataset_release_id: str
    dataset_release_hash: str
    state: BaselineState = BaselineState.CANDIDATE
    approved_by: str | None = None
    approved_at: datetime | None = None
    rationale: str | None = None
    limitations: list[str] = Field(default_factory=list)
    # Snapshots taken from the approved run.
    metrics: dict[str, float | None] = Field(default_factory=dict)
    case_passed: dict[str, bool] = Field(default_factory=dict)
    critical_case_failures: int = 0

    @property
    def is_usable(self) -> bool:
        """Only an approved/active baseline may back a publishable comparison."""
        return self.state in (BaselineState.APPROVED, BaselineState.ACTIVE)


def build_baseline_candidate(
    *,
    baseline_id: str,
    workflow_ref: str,
    run_id: str,
    dataset_release_id: str,
    dataset_release_hash: str,
    evaluation: RunEvaluation,
    limitations: list[str] | None = None,
) -> Baseline:
    """Snapshot a completed run as a baseline **candidate** (not yet approved)."""
    return Baseline(
        baseline_id=baseline_id,
        workflow_ref=workflow_ref,
        run_id=run_id,
        dataset_release_id=dataset_release_id,
        dataset_release_hash=dataset_release_hash,
        state=BaselineState.CANDIDATE,
        limitations=limitations or [],
        metrics={m.name: m.value for m in evaluation.summary.metrics},
        case_passed={s.case_id: s.passed for s in evaluation.scores},
        critical_case_failures=evaluation.summary.critical_case_failures,
    )


def build_baseline_from_snapshot(
    *,
    baseline_id: str,
    workflow_ref: str,
    run_id: str,
    dataset_release_id: str,
    dataset_release_hash: str,
    metrics: dict[str, float | None],
    case_passed: dict[str, bool],
    critical_case_failures: int,
    limitations: list[str] | None = None,
) -> Baseline:
    """Build a baseline **candidate** from a stored run's snapshots (no re-execution needed)."""
    return Baseline(
        baseline_id=baseline_id,
        workflow_ref=workflow_ref,
        run_id=run_id,
        dataset_release_id=dataset_release_id,
        dataset_release_hash=dataset_release_hash,
        state=BaselineState.CANDIDATE,
        limitations=limitations or [],
        metrics=metrics,
        case_passed=case_passed,
        critical_case_failures=critical_case_failures,
    )


def approve_baseline(
    baseline: Baseline, *, approver: str, rationale: str, approved_at: datetime
) -> Baseline:
    """Explicit human approval. The highest score never auto-promotes."""
    if baseline.state is not BaselineState.CANDIDATE:
        raise ValueError(f"only a CANDIDATE baseline can be approved (state={baseline.state})")
    return baseline.model_copy(
        update={
            "state": BaselineState.ACTIVE,
            "approved_by": approver,
            "rationale": rationale,
            "approved_at": approved_at,
        }
    )
