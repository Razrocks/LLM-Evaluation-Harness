"""Dataset loader / validator / release-freezer tests, plus the frozen reference release."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_eval.datasets import (
    ReleaseError,
    build_release,
    dump_cases_jsonl,
    finalize_case_hashes,
    load_cases_dir,
    load_cases_jsonl,
    validate_case,
    validate_dataset,
)
from ai_eval.domain import (
    Assertion,
    AssertionType,
    FailureCode,
    OnUnevaluable,
    Provenance,
    ProvenanceOrigin,
    Review,
    ReviewStatus,
    Severity,
)
from ai_eval.domain.models import EvalCase

REPO_ROOT = Path(__file__).resolve().parents[2]
REF_V1 = REPO_ROOT / "datasets" / "reference" / "request_triage" / "v1"

WORKFLOW = "reference.request_triage.v1"


def _assertion(**overrides: object) -> Assertion:
    data: dict[str, object] = dict(
        assertion_id="risk",
        type=AssertionType.CATEGORICAL_EQUAL,
        scorer_ref="categorical_equal.v1",
        observed_selector="$.risk_level",
        expected="high",
        required=True,
        severity=Severity.MAJOR,
        on_unevaluable=OnUnevaluable.FAIL,
    )
    data.update(overrides)
    return Assertion(**data)  # type: ignore[arg-type]


def _case(
    case_id: str = "c1", version: int = 1, approved: bool = True, **overrides: object
) -> EvalCase:
    status = ReviewStatus.APPROVED if approved else ReviewStatus.DRAFT
    data: dict[str, object] = dict(
        case_id=case_id,
        case_version=version,
        workflow_ref=WORKFLOW,
        input={"request_id": "r1"},
        expected={"risk_level": "high"},
        assertions=[_assertion()],
        provenance=Provenance(origin=ProvenanceOrigin.SYNTHETIC, author_id="a"),
        review=Review(status=status),
    )
    data.update(overrides)
    return EvalCase(**data)  # type: ignore[arg-type]


def _codes(report_or_issues: object) -> set[FailureCode]:
    issues = getattr(report_or_issues, "issues", report_or_issues)
    return {i.code for i in issues}  # type: ignore[attr-defined]


# --- per-case validation ------------------------------------------------------------------


def test_valid_case_has_no_issues() -> None:
    assert validate_case(_case()) == []


def test_missing_selector_is_flagged() -> None:
    bad = _assertion(
        assertion_id="deadline",
        type=AssertionType.NORMALIZED_DATE_EQUAL,
        scorer_ref="normalized_date_equal.v1",
        observed_selector=None,
    )
    issues = validate_case(_case(assertions=[bad]))
    assert FailureCode.ASSERTION_INVALID in _codes(issues)


def test_duplicate_assertion_id_is_flagged() -> None:
    issues = validate_case(_case(assertions=[_assertion(), _assertion()]))
    assert FailureCode.ASSERTION_INVALID in _codes(issues)


def test_content_hash_mismatch_is_flagged() -> None:
    issues = validate_case(_case(content_hash="sha256:deadbeef"))
    assert FailureCode.DATASET_HASH_MISMATCH in _codes(issues)


# --- dataset validation -------------------------------------------------------------------


def test_duplicate_case_version_is_flagged() -> None:
    report = validate_dataset([_case("c1", 1), _case("c1", 1)])
    assert FailureCode.DUPLICATE_CASE in _codes(report)


def test_workflow_mismatch_is_flagged() -> None:
    report = validate_dataset([_case(), _case("c2", workflow_ref="other.workflow.v1")])
    assert FailureCode.WORKFLOW_INCOMPATIBLE in _codes(report)


def test_unapproved_case_rejected_when_required() -> None:
    report = validate_dataset([_case(approved=False)], require_approved=True)
    assert FailureCode.CASE_UNAPPROVED in _codes(report)
    assert validate_dataset([_case(approved=False)], require_approved=False).ok


def test_empty_dataset_is_flagged() -> None:
    report = validate_dataset([])
    assert FailureCode.EMPTY_DENOMINATOR in _codes(report)


# --- release freezing ---------------------------------------------------------------------


def _release(cases: list[EvalCase]) -> str:
    rel = build_release(
        release_id="r.v1", dataset_id="r", workflow_ref=WORKFLOW, cases=cases
    )
    assert rel.content_hash is not None
    return rel.content_hash


def test_release_hash_is_reproducible() -> None:
    cases = [_case("c2", 1), _case("c1", 1)]
    assert _release(cases) == _release(list(reversed(cases)))  # order-independent


def test_editing_a_case_changes_release_hash() -> None:
    before = _release([_case("c1", 1)])
    after = _release([_case("c1", 1, expected={"risk_level": "low"})])
    assert before != after


def test_build_release_requires_approved() -> None:
    with pytest.raises(ReleaseError):
        build_release(
            release_id="r.v1", dataset_id="r", workflow_ref=WORKFLOW, cases=[_case(approved=False)]
        )


def test_release_is_frozen_and_sorted() -> None:
    rel = build_release(
        release_id="r.v1", dataset_id="r", workflow_ref=WORKFLOW,
        cases=[_case("c2", 1), _case("c1", 1)],
    )
    assert str(rel.state) == "frozen"
    assert [c.case_id for c in rel.cases] == ["c1", "c2"]


# --- loader round-trip --------------------------------------------------------------------


def test_jsonl_round_trip(tmp_path: Path) -> None:
    cases = finalize_case_hashes([_case("c1", 1), _case("c2", 1)])
    path = tmp_path / "cases.jsonl"
    dump_cases_jsonl(cases, path)
    assert load_cases_jsonl(path) == cases


# --- the frozen reference release ---------------------------------------------------------


def test_reference_release_loads_and_validates() -> None:
    cases = load_cases_dir(REF_V1 / "cases")
    assert len(cases) == 12
    report = validate_dataset(cases, require_approved=True, workflow_ref=WORKFLOW)
    assert report.ok, str(report)


def test_reference_manifest_hash_is_reproducible() -> None:
    cases = load_cases_dir(REF_V1 / "cases")
    rebuilt = build_release(
        release_id="reference.request_triage.dataset.v1",
        dataset_id="reference.request_triage.dataset",
        workflow_ref=WORKFLOW,
        cases=cases,
    )
    on_disk = json.loads((REF_V1 / "manifest.json").read_text(encoding="utf-8"))
    assert rebuilt.content_hash == on_disk["content_hash"]
