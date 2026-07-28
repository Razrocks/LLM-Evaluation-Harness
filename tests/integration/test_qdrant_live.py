"""Live Qdrant integration — skips unless a Qdrant is reachable at ``QDRANT_URL``.

Validates the real :class:`QdrantVectorIndex` against a running service (``docker compose up -d
qdrant``). It uses the deterministic hashing embedder, so it needs **Qdrant only** — no
HuggingFace model download. This is the test that turns the Qdrant adapter from "written" into
"exercised".
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO / "corpora/reference/business_docs/v1/documents"
CASES = REPO / "datasets/reference/grounded_qa/v1/retrieval_cases.jsonl"
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")

pytest.importorskip("qdrant_client", reason="qdrant-client not installed (uv sync --extra rag)")


def _qdrant_reachable() -> bool:
    try:
        from qdrant_client import QdrantClient

        QdrantClient(url=QDRANT_URL, timeout=2.0).get_collections()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _qdrant_reachable(), reason=f"no Qdrant reachable at {QDRANT_URL}"
)


def test_qdrant_roundtrip_recall_and_integrity() -> None:
    from qdrant_client import QdrantClient

    from ai_eval.retrieval import (
        HashingEmbedder,
        IndexIntegrityError,
        QdrantVectorIndex,
        RetrievalConfig,
        Retriever,
        build_corpus_from_dir,
        build_index,
        chunk_corpus,
        evaluate_retrieval,
        load_retrieval_cases,
    )

    corpus = build_corpus_from_dir(CORPUS_DIR, corpus_id="business_docs", corpus_version="1")
    chunks = chunk_corpus(corpus).chunks
    embedder = HashingEmbedder()
    collection = f"ai_eval_test_{uuid.uuid4().hex[:8]}"

    index = QdrantVectorIndex(
        collection, dimension=embedder.config.dimension, url=QDRANT_URL
    )
    try:
        assert build_index(chunks, embedder, index, _cfg(embedder, collection)) == len(chunks)

        retriever = Retriever(embedder, index, _cfg(embedder, collection))
        pairs = [
            (case, [r.chunk_id for r in retriever.retrieve(case.query).results])
            for case in load_retrieval_cases(CASES)
        ]
        summary = evaluate_retrieval(pairs, k=3)
        assert summary.recall_at_k == 1.0

        # The real index also carries the payload refs that catch a stale corpus version.
        stale = _cfg(embedder, collection, corpus_version="2")
        with pytest.raises(IndexIntegrityError):
            Retriever(embedder, index, stale).retrieve("refunds")
    finally:
        QdrantClient(url=QDRANT_URL).delete_collection(collection)


def _cfg(embedder, collection: str, corpus_version: str = "1"):
    from ai_eval.retrieval import RetrievalConfig

    return RetrievalConfig(
        retrieval_config_id="live_cfg",
        corpus_id="business_docs",
        corpus_version=corpus_version,
        chunker_version="v1",
        embedding=embedder.config,
        collection=collection,
        top_k=3,
    )
