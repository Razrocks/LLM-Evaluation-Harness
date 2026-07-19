"""Pydantic model for ``request_triage.output.v1``.

Mirrors ``schemas/reference/request_triage_output.v1.json`` exactly: every field the schema
marks ``required`` has no default (so an omission is a schema failure, not a silent fill), and
``extra="forbid"`` rejects unexpected fields. This is the trusted output contract; model
self-confidence is deliberately absent.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ai_eval.domain import DeadlineKind, RiskLevel


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Task(_Base):
    task_id: str
    description: str
    owner_role: str | None
    due_date: str | None
    evidence_refs: list[str]


class Deadline(_Base):
    date: str | None
    kind: DeadlineKind
    evidence_refs: list[str]


class RiskReason(_Base):
    code: str
    description: str
    evidence_refs: list[str]


class MissingInfoItem(_Base):
    key: str
    label: str
    reason: str
    evidence_refs: list[str]


class MaterialClaim(_Base):
    claim: str
    evidence_refs: list[str]


class TriageOutput(_Base):
    """The canonical parsed candidate output for ``reference.request_triage.v1``."""

    summary: str
    tasks: list[Task]
    deadline: Deadline
    risk_level: RiskLevel
    risk_reasons: list[RiskReason]
    missing_information: list[MissingInfoItem]
    needs_attention: bool
    material_claims: list[MaterialClaim]
