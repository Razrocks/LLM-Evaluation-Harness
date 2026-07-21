"""SQLAlchemy ORM models — the relational system of record (M6).

These rows persist what a run *produced*; they never recompute it. Large raw artifacts stay on
the filesystem/object store under ``artifacts_dir`` and are referenced, not inlined. JSON columns
carry the already-computed manifest, metric summary, gate result, and failure inventory, so the
API can serve them without re-running anything.

Immutability (invariant #12) is enforced by the repository, which offers no update path for a
completed run and appends audit events rather than mutating history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class EvalRunRow(Base):
    __tablename__ = "eval_runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_ref: Mapped[str] = mapped_column(String(128), index=True)
    dataset_release_id: Mapped[str] = mapped_column(String(128), index=True)
    dataset_release_hash: Mapped[str] = mapped_column(String(128))
    adapter_id: Mapped[str] = mapped_column(String(128), index=True)
    adapter_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    artifacts_dir: Mapped[str] = mapped_column(Text)
    total_cases: Mapped[int] = mapped_column(Integer)
    cases_passed: Mapped[int] = mapped_column(Integer)
    critical_case_failures: Mapped[int] = mapped_column(Integer)
    gate_outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON)
    metric_summary: Mapped[dict[str, Any]] = mapped_column(JSON)
    case_passed: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    failures: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    gate_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    comparison: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class BaselineRow(Base):
    __tablename__ = "baselines"

    baseline_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    baseline_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_ref: Mapped[str] = mapped_column(String(128), index=True)
    run_id: Mapped[str] = mapped_column(String(128), index=True)
    dataset_release_id: Mapped[str] = mapped_column(String(128))
    dataset_release_hash: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(32), index=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuditEventRow(Base):
    """Append-only record of privileged state transitions; history is never rewritten."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), index=True)
    object_type: Mapped[str] = mapped_column(String(64))
    object_id: Mapped[str] = mapped_column(String(256), index=True)
    previous_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
