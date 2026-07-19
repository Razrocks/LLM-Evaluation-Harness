"""Run-evaluation pipeline: raw outputs -> scores, metrics, and a failure inventory."""

from __future__ import annotations

from .pipeline import ExecutionObservation, RunEvaluation, evaluate_raw_outputs

__all__ = ["ExecutionObservation", "RunEvaluation", "evaluate_raw_outputs"]
