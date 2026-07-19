"""Run orchestrator (M2 scope: execution + evidence capture, no parsing yet).

For each case in a resolved plan it: emits an ``invocation_started`` trace, invokes the target,
**persists the raw output before anything else**, emits ``response_received`` /
``invocation_error``, and records a case-execution row. Parsing and scoring are added in M3 and
slot in *after* the raw-capture step, never before.

Timestamps come from an injectable ``clock`` so recorded-target runs can be fully deterministic
(the demo and golden tests inject a fixed/monotonic clock).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_eval.artifacts import RunArtifactWriter
from ai_eval.domain import CaseExecutionState, RunStatus, StateTransition, TraceEvent
from ai_eval.targets import InvocationContext, TargetAdapter

from .models import EvalPlan, RunManifest
from .resolver import resolve_eval_plan

Clock = Callable[[], datetime]


@dataclass
class CaseExecutionRecord:
    case_execution_id: str
    case_id: str
    case_version: int
    state: str
    request_hash: str
    adapter_id: str
    adapter_version: str
    latency_ms: float
    usage: dict[str, Any] | None
    error: dict[str, Any] | None
    raw_path: str


@dataclass
class RunResult:
    manifest: RunManifest
    records: list[CaseExecutionRecord]
    run_dir: Path


def _emit(
    writer: RunArtifactWriter,
    case_execution_id: str,
    sequence: int,
    event_type: str,
    timestamp: datetime,
    transition: StateTransition,
    output_refs: list[str] | None = None,
) -> int:
    event = TraceEvent(
        event_id=f"{case_execution_id}:{sequence}",
        case_execution_id=case_execution_id,
        sequence=sequence,
        event_type=event_type,
        actor="harness.orchestrator",
        timestamp=timestamp,
        state_transition=transition,
        output_refs=output_refs or [],
    )
    writer.append_traces([event.model_dump(mode="json", by_alias=True)])
    return sequence + 1


def execute_plan(
    plan: EvalPlan,
    adapter: TargetAdapter,
    *,
    repo_root: Path,
    runs_dir: Path | None = None,
    run_id: str | None = None,
    repo_revision: str | None = None,
    clock: Clock | None = None,
) -> RunResult:
    tick: Clock = clock or (lambda: datetime.now(UTC))
    run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
    runs_dir = runs_dir or (repo_root / "runs")

    resolved = resolve_eval_plan(
        plan, run_id=run_id, repo_root=repo_root, repo_revision=repo_revision, now=tick()
    )
    writer = RunArtifactWriter(runs_dir, run_id)
    running = resolved.manifest.model_copy(update={"status": RunStatus.RUNNING})
    writer.write_manifest(running.as_json())

    records: list[CaseExecutionRecord] = []
    for case in resolved.cases:
        cx_id = f"{run_id}:{case.case_id}"
        seq = _emit(
            writer, cx_id, 0, "invocation_started", tick(),
            StateTransition.of("pending", "invoking"),
        )
        result = adapter.invoke(case, InvocationContext(run_id=run_id, case_execution_id=cx_id))

        # --- RAW CAPTURE BEFORE ANY PARSING (ADR 0002) ---
        raw_path = writer.write_raw(cx_id, result.raw_output)

        if result.error is not None or result.raw_output is None:
            state = CaseExecutionState.INVOCATION_ERROR
            seq = _emit(
                writer, cx_id, seq, "invocation_error", tick(),
                StateTransition.of("invoking", "invocation_error"),
            )
        else:
            state = CaseExecutionState.RESPONSE_RECEIVED
            seq = _emit(
                writer, cx_id, seq, "response_received", tick(),
                StateTransition.of("invoking", "response_received"),
                output_refs=[f"raw/{raw_path.name}"],
            )

        record = CaseExecutionRecord(
            case_execution_id=cx_id,
            case_id=case.case_id,
            case_version=case.case_version,
            state=str(state),
            request_hash=result.request_hash,
            adapter_id=result.adapter_id,
            adapter_version=result.adapter_version,
            latency_ms=result.latency_ms,
            usage=result.usage,
            error=result.error.model_dump() if result.error is not None else None,
            raw_path=str(raw_path.relative_to(writer.paths.root)).replace("\\", "/"),
        )
        writer.append_case_execution(asdict(record))
        records.append(record)

    completed = resolved.manifest.model_copy(
        update={"status": RunStatus.COMPLETED, "completed_at": tick()}
    )
    writer.write_manifest(completed.as_json())
    return RunResult(manifest=completed, records=records, run_dir=writer.paths.root)
