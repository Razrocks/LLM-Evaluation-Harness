"""Concrete provider clients: Claude, ChatGPT, Gemini, and local HuggingFace.

Every client does the same three things and nothing more: lazy-import its SDK (so the core
install needs none of them), issue one completion under the frozen :class:`ModelConfig`, and
translate SDK failures into :class:`ProviderError`. Business meaning stays entirely outside.

Each accepts an injected ``client`` object, which is what lets the contract tests exercise the
full adapter offline with a stub.
"""

from __future__ import annotations

from typing import Any

from .base import (
    ModelConfig,
    ProviderError,
    ProviderErrorKind,
    ProviderResponse,
    classify_sdk_exception,
)


def _missing_sdk(package: str, extra: str) -> ProviderError:
    return ProviderError(
        ProviderErrorKind.UNAVAILABLE,
        f"{package} is not installed; install the optional extra: uv sync --extra {extra}",
    )


def _wrap(exc: BaseException) -> ProviderError:
    return ProviderError(
        classify_sdk_exception(exc),
        f"{type(exc).__name__}: {exc}",
        provider_request_id=getattr(exc, "request_id", None),
    )


class AnthropicClient:
    """Claude via the official Anthropic SDK."""

    provider = "anthropic"

    def __init__(self, *, api_key: str | None = None, client: Any | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def _ensure(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise _missing_sdk("anthropic", "providers") from exc
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, *, system: str, user: str, config: ModelConfig) -> ProviderResponse:
        client = self._ensure()
        try:
            message = client.messages.create(
                model=config.model,
                max_tokens=config.max_output_tokens,
                temperature=config.temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
                timeout=config.timeout_s,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise _wrap(exc) from exc

        text = "".join(
            getattr(block, "text", "")
            for block in getattr(message, "content", []) or []
            if getattr(block, "type", None) == "text"
        )
        usage = getattr(message, "usage", None)
        return ProviderResponse(
            text=text or None,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            provider_request_id=getattr(message, "id", None),
            model_revision=getattr(message, "model", None),
            finish_reason=getattr(message, "stop_reason", None),
        )


class OpenAIClient:
    """ChatGPT via the official OpenAI SDK."""

    provider = "openai"

    def __init__(self, *, api_key: str | None = None, client: Any | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def _ensure(self) -> Any:
        if self._client is None:
            try:
                import openai
            except ImportError as exc:  # pragma: no cover
                raise _missing_sdk("openai", "providers") from exc
            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def complete(self, *, system: str, user: str, config: ModelConfig) -> ProviderResponse:
        client = self._ensure()
        try:
            completion = client.chat.completions.create(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_output_tokens,
                timeout=config.timeout_s,
                seed=config.seed,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise _wrap(exc) from exc

        choices = getattr(completion, "choices", []) or []
        first = choices[0] if choices else None
        text = getattr(getattr(first, "message", None), "content", None)
        usage = getattr(completion, "usage", None)
        return ProviderResponse(
            text=text or None,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            provider_request_id=getattr(completion, "id", None),
            model_revision=getattr(completion, "model", None),
            finish_reason=getattr(first, "finish_reason", None),
        )


class GeminiClient:
    """Gemini via the official google-genai SDK."""

    provider = "google"

    def __init__(self, *, api_key: str | None = None, client: Any | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def _ensure(self) -> Any:
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover
                raise _missing_sdk("google-genai", "providers") from exc
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def complete(self, *, system: str, user: str, config: ModelConfig) -> ProviderResponse:
        client = self._ensure()
        try:
            response = client.models.generate_content(
                model=config.model,
                contents=user,
                config={
                    "system_instruction": system,
                    "temperature": config.temperature,
                    "max_output_tokens": config.max_output_tokens,
                    "response_mime_type": "application/json",
                },
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise _wrap(exc) from exc

        usage = getattr(response, "usage_metadata", None)
        return ProviderResponse(
            text=getattr(response, "text", None) or None,
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
            provider_request_id=getattr(response, "response_id", None),
            model_revision=getattr(response, "model_version", None),
            finish_reason=None,
        )


class HuggingFaceClient:
    """A locally hosted HuggingFace model (no API key, no network at inference time).

    Token counts come from the tokenizer, so a local model still reports usage and can be
    compared on the same operational metrics as the hosted providers.
    """

    provider = "huggingface"

    def __init__(self, *, model_id: str | None = None, pipeline: Any | None = None) -> None:
        self._pipeline = pipeline
        self._model_id = model_id

    def _ensure(self) -> Any:
        if self._pipeline is None:
            try:
                from transformers import pipeline as hf_pipeline
            except ImportError as exc:  # pragma: no cover
                raise _missing_sdk("transformers", "ml") from exc
            self._pipeline = hf_pipeline("text-generation", model=self._model_id)
        return self._pipeline

    def complete(self, *, system: str, user: str, config: ModelConfig) -> ProviderResponse:
        pipe = self._ensure()
        prompt = f"{system}\n\n{user}\n"
        try:
            outputs = pipe(
                prompt,
                max_new_tokens=config.max_output_tokens,
                do_sample=config.temperature > 0,
                temperature=config.temperature if config.temperature > 0 else None,
                return_full_text=False,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise _wrap(exc) from exc

        text = None
        if isinstance(outputs, list) and outputs:
            first = outputs[0]
            text = first.get("generated_text") if isinstance(first, dict) else None

        tokenizer = getattr(pipe, "tokenizer", None)
        input_tokens = len(tokenizer.encode(prompt)) if tokenizer is not None else None
        output_tokens = (
            len(tokenizer.encode(text)) if (tokenizer is not None and text) else None
        )
        return ProviderResponse(
            text=text or None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_request_id=None,
            model_revision=self._model_id,
            finish_reason=None,
        )
