"""Repeated trials and variance.

A single run of a probabilistic target is one sample, not a measurement. Running the same
frozen plan N times and reporting spread is what separates "the model got better" from "we got
a luckier sample". Recorded fixture targets are deterministic, so their spread is exactly zero
— which is itself a useful assertion that the harness adds no nondeterminism of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ai_eval.execution import EvalPlan
from ai_eval.harness import RunOutcome, run_and_evaluate
from ai_eval.metrics import MetricSummary
from ai_eval.targets import TargetAdapter


@dataclass
class TrialStats:
    """Spread of one metric across repeated runs of the same plan."""

    metric: str
    values: list[float]
    mean: float
    stdev: float
    minimum: float
    maximum: float

    @property
    def is_stable(self) -> bool:
        return self.stdev == 0.0


@dataclass
class TrialsResult:
    trials: int
    run_ids: list[str]
    stats: dict[str, TrialStats]
    outcomes: list[RunOutcome]

    def unstable_metrics(self, tolerance: float = 0.0) -> list[str]:
        """Metrics whose spread exceeds ``tolerance`` — the ones a single run would misreport."""
        return sorted(k for k, s in self.stats.items() if s.stdev > tolerance)


def variance_across_runs(summaries: list[MetricSummary]) -> dict[str, TrialStats]:
    """Per-metric mean/stdev/min/max across runs, over metrics that have a value everywhere."""
    if not summaries:
        return {}
    per_metric: dict[str, list[float]] = {}
    for summary in summaries:
        for metric in summary.metrics:
            if metric.value is not None:
                per_metric.setdefault(metric.name, []).append(float(metric.value))

    stats: dict[str, TrialStats] = {}
    for name, values in per_metric.items():
        if len(values) != len(summaries):
            continue  # metric absent from at least one run; not comparable across trials
        array = np.asarray(values, dtype=float)
        stats[name] = TrialStats(
            metric=name,
            values=values,
            mean=float(array.mean()),
            # Sample stdev (ddof=1) once there are >= 2 trials; a single trial has no spread.
            stdev=float(array.std(ddof=1)) if len(values) > 1 else 0.0,
            minimum=float(array.min()),
            maximum=float(array.max()),
        )
    return stats


def run_trials(
    plan: EvalPlan,
    adapter: TargetAdapter,
    *,
    repo_root: Path,
    trials: int = 3,
    run_id_prefix: str = "trial",
    **kwargs: Any,
) -> TrialsResult:
    """Execute the same frozen plan ``trials`` times and summarize the spread."""
    if trials < 1:
        raise ValueError("trials must be >= 1")
    outcomes: list[RunOutcome] = []
    for index in range(1, trials + 1):
        outcomes.append(
            run_and_evaluate(
                plan, adapter, repo_root=repo_root,
                run_id=f"{run_id_prefix}_{index:02d}", **kwargs,
            )
        )
    return TrialsResult(
        trials=trials,
        run_ids=[o.run_id for o in outcomes],
        stats=variance_across_runs([o.evaluation.summary for o in outcomes]),
        outcomes=outcomes,
    )
