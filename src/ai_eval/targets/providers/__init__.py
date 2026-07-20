"""Live model-provider targets behind the one shared TargetAdapter contract.

Claude, ChatGPT, Gemini, and local HuggingFace models are evaluated with the *same* dataset,
prompt spec, output schema, scorers, and gate as the recorded fixtures — which is what makes a
cross-model comparison fair rather than an accident of plumbing.

All SDKs are optional (``uv sync --extra providers`` / ``--extra ml``) and imported lazily, so
the core install, the offline demo, and CI never require them.
"""

from __future__ import annotations

from typing import Any

from .base import (
    TRANSIENT_KINDS,
    ModelConfig,
    ProviderClient,
    ProviderError,
    ProviderErrorKind,
    ProviderResponse,
    ProviderTargetAdapter,
    classify_sdk_exception,
)
from .clients import AnthropicClient, GeminiClient, HuggingFaceClient, OpenAIClient

#: Provider key -> client class, for building an adapter from configuration.
#: Clients satisfy :class:`ProviderClient` structurally rather than by inheritance.
PROVIDER_CLIENTS: dict[str, type[Any]] = {
    "anthropic": AnthropicClient,
    "openai": OpenAIClient,
    "google": GeminiClient,
    "huggingface": HuggingFaceClient,
}

__all__ = [
    "PROVIDER_CLIENTS",
    "TRANSIENT_KINDS",
    "AnthropicClient",
    "GeminiClient",
    "HuggingFaceClient",
    "ModelConfig",
    "OpenAIClient",
    "ProviderClient",
    "ProviderError",
    "ProviderErrorKind",
    "ProviderResponse",
    "ProviderTargetAdapter",
    "classify_sdk_exception",
]
