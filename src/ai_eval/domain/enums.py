"""Controlled vocabularies and lifecycle states.

Every enum value is a string that matches the corresponding JSON Schema enum verbatim, so
domain models round-trip losslessly to and from the on-disk contracts under ``schemas/``.
"""

from __future__ import annotations

from enum import Enum


class _StrEnum(str, Enum):
    """String enum whose ``str()`` is the bare value (JSON-friendly)."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


# --- review / lifecycle states ------------------------------------------------------------


class ReviewStatus(_StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class DatasetReleaseState(_StrEnum):
    DRAFT = "draft"
    VALIDATING = "validating"
    FROZEN = "frozen"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class RunStatus(_StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SCORING = "scoring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CaseExecutionState(_StrEnum):
    PENDING = "pending"
    INVOKING = "invoking"
    RESPONSE_RECEIVED = "response_received"
    PARSING = "parsing"
    SCORING = "scoring"
    PASSED = "passed"
    FAILED_ASSERTIONS = "failed_assertions"
    # error terminals
    INVOCATION_ERROR = "invocation_error"
    PARSE_ERROR = "parse_error"
    SCHEMA_ERROR = "schema_error"
    SCORING_ERROR = "scoring_error"
    UNEVALUABLE = "unevaluable"


class BaselineState(_StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"
    REJECTED = "rejected"


# --- case authoring vocabularies ----------------------------------------------------------


class ProvenanceOrigin(_StrEnum):
    SYNTHETIC = "synthetic"
    PUBLIC = "public"
    DERIVED = "derived"


class Difficulty(_StrEnum):
    EASY = "easy"
    STANDARD = "standard"
    HARD = "hard"
    ADVERSARIAL = "adversarial"


class Criticality(_StrEnum):
    NORMAL = "normal"
    CRITICAL = "critical"


# --- assertion vocabularies ---------------------------------------------------------------


class AssertionType(_StrEnum):
    SCHEMA_VALID = "schema_valid"
    NORMALIZED_DATE_EQUAL = "normalized_date_equal"
    DEADLINE_KIND_EQUAL = "deadline_kind_equal"
    CATEGORICAL_EQUAL = "categorical_equal"
    BOOLEAN_EQUAL = "boolean_equal"
    SET_PRECISION_RECALL_F1 = "set_precision_recall_f1"
    REQUIRED_TASK_COVERAGE = "required_task_coverage"
    EVIDENCE_REFERENCE_VALID = "evidence_reference_valid"
    EVIDENCE_SPAN_SUPPORT = "evidence_span_support"
    UNSUPPORTED_MATERIAL_CLAIM_ABSENT = "unsupported_material_claim_absent"
    PROHIBITED_VALUE_ABSENT = "prohibited_value_absent"
    SEMANTIC_EQUIVALENCE_JUDGE = "semantic_equivalence_judge"


class Severity(_StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFORMATIONAL = "informational"


class OnUnevaluable(_StrEnum):
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class EvidenceRequirementType(_StrEnum):
    NONE = "none"
    SOURCE_REFERENCE_REQUIRED = "source_reference_required"
    SOURCE_SPAN_REQUIRED = "source_span_required"


class AssertionResultStatus(_StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNEVALUABLE = "unevaluable"
    ERROR = "error"


# --- request-triage output vocabularies ---------------------------------------------------


class DeadlineKind(_StrEnum):
    EXPLICIT_ABSOLUTE = "explicit_absolute"
    EXPLICIT_RELATIVE = "explicit_relative"
    INFERRED = "inferred"
    NONE = "none"
    AMBIGUOUS = "ambiguous"


class RiskLevel(_StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MetadataSource(_StrEnum):
    EMAIL = "email"
    FORM = "form"
    CHAT = "chat"
    OTHER = "other"


# --- gate vocabularies --------------------------------------------------------------------


class GateRuleType(_StrEnum):
    CRITICAL_CASE_COUNT_MAX = "critical_case_count_max"
    METRIC_MINIMUM = "metric_minimum"
    METRIC_MAXIMUM = "metric_maximum"
    BASELINE_DELTA_MINIMUM = "baseline_delta_minimum"
    BASELINE_DELTA_MAXIMUM = "baseline_delta_maximum"
    REQUIRED_METRIC_PRESENT = "required_metric_present"


class GateOutcome(_StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INVALID = "invalid"
