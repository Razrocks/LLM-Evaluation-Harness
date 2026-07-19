"""The provider-neutral target-adapter contract.

A target adapter invokes one workflow implementation behind a single typed interface and
returns everything needed as evidence — the raw output (captured verbatim, never repaired
here), traces, attempts, usage, latency, and a structured error envelope. Scoring lives
elsewhere; an adapter never judges correctness.

The same contract is satisfied by the recorded fixtures (this milestone) and by live provider
adapters (M5), so the orchestrator, artifact writer, parser, and scorers never learn which
kind of target produced a result.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import ErrorEnvelope, EvalCase, TraceEvent


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InvocationContext(_Base):
    """Run-scoped identifiers passed to an adapter for a single case execution."""

    run_id: str
    case_execution_id: str


class Attempt(_Base):
    """One invocation attempt (retries append further attempts)."""

    number: int = Field(ge=1)
    latency_ms: float = Field(ge=0)
    provider_request_id: str | None = None
    error: ErrorEnvelope | None = None


class TargetInvocationResult(_Base):
    """Everything one target invocation produced, captured as evidence before any parsing."""

    adapter_id: str
    adapter_version: str
    target_workflow_ref: str
    request_hash: str
    raw_output: str | None
    native_parsed: dict[str, Any] | None = None
    provider_request_id: str | None = None
    attempts: list[Attempt] = Field(default_factory=list)
    trace_events: list[TraceEvent] = Field(default_factory=list)
    usage: dict[str, Any] | None = None
    latency_ms: float = Field(default=0.0, ge=0)
    error: ErrorEnvelope | None = None
    config_refs: dict[str, Any] = Field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.raw_output is not None


class TargetAdapter(ABC):
    """Base class for all target adapters.

    Implementations must set ``adapter_id`` / ``adapter_version`` and implement
    :meth:`invoke`. **Live provider adapters must read only ``case.input``.** Recorded fixture
    adapters may additionally read ``case.expected`` to synthesize deterministic outputs —
    that is their entire purpose as test doubles.
    """

    adapter_id: str
    adapter_version: str

    @abstractmethod
    def invoke(self, case: EvalCase, ctx: InvocationContext) -> TargetInvocationResult:
        """Invoke the target for one case and return captured evidence."""
        raise NotImplementedError

    @property
    def ref(self) -> str:
        return f"{self.adapter_id}.{self.adapter_version}"
