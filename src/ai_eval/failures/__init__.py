"""Failure classification: scored results -> controlled failure inventory."""

from __future__ import annotations

from .classify import FailureRecord, build_failures, failure_code_counts

__all__ = ["FailureRecord", "build_failures", "failure_code_counts"]
