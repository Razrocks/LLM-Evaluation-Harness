"""Top-level orchestration: execute a plan, score it, report, compare, and gate.

This is the only module that spans every layer, and it does so in strict order:

1. **execute** (M2) — invoke the target and persist raw output *before* parsing;
2. **evaluate** (M3) — read that raw evidence back off disk, parse, score, aggregate;
3. **report** (M3) — write the JSONL/JSON/CSV/Markdown artifacts;
4. **compare** (M4) — optional candidate-vs-baseline deltas;
5. **gate** (M4) — optional deterministic PASS/FAIL/INVALID with per-rule evidence.

Reading the raw output back from ``runs/<run_id>/raw/`` rather than reusing the in-memory
value is deliberate: it proves the stored evidence is what actually gets scored.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_eval.baselines import (
    Baseline,
    ComparisonReport,
    compare_to_baseline,
    render_comparison_markdown,
)
from ai_eval.evaluation import ExecutionObservation, RunEvaluation, evaluate_raw_outputs
from ai_eval.execution import EvalPlan, execute_plan
from ai_eval.execution.orchestrator import Clock
from ai_eval.gates import GatePolicy, GateResult, evaluate_gate
from ai_eval.reporting import write_evaluation_reports
from ai_eval.targets import TargetAdapter


@dataclass
class RunOutcome:
    run_id: str
    run_dir: Path
    evaluation: RunEvaluation
    report_paths: dict[str, Path]
    comparison: ComparisonReport | None = None
    gate: GateResult | None = None

    @property
    def exit_code(self) -> int:
        return self.gate.exit_code if self.gate is not None else 0


def run_and_evaluate(
    plan: EvalPlan,
    adapter: TargetAdapter,
    *,
    repo_root: Path,
    runs_dir: Path | None = None,
    run_id: str | None = None,
    repo_revision: str | None = None,
    clock: Clock | None = None,
    baseline: Baseline | None = None,
    gate_policy: GatePolicy | None = None,
) -> RunOutcome:
    run = execute_plan(
        plan, adapter, repo_root=repo_root, runs_dir=runs_dir, run_id=run_id,
        repo_revision=repo_revision, clock=clock,
    )
    cases_by_id = {c.case_id: c for c in run.cases}

    items = []
    observations: dict[str, ExecutionObservation] = {}
    for record in run.records:
        case = cases_by_id[record.case_id]
        raw_path = run.run_dir / record.raw_path
        raw_text = raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""
        invoked_ok = record.error is None and raw_text != ""
        items.append((case, raw_text if invoked_ok else None, invoked_ok))
        observations[record.case_id] = ExecutionObservation(latency_ms=record.latency_ms)

    evaluation = evaluate_raw_outputs(items, observations)
    report_paths = write_evaluation_reports(run.run_dir, evaluation)

    comparison: ComparisonReport | None = None
    if baseline is not None:
        comparison = compare_to_baseline(
            baseline,
            evaluation,
            candidate_run_id=run.manifest.run_id,
            candidate_workflow_ref=run.manifest.workflow_ref,
            candidate_dataset_release_id=run.manifest.dataset_release_id,
            candidate_dataset_release_hash=run.manifest.dataset_release_hash,
        )
        path = run.run_dir / "comparison_report.md"
        path.write_text(render_comparison_markdown(comparison), encoding="utf-8")
        report_paths["comparison_report"] = path

    gate: GateResult | None = None
    if gate_policy is not None:
        gate = evaluate_gate(gate_policy, evaluation.summary, comparison)
        path = run.run_dir / "gate_result.json"
        path.write_text(
            json.dumps(gate.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report_paths["gate_result"] = path

    return RunOutcome(
        run_id=run.manifest.run_id,
        run_dir=run.run_dir,
        evaluation=evaluation,
        report_paths=report_paths,
        comparison=comparison,
        gate=gate,
    )
