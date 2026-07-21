"""Application service — the use cases the API and workers call.

It reuses the *same* domain contracts the CLI does: a run executes through
``harness.run_and_evaluate``, is persisted by the repositories, and every privileged action is
authorized server-side and audited. Nothing here reimplements scoring, gating, or comparison.

Each use case runs in one transactional scope, so a failure never leaves a half-written run.
Persisting a run is idempotent: re-publishing the same run_id (e.g. a retried worker job) is a
no-op, not an overwrite.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_eval.baselines import approve_baseline, build_baseline_from_snapshot
from ai_eval.config import Settings
from ai_eval.execution import EvalPlan
from ai_eval.gates import GatePolicy, evaluate_gate
from ai_eval.harness import RunOutcome, run_and_evaluate
from ai_eval.identity import Action, Principal, authorize
from ai_eval.metrics import MetricSummary
from ai_eval.storage import (
    AuditRepository,
    BaselineRepository,
    EvalRunRow,
    RunRepository,
    session_scope,
)
from ai_eval.storage.engine import build_engine, create_all, make_session_factory
from ai_eval.targets.factory import build_target


class RunNotFound(KeyError):
    pass


def _row_from_outcome(outcome: RunOutcome) -> EvalRunRow:
    manifest = json.loads((outcome.run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    summary = outcome.evaluation.summary
    case_passed = {s.case_id: s.passed for s in outcome.evaluation.scores}
    return EvalRunRow(
        run_id=outcome.run_id,
        workflow_ref=manifest["workflow_ref"],
        dataset_release_id=manifest["dataset_release_id"],
        dataset_release_hash=manifest["dataset_release_hash"],
        adapter_id=manifest["target_adapter"]["adapter_id"],
        adapter_version=manifest["target_adapter"]["adapter_version"],
        status="completed",
        artifacts_dir=str(outcome.run_dir),
        total_cases=summary.total_cases,
        cases_passed=sum(1 for passed in case_passed.values() if passed),
        critical_case_failures=summary.critical_case_failures,
        gate_outcome=str(outcome.gate.outcome) if outcome.gate else None,
        manifest=manifest,
        metric_summary=summary.model_dump(mode="json"),
        case_passed=case_passed,
        failures=[f.model_dump(mode="json") for f in outcome.evaluation.failures],
        gate_result=outcome.gate.model_dump(mode="json") if outcome.gate else None,
        comparison=outcome.comparison.model_dump(mode="json") if outcome.comparison else None,
    )


class ApplicationService:
    def __init__(self, *, database_url: str, repo_root: Path, runs_dir: Path) -> None:
        engine = build_engine(Settings(database_url, None, str(runs_dir), "sync"))
        create_all(engine)
        self._sessions = make_session_factory(engine)
        self.repo_root = repo_root
        self.runs_dir = runs_dir

    # --- runs ---------------------------------------------------------------------------

    def execute_run(
        self,
        principal: Principal,
        plan: EvalPlan,
        *,
        gate_policy: GatePolicy | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        authorize(principal, Action.EXECUTE_RUN)
        adapter = build_target(plan.target, repo_root=self.repo_root)
        outcome = run_and_evaluate(
            plan, adapter, repo_root=self.repo_root, runs_dir=self.runs_dir,
            run_id=run_id, gate_policy=gate_policy,
        )
        with session_scope(self._sessions) as session:
            runs = RunRepository(session)
            first_publish = not runs.exists(outcome.run_id)
            runs.add(_row_from_outcome(outcome))
            if first_publish:
                AuditRepository(session).record(
                    actor=principal.actor_id, role=str(principal.role), action="run.completed",
                    object_type="eval_run", object_id=outcome.run_id, new_state="completed",
                    correlation_id=outcome.run_id,
                )
        return self.get_run(outcome.run_id)

    def list_runs(
        self, *, workflow_ref: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        with session_scope(self._sessions) as session:
            rows = RunRepository(session).list(
                workflow_ref=workflow_ref, limit=limit, offset=offset
            )
            return [self._run_summary(r) for r in rows]

    def get_run(self, run_id: str) -> dict[str, Any]:
        with session_scope(self._sessions) as session:
            row = RunRepository(session).get(run_id)
            if row is None:
                raise RunNotFound(run_id)
            return self._run_detail(row)

    def get_run_results(self, run_id: str) -> dict[str, Any]:
        with session_scope(self._sessions) as session:
            row = RunRepository(session).get(run_id)
            if row is None:
                raise RunNotFound(run_id)
            return {
                "run_id": run_id, "metric_summary": row.metric_summary,
                "failures": row.failures, "gate_result": row.gate_result,
            }

    # --- baselines ----------------------------------------------------------------------

    def approve_baseline_from_run(
        self, principal: Principal, *, baseline_id: str, run_id: str, rationale: str
    ) -> dict[str, Any]:
        authorize(principal, Action.APPROVE_BASELINE)
        with session_scope(self._sessions) as session:
            row = RunRepository(session).get(run_id)
            if row is None:
                raise RunNotFound(run_id)
            summary = MetricSummary.model_validate(row.metric_summary)
            candidate = build_baseline_from_snapshot(
                baseline_id=baseline_id,
                workflow_ref=row.workflow_ref,
                run_id=row.run_id,
                dataset_release_id=row.dataset_release_id,
                dataset_release_hash=row.dataset_release_hash,
                metrics={m.name: m.value for m in summary.metrics},
                case_passed=dict(row.case_passed),
                critical_case_failures=row.critical_case_failures,
            )
            approved = approve_baseline(
                candidate, approver=principal.actor_id, rationale=rationale,
                approved_at=datetime.now(UTC),
            )
            BaselineRepository(session).upsert(approved)
            AuditRepository(session).record(
                actor=principal.actor_id, role=str(principal.role), action="baseline.approved",
                object_type="baseline", object_id=baseline_id,
                previous_state="candidate", new_state="active", rationale=rationale,
                correlation_id=run_id,
            )
            return approved.model_dump(mode="json")

    # --- gate ---------------------------------------------------------------------------

    def evaluate_stored_gate(
        self, principal: Principal, *, run_id: str, policy: GatePolicy
    ) -> dict[str, Any]:
        authorize(principal, Action.EVALUATE_GATE)
        with session_scope(self._sessions) as session:
            row = RunRepository(session).get(run_id)
            if row is None:
                raise RunNotFound(run_id)
            summary = MetricSummary.model_validate(row.metric_summary)
            return evaluate_gate(policy, summary, None).model_dump(mode="json")

    def get_audit(self, object_id: str) -> list[dict[str, Any]]:
        with session_scope(self._sessions) as session:
            return AuditRepository(session).list(object_id=object_id)

    # --- serialization helpers ----------------------------------------------------------

    @staticmethod
    def _run_summary(row: EvalRunRow) -> dict[str, Any]:
        return {
            "run_id": row.run_id, "workflow_ref": row.workflow_ref,
            "adapter_id": row.adapter_id, "status": row.status,
            "total_cases": row.total_cases, "cases_passed": row.cases_passed,
            "critical_case_failures": row.critical_case_failures,
            "gate_outcome": row.gate_outcome, "created_at": row.created_at.isoformat(),
        }

    @classmethod
    def _run_detail(cls, row: EvalRunRow) -> dict[str, Any]:
        detail = cls._run_summary(row)
        detail.update({
            "dataset_release_id": row.dataset_release_id,
            "manifest": row.manifest, "metric_summary": row.metric_summary,
            "gate_result": row.gate_result, "comparison": row.comparison,
            "artifacts_dir": row.artifacts_dir,
        })
        return detail
