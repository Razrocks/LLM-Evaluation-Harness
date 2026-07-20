"""``ai-eval`` command line interface.

Five use cases, each mapping to one application capability:

``dataset validate``  validate a dataset release before anything cites it
``run``               execute a plan end to end (invoke -> score -> report -> compare -> gate)
``compare``           compare a stored run against an approved baseline
``gate``              apply a gate policy to a stored run
``demo``              the offline regression story: PASS -> FAIL -> PASS

Exit-code contract (documented, relied on by CI): ``0`` PASS, ``1`` FAIL, ``2`` INVALID.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ai_eval.baselines import (
    Baseline,
    compare_snapshots,
    render_comparison_markdown,
)
from ai_eval.datasets import load_cases_dir, load_cases_jsonl, validate_dataset
from ai_eval.domain import GateOutcome
from ai_eval.execution import EvalPlan
from ai_eval.gates import (
    EXIT_FAIL,
    EXIT_INVALID,
    EXIT_PASS,
    RuleStatus,
    evaluate_gate,
    load_gate_policy,
)
from ai_eval.harness import run_and_evaluate
from ai_eval.metrics import MetricSummary
from ai_eval.targets import get_recorded_target

app = typer.Typer(add_completion=False, help="Standalone AI evaluation & reliability platform.")
dataset_app = typer.Typer(help="Dataset release operations.")
app.add_typer(dataset_app, name="dataset")

REPO_ROOT = Path.cwd()


# --- helpers ------------------------------------------------------------------------------


def _load_plan(path: Path) -> EvalPlan:
    return EvalPlan.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _load_baseline(path: Path) -> Baseline:
    return Baseline.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _load_summary(run_dir: Path) -> MetricSummary:
    return MetricSummary.model_validate(
        json.loads((run_dir / "metric_summary.json").read_text(encoding="utf-8"))
    )


def _case_passed_from_run(run_dir: Path) -> dict[str, bool]:
    passed: dict[str, bool] = {}
    path = run_dir / "parsed_outputs.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                passed[row["case_id"]] = row.get("state") == "passed"
    return passed


def _failure_codes_from_run(run_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    path = run_dir / "failures.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                for code in json.loads(line).get("failure_codes", []):
                    counts[code] = counts.get(code, 0) + 1
    return counts


def _echo_gate(outcome: GateOutcome, detail: str = "") -> None:
    colour = {
        GateOutcome.PASS: typer.colors.GREEN,
        GateOutcome.FAIL: typer.colors.RED,
        GateOutcome.INVALID: typer.colors.YELLOW,
    }[outcome]
    typer.secho(f"GATE: {str(outcome).upper()} {detail}", fg=colour, bold=True)


# --- commands -----------------------------------------------------------------------------


@dataset_app.command("validate")
def dataset_validate(
    dataset: Path = typer.Option(..., help="Dataset release directory (contains cases/)."),
    require_approved: bool = typer.Option(True, help="Require every case to be APPROVED."),
) -> None:
    """Validate every case in a dataset release."""
    cases_dir = dataset / "cases"
    cases = load_cases_dir(cases_dir) if cases_dir.exists() else load_cases_jsonl(dataset / "cases.jsonl")
    report = validate_dataset(cases, require_approved=require_approved)
    if report.issues:
        for issue in report.issues:
            typer.secho(f"  {issue.code}: {issue.message}", fg=typer.colors.RED)
        typer.secho(f"INVALID: {len(report.issues)} issue(s) in {len(cases)} case(s)",
                    fg=typer.colors.RED, bold=True)
        raise typer.Exit(EXIT_FAIL)
    typer.secho(f"OK: {len(cases)} case(s) valid", fg=typer.colors.GREEN, bold=True)


@app.command("run")
def run_cmd(
    plan: Path = typer.Option(..., help="Eval plan JSON."),
    gate: Path | None = typer.Option(None, help="Gate policy JSON."),
    baseline: Path | None = typer.Option(None, help="Approved baseline JSON."),
    runs_dir: Path | None = typer.Option(None, help="Where to write runs/ (default ./runs)."),
    run_id: str | None = typer.Option(None, help="Explicit run id."),
) -> None:
    """Execute a plan: invoke the target, score, report, optionally compare and gate."""
    eval_plan = _load_plan(plan)
    outcome = run_and_evaluate(
        eval_plan,
        get_recorded_target(eval_plan.target.adapter_id),
        repo_root=REPO_ROOT,
        runs_dir=runs_dir,
        run_id=run_id,
        baseline=_load_baseline(baseline) if baseline else None,
        gate_policy=load_gate_policy(gate) if gate else None,
    )
    typer.echo(f"run_id: {outcome.run_id}")
    typer.echo(f"artifacts: {outcome.run_dir}")
    for metric in outcome.evaluation.summary.metrics:
        if metric.name in ("cases_passed", "schema_pass_rate", "missing_information_recall",
                           "risk_recall.high", "deadline_accuracy"):
            typer.echo(f"  {metric.name}: {metric.value}  (n={metric.denominator})")
    if outcome.gate is not None:
        _echo_gate(outcome.gate.outcome)
        for rule in outcome.gate.rule_results:
            if rule.status not in (RuleStatus.PASS, RuleStatus.SKIPPED):
                typer.echo(f"  [{rule.status}] {rule.rule_id}: {rule.message}")
        raise typer.Exit(outcome.gate.exit_code)


@app.command("compare")
def compare_cmd(
    candidate: Path = typer.Option(..., help="Candidate run directory."),
    baseline: Path = typer.Option(..., help="Approved baseline JSON."),
) -> None:
    """Compare a stored run against an approved baseline."""
    base = _load_baseline(baseline)
    summary = _load_summary(candidate)
    manifest = json.loads((candidate / "run_manifest.json").read_text(encoding="utf-8"))
    report = compare_snapshots(
        base,
        candidate_metrics={m.name: m.value for m in summary.metrics},
        candidate_case_passed=_case_passed_from_run(candidate),
        candidate_critical_failures=summary.critical_case_failures,
        candidate_failure_codes=_failure_codes_from_run(candidate),
        candidate_run_id=manifest["run_id"],
        candidate_workflow_ref=manifest["workflow_ref"],
        candidate_dataset_release_id=manifest["dataset_release_id"],
        candidate_dataset_release_hash=manifest["dataset_release_hash"],
    )
    out = candidate / "comparison_report.md"
    out.write_text(render_comparison_markdown(report), encoding="utf-8")
    typer.echo(f"comparison written: {out}")
    typer.echo(f"compatible: {report.compatible}")
    typer.echo(f"newly failing: {report.newly_failing_cases or '(none)'}")
    typer.echo(f"recovered: {report.recovered_cases or '(none)'}")


@app.command("gate")
def gate_cmd(
    run: Path = typer.Option(..., help="Run directory containing metric_summary.json."),
    policy: Path = typer.Option(..., help="Gate policy JSON."),
) -> None:
    """Apply a gate policy to a stored run. Exit 0 PASS / 1 FAIL / 2 INVALID."""
    result = evaluate_gate(load_gate_policy(policy), _load_summary(run), None)
    _echo_gate(result.outcome,
               f"({result.passed_rules} passed, {result.failed_rules} failed, "
               f"{result.invalid_rules} invalid)")
    for rule in result.rule_results:
        if rule.status not in (RuleStatus.PASS, RuleStatus.SKIPPED):
            typer.echo(f"  [{rule.status}] {rule.rule_id}: {rule.message}")
    raise typer.Exit(result.exit_code)


@app.command("demo")
def demo_cmd(
    runs_dir: Path | None = typer.Option(None, help="Where to write runs/ (default ./runs)."),
) -> None:
    """The offline regression story: baseline PASS -> degraded FAIL -> corrected PASS."""
    from ai_eval.demo import run_demo

    code = run_demo(repo_root=REPO_ROOT, runs_dir=runs_dir, echo=typer.echo)
    raise typer.Exit(code)


def main() -> None:  # pragma: no cover - console-script shim
    app()


__all__ = ["EXIT_FAIL", "EXIT_INVALID", "EXIT_PASS", "app", "main"]
