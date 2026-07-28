"""RAG evaluation (M7): deterministic ingestion, chunking, embeddings, vector retrieval, and
retrieval metrics. Qdrant is a derived index; canonical sources live in these models.

sentence-transformers and qdrant-client are optional (``uv sync --extra rag``) and lazy-imported;
the offline path (:class:`HashingEmbedder` + :class:`InMemoryVectorIndex`) needs neither.
"""

from __future__ import annotations

from .chunker import CHUNKER_VERSION, chunk_corpus
from .embeddings import Embedder, HashingEmbedder, SentenceTransformerEmbedder
from .index import IndexPoint, InMemoryVectorIndex, QdrantVectorIndex, ScoredPoint, VectorIndex
from .ingest import build_corpus_from_dir, ingest_document, load_corpus, load_retrieval_cases
from .metrics import (
    RetrievalCase,
    RetrievalMetricSummary,
    evaluate_retrieval,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from .models import (
    Chunk,
    ChunkManifest,
    Corpus,
    DocumentVersion,
    EmbeddingConfig,
    RetrievalConfig,
    RetrievalRun,
    RetrievedChunk,
)
from .retriever import IndexIntegrityError, Retriever, build_index

__all__ = [
    "CHUNKER_VERSION",
    "Chunk",
    "ChunkManifest",
    "Corpus",
    "DocumentVersion",
    "Embedder",
    "EmbeddingConfig",
    "HashingEmbedder",
    "InMemoryVectorIndex",
    "IndexIntegrityError",
    "IndexPoint",
    "QdrantVectorIndex",
    "RetrievalCase",
    "RetrievalConfig",
    "RetrievalMetricSummary",
    "RetrievalRun",
    "RetrievedChunk",
    "Retriever",
    "ScoredPoint",
    "SentenceTransformerEmbedder",
    "VectorIndex",
    "build_corpus_from_dir",
    "build_index",
    "chunk_corpus",
    "evaluate_retrieval",
    "ingest_document",
    "load_corpus",
    "load_retrieval_cases",
    "ndcg_at_k",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
]
