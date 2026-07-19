"""Gate policy model — thresholds live in versioned data, never in code.

Mirrors ``schemas/gate_policy.v1.json``. A policy is a list of deterministic rules over
metrics, critical-case outcomes, and baseline deltas.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import GateRuleType, Severity


class GateRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    type: GateRuleType
    metric: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    minimum_delta: float | None = None
    maximum_delta: float | None = None
    requires_baseline: bool = False
    min_sample_size: int | None = None
    severity: Severity = Severity.MAJOR


class GatePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_id: str
    gate_version: str
    description: str | None = None
    rules: list[GateRule] = Field(min_length=1)


def load_gate_policy(path: Path) -> GatePolicy:
    return GatePolicy.model_validate(json.loads(path.read_text(encoding="utf-8")))
