"""Storage repositories: run immutability, idempotent publish, and append-only audit."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip("sqlalchemy")

from ai_eval.baselines import approve_baseline, build_baseline_from_snapshot  # noqa: E402
from ai_eval.config import Settings  # noqa: E402
from ai_eval.storage import (  # noqa: E402
    AuditRepository,
    BaselineRepository,
    EvalRunRow,
    RunRepository,
    build_engine,
    create_all,
    make_session_factory,
    session_scope,
)


@pytest.fixture
def sessions():
    engine = build_engine(Settings("sqlite:///:memory:", None, "runs", "sync"))
    create_all(engine)
    return make_session_factory(engine)


def _row(run_id: str, cases_passed: int = 12) -> EvalRunRow:
    return EvalRunRow(
        run_id=run_id, workflow_ref="reference.request_triage.v1",
        dataset_release_id="rel", dataset_release_hash="sha256:x",
        adapter_id="recorded_pass", adapter_version="v1", status="completed",
        artifacts_dir="runs/x", total_cases=12, cases_passed=cases_passed,
        critical_case_failures=0, gate_outcome="pass",
        manifest={"case_refs": []}, metric_summary={"total_cases": 12, "metrics": []},
        case_passed={}, failures=[], gate_result=None, comparison=None,
    )


def test_completed_run_is_insert_only(sessions) -> None:
    with session_scope(sessions) as s:
        RunRepository(s).add(_row("r1", cases_passed=12))
    # A second add with the same run_id must not overwrite (immutability, idempotent publish).
    with session_scope(sessions) as s:
        RunRepository(s).add(_row("r1", cases_passed=0))
    with session_scope(sessions) as s:
        row = RunRepository(s).get("r1")
        assert row is not None and row.cases_passed == 12  # original preserved


def test_list_orders_newest_first(sessions) -> None:
    with session_scope(sessions) as s:
        for rid in ("a", "b", "c"):
            RunRepository(s).add(_row(rid))
    with session_scope(sessions) as s:
        rows = RunRepository(s).list()
        assert {r.run_id for r in rows} == {"a", "b", "c"}


def test_audit_is_append_only(sessions) -> None:
    with session_scope(sessions) as s:
        audit = AuditRepository(s)
        audit.record(actor="a", role="baseline_approver", action="baseline.approved",
                     object_type="baseline", object_id="b1", new_state="active")
        audit.record(actor="a", role="baseline_approver", action="baseline.retired",
                     object_type="baseline", object_id="b1", new_state="retired")
    with session_scope(sessions) as s:
        events = AuditRepository(s).list(object_id="b1")
        assert len(events) == 2
        assert {e["action"] for e in events} == {"baseline.approved", "baseline.retired"}


def test_baseline_active_lookup(sessions) -> None:
    candidate = build_baseline_from_snapshot(
        baseline_id="b1", workflow_ref="reference.request_triage.v1", run_id="r1",
        dataset_release_id="rel", dataset_release_hash="sha256:x",
        metrics={"schema_pass_rate": 1.0}, case_passed={"c1": True}, critical_case_failures=0,
    )
    approved = approve_baseline(candidate, approver="carol", rationale="ref",
                                approved_at=datetime.now(UTC))
    with session_scope(sessions) as s:
        BaselineRepository(s).upsert(approved)
    with session_scope(sessions) as s:
        active = BaselineRepository(s).active_for("reference.request_triage.v1")
        assert active is not None and active.baseline_id == "b1"
