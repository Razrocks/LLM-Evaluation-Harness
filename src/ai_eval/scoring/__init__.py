"""Deterministic, versioned scoring: assertion results, scorers, and per-case evaluation."""

from __future__ import annotations

from .context import ScoringContext
from .evaluate import CaseScore, evaluate_case
from .normalize import (
    NORMALIZER_VERSION,
    DateNormalizationError,
    normalize_iso_date,
    resolve_relative_weekday,
)
from .result import AssertionResult
from .scorers import SCORERS, get_scorer
from .vocab import (
    CANONICAL_MISSING_INFO_KEYS,
    MISSING_INFO_VOCAB_VERSION,
    normalize_missing_info_key,
)

__all__ = [
    "CANONICAL_MISSING_INFO_KEYS",
    "MISSING_INFO_VOCAB_VERSION",
    "NORMALIZER_VERSION",
    "AssertionResult",
    "CaseScore",
    "DateNormalizationError",
    "SCORERS",
    "ScoringContext",
    "evaluate_case",
    "get_scorer",
    "normalize_iso_date",
    "normalize_missing_info_key",
    "resolve_relative_weekday",
]
