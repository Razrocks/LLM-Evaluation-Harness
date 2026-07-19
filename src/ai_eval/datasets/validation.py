"""Dataset validation.

Validation returns a structured :class:`ValidationReport` of typed issues rather than raising
on the first problem, so an author sees every issue at once. Each issue carries a controlled
:class:`FailureCode` and a human-readable location.

Two layers:

* :func:`validate_case` — structural checks on one case (unique assertion IDs, required
  selectors per assertion type, evidence-requirement wiring, content-hash integrity).
* :func:`validate_dataset` — collection checks (duplicate case versions, single workflow,
  optional approval requirement, non-empty population).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ai_eval.domain import (
    Assertion,
    AssertionType,
    EvalCase,
    EvidenceRequirementType,
    FailureCode,
    ReviewStatus,
    content_hash,
)

# Assertion types that compare an observed value at a selector and therefore require one.
_SELECTOR_REQUIRED: frozenset[AssertionType] = frozenset(
    {
        AssertionType.NORMALIZED_DATE_EQUAL,
        AssertionType.DEADLINE_KIND_EQUAL,
        AssertionType.CATEGORICAL_EQUAL,
        AssertionType.BOOLEAN_EQUAL,
        AssertionType.SET_PRECISION_RECALL_F1,
        AssertionType.REQUIRED_TASK_COVERAGE,
        AssertionType.EVIDENCE_REFERENCE_VALID,
        AssertionType.EVIDENCE_SPAN_SUPPORT,
    }
)


@dataclass(frozen=True)
class ValidationIssue:
    code: FailureCode
    message: str
    location: str | None = None

    def __str__(self) -> str:
        where = f" [{self.location}]" if self.location else ""
        return f"{self.code}: {self.message}{where}"


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.issues

    def with_issues(self, more: list[ValidationIssue]) -> ValidationReport:
        return ValidationReport(issues=self.issues + tuple(more))

    def __str__(self) -> str:
        if self.ok:
            return "OK"
        return "\n".join(str(i) for i in self.issues)


def _validate_assertion(case_id: str, assertion: Assertion) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    loc = f"{case_id}#{assertion.assertion_id}"
    if assertion.type in _SELECTOR_REQUIRED and not assertion.observed_selector:
        issues.append(
            ValidationIssue(
                FailureCode.ASSERTION_INVALID,
                f"assertion type '{assertion.type}' requires an observed_selector",
                loc,
            )
        )
    req = assertion.evidence_requirement
    if (
        req is not None
        and req.type is not EvidenceRequirementType.NONE
        and not req.observed_selector
    ):
        issues.append(
            ValidationIssue(
                FailureCode.ASSERTION_INVALID,
                f"evidence_requirement '{req.type}' requires an observed_selector",
                loc,
            )
        )
    return issues


def validate_case(case: EvalCase) -> list[ValidationIssue]:
    """Structural checks on a single case."""
    issues: list[ValidationIssue] = []

    dupe_ids = [aid for aid, n in Counter(a.assertion_id for a in case.assertions).items() if n > 1]
    for aid in sorted(dupe_ids):
        issues.append(
            ValidationIssue(
                FailureCode.ASSERTION_INVALID,
                f"duplicate assertion_id '{aid}'",
                case.case_id,
            )
        )

    for assertion in case.assertions:
        issues.extend(_validate_assertion(case.case_id, assertion))

    if case.content_hash is not None:
        recomputed = content_hash(case.model_dump(mode="json"))
        if recomputed != case.content_hash:
            issues.append(
                ValidationIssue(
                    FailureCode.DATASET_HASH_MISMATCH,
                    f"content_hash mismatch: stored {case.content_hash}, recomputed {recomputed}",
                    case.case_id,
                )
            )
    return issues


def validate_dataset(
    cases: list[EvalCase],
    *,
    require_approved: bool = False,
    workflow_ref: str | None = None,
) -> ValidationReport:
    """Collection-level checks across a set of cases."""
    issues: list[ValidationIssue] = []

    if not cases:
        return ValidationReport(
            (ValidationIssue(FailureCode.EMPTY_DENOMINATOR, "dataset contains no cases"),)
        )

    keys = [(c.case_id, c.case_version) for c in cases]
    for key, n in Counter(keys).items():
        if n > 1:
            issues.append(
                ValidationIssue(
                    FailureCode.DUPLICATE_CASE,
                    f"case {key[0]} v{key[1]} appears {n} times",
                    key[0],
                )
            )

    expected_workflow = workflow_ref or cases[0].workflow_ref
    for case in cases:
        if case.workflow_ref != expected_workflow:
            issues.append(
                ValidationIssue(
                    FailureCode.WORKFLOW_INCOMPATIBLE,
                    f"workflow_ref '{case.workflow_ref}' != expected '{expected_workflow}'",
                    case.case_id,
                )
            )
        if require_approved and case.review.status is not ReviewStatus.APPROVED:
            issues.append(
                ValidationIssue(
                    FailureCode.CASE_UNAPPROVED,
                    f"case is '{case.review.status}', not approved",
                    case.case_id,
                )
            )
        issues.extend(validate_case(case))

    return ValidationReport(tuple(issues))
