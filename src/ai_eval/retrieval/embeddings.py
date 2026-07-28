"""Embedding models behind one interface.

Two implementations:

- :class:`HashingEmbedder` — deterministic, dependency-free, no download. It hashes tokens into
  a fixed-dimension bag-of-words vector, so shared vocabulary produces high cosine similarity.
  It is not semantic, but it is *reproducible*, which is exactly what the offline retrieval-metric
  and mutation tests need.
- :class:`SentenceTransformerEmbedder` — the real model (default
  ``sentence-transformers/all-MiniLM-L6-v2``), lazy-imported so the core install and offline
  tests never require ``torch``. The exact model + revision + dimension are recorded in the
  embedding config, so an index built with a different revision is detectable.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Protocol

from .models import EmbeddingConfig

_TOKEN = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    @property
    def config(self) -> EmbeddingConfig: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm > 0 else vector


class HashingEmbedder:
    """Deterministic hashing embedder (offline default for tests and the recorded RAG path)."""

    def __init__(self, dimension: int = 64) -> None:
        self._config = EmbeddingConfig(
            embedding_config_id=f"hashing.d{dimension}.v1",
            model="hashing-embedder",
            revision="v1",
            dimension=dimension,
            normalize=True,
            distance="cosine",
        )

    @property
    def config(self) -> EmbeddingConfig:
        return self._config

    def _embed_one(self, text: str) -> list[float]:
        dim = self._config.dimension
        vector = [0.0] * dim
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = digest[0] % dim
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            vector[bucket] += sign
        return _l2_normalize(vector)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


class SentenceTransformerEmbedder:
    """HuggingFace sentence-transformers embedder (live path; lazy-imported)."""

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        revision: str = "main",
        model_obj: Any | None = None,
    ) -> None:
        self._model_name = model
        self._revision = revision
        self._model = model_obj
        self._config: EmbeddingConfig | None = None

    def _ensure(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - only without the rag extra
                raise RuntimeError(
                    "sentence-transformers not installed; run: uv sync --extra rag"
                ) from exc
            self._model = SentenceTransformer(self._model_name, revision=self._revision)
        return self._model

    @property
    def config(self) -> EmbeddingConfig:
        if self._config is None:
            model = self._ensure()
            dim = int(model.get_sentence_embedding_dimension())
            self._config = EmbeddingConfig(
                embedding_config_id=f"{self._model_name}@{self._revision}",
                model=self._model_name,
                revision=self._revision,
                dimension=dim,
                normalize=True,
                distance="cosine",
            )
        return self._config

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vectors]
