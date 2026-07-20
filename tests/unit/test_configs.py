"""Shipped configs must satisfy both their JSON Schema and their runtime model.

A gate policy or plan that only validates in one of the two would drift silently.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_eval.execution import EvalPlan
from ai_eval.gates import load_gate_policy

REPO = Path(__file__).resolve().parents[2]
GATES = sorted((REPO / "configs" / "gates").glob("*.json"))
PLANS = sorted((REPO / "configs" / "plans").glob("*.json"))


def test_configs_exist() -> None:
    assert GATES, "no gate policies shipped"
    assert PLANS, "no eval plans shipped"


@pytest.mark.parametrize("path", GATES, ids=lambda p: p.name)
def test_gate_policy_matches_schema_and_model(path: Path) -> None:
    schema = json.loads((REPO / "schemas" / "gate_policy.v1.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(json.loads(path.read_text(encoding="utf-8")))
    policy = load_gate_policy(path)
    assert policy.rules
    # Every rule that reads a metric must name one.
    for rule in policy.rules:
        if rule.type.value.startswith(("metric_", "baseline_delta_")):
            assert rule.metric, f"rule '{rule.rule_id}' has no metric"


@pytest.mark.parametrize("path", PLANS, ids=lambda p: p.name)
def test_plan_matches_model_and_points_at_real_files(path: Path) -> None:
    plan = EvalPlan.model_validate(json.loads(path.read_text(encoding="utf-8")))
    assert (REPO / plan.dataset_manifest_path).exists(), plan.dataset_manifest_path
    assert plan.target.adapter_id
    assert plan.workflow_ref == "reference.request_triage.v1"
