"""Domain models for the eval-case and dataset world.

These Pydantic v2 models mirror the JSON Schemas under ``schemas/`` one-to-one and forbid
unknown fields (``extra="forbid"``), so a model that validates here is a payload that
validates there. Models are intentionally *not* frozen: a case is constructed, hashed, and
then treated as immutable by convention and enforced by the dataset validator and tests —
not by Python-level immutability, which would complicate loading and hashing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    AssertionType,
    Criticality,
    DatasetReleaseState,
    Difficulty,
    EvidenceRequirementType,
    OnUnevaluable,
    ProvenanceOrigin,
    ReviewStatus,
    Severity,
)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceUnit(_Base):
    """A referenceable slice of source context (a span in a document or the message)."""

    evidence_id: str
    source_id: str
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    text: str | None = None


class EvidenceRequirement(_Base):
    type: EvidenceRequirementType
    observed_selector: str | None = None


class Assertion(_Base):
    """One atomic, typed claim about the target's output, bound to exactly one scorer."""

    assertion_id: str
    type: AssertionType
    scorer_ref: str
    observed_selector: str | None = None
    expected: Any = None
    params: dict[str, Any] = Field(default_factory=dict)
    required: bool
    weight: float = Field(default=1.0, ge=0)
    severity: Severity
    pass_threshold: float | None = Field(default=None, ge=0, le=1)
    evidence_requirement: EvidenceRequirement | None = None
    on_unevaluable: OnUnevaluable


class Provenance(_Base):
    origin: ProvenanceOrigin
    author_id: str
    created_at: datetime | None = None


class Review(_Base):
    status: ReviewStatus
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
    rationale: str | None = None


class Ambiguity(_Base):
    is_ambiguous: bool = False
    notes: str | None = None
    accepted_alternatives: list[Any] = Field(default_factory=list)


class EvalCase(_Base):
    """One versioned evaluation scenario. An APPROVED version is immutable; corrections make
    a new ``case_version``."""

    case_id: str
    case_version: int = Field(ge=1)
    workflow_ref: str
    title: str | None = None
    input: dict[str, Any]
    source_context: list[EvidenceUnit] = Field(default_factory=list)
    expected: dict[str, Any]
    assertions: list[Assertion] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.STANDARD
    criticality: Criticality = Criticality.NORMAL
    ambiguity: Ambiguity | None = None
    provenance: Provenance
    review: Review
    content_hash: str | None = None

    @property
    def is_approved(self) -> bool:
        return self.review.status is ReviewStatus.APPROVED


class CaseRef(_Base):
    """A pointer to one exact case version inside a dataset release.

    ``content_hash`` binds the reference to the case's exact content, so a frozen release's
    own hash changes if any member case is edited. It is optional because run manifests (M2)
    reference cases by id+version only.
    """

    case_id: str
    case_version: int = Field(ge=1)
    content_hash: str | None = None


class DatasetRelease(_Base):
    """An immutable, content-addressed snapshot of exact case versions."""

    release_id: str
    dataset_id: str
    workflow_ref: str
    state: DatasetReleaseState = DatasetReleaseState.DRAFT
    cases: list[CaseRef] = Field(default_factory=list)
    purpose: str | None = None
    distribution: str | None = None
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    content_hash: str | None = None


class StateTransition(_Base):
    # 'from' is a Python keyword, so the field is 'from_' with a JSON alias.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str | None = Field(default=None, alias="from")
    to: str | None = None

    @classmethod
    def of(cls, from_state: str | None, to_state: str | None) -> StateTransition:
        """Build a transition without tripping over the reserved ``from`` alias."""
        return cls.model_validate({"from": from_state, "to": to_state})


class TraceEvent(_Base):
    """One ordered, append-only material event during a case execution (evidence memory)."""

    event_id: str
    case_execution_id: str
    sequence: int = Field(ge=0)
    event_type: str
    actor: str
    timestamp: datetime
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    state_transition: StateTransition | None = None
    payload_ref: str | None = None
    content_hash: str | None = None


class ErrorEnvelope(_Base):
    """A structured, redaction-safe error. ``error_code`` is a controlled FailureCode value."""

    error_class: str
    error_code: str
    retryable: bool = False
    message: str
    attempt: int = 1
    provider_request_id: str | None = None
    details_ref: str | None = None
