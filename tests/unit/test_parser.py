"""Parser keeps malformed JSON, schema-invalid JSON, and empty output distinct (ADR 0002)."""

from __future__ import annotations

import json

from ai_eval.domain import FailureCode
from ai_eval.parsing import ParseStatus, parse_triage_output

VALID = {
    "summary": "s",
    "tasks": [],
    "deadline": {"date": "2026-07-17", "kind": "explicit_relative", "evidence_refs": []},
    "risk_level": "high",
    "risk_reasons": [],
    "missing_information": [],
    "needs_attention": True,
    "material_claims": [],
}


def test_valid_output_parses() -> None:
    outcome = parse_triage_output(json.dumps(VALID))
    assert outcome.ok
    assert outcome.status is ParseStatus.PARSED
    assert outcome.model is not None and outcome.model.risk_level == "high"


def test_empty_is_empty_not_parse_error() -> None:
    for raw in ("", "   ", None):
        outcome = parse_triage_output(raw)
        assert outcome.status is ParseStatus.EMPTY
        assert outcome.failure_code is FailureCode.OUTPUT_EMPTY


def test_malformed_json_is_parse_error() -> None:
    outcome = parse_triage_output("{not valid json")
    assert outcome.status is ParseStatus.PARSE_ERROR
    assert outcome.failure_code is FailureCode.OUTPUT_PARSE_ERROR
    assert outcome.model is None


def test_missing_required_field_is_schema_error() -> None:
    bad = {k: v for k, v in VALID.items() if k != "summary"}
    outcome = parse_triage_output(json.dumps(bad))
    assert outcome.status is ParseStatus.SCHEMA_ERROR
    assert outcome.failure_code is FailureCode.OUTPUT_SCHEMA_INVALID
    assert outcome.errors  # validation errors retained as evidence


def test_extra_field_is_schema_error() -> None:
    outcome = parse_triage_output(json.dumps({**VALID, "confidence": 0.9}))
    assert outcome.status is ParseStatus.SCHEMA_ERROR


def test_bad_enum_is_schema_error() -> None:
    outcome = parse_triage_output(json.dumps({**VALID, "risk_level": "urgent"}))
    assert outcome.status is ParseStatus.SCHEMA_ERROR


def test_no_silent_repair_on_schema_error() -> None:
    # A schema-invalid payload never yields a usable model.
    outcome = parse_triage_output(json.dumps({**VALID, "risk_level": "urgent"}))
    assert outcome.model is None
    assert not outcome.ok
