"""Shared plumbing for live model-provider targets.

The provider boundary has exactly one job: turn a rendered prompt into raw text plus usage
metadata, and normalize provider-specific failures into our controlled vocabulary. It never
scores, never repairs output, and never decides business correctness.

Two design choices make this testable without installing a single SDK:

1. Each concrete client lazy-imports its SDK and translates that SDK's exceptions into
   :class:`ProviderError` with a typed :class:`ProviderErrorKind`. The retry/classification
   logic here therefore depends on *our* types, not on ``anthropic.RateLimitError``.
2. :class:`ProviderTargetAdapter` takes an injectable client, so contract tests drive the full
   adapter with a fake and no network.

Retries are attempted **only** for transient kinds. A semantic failure — a model that returns
bad JSON — is never retried; that is the thing being measured.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import ErrorEnvelope, EvalCase, FailureCode
from ai_eval.prompts import PromptSpec, render_prompt
from ai_eval.targets.base import (
    Attempt,
    InvocationContext,
    TargetAdapter,
    TargetInvocationResult,
)


class ProviderErrorKind(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    SERVER = "server"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


#: Kinds worth retrying. Everything else fails fast — including anything semantic.
TRANSIENT_KINDS = frozenset(
    {ProviderErrorKind.TIMEOUT, ProviderErrorKind.RATE_LIMIT,
     ProviderErrorKind.SERVER, ProviderErrorKind.UNAVAILABLE}
)

# HTTP statuses that carry meaning for retry classification.
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR_FLOOR = 500
_HTTP_SERVER_ERROR_CEILING = 600

_KIND_TO_CODE = {
    ProviderErrorKind.TIMEOUT: FailureCode.PROVIDER_TIMEOUT,
    ProviderErrorKind.RATE_LIMIT: FailureCode.PROVIDER_RATE_LIMIT,
    ProviderErrorKind.AUTH: FailureCode.PROVIDER_AUTH_ERROR,
    ProviderErrorKind.SERVER: FailureCode.TARGET_INTERNAL_ERROR,
    ProviderErrorKind.UNAVAILABLE: FailureCode.TARGET_UNAVAILABLE,
    ProviderErrorKind.UNKNOWN: FailureCode.TARGET_INTERNAL_ERROR,
}


class ProviderError(Exception):
    """A provider failure normalized into our vocabulary by a concrete client."""

    def __init__(
        self, kind: ProviderErrorKind, message: str, *, provider_request_id: str | None = None
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.provider_request_id = provider_request_id

    @property
    def failure_code(self) -> FailureCode:
        return _KIND_TO_CODE[self.kind]

    @property
    def retryable(self) -> bool:
        return self.kind in TRANSIENT_KINDS


def classify_sdk_exception(exc: BaseException) -> ProviderErrorKind:
    """Classify an SDK exception without importing that SDK's exception types.

    Provider SDKs are optional dependencies, so we cannot ``isinstance`` against
    ``anthropic.RateLimitError``. Class name plus HTTP status is enough to separate the cases
    that matter — transient (retry) from terminal (fail fast) — and each client may override.
    """
    name = type(exc).__name__.lower()
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)

    if isinstance(exc, TimeoutError) or "timeout" in name or "deadline" in name:
        return ProviderErrorKind.TIMEOUT
    if "ratelimit" in name or "resourceexhausted" in name or status == _HTTP_TOO_MANY_REQUESTS:
        return ProviderErrorKind.RATE_LIMIT
    if "auth" in name or "permission" in name or status in (401, 403):
        return ProviderErrorKind.AUTH
    if "connection" in name or "unavailable" in name or status in (404, 503):
        return ProviderErrorKind.UNAVAILABLE
    if isinstance(status, int) and _HTTP_SERVER_ERROR_FLOOR <= status < _HTTP_SERVER_ERROR_CEILING:
        return ProviderErrorKind.SERVER
    return ProviderErrorKind.UNKNOWN


class ModelConfig(BaseModel):
    """The frozen decoding configuration. A model *name* alone is not a configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

    provider: str
    model: str
    temperature: float = 0.0
    max_output_tokens: int = 2048
    timeout_s: float = 60.0
    max_attempts: int = Field(default=3, ge=1)
    seed: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


@dataclass
class ProviderResponse:
    """What a client returns on success. ``text`` is the raw, unmodified model output."""

    text: str | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider_request_id: str | None = None
    model_revision: str | None = None
    finish_reason: str | None = None


