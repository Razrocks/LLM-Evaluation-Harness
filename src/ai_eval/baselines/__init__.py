"""Baselines: approved comparison references and candidate-vs-baseline comparison."""

from __future__ import annotations

from .compare import (
    ComparisonReport,
    MetricDelta,
    compare_snapshots,
    compare_to_baseline,
    render_comparison_markdown,
)
from .models import (
    Baseline,
    approve_baseline,
    build_baseline_candidate,
    build_baseline_from_snapshot,
)

__all__ = [
    "Baseline",
    "ComparisonReport",
    "MetricDelta",
    "approve_baseline",
    "build_baseline_candidate",
    "build_baseline_from_snapshot",
    "compare_snapshots",
    "compare_to_baseline",
    "render_comparison_markdown",
]
