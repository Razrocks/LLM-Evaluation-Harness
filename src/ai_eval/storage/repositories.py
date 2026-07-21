"""Repositories — the only code that reads and writes the ORM rows.

They translate between persistence rows and plain dicts/domain values; the service layer above
never sees a SQLAlchemy model, and the domain layer never imports one. Completed runs are
insert-only (invariant #12): there is deliberately no ``update_run``. Audit is append-only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_eval.baselines import Baseline
from ai_eval.domain import BaselineState

from .models import AuditEventRow, BaselineRow, EvalRunRow


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def exists(self, run_id: str) -> bool:
        return self.session.get(EvalRunRow, run_id) is not None

    def add(self, row: EvalRunRow) -> None:
        # Insert-only: a completed run is immutable. Re-persisting the same run_id is a no-op
        # (idempotent worker publish), never an overwrite.
        if not self.exists(row.run_id):
            self.session.add(row)

    def get(self, run_id: str) -> EvalRunRow | None:
        return self.session.get(EvalRunRow, run_id)

    def list(
        self, *, workflow_ref: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[EvalRunRow]:
        stmt = select(EvalRunRow).order_by(EvalRunRow.created_at.desc())
        if workflow_ref is not None:
            stmt = stmt.where(EvalRunRow.workflow_ref == workflow_ref)
        return list(self.session.scalars(stmt.limit(limit).offset(offset)))


class BaselineRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, baseline: Baseline) -> None:
        key = (baseline.baseline_id, baseline.baseline_version)
        row = self.session.get(BaselineRow, key)
        payload = baseline.model_dump(mode="json")
        if row is None:
            self.session.add(
                BaselineRow(
                    baseline_id=baseline.baseline_id,
                    baseline_version=baseline.baseline_version,
                    workflow_ref=baseline.workflow_ref,
                    run_id=baseline.run_id,
                    dataset_release_id=baseline.dataset_release_id,
                    dataset_release_hash=baseline.dataset_release_hash,
                    state=str(baseline.state),
                    approved_by=baseline.approved_by,
                    approved_at=baseline.approved_at,
                    rationale=baseline.rationale,
                    payload=payload,
                )
            )
        else:
            row.state = str(baseline.state)
            row.approved_by = baseline.approved_by
            row.approved_at = baseline.approved_at
            row.rationale = baseline.rationale
            row.payload = payload

    def get(self, baseline_id: str, version: str = "v1") -> Baseline | None:
        row = self.session.get(BaselineRow, (baseline_id, version))
        return Baseline.model_validate(row.payload) if row is not None else None

    def active_for(self, workflow_ref: str) -> Baseline | None:
        stmt = (
            select(BaselineRow)
            .where(BaselineRow.workflow_ref == workflow_ref)
            .where(BaselineRow.state == str(BaselineState.ACTIVE))
            .order_by(BaselineRow.created_at.desc())
        )
        row = self.session.scalars(stmt).first()
        return Baseline.model_validate(row.payload) if row is not None else None


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        actor: str,
        role: str,
        action: str,
        object_type: str,
        object_id: str,
        previous_state: str | None = None,
        new_state: str | None = None,
        rationale: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.session.add(
            AuditEventRow(
                actor=actor, role=role, action=action, object_type=object_type,
                object_id=object_id, previous_state=previous_state, new_state=new_state,
                rationale=rationale, correlation_id=correlation_id,
            )
        )

    def list(self, *, object_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        stmt = select(AuditEventRow).order_by(AuditEventRow.created_at.desc())
        if object_id is not None:
            stmt = stmt.where(AuditEventRow.object_id == object_id)
        return [
            {
                "id": r.id, "actor": r.actor, "role": r.role, "action": r.action,
                "object_type": r.object_type, "object_id": r.object_id,
                "previous_state": r.previous_state, "new_state": r.new_state,
                "rationale": r.rationale, "correlation_id": r.correlation_id,
                "created_at": r.created_at.isoformat(),
            }
            for r in self.session.scalars(stmt.limit(limit))
        ]
