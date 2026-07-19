"""Target adapters: one typed contract, many implementations.

Recorded fixtures ship now (offline, no credentials). Provider adapters (Claude / ChatGPT /
Gemini / HuggingFace) arrive in M5 behind the same :class:`TargetAdapter` contract.
"""

from __future__ import annotations

from .base import Attempt, InvocationContext, TargetAdapter, TargetInvocationResult
from .fixture import (
    RECORDED_TARGETS,
    RecordedDeadlineRegression,
    RecordedEvidenceRegression,
    RecordedMissingInformationRegression,
    RecordedPass,
    RecordedSchemaFailure,
    build_correct_output,
    get_recorded_target,
)

__all__ = [
    "RECORDED_TARGETS",
    "Attempt",
    "InvocationContext",
    "RecordedDeadlineRegression",
    "RecordedEvidenceRegression",
    "RecordedMissingInformationRegression",
    "RecordedPass",
    "RecordedSchemaFailure",
    "TargetAdapter",
    "TargetInvocationResult",
    "build_correct_output",
    "get_recorded_target",
]
