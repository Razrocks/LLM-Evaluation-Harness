"""Index building and retrieval.

Indexing embeds each chunk and upserts it with the canonical payload references. Retrieval
embeds the query, asks the index for the top-k, and **validates each result's payload against
the frozen config** — a result whose ``corpus_version_id`` or ``embedding_config_id`` disagrees
with the retrieval config means the index is wrong or stale, and is raised rather than scored.
"""

from __future__ import annotations

import time

from .embeddings import Embedder
from .index import IndexPoint, VectorIndex
from .models import Chunk, RetrievalConfig, RetrievalRun, RetrievedChunk


class IndexIntegrityError(RuntimeError):
    """A retrieved result does not match the frozen retrieval configuration."""


def build_index(
    chunks: list[Chunk], embedder: Embedder, index: VectorIndex, config: RetrievalConfig
) -> int:
    """Embed and upsert chunks with canonical payload references. Returns the point count."""
    vectors = embedder.embed([c.text for c in chunks])
    points = [
        IndexPoint(
            chunk_id=chunk.chunk_id,
            vector=vector,
            payload={
                "chunk_id": chunk.chunk_id,
                "document_version_id": f"{chunk.document_id}:{chunk.document_version}",
                "corpus_version_id": f"{chunk.corpus_id}:{chunk.corpus_version}",
                "chunk_hash": chunk.chunk_hash,
                "embedding_config_id": config.embedding.embedding_config_id,
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    index.upsert(points)
    return index.count()


class Retriever:
    def __init__(self, embedder: Embedder, index: VectorIndex, config: RetrievalConfig) -> None:
        self.embedder = embedder
        self.index = index
        self.config = config
        self._expected_corpus = f"{config.corpus_id}:{config.corpus_version}"

    def retrieve(self, query: str) -> RetrievalRun:
        started = time.perf_counter()
        vector = self.embedder.embed([query])[0]
        hits = self.index.query(vector, top_k=self.config.top_k)
        latency_ms = (time.perf_counter() - started) * 1000.0

        results: list[RetrievedChunk] = []
        for rank, hit in enumerate(hits):
            if self.config.score_threshold is not None and hit.score < self.config.score_threshold:
                continue
            payload = hit.payload
            corpus_version_id = str(payload.get("corpus_version_id", ""))
            embedding_config_id = str(payload.get("embedding_config_id", ""))
            if corpus_version_id != self._expected_corpus:
                raise IndexIntegrityError(
                    f"index serves corpus '{corpus_version_id}' but config expects "
                    f"'{self._expected_corpus}' (wrong or stale index)"
                )
            if embedding_config_id != self.config.embedding.embedding_config_id:
                raise IndexIntegrityError(
                    f"index built with embedding '{embedding_config_id}' but config expects "
                    f"'{self.config.embedding.embedding_config_id}' (embedding drift)"
                )
            results.append(
                RetrievedChunk(
                    chunk_id=hit.chunk_id,
                    rank=rank,
                    score=hit.score,
                    document_version_id=str(payload["document_version_id"]),
                    corpus_version_id=corpus_version_id,
                    chunk_hash=str(payload["chunk_hash"]),
                    embedding_config_id=embedding_config_id,
                )
            )
        return RetrievalRun(
            query=query,
            retrieval_config_id=self.config.retrieval_config_id,
            collection=self.config.collection,
            results=results,
            latency_ms=latency_ms,
        )
