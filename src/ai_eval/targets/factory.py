"""Build a target adapter from a plan's :class:`TargetSpec`.

One entry point resolves both kinds of target, so the runner, CLI, and CI never branch on
"is this a fixture or a real model?" — a recorded fixture and Claude are selected the same way
and produce the same evidence envelope.

API keys are never read or stored here: each provider SDK picks up its own environment
variable, so no credential ever passes through platform code or lands in a manifest.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_eval.execution.models import TargetSpec
from ai_eval.prompts import load_prompt_spec

from .base import TargetAdapter
from .fixture import RECORDED_TARGETS, get_recorded_target
from .providers import PROVIDER_CLIENTS, ModelConfig, ProviderTargetAdapter

DEFAULT_PROMPT_ROOT = Path("prompts") / "reference"


class TargetBuildError(ValueError):
    """Raised when a target spec cannot be resolved into an adapter."""


def build_target(
    spec: TargetSpec,
    *,
    repo_root: Path,
    client: Any | None = None,
) -> TargetAdapter:
    """Resolve a target spec into a live adapter.

    ``client`` may be injected to bypass SDK construction (used by tests and for recorded
    provider responses).
    """
    if spec.adapter_id in RECORDED_TARGETS:
        return get_recorded_target(spec.adapter_id)

    config = dict(spec.config_refs or {})
    provider = config.get("provider")
    if provider is None:
        raise TargetBuildError(
            f"unknown target '{spec.adapter_id}': not a recorded fixture and no 'provider' "
            f"in config_refs. Known fixtures: {sorted(RECORDED_TARGETS)}"
        )
    if provider not in PROVIDER_CLIENTS:
        raise TargetBuildError(
            f"unsupported provider '{provider}'; known: {sorted(PROVIDER_CLIENTS)}"
        )
    model = config.get("model")
    if not model:
        raise TargetBuildError(f"target '{spec.adapter_id}' config_refs is missing 'model'")

    prompt_spec = load_prompt_spec(
        repo_root / DEFAULT_PROMPT_ROOT,
        str(config.get("prompt_spec_id", "request_triage")),
        str(config.get("prompt_spec_version", "v1")),
    )
    model_config = ModelConfig(
        provider=str(provider),
        model=str(model),
        temperature=float(config.get("temperature", 0.0)),
        max_output_tokens=int(config.get("max_output_tokens", 2048)),
        timeout_s=float(config.get("timeout_s", 60.0)),
        max_attempts=int(config.get("max_attempts", 3)),
        seed=config.get("seed"),
    )
    if client is None:
        client_cls = PROVIDER_CLIENTS[provider]
        client = (
            client_cls(model_id=str(model))
            if provider == "huggingface"
            else client_cls()
        )
    return ProviderTargetAdapter(
        client=client,
        prompt_spec=prompt_spec,
        model_config=model_config,
        adapter_id=spec.adapter_id,
        adapter_version=spec.adapter_version,
    )
