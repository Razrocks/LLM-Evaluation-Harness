"""Target-adapter contract tests: envelope shape + recorded-fixture behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ai_eval.datasets import load_cases_dir
from ai_eval.domain.models import EvalCase
from ai_eval.targets import (
    InvocationContext,
    RecordedDeadlineRegression,
    RecordedEvidenceRegression,
    RecordedMissingInformationRegression,
    RecordedPass,
    RecordedSchemaFailure,
    TargetAdapter,
    get_recorded_target,
)

REPO = Path(__file__).resolve().parents[2]
CASES = load_cases_dir(REPO / "datasets" / "reference" / "request_triage" / "v1" / "cases")


def _ctx() -> InvocationContext:
    return InvocationContext(run_id="r", case_execution_id="cx")


def _output_validator() -> Draft202012Validator:
    resources = []
    for path in (REPO / "schemas").rglob("*.json"):
        if "examples" in path.parts:
            continue
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    out_path = REPO / "schemas" / "reference" / "request_triage_output.v1.json"
    out = json.loads(out_path.read_text(encoding="utf-8"))
    return Draft202012Validator(out, registry=registry)


def _invoke(adapter: TargetAdapter, case: EvalCase) -> dict:
    raw = adapter.invoke(case, _ctx()).raw_output
    assert raw is not None
    return json.loads(raw)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.case_id)
def test_recorded_pass_output_is_schema_valid(case: EvalCase) -> None:
    out = _invoke(RecordedPass(), case)
    errors = sorted(_output_validator().iter_errors(out), key=lambda e: list(map(str, e.path)))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_invocation_envelope_fields() -> None:
    result = RecordedPass().invoke(CASES[0], _ctx())
    assert result.adapter_id == "recorded_pass"
    assert result.adapter_version == "v1"
    assert result.target_workflow_ref == "reference.request_triage.v1"
    assert result.request_hash.startswith("sha256:")
    assert isinstance(result.raw_output, str)
    assert result.succeeded and result.error is None
    assert result.attempts and result.attempts[0].number == 1
    assert result.config_refs.get("kind") == "recorded"


def test_missing_information_regression_drops_items() -> None:
    case = next(c for c in CASES if c.expected.get("missing_information"))
    assert _invoke(RecordedMissingInformationRegression(), case)["missing_information"] == []


def test_deadline_regression_shifts_date() -> None:
    case = next(c for c in CASES if c.expected["deadline"]["date"])
    out = _invoke(RecordedDeadlineRegression(), case)
    assert out["deadline"]["date"] != case.expected["deadline"]["date"]


def test_evidence_regression_cites_nonexistent_reference() -> None:
    out = _invoke(RecordedEvidenceRegression(), CASES[0])
    assert out["deadline"]["evidence_refs"] == ["nonexistent#span-999"]


def test_schema_failure_output_is_invalid() -> None:
    out = _invoke(RecordedSchemaFailure(), CASES[0])
    assert list(_output_validator().iter_errors(out)), "expected schema-invalid output"


def test_unknown_recorded_target_raises() -> None:
    with pytest.raises(KeyError):
        get_recorded_target("does_not_exist")