class ProviderClient(Protocol):
    """The minimal surface every provider client implements."""

    provider: str

    def complete(self, *, system: str, user: str, config: ModelConfig) -> ProviderResponse:
        """Return raw model output, or raise :class:`ProviderError`."""
        ...


Sleeper = Callable[[float], None]


class ProviderTargetAdapter(TargetAdapter):
    """A live-model target: render a versioned prompt, call a provider, capture evidence."""

    def __init__(
        self,
        *,
        client: ProviderClient,
        prompt_spec: PromptSpec,
        model_config: ModelConfig,
        adapter_id: str | None = None,
        adapter_version: str = "v1",
        target_workflow_ref: str = "reference.request_triage.v1",
        sleeper: Sleeper | None = None,
    ) -> None:
        self.client = client
        self.prompt_spec = prompt_spec
        self.config = model_config
        self.adapter_id = adapter_id or f"provider_{model_config.provider}"
        self.adapter_version = adapter_version
        self.target_workflow_ref = target_workflow_ref
        self._sleep: Sleeper = sleeper if sleeper is not None else time.sleep

    def _backoff_seconds(self, attempt: int) -> float:
        """Deterministic exponential backoff (no jitter: reproducibility beats thundering-herd
        avoidance at eval scale, and tests inject a no-op sleeper anyway)."""
        return min(2.0 ** (attempt - 1), 8.0)

    def invoke(self, case: EvalCase, ctx: InvocationContext) -> TargetInvocationResult:
        rendered = render_prompt(self.prompt_spec, case.input)
        attempts: list[Attempt] = []
        last_error: ProviderError | None = None
        response: ProviderResponse | None = None

        started = time.perf_counter()
        for attempt_number in range(1, self.config.max_attempts + 1):
            attempt_started = time.perf_counter()
            try:
                response = self.client.complete(
                    system=rendered.system, user=rendered.user, config=self.config
                )
                attempts.append(
                    Attempt(
                        number=attempt_number,
                        latency_ms=(time.perf_counter() - attempt_started) * 1000.0,
                        provider_request_id=response.provider_request_id,
                    )
                )
                last_error = None
                break
            except ProviderError as exc:
                last_error = exc
                attempts.append(
                    Attempt(
                        number=attempt_number,
                        latency_ms=(time.perf_counter() - attempt_started) * 1000.0,
                        provider_request_id=exc.provider_request_id,
                        error=ErrorEnvelope(
                            error_class="invocation_error",
                            error_code=str(exc.failure_code),
                            retryable=exc.retryable,
                            message=exc.message,
                            attempt=attempt_number,
                            provider_request_id=exc.provider_request_id,
                        ),
                    )
                )
                if not exc.retryable or attempt_number == self.config.max_attempts:
                    break
                self._sleep(self._backoff_seconds(attempt_number))

        latency_ms = (time.perf_counter() - started) * 1000.0
        config_refs: dict[str, Any] = {
            "prompt_spec_ref": rendered.prompt_spec_ref,
            "prompt_spec_hash": rendered.prompt_spec_hash,
            "provider": self.config.provider,
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_output_tokens": self.config.max_output_tokens,
            "seed": self.config.seed,
        }

        if last_error is not None or response is None:
            code = last_error.failure_code if last_error else FailureCode.TARGET_UNAVAILABLE
            exhausted = (
                last_error is not None
                and last_error.retryable
                and len(attempts) >= self.config.max_attempts
            )
            return TargetInvocationResult(
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                target_workflow_ref=self.target_workflow_ref,
                request_hash=rendered.request_hash,
                raw_output=None,
                attempts=attempts,
                latency_ms=latency_ms,
                error=ErrorEnvelope(
                    error_class="invocation_error",
                    error_code=str(FailureCode.RETRY_EXHAUSTED if exhausted else code),
                    retryable=bool(last_error and last_error.retryable),
                    message=last_error.message if last_error else "no response from provider",
                    attempt=len(attempts),
                    provider_request_id=last_error.provider_request_id if last_error else None,
                ),
                config_refs=config_refs,
            )

        if response.model_revision:
            config_refs["model_revision"] = response.model_revision

        return TargetInvocationResult(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            target_workflow_ref=self.target_workflow_ref,
            request_hash=rendered.request_hash,
            raw_output=response.text,
            provider_request_id=response.provider_request_id,
            attempts=attempts,
            usage={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "finish_reason": response.finish_reason,
            },
            latency_ms=latency_ms,
            config_refs=config_refs,
        )
