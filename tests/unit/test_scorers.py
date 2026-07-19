"""Per-scorer pass/fail behavior and failure-code classification, plus invariant #8."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from ai_eval.datasets import load_cases_dir
from ai_eval.domain import (
    Assertion,
    AssertionResultStatus,
    AssertionType,
    FailureCode,
    OnUnevaluable,
    Severity,
)
from ai_eval.parsing import parse_triage_output
from ai_eval.scoring import ScoringContext, evaluate_case, get_scorer
from ai_eval.targets import build_correct_output

REPO = Path(__file__).resolve().parents[2]
CASES = {c.case_id: c for c in load_cases_dir(REPO / "datasets/reference/request_triage/v1/cases")}
CASE = CASES["request_triage_001"]
CORRECT = build_correct_output(CASE)


def _ctx(output: dict) -> ScoringContext:
    return ScoringContext.build(CASE, parse_triage_output(json.dumps(output)))


def _score(scorer_ref: str, atype: AssertionType, output: dict, **kw: object):
    scorer = get_scorer(scorer_ref)
    assert scorer is not None
    assertion = Assertion(
        assertion_id="a",
        type=atype,
        scorer_ref=scorer_ref,
        required=True,
        severity=Severity.MAJOR,
        on_unevaluable=OnUnevaluable.FAIL,
        **kw,
    )
    return scorer(assertion, _ctx(output))


def _codes(result) -> set[str]:
    return set(result.failure_codes)


def test_schema_valid_pass_and_fail() -> None:
    assert _score("schema_valid.v1", AssertionType.SCHEMA_VALID, CORRECT).passed
    bad = {k: v for k, v in CORRECT.items() if k != "summary"}
    res = _score("schema_valid.v1", AssertionType.SCHEMA_VALID, bad)
    assert not res.passed
    assert FailureCode.OUTPUT_SCHEMA_INVALID.value in _codes(res)


def test_normalized_date_equal() -> None:
    ok = _score("normalized_date_equal.v1", AssertionType.NORMALIZED_DATE_EQUAL, CORRECT,
                observed_selector="$.deadline.date", expected="2026-07-17")
    assert ok.passed
    wrong = copy.deepcopy(CORRECT)
    wrong["deadline"]["date"] = "2026-07-18"
    res = _score("normalized_date_equal.v1", AssertionType.NORMALIZED_DATE_EQUAL, wrong,
                 observed_selector="$.deadline.date", expected="2026-07-17")
    assert FailureCode.DEADLINE_MISSED.value in _codes(res)


def test_risk_under_and_over_classification() -> None:
    under = copy.deepcopy(CORRECT)
    under["risk_level"] = "medium"
    res = _score("categorical_equal.v1", AssertionType.CATEGORICAL_EQUAL, under,
                 observed_selector="$.risk_level", expected="high")
    assert FailureCode.RISK_UNDERCLASSIFIED.value in _codes(res)

    over = copy.deepcopy(CORRECT)
    over["risk_level"] = "high"
    res = _score("categorical_equal.v1", AssertionType.CATEGORICAL_EQUAL, over,
                 observed_selector="$.risk_level", expected="low")
    assert FailureCode.RISK_OVERCLASSIFIED.value in _codes(res)


def test_needs_attention_boolean() -> None:
    flipped = copy.deepcopy(CORRECT)
    flipped["needs_attention"] = not CORRECT["needs_attention"]
    res = _score("boolean_equal.v1", AssertionType.BOOLEAN_EQUAL, flipped,
                 observed_selector="$.needs_attention", expected=CORRECT["needs_attention"])
    assert FailureCode.NEEDS_ATTENTION_INCORRECT.value in _codes(res)


def test_missing_info_recall_and_alias() -> None:
    dropped = copy.deepcopy(CORRECT)
    dropped["missing_information"] = []
    res = _score("set_precision_recall_f1.v1", AssertionType.SET_PRECISION_RECALL_F1, dropped,
                 observed_selector="$.missing_information[*].key",
                 expected=["amount_or_scope_breakdown"], params={"minimum_recall": 1.0})
    assert not res.passed
    assert FailureCode.MISSING_INFO_OMITTED.value in _codes(res)
    assert res.metadata["recall"] == 0.0

    aliased = copy.deepcopy(CORRECT)
    aliased["missing_information"] = [
        {"key": "line_item_detail", "label": "x", "reason": "y", "evidence_refs": []}
    ]
    res = _score("set_precision_recall_f1.v1", AssertionType.SET_PRECISION_RECALL_F1, aliased,
                 observed_selector="$.missing_information[*].key",
                 expected=["amount_or_scope_breakdown"], params={"minimum_recall": 1.0})
    assert res.passed  # alias normalized to canonical key
    assert res.normalization and res.normalization[0]["canonical"] == "amount_or_scope_breakdown"


def test_evidence_reference_valid() -> None:
    ok = _score("evidence_reference_valid.v1", AssertionType.EVIDENCE_REFERENCE_VALID, CORRECT)
    assert ok.passed
    bad = copy.deepcopy(CORRECT)
    bad["deadline"]["evidence_refs"] = ["nonexistent_source#span-1"]
    res = _score("evidence_reference_valid.v1", AssertionType.EVIDENCE_REFERENCE_VALID, bad)
    assert FailureCode.INVALID_EVIDENCE_REFERENCE.value in _codes(res)


def test_unsupported_material_claim() -> None:
    assert _score(
        "unsupported_material_claim_absent.v1",
        AssertionType.UNSUPPORTED_MATERIAL_CLAIM_ABSENT, CORRECT).passed
    invented = copy.deepcopy(CORRECT)
    invented["material_claims"].append(
        {"claim": "The total owed is CAD 9,999.", "evidence_refs": ["invoice_001#span-1"]}
    )
    res = _score("unsupported_material_claim_absent.v1",
                 AssertionType.UNSUPPORTED_MATERIAL_CLAIM_ABSENT, invented)
    assert FailureCode.UNSUPPORTED_MATERIAL_CLAIM.value in _codes(res)


def test_every_assertion_gets_a_result() -> None:
    parse = parse_triage_output(json.dumps(CORRECT))
    score = evaluate_case(CASE, parse)
    assert len(score.results) == len(CASE.assertions)
    assert score.passed


def test_unknown_scorer_becomes_scorer_error() -> None:
    broken = CASE.model_copy(deep=True)
    broken.assertions[0].scorer_ref = "does_not_exist.v1"
    score = evaluate_case(broken, parse_triage_output(json.dumps(CORRECT)))
    err = next(r for r in score.results if r.scorer_ref == "does_not_exist.v1")
    assert err.status is AssertionResultStatus.ERROR
    assert FailureCode.SCORER_ERROR.value in err.failure_codes
