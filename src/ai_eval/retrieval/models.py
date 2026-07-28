"""Canonical retrieval domain models (M7).

Qdrant is a *derived* index ([adr/0004]); these models are the source of truth. A corpus has
versioned documents; a document version deterministically produces chunks; a frozen
:class:`RetrievalConfig` pins everything needed to reproduce a retrieval run. Every chunk and
every retrieved result carries the references (`corpus_version_id`, `document_version_id`,
`chunk_id`, `chunk_hash`, `embedding_config_id`) that let the harness detect a wrong or stale
index instead of silently scoring against it.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentVersion(_Base):
    """An immutable snapshot of one source document."""

    document_id: str
    document_version: str
    text: str
    content_hash: str


class Corpus(_Base):
    """A versioned set of source documents available to a retrieval workflow."""

    corpus_id: str
    corpus_version: str
    documents: list[DocumentVersion] = Field(default_factory=list)
    content_hash: str | None = None


class Chunk(_Base):
    """A deterministic, addressable segment of one document version.

    ``chunk_id`` is stable and resolvable back to immutable source text:
    ``<document_id>:<document_version>:chunk-<index>``.
    """

    chunk_id: str
    corpus_id: str
    corpus_version: str
    document_id: str
    document_version: str
    index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str
    chunk_hash: str


class ChunkManifest(_Base):
    """The deterministic output of chunking one corpus version."""

    corpus_id: str
    corpus_version: str
    chunker_version: str
    params: dict[str, int] = Field(default_factory=dict)
    chunks: list[Chunk] = Field(default_factory=list)
    content_hash: str | None = None


class EmbeddingConfig(_Base):
    """Frozen embedding configuration. The model revision and dimension are recorded so a
    later index built with a different revision is detectable."""

    embedding_config_id: str
    model: str
    revision: str
    dimension: int
    normalize: bool = True
    distance: str = "cosine"


class RetrievalConfig(_Base):
    """Everything a retrieval run freezes, so it is reproducible."""

    retrieval_config_id: str
    corpus_id: str
    corpus_version: str
    chunker_version: str
    embedding: EmbeddingConfig
    collection: str
    top_k: int = Field(default=5, ge=1)
    score_threshold: float | None = None
    content_hash: str | None = None


class RetrievedChunk(_Base):
    """One ranked result. Payload carries the references used to validate the index."""

    chunk_id: str
    rank: int = Field(ge=0)
    score: float
    document_version_id: str
    corpus_version_id: str
    chunk_hash: str
    embedding_config_id: str


class RetrievalRun(_Base):
    """The ranked results for one query under one frozen configuration."""

    query: str
    retrieval_config_id: str
    collection: str
    results: list[RetrievedChunk] = Field(default_factory=list)
    latency_ms: float = 0.0
