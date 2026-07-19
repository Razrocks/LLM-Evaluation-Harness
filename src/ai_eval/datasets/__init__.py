"""Dataset layer: load cases, validate them, and freeze immutable releases."""

from __future__ import annotations

from .loader import CaseLoadError, dump_cases_jsonl, load_cases_jsonl
from .release import (
    ReleaseError,
    build_release,
    compute_case_hash,
    finalize_case_hashes,
    write_manifest,
)
from .validation import (
    ValidationIssue,
    ValidationReport,
    validate_case,
    validate_dataset,
)

__all__ = [
    "CaseLoadError",
    "ReleaseError",
    "ValidationIssue",
    "ValidationReport",
    "build_release",
    "compute_case_hash",
    "dump_cases_jsonl",
    "finalize_case_hashes",
    "load_cases_jsonl",
    "validate_case",
    "validate_dataset",
    "write_manifest",
]
