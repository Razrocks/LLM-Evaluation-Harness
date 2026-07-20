"""Deterministic regression gates: versioned policy in, PASS/FAIL/INVALID + evidence out."""

from __future__ import annotations

from .evaluate import (
    EXIT_FAIL,
    EXIT_INVALID,
    EXIT_PASS,
    GateResult,
    RuleResult,
    RuleStatus,
    evaluate_gate,
)
from .policy import GatePolicy, GateRule, load_gate_policy

__all__ = [
    "EXIT_FAIL",
    "EXIT_INVALID",
    "EXIT_PASS",
    "GatePolicy",
    "GateResult",
    "GateRule",
    "RuleResult",
    "RuleStatus",
    "evaluate_gate",
    "load_gate_policy",
]
