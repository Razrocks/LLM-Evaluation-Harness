"""Provider adapter contract — exercised with a fake client, so no SDK and no network.

These prove the parts that actually bite in production: retry only on transient failures,
never on a semantic one; errors normalized into the controlled taxonomy; usage/latency/config
captured as evidence; and the raw output passed through completely unmodified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_eval.datasets import load_cases_dir
from ai_eval.domain import FailureCode
from ai_eval.execution.models import TargetSpec
from ai_eval.prompts import load_prompt_spec, render_prompt
from ai_eval.targets import InvocationContext, TargetBuildError, build_target
from ai_eval.targets.providers import (
    ModelConfig,
    ProviderError,
    ProviderErrorKind,
    ProviderResponse,
    ProviderTargetAdapter,
    classify_sdk_exception,
)

REPO = Path(__file__).resolve().parents[2]
CASES = load_cases_dir(REPO / "datasets/reference/request_triage/v1/cases")
CASE = CASES[0]
SPEC = load_prompt_spec(REPO / "prompts" / "reference", "request_triage", "v1")
CONFIG = ModelConfig(provider="fake", model="fake-1", max_attempts=3)


class FakeClient:
    """Scripted client: each entry is a ProviderResponse to return or an exception to raise."""

    provider = "fake"

    def __init__(self, script: list[object]) -> None:
        self.script = list(script)
        self.calls = 0
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(self, *, system: str, user: str, config: ModelConfig) -> ProviderResponse:
        self.calls += 1
        self.last_system, self.last_user = system, user
        item = self.script.pop(0) if self.script else ProviderResponse(text="{}")
        if isinstance(item, BaseException):
            raise item
        assert isinstance(item, ProviderResponse)
        return item


def _adapter(script: list[object]) -> tuple[ProviderTargetAdapter, FakeClient]:
    client = FakeClient(script)
    adapter = ProviderTargetAdapter(
        client=client, prompt_spec=SPEC, model_config=CONFIG,
        sleeper=lambda _s: None,  # no real backoff in tests
    )
    return adapter, client


def _ctx() -> InvocationContext:
    return InvocationContext(run_id="r", case_execution_id="r:c")


def test_successful_invocation_captures_evidence() -> None:
    payload = json.dumps({"summary": "s"})
    adapter, client = _adapter([
        ProviderResponse(text=payload, input_tokens=100, output_tokens=20,
                         provider_request_id="req_1", model_revision="fake-1-2026",
                         finish_reason="stop")
    ])
    result = adapter.invoke(CASE, _ctx())

    assert result.raw_output == payload  # passed through verbatim, never repaired
    assert result.succeeded
    assert result.usage == {"input_tokens": 100, "output_tokens": 20, "finish_reason": "stop"}
    assert result.provider_request_id == "req_1"
    assert result.latency_ms >= 0
    assert result.config_refs["model"] == "fake-1"
    assert result.config_refs["model_revision"] == "fake-1-2026"
    assert result.config_refs["prompt_spec_hash"] == SPEC.content_hash
    assert client.calls == 1


def test_transient_failure_is_retried_then_succeeds() -> None:
    adapter, client = _adapter([
        ProviderError(ProviderErrorKind.RATE_LIMIT, "429"),
        ProviderResponse(text="{}", input_tokens=1, output_tokens=1),
    ])
    result = adapter.invoke(CASE, _ctx())
    assert result.succeeded
    assert client.calls == 2
    assert len(result.attempts) == 2
    assert result.attempts[0].error is not None  # the failed attempt is retained as evidence


def test_auth_failure_is_not_retried() -> None:
    adapter, client = _adapter([ProviderError(ProviderErrorKind.AUTH, "401")])
    result = adapter.invoke(CASE, _ctx())
    assert client.calls == 1  # terminal: fail fast
    assert result.error is not None
    assert result.error.error_code == str(FailureCode.PROVIDER_AUTH_ERROR)
    assert result.raw_output is None


def test_exhausted_retries_report_retry_exhausted() -> None:
    adapter, client = _adapter([ProviderError(ProviderErrorKind.TIMEOUT, "t") for _ in range(3)])
    result = adapter.invoke(CASE, _ctx())
    assert client.calls == CONFIG.max_attempts
    assert result.error is not None
    assert result.error.error_code == str(FailureCode.RETRY_EXHAUSTED)


def test_bad_json_is_never_retried() -> None:
    """A semantic failure is the measurement, not an error to paper over."""
    adapter, client = _adapter([ProviderResponse(text="{not json")])
    result = adapter.invoke(CASE, _ctx())
    assert client.calls == 1
    assert result.raw_output == "{not json"
    assert result.error is None  # invocation succeeded; scoring will judge the content


def test_prompt_sent_matches_rendered_spec() -> None:
    adapter, client = _adapter([ProviderResponse(text="{}")])
    adapter.invoke(CASE, _ctx())
    rendered = render_prompt(SPEC, CASE.input)
    assert client.last_system == rendered.system
    assert client.last_user == rendered.user


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (TimeoutError("t"), ProviderErrorKind.TIMEOUT),
        (type("RateLimitError", (Exception,), {})(), ProviderErrorKind.RATE_LIMIT),
        (type("AuthenticationError", (Exception,), {})(), ProviderErrorKind.AUTH),
        (type("APIConnectionError", (Exception,), {})(), ProviderErrorKind.UNAVAILABLE),
        (type("WeirdError", (Exception,), {})(), ProviderErrorKind.UNKNOWN),
    ],
)
def test_sdk_exception_classification(exc: BaseException, expected: ProviderErrorKind) -> None:
    assert classify_sdk_exception(exc) is expected


def test_http_status_classification() -> None:
    exc = type("SomeError", (Exception,), {})()
    exc.status_code = 503  # type: ignore[attr-defined]
    assert classify_sdk_exception(exc) is ProviderErrorKind.UNAVAILABLE
    exc.status_code = 500  # type: ignore[attr-defined]
    assert classify_sdk_exception(exc) is ProviderErrorKind.SERVER


# --- target factory -----------------------------------------------------------------------


def test_factory_resolves_recorded_fixture() -> None:
    spec = TargetSpec(adapter_id="recorded_pass", adapter_version="v1")
    adapter = build_target(spec, repo_root=REPO)
    assert adapter.adapter_id == "recorded_pass"


def test_factory_builds_provider_adapter_with_injected_client() -> None:
    spec = TargetSpec(
        adapter_id="provider_anthropic",
        adapter_version="v1",
        config_refs={"provider": "anthropic", "model": "claude-sonnet-5", "temperature": 0.0},
    )
    client = FakeClient([ProviderResponse(text="{}")])
    adapter = build_target(spec, repo_root=REPO, client=client)
    assert isinstance(adapter, ProviderTargetAdapter)
    assert adapter.config.model == "claude-sonnet-5"
    assert adapter.prompt_spec.content_hash == SPEC.content_hash


def test_factory_rejects_unknown_target() -> None:
    with pytest.raises(TargetBuildError, match="not a recorded fixture"):
        build_target(TargetSpec(adapter_id="nope", adapter_version="v1"), repo_root=REPO)


def test_factory_rejects_unsupported_provider() -> None:
    spec = TargetSpec(
        adapter_id="provider_x", adapter_version="v1",
        config_refs={"provider": "not_a_provider", "model": "m"},
    )
    with pytest.raises(TargetBuildError, match="unsupported provider"):
        build_target(spec, repo_root=REPO)


def test_factory_requires_a_model() -> None:
    spec = TargetSpec(
        adapter_id="provider_anthropic", adapter_version="v1",
        config_refs={"provider": "anthropic"},
    )
    with pytest.raises(TargetBuildError, match="missing 'model'"):
        build_target(spec, repo_root=REPO)


def test_shipped_provider_plan_builds_with_injected_client() -> None:
    """The plan committed for the live-provider workflow must actually resolve."""
    plan = json.loads(
        (REPO / "configs" / "plans" / "reference_request_triage_provider.json").read_text(
            encoding="utf-8"
        )
    )
    spec = TargetSpec.model_validate(plan["target"])
    adapter = build_target(spec, repo_root=REPO, client=FakeClient([ProviderResponse(text="{}")]))
    assert isinstance(adapter, ProviderTargetAdapter)
