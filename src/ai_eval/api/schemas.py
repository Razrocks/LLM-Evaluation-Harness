"""API request/response contracts (Pydantic v2).

These are transport shapes only. They wrap the domain models the service already speaks; they
never redefine a metric, a gate rule, or a baseline.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from ai_eval.execution import EvalPlan
from ai_eval.gates import GatePolicy


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateRunRequest(_Base):
    plan: EvalPlan
    gate_policy: GatePolicy | None = None
    run_id: str | None = None


class ApproveBaselineRequest(_Base):
    baseline_id: str
    run_id: str
    rationale: str


class EvaluateGateRequest(_Base):
    run_id: str
    policy: GatePolicy


class Capabilities(_Base):
    workflows: list[str]
    recorded_targets: list[str]
    providers: list[str]
    execution_mode: str
    endpoints: list[str]


class HealthResponse(_Base):
    status: str
    database: str


class RunSummary(_Base):
    model_config = ConfigDict(extra="allow")

    run_id: str
    status: str


def as_any(payload: dict[str, Any]) -> dict[str, Any]:
    return payload
