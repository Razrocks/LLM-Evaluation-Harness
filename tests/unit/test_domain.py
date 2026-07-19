"""Domain model + hashing tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_eval.domain import (
    Assertion,
    AssertionType,
    OnUnevaluable,
    Provenance,
    ProvenanceOrigin,
    Review,
    ReviewStatus,
    Severity,
    canonical_json,
    content_hash,
)
from ai_eval.domain.models import EvalCase


def _assertion() -> Assertion:
    return Assertion(
        assertion_id="risk",
        type=AssertionType.CATEGORICAL_EQUAL,
        scorer_ref="categorical_equal.v1",
        observed_selector="$.risk_level",
        expected="high",
        required=True,
        severity=Severity.MAJOR,
        on_unevaluable=OnUnevaluable.FAIL,
    )


def _case(**overrides: object) -> EvalCase:
    data: dict[str, object] = dict(
        case_id="c1",
        case_version=1,
        workflow_ref="reference.request_triage.v1",
        input={"request_id": "r1"},
        expected={"risk_level": "high"},
        assertions=[_assertion()],
        provenance=Provenance(origin=ProvenanceOrigin.SYNTHETIC, author_id="a"),
        review=Review(status=ReviewStatus.APPROVED),
    )
    data.update(overrides)
    return EvalCase(**data)  # type: ignore[arg-type]


# --- hashing ------------------------------------------------------------------------------


def test_canonical_json_is_key_order_invariant() -> None:
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_content_hash_has_sha256_prefix() -> None:
    assert content_hash({"a": 1}).startswith("sha256:")


def test_content_hash_excludes_content_hash_field() -> None:
    base = {"a": 1}
    with_hash = {"a": 1, "content_hash": "sha256:whatever"}
    assert content_hash(base) == content_hash(with_hash)


def test_content_hash_changes_with_content() -> None:
    assert content_hash({"a": 1}) != content_hash({"a": 2})


# --- models -------------------------------------------------------------------------------


def test_eval_case_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _case(surprise="nope")


def test_eval_case_requires_at_least_one_assertion() -> None:
    with pytest.raises(ValidationError):
        _case(assertions=[])


def test_case_version_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        _case(case_version=0)


def test_is_approved_property() -> None:
    assert _case().is_approved is True
    assert _case(review=Review(status=ReviewStatus.DRAFT)).is_approved is False


def test_case_round_trips_through_json() -> None:
    case = _case()
    dumped = case.model_dump(mode="json")
    assert EvalCase.model_validate(dumped) == case
