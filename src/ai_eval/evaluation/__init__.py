"""Run-evaluation pipeline: raw outputs -> scores, metrics, and a failure inventory."""

from __future__ import annotations

from .pipeline import RunEvaluation, evaluate_raw_outputs

__all__ = ["RunEvaluation", "evaluate_raw_outputs"]
