"""Grounded-QA evaluation: faithful answers pass; invented facts / bad citations / failure to
abstain are caught and **attributed to generation**; missing evidence is attributed to retrieval.
All offline (hashing embedder + in-memory index + recorded generators)."""

from __future__ import annotations

from pathlib import Path

from ai_eval.grounded import (
    Attribution,
    GroundedAnswer,
    GroundedQACase,
    chunk_text_index,
    evaluate_grounded_qa,
    get_recorded_generator,
    load_grounded_cases,
    score_grounded,
)
from ai_eval.retrieval import (
    HashingEmbedder,
    InMemoryVectorIndex,
    RetrievalConfig,
    Retriever,
    build_corpus_from_dir,
    build_index,
    chunk_corpus,
)

REPO = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO / "corpora/reference/business_docs/v1/documents"
CASES = REPO / "datasets/reference/grounded_qa/v1/grounded_qa_cases.jsonl"


def _setup():
    corpus = build_corpus_from_dir(CORPUS_DIR, corpus_id="business_docs", corpus_version="1")
    chunks = chunk_corpus(corpus).chunks
    embedder = HashingEmbedder()
    config = RetrievalConfig(
        retrieval_config_id="gqa_cfg", corpus_id="business_docs", corpus_version="1",
        chunker_version="v1", embedding=embedder.config, collection="gqa", top_k=3,
    )
    index = InMemoryVectorIndex(config.collection)
    build_index(chunks, embedder, index, config)
    return Retriever(embedder, index, config), chunk_text_index(chunks)


def test_faithful_answers_pass_including_abstention() -> None:
    retriever, chunk_text = _setup()
    cases = load_grounded_cases(CASES)
    ev = evaluate_grounded_qa(cases, retriever, get_recorded_generator("grounded_pass"), chunk_text)
    assert ev.retrieval.recall_at_k == 1.0
    assert ev.grounded.answer_pass_rate == 1.0            # includes correct abstention on gqa_004
    assert ev.grounded.unsupported_claim_rate == 0.0
    assert ev.grounded.correct_abstention_rate == 1.0
    assert ev.grounded.generation_attributed_failures == 0


def test_invented_fact_is_generation_failure() -> None:
    retriever, chunk_text = _setup()
    cases = load_grounded_cases(CASES)
    ev = evaluate_grounded_qa(
        cases, retriever, get_recorded_generator("grounded_invented_fact"), chunk_text
    )
    assert ev.retrieval.recall_at_k == 1.0                # retrieval is fine...
    assert ev.grounded.answer_pass_rate is not None and ev.grounded.answer_pass_rate < 1.0
    assert ev.grounded.unsupported_claim_rate > 0.0       # ...generation invented a fact
    assert ev.grounded.generation_attributed_failures >= 1
    assert ev.grounded.retrieval_attributed_failures == 0
    codes = {c for r in ev.results for c in r.failure_codes}
    assert "UNSUPPORTED_MATERIAL_CLAIM" in codes


def test_bad_citation_is_generation_failure() -> None:
    retriever, chunk_text = _setup()
    cases = load_grounded_cases(CASES)
    ev = evaluate_grounded_qa(
        cases, retriever, get_recorded_generator("grounded_bad_citation"), chunk_text
    )
    codes = {c for r in ev.results for c in r.failure_codes}
    assert "INVALID_EVIDENCE_REFERENCE" in codes
    assert ev.grounded.generation_attributed_failures >= 1


def test_failure_to_abstain_is_caught() -> None:
    retriever, chunk_text = _setup()
    cases = load_grounded_cases(CASES)
    ev = evaluate_grounded_qa(
        cases, retriever, get_recorded_generator("grounded_no_abstain"), chunk_text
    )
    unanswerable = next(r for r in ev.results if not r.answerable)
    assert not unanswerable.passed
    assert not unanswerable.abstention_correct


# --- direct attribution unit tests --------------------------------------------------------


def _case(**kw) -> GroundedQACase:
    base = {"query_id": "q", "query": "?", "relevant_chunk_ids": ["d:1:chunk-0"],
            "required_evidence_chunk_ids": ["d:1:chunk-0"],
            "expected_answer_facts": ["the fact"], "answerable": True}
    base.update(kw)
    return GroundedQACase.model_validate(base)


def test_missing_evidence_attributed_to_retrieval() -> None:
    case = _case()
    answer = GroundedAnswer(answer="the fact", citations=[], answerable=True)
    # required chunk was NOT retrieved
    result = score_grounded(case, ["other:1:chunk-0"], answer, {"other:1:chunk-0": "unrelated"})
    assert result.attribution is Attribution.RETRIEVAL
    assert "RELEVANT_CHUNK_NOT_RETRIEVED" in result.failure_codes


def test_evidence_retrieved_but_wrong_answer_attributed_to_generation() -> None:
    case = _case(prohibited_facts=["a lie"])
    answer = GroundedAnswer(
        answer="the fact and a lie",
        citations=[{"document_id": "d", "chunk_id": "d:1:chunk-0"}],  # type: ignore[list-item]
        answerable=True,
    )
    result = score_grounded(case, ["d:1:chunk-0"], answer, {"d:1:chunk-0": "the fact"})
    assert result.attribution is Attribution.GENERATION
    assert "UNSUPPORTED_MATERIAL_CLAIM" in result.failure_codes
