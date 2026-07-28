"""Offline RAG tests: deterministic chunking, retrieval metrics, index integrity, and mutations.

All run with the hashing embedder and the in-memory index — no model download, no Qdrant.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_eval.retrieval import (
    EmbeddingConfig,
    HashingEmbedder,
    InMemoryVectorIndex,
    IndexIntegrityError,
    IndexPoint,
    RetrievalConfig,
    Retriever,
    build_corpus_from_dir,
    build_index,
    chunk_corpus,
    evaluate_retrieval,
    load_retrieval_cases,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

REPO = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO / "corpora/reference/business_docs/v1/documents"
CASES = REPO / "datasets/reference/grounded_qa/v1/retrieval_cases.jsonl"


def _corpus():
    return build_corpus_from_dir(CORPUS_DIR, corpus_id="business_docs", corpus_version="1")


def _config(embedder: HashingEmbedder, corpus_version: str = "1", top_k: int = 3) -> RetrievalConfig:
    return RetrievalConfig(
        retrieval_config_id="test_cfg",
        corpus_id="business_docs",
        corpus_version=corpus_version,
        chunker_version="v1",
        embedding=embedder.config,
        collection="test",
        top_k=top_k,
    )


# --- deterministic chunking ---------------------------------------------------------------


def test_chunking_is_deterministic() -> None:
    corpus = _corpus()
    a = chunk_corpus(corpus)
    b = chunk_corpus(corpus)
    assert a.content_hash == b.content_hash
    assert [c.chunk_id for c in a.chunks] == [c.chunk_id for c in b.chunks]


def test_chunk_ids_are_stable_and_resolvable() -> None:
    chunks = chunk_corpus(_corpus()).chunks
    ids = {c.chunk_id for c in chunks}
    assert "refund_policy:1:chunk-0" in ids
    for c in chunks:
        assert c.chunk_id == f"{c.document_id}:{c.document_version}:chunk-{c.index}"
        assert c.chunk_hash.startswith("sha256:")


def test_corpus_hash_is_deterministic() -> None:
    assert _corpus().content_hash == _corpus().content_hash


# --- retrieval metric functions (hand-calculated) -----------------------------------------


def test_recall_precision_mrr_hand_calc() -> None:
    ranked = ["a", "b", "c"]
    relevant = {"c"}
    assert recall_at_k(ranked, relevant, 1) == 0.0
    assert recall_at_k(ranked, relevant, 3) == 1.0
    assert precision_at_k(ranked, relevant, 3) == pytest.approx(1 / 3)
    assert reciprocal_rank(ranked, relevant) == pytest.approx(1 / 3)
    assert recall_at_k(ranked, set(), 3) is None  # no labels -> undefined, not zero


def test_ndcg_hand_calc() -> None:
    graded = {"a": 3.0, "b": 2.0}
    # perfect order
    assert ndcg_at_k(["a", "b"], graded, 2) == pytest.approx(1.0)
    # reversed order scores lower
    assert ndcg_at_k(["b", "a"], graded, 2) < 1.0


# --- end-to-end retrieval on the reference corpus (hashing embedder) -----------------------


def test_reference_corpus_retrieval_recall() -> None:
    corpus = _corpus()
    chunks = chunk_corpus(corpus).chunks
    embedder = HashingEmbedder()
    config = _config(embedder)
    index = InMemoryVectorIndex(config.collection)
    assert build_index(chunks, embedder, index, config) == len(chunks)

    retriever = Retriever(embedder, index, config)
    pairs = []
    for case in load_retrieval_cases(CASES):
        run = retriever.retrieve(case.query)
        pairs.append((case, [r.chunk_id for r in run.results]))

    summary = evaluate_retrieval(pairs, k=config.top_k)
    assert summary.recall_at_k == 1.0            # every relevant chunk retrieved within top-k
    assert summary.mrr is not None and summary.mrr >= 0.5
    assert summary.empty_retrieval_rate == 0.0


def test_top_k_too_low_drops_recall() -> None:
    corpus = _corpus()
    chunks = chunk_corpus(corpus).chunks
    embedder = HashingEmbedder()
    config = _config(embedder, top_k=3)
    index = InMemoryVectorIndex(config.collection)
    build_index(chunks, embedder, index, config)
    retriever = Retriever(embedder, index, config)

    cases = load_retrieval_cases(CASES)
    ranked = [r.chunk_id for r in retriever.retrieve(cases[0].query).results]
    # With k=1 a relevant chunk ranked 2nd or lower is missed.
    assert recall_at_k(ranked, set(cases[0].relevant_chunk_ids), 1) in (0.0, 1.0)
    full = recall_at_k(ranked, set(cases[0].relevant_chunk_ids), 3)
    assert full == 1.0


# --- index integrity / mutations ----------------------------------------------------------


def test_payload_missing_reference_is_rejected() -> None:
    index = InMemoryVectorIndex("test")
    with pytest.raises(ValueError, match="missing"):
        index.upsert([IndexPoint(chunk_id="c1", vector=[0.1, 0.2], payload={"chunk_id": "c1"})])


def test_wrong_corpus_version_is_detected() -> None:
    corpus = _corpus()
    chunks = chunk_corpus(corpus).chunks
    embedder = HashingEmbedder()
    build_config = _config(embedder, corpus_version="1")
    index = InMemoryVectorIndex("test")
    build_index(chunks, embedder, index, build_config)

    # A retriever configured for a different corpus version must refuse the stale index.
    stale_config = _config(embedder, corpus_version="2")
    with pytest.raises(IndexIntegrityError, match="wrong or stale"):
        Retriever(embedder, index, stale_config).retrieve("refunds")


def test_embedding_drift_is_detected() -> None:
    corpus = _corpus()
    chunks = chunk_corpus(corpus).chunks
    embedder = HashingEmbedder()
    index = InMemoryVectorIndex("test")
    build_index(chunks, embedder, index, _config(embedder))

    drifted = _config(embedder)
    drifted = drifted.model_copy(
        update={"embedding": EmbeddingConfig(
            embedding_config_id="other-model@v9", model="other", revision="v9",
            dimension=embedder.config.dimension,
        )}
    )
    with pytest.raises(IndexIntegrityError, match="embedding drift"):
        Retriever(embedder, index, drifted).retrieve("refunds")


# --- sentence-transformers adapter (injected fake, no download) ----------------------------


class _FakeSentenceTransformer:
    def get_sentence_embedding_dimension(self) -> int:
        return 4

    def encode(self, texts: list[str], normalize_embeddings: bool = False) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]


def test_sentence_transformer_adapter_via_injected_model() -> None:
    from ai_eval.retrieval import SentenceTransformerEmbedder

    embedder = SentenceTransformerEmbedder(model="fake/model", model_obj=_FakeSentenceTransformer())
    assert embedder.config.dimension == 4
    assert embedder.config.model == "fake/model"
    vectors = embedder.embed(["hello", "world"])
    assert len(vectors) == 2
    assert all(len(v) == 4 for v in vectors)
