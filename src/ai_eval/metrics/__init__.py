"""Metric aggregation with explicit numerators, denominators, and missing-data rules."""

from __future__ import annotations

from .aggregate import (
    CaseMetricInput,
    Metric,
    MetricSummary,
    aggregate_metrics,
    build_metric_input,
)

__all__ = [
    "CaseMetricInput",
    "Metric",
    "MetricSummary",
    "aggregate_metrics",
    "build_metric_input",
]
