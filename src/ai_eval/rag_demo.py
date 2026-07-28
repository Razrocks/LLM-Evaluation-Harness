"""Offline RAG evaluation run for reference.grounded_qa.v1.

Four steps against the built-in corpus, using the deterministic hashing embedder and the
in-memory index (no download, no Qdrant):

1. baseline: faithful answers -> retrieval recall and grounded pass rate both 1.0;
2. retrieval integrity: a stale corpus version is detected and refused, not scored;
3. generation regression: an invented fact -> grounded pass rate drops while **retrieval recall
   stays 1.0**, and the failure is attributed to generation, not retrieval;
4. corrected: faithful answers pass again.

Returns non-zero if any step's outcome differs from expectation, so it doubles as a smoke test.
ASCII-only output for the Windows console.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ai_eval.grounded import (
    Attribution,
    chunk_text_index,
    evaluate_grounded_qa,
    get_recorded_generator,
    load_grounded_cases,
)
from ai_eval.retrieval import (
    HashingEmbedder,
    IndexIntegrityError,
    InMemoryVectorIndex,
    RetrievalConfig,
    Retriever,
    build_corpus_from_dir,
    build_index,
    chunk_corpus,
)

Echo = Callable[[str], Any]

CORPUS_DIR = Path("corpora/reference/business_docs/v1/documents")
CASES = Path("datasets/reference/grounded_qa/v1/grounded_qa_cases.jsonl")
_RULE = "-" * 72


def _config(embedder: HashingEmbedder, corpus_version: str = "1") -> RetrievalConfig:
    return RetrievalConfig(
        retrieval_config_id="rag_demo", corpus_id="business_docs", corpus_version=corpus_version,
        chunker_version="v1", embedding=embedder.config, collection="rag_demo", top_k=3,
    )


def run_rag_demo(*, repo_root: Path, echo: Echo = print) -> int:  # noqa: PLR0915
    # Linear by design: the four numbered steps map 1:1 to the printed output.
    ok = True
    corpus = build_corpus_from_dir(
        repo_root / CORPUS_DIR, corpus_id="business_docs", corpus_version="1"
    )
    chunks = chunk_corpus(corpus).chunks
    chunk_text = chunk_text_index(chunks)
    embedder = HashingEmbedder()
    config = _config(embedder)
    index = InMemoryVectorIndex(config.collection)
    n = build_index(chunks, embedder, index, config)
    retriever = Retriever(embedder, index, config)
    cases = load_grounded_cases(repo_root / CASES)

    echo(_RULE)
    echo(f"1. Baseline: ingest {len(corpus.documents)} docs -> {len(chunks)} chunks "
         f"({n} indexed); faithful answers")
    echo(_RULE)
    base = evaluate_grounded_qa(
        cases, retriever, get_recorded_generator("grounded_pass"), chunk_text
    )
    echo(f"   retrieval recall@k        = {base.retrieval.recall_at_k}")
    echo(f"   grounded answer_pass_rate = {base.grounded.answer_pass_rate}")
    echo(f"   correct_abstention_rate   = {base.grounded.correct_abstention_rate}")
    ok &= base.retrieval.recall_at_k == 1.0 and base.grounded.answer_pass_rate == 1.0
    echo("")

    echo(_RULE)
    echo("2. Retrieval integrity: point a stale corpus version at the same index")
    echo(_RULE)
    stale = Retriever(embedder, index, _config(embedder, corpus_version="2"))
    try:
        stale.retrieve("refunds")
        echo("   [X] stale index was NOT detected")
        ok = False
    except IndexIntegrityError as exc:
        echo(f"   [OK] refused stale index: {exc}")
    echo("")

    echo(_RULE)
    echo("3. Generation regression: answers invent an unsupported fact")
    echo(_RULE)
    bad = evaluate_grounded_qa(
        cases, retriever, get_recorded_generator("grounded_invented_fact"), chunk_text
    )
    echo(f"   retrieval recall@k        = {bad.retrieval.recall_at_k}   <- retrieval UNCHANGED")
    echo(f"   grounded answer_pass_rate = {bad.grounded.answer_pass_rate}   <- REGRESSED")
    echo(f"   unsupported_claim_rate    = {bad.grounded.unsupported_claim_rate}")
    echo(f"   attribution: retrieval={bad.grounded.retrieval_attributed_failures} "
         f"generation={bad.grounded.generation_attributed_failures}")
    failing = next((r for r in bad.results if not r.passed and r.answerable), None)
    if failing is not None:
        echo(f"   failing query {failing.query_id}: attribution={failing.attribution} "
             f"codes={failing.failure_codes}")
    ok &= bad.retrieval.recall_at_k == 1.0
    ok &= (bad.grounded.answer_pass_rate or 1.0) < 1.0
    ok &= bad.grounded.generation_attributed_failures >= 1
    ok &= bad.grounded.retrieval_attributed_failures == 0
    echo("")

    echo(_RULE)
    echo("4. Corrected: faithful answers again")
    echo(_RULE)
    fixed = evaluate_grounded_qa(
        cases, retriever, get_recorded_generator("grounded_pass"), chunk_text
    )
    echo(f"   grounded answer_pass_rate = {fixed.grounded.answer_pass_rate}")
    ok &= fixed.grounded.answer_pass_rate == 1.0
    echo("")

    echo(_RULE)
    if ok:
        echo("RESULT: retrieval and generation scored separately; the invented-fact regression")
        echo("was attributed to GENERATION (retrieval recall stayed 1.0) and a stale index was")
        echo("refused. No model download and no Qdrant required.")
        echo(_RULE)
        return 0
    echo("RESULT: RAG demo did not hold - unexpected outcomes")
    echo(_RULE)
    return 1


_ = Attribution  # re-exported for callers that inspect attribution
