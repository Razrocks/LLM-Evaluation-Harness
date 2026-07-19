"""Execution layer: resolve plans into immutable manifests and run them."""

from __future__ import annotations

from .models import EvalPlan, ManifestCaseRef, RunManifest, TargetAdapterRef, TargetSpec
from .orchestrator import CaseExecutionRecord, RunResult, execute_plan
from .resolver import PlanResolutionError, ResolvedPlan, resolve_eval_plan

__all__ = [
    "CaseExecutionRecord",
    "EvalPlan",
    "ManifestCaseRef",
    "PlanResolutionError",
    "ResolvedPlan",
    "RunManifest",
    "RunResult",
    "TargetAdapterRef",
    "TargetSpec",
    "execute_plan",
    "resolve_eval_plan",
]
