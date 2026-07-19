"""Domain layer: canonical models, enums, failure codes, and content hashing.

Provider-SDK-free and framework-free by design — nothing here imports a model provider, a
web framework, or a database driver.
"""

from __future__ import annotations

from .enums import (
    AssertionResultStatus,
    AssertionType,
    BaselineState,
    CaseExecutionState,
    Criticality,
    DatasetReleaseState,
    DeadlineKind,
    Difficulty,
    EvidenceRequirementType,
    GateOutcome,
    GateRuleType,
    MetadataSource,
    OnUnevaluable,
    ProvenanceOrigin,
    ReviewStatus,
    RiskLevel,
    RunStatus,
    Severity,
)
from .failure_codes import FailureCode
from .hashing import canonical_json, content_hash, sha256_hex
from .models import (
    Ambiguity,
    Assertion,
    CaseRef,
    DatasetRelease,
    ErrorEnvelope,
    EvalCase,
    EvidenceRequirement,
    EvidenceUnit,
    Provenance,
    Review,
    StateTransition,
    TraceEvent,
)

__all__ = [
    # enums
    "AssertionResultStatus",
    "AssertionType",
    "BaselineState",
    "CaseExecutionState",
    "Criticality",
    "DatasetReleaseState",
    "DeadlineKind",
    "Difficulty",
    "EvidenceRequirementType",
    "GateOutcome",
    "GateRuleType",
    "MetadataSource",
    "OnUnevaluable",
    "ProvenanceOrigin",
    "ReviewStatus",
    "RiskLevel",
    "RunStatus",
    "Severity",
    # failure codes
    "FailureCode",
    # hashing
    "canonical_json",
    "content_hash",
    "sha256_hex",
    # models
    "Ambiguity",
    "Assertion",
    "CaseRef",
    "DatasetRelease",
    "ErrorEnvelope",
    "EvalCase",
    "EvidenceRequirement",
    "EvidenceUnit",
    "Provenance",
    "Review",
    "StateTransition",
    "TraceEvent",
]
