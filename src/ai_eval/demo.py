"""The offline regression demo — the platform's first proof, in one command.

Story:

1. validate the frozen dataset release;
2. run the **approved baseline** configuration -> gate **PASS**;
3. approve that run as the baseline;
4. run a **degraded candidate** that still returns schema-valid JSON but drops required
   missing-information items -> gate **FAIL**, with case-level evidence;
5. run the **corrected** configuration -> gate **PASS** again.

It needs no API credentials and is fully deterministic. The demo is *self-verifying*: it
returns a non-zero exit code if the story does not hold, so it doubles as a smoke test.

Output is deliberately ASCII-only so it renders on a default Windows (cp1252) console.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_eval.baselines import approve_baseline, build_baseline_candidate
from ai_eval.datasets import load_cases_dir, validate_dataset
from ai_eval.domain import GateOutcome
from ai_eval.execution import EvalPlan
from ai_eval.gates import RuleStatus, load_gate_policy
from ai_eval.harness import RunOutcome, run_and_evaluate
from ai_eval.targets import get_recorded_target

Echo = Callable[[str], Any]

PLANS = Path("configs/plans")
GATE_POLICY = Path("configs/gates/reference_request_triage_v1.json")
DATASET = Path("datasets/reference/request_triage/v1")

_FIXED_NOW = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)
_RULE = "-" * 72


def _plan(repo_root: Path, name: str) -> EvalPlan:
    return EvalPlan.model_validate(
        json.loads((repo_root / PLANS / name).read_text(encoding="utf-8"))
    )


def _run(
    repo_root: Path, runs_dir: Path | None, plan_file: str, run_id: str, **kw: Any
) -> RunOutcome:
    plan = _plan(repo_root, plan_file)
    return run_and_evaluate(
        plan,
        get_recorded_target(plan.target.adapter_id),
        repo_root=repo_root,
        runs_dir=runs_dir,
        run_id=run_id,
        clock=lambda: _FIXED_NOW,
        gate_policy=load_gate_policy(repo_root / GATE_POLICY),
        **kw,
    )


def _metric(outcome: RunOutcome, name: str) -> float | None:
    return outcome.evaluation.summary.by_name()[name].value


def _manifest_field(outcome: RunOutcome, key: str) -> str:
    data = json.loads((outcome.run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    return str(data[key])


def _show_failed_rules(outcome: RunOutcome, echo: Echo) -> None:
    assert outcome.gate is not None
    for rule in outcome.gate.rule_results:
        if rule.status not in (RuleStatus.PASS, RuleStatus.SKIPPED):
            echo(f"     [{str(rule.status).upper()}] {rule.rule_id}: {rule.message}")


def run_demo(*, repo_root: Path, runs_dir: Path | None = None, echo: Echo = print) -> int:
    ok = True

    echo(_RULE)
    echo("1. Validate the frozen dataset release")
    echo(_RULE)
    cases = load_cases_dir(repo_root / DATASET / "cases")
    report = validate_dataset(cases, require_approved=True)
    if report.issues:
        for issue in report.issues:
            echo(f"   [X] {issue.code}: {issue.message}")
        return 1
    echo(f"   [OK] {len(cases)} approved cases valid\n")

    echo(_RULE)
    echo("2. Run the approved BASELINE configuration (recorded_pass.v1)")
    echo(_RULE)
    base_run = _run(repo_root, runs_dir, "reference_request_triage_baseline.json", "demo_baseline")
    echo(f"   artifacts: {base_run.run_dir}")
    echo(f"   cases_passed              = {_metric(base_run, 'cases_passed')}")
    echo(f"   schema_pass_rate          = {_metric(base_run, 'schema_pass_rate')}")
    echo(f"   missing_information_recall= {_metric(base_run, 'missing_information_recall')}")
    assert base_run.gate is not None
    echo(f"   GATE: {str(base_run.gate.outcome).upper()}")
    ok &= base_run.gate.outcome is GateOutcome.PASS
    _show_failed_rules(base_run, echo)
    echo("")

    echo(_RULE)
    echo("3. Approve that run as the baseline (explicit human decision)")
    echo(_RULE)
    baseline = build_baseline_candidate(
        baseline_id="reference_request_triage_baseline_v1",
        workflow_ref="reference.request_triage.v1",
        run_id=base_run.run_id,
        dataset_release_id=_manifest_field(base_run, "dataset_release_id"),
        dataset_release_hash=_manifest_field(base_run, "dataset_release_hash"),
        evaluation=base_run.evaluation,
        limitations=["12 synthetic cases; recorded target, no live provider"],
    )
    baseline = approve_baseline(
        baseline,
        approver="demo_baseline_approver",
        rationale="Reference configuration; all critical rules met.",
        approved_at=_FIXED_NOW,
    )
    echo(f"   [OK] baseline '{baseline.baseline_id}' state={baseline.state}\n")

    echo(_RULE)
    echo("4. Run a DEGRADED candidate: valid JSON, but drops missing-information")
    echo(_RULE)
    bad_run = _run(
        repo_root, runs_dir, "reference_request_triage_candidate_degraded.json",
        "demo_degraded", baseline=baseline,
    )
    echo(f"   schema_pass_rate          = {_metric(bad_run, 'schema_pass_rate')}"
         "   <- STILL VALID JSON")
    echo(f"   missing_information_recall= {_metric(bad_run, 'missing_information_recall')}"
         "   <- REGRESSED")
    assert bad_run.gate is not None
    echo(f"   GATE: {str(bad_run.gate.outcome).upper()}")
    _show_failed_rules(bad_run, echo)
    ok &= bad_run.gate.outcome is GateOutcome.FAIL

    if bad_run.evaluation.failures:
        f = bad_run.evaluation.failures[0]
        echo("")
        echo("   One failing case, with evidence:")
        echo(f"     case      : {f.case_id}")
        echo(f"     assertion : {f.assertion_id} (scorer {f.scorer_ref}, severity {f.severity})")
        echo(f"     expected  : {f.expected}")
        echo(f"     observed  : {f.observed}")
        echo(f"     codes     : {f.failure_codes}")
    if bad_run.comparison is not None:
        echo(f"     newly failing vs baseline: {bad_run.comparison.newly_failing_cases}")
    echo("")

    echo(_RULE)
    echo("5. Run the CORRECTED configuration")
    echo(_RULE)
    fixed_run = _run(
        repo_root, runs_dir, "reference_request_triage_candidate_corrected.json",
        "demo_corrected", baseline=baseline,
    )
    echo(f"   missing_information_recall= {_metric(fixed_run, 'missing_information_recall')}")
    assert fixed_run.gate is not None
    echo(f"   GATE: {str(fixed_run.gate.outcome).upper()}")
    ok &= fixed_run.gate.outcome is GateOutcome.PASS
    _show_failed_rules(fixed_run, echo)
    echo("")

    echo(_RULE)
    if ok:
        echo("RESULT: PASS -> FAIL -> PASS.")
        echo("The gate caught the regression, explained it with case-level evidence, and")
        echo("blocked promotion. No API keys were used.")
        echo(_RULE)
        return 0
    echo("RESULT: demo did not hold - unexpected gate outcomes")
    echo(_RULE)
    return 1
