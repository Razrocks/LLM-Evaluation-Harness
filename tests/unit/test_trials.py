"""Repeated-trial variance: spread across runs, and the harness's own determinism."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_eval.execution import EvalPlan
from ai_eval.metrics import Metric, MetricSummary
from ai_eval.targets import get_recorded_target
from ai_eval.trials import run_trials, variance_across_runs

REPO = Path(__file__).resolve().parents[2]


def _summary(**values: float | None) -> MetricSummary:
    return MetricSummary(
        total_cases=1,
        metrics=[
            Metric(name=k, value=v, numerator=None, denominator=1, aggregation="rate",
                   missing_data_rule="fixture")
            for k, v in values.items()
        ],
    )


def test_variance_of_identical_runs_is_zero() -> None:
    stats = variance_across_runs([_summary(m=1.0), _summary(m=1.0), _summary(m=1.0)])
    assert stats["m"].stdev == 0.0
    assert stats["m"].is_stable
    assert stats["m"].mean == 1.0


def test_variance_reports_spread() -> None:
    stats = variance_across_runs([_summary(m=1.0), _summary(m=0.0)])
    assert stats["m"].mean == 0.5
    assert stats["m"].stdev > 0
    assert (stats["m"].minimum, stats["m"].maximum) == (0.0, 1.0)
    assert not stats["m"].is_stable


def test_single_trial_has_no_spread() -> None:
    stats = variance_across_runs([_summary(m=0.7)])
    assert stats["m"].stdev == 0.0
    assert stats["m"].values == [0.7]


def test_metric_missing_from_one_run_is_not_compared() -> None:
    """A metric that is absent (None) somewhere is excluded rather than silently averaged."""
    stats = variance_across_runs([_summary(m=1.0), _summary(m=None)])
    assert "m" not in stats


def test_empty_input() -> None:
    assert variance_across_runs([]) == {}


def test_recorded_target_is_perfectly_stable_across_trials(tmp_path: Path) -> None:
    """End-to-end: the harness itself introduces no nondeterminism."""
    plan = EvalPlan.model_validate(
        json.loads(
            (REPO / "configs/plans/reference_request_triage_baseline.json").read_text(
                encoding="utf-8"
            )
        )
    )
    result = run_trials(
        plan, get_recorded_target("recorded_pass"),
        repo_root=REPO, trials=3, runs_dir=tmp_path, run_id_prefix="t",
    )
    assert result.trials == 3
    assert len(result.run_ids) == 3
    assert result.unstable_metrics() == []  # zero spread everywhere
    assert result.stats["cases_passed"].mean == 1.0


def test_trials_must_be_positive() -> None:
    with pytest.raises(ValueError, match="trials must be >= 1"):
        run_trials(
            EvalPlan(eval_plan_id="p", workflow_ref="w", dataset_manifest_path="x",
                     target={"adapter_id": "recorded_pass", "adapter_version": "v1"}),
            get_recorded_target("recorded_pass"), repo_root=REPO, trials=0,
        )
