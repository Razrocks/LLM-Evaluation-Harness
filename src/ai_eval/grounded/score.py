"""Grounding scoring and failure attribution.

Given a case, the ranked retrieval result, the generated answer, and the chunk texts, this
computes generation-side metrics (answer-fact recall, citation validity, unsupported claims,
abstention correctness) and — critically — **attributes a failure to retrieval or generation**:
if the required evidence was never retrieved, that is a retrieval failure; if it was retrieved
and the answer is still wrong, that is a generation failure. The two are never conflated.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import FailureCode

from .models import GroundedAnswer, GroundedQACase


class Attribution(StrEnum):
    OK = "ok"
    RETRIEVAL = "retrieval"
    GENERATION = "generation"


def _norm(text: str) -> str:
    return " ".join(text.split()).lower()


def _contains(haystack: str, needle: str) -> bool:
    n = _norm(needle)
    return bool(n) and n in _norm(haystack)


class GroundedCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    answerable: bool
    required_evidence_retrieved: bool
    answer_fact_recall: float | None
    citation_valid_rate: float | None
    unsupported_claims: list[str] = Field(default_factory=list)
    abstention_correct: bool
    passed: bool
    attribution: Attribution
    failure_codes: list[str] = Field(default_factory=list)


def score_grounded(
    case: GroundedQACase,
    ranked_chunk_ids: list[str],
    answer: GroundedAnswer,
    chunk_text: dict[str, str],
) -> GroundedCaseResult:
    retrieved = set(ranked_chunk_ids)
    required = set(case.required_evidence_chunk_ids) or set(case.relevant_chunk_ids)
    required_retrieved = required.issubset(retrieved) if required else True
    context_text = " ".join(chunk_text.get(cid, "") for cid in ranked_chunk_ids)

    codes: list[FailureCode] = []
    unsupported: list[str] = []

    # --- abstention -----------------------------------------------------------------------
    if not case.answerable:
        abstained = answer.answerable is False
        passed = abstained
        if not abstained:
            codes.append(FailureCode.UNSUPPORTED_MATERIAL_CLAIM)  # answered without evidence
            unsupported.append("answered an unanswerable question")
        return GroundedCaseResult(
            query_id=case.query_id, answerable=False,
            required_evidence_retrieved=required_retrieved,
            answer_fact_recall=None, citation_valid_rate=None, unsupported_claims=unsupported,
            abstention_correct=abstained, passed=passed,
            attribution=Attribution.OK if passed else Attribution.GENERATION,
            failure_codes=[str(c) for c in codes],
        )

    # --- answerable case ------------------------------------------------------------------
    facts = case.expected_answer_facts
    fact_hits = sum(1 for f in facts if _contains(answer.answer, f)) if facts else 0
    fact_recall = (fact_hits / len(facts)) if facts else 1.0

    for prohibited in case.prohibited_facts:
        if _contains(answer.answer, prohibited):
            unsupported.append(prohibited)
    # A stated fact not supported anywhere in the retrieved context is unsupported.
    for fact in facts:
        if _contains(answer.answer, fact) and not _contains(context_text, fact):
            unsupported.append(fact)

    citations = answer.citations
    valid_citations = sum(1 for c in citations if c.chunk_id in retrieved)
    citation_valid_rate = (valid_citations / len(citations)) if citations else 0.0
    has_valid_citation = valid_citations > 0

    abstention_correct = answer.answerable is True and answer.answer.strip() != ""

    generation_ok = (
        fact_recall >= 1.0 and not unsupported and has_valid_citation and abstention_correct
    )
    passed = required_retrieved and generation_ok

    attribution = Attribution.OK
    if not passed:
        if not required_retrieved:
            attribution = Attribution.RETRIEVAL
            codes.append(FailureCode.RELEVANT_CHUNK_NOT_RETRIEVED)
        else:
            attribution = Attribution.GENERATION
            if unsupported:
                codes.append(FailureCode.UNSUPPORTED_MATERIAL_CLAIM)
            if not has_valid_citation:
                codes.append(FailureCode.INVALID_EVIDENCE_REFERENCE)
            if fact_recall < 1.0:
                codes.append(FailureCode.EVIDENCE_COVERAGE_LOW)

    return GroundedCaseResult(
        query_id=case.query_id, answerable=True, required_evidence_retrieved=required_retrieved,
        answer_fact_recall=fact_recall, citation_valid_rate=citation_valid_rate,
        unsupported_claims=unsupported, abstention_correct=abstention_correct, passed=passed,
        attribution=attribution, failure_codes=[str(c) for c in codes],
    )


class GroundedMetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_queries: int
    answer_pass_rate: float | None
    answer_fact_recall: float | None
    citation_validity: float | None
    unsupported_claim_rate: float
    correct_abstention_rate: float | None
    retrieval_attributed_failures: int
    generation_attributed_failures: int
    per_query: list[dict[str, Any]] = Field(default_factory=list)


def _mean(values: list[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def evaluate_grounded(results: list[GroundedCaseResult]) -> GroundedMetricSummary:
    total = len(results)
    fact_recalls = [r.answer_fact_recall for r in results if r.answer_fact_recall is not None]
    citation_rates = [r.citation_valid_rate for r in results if r.citation_valid_rate is not None]
    unanswerable = [r for r in results if not r.answerable]
    return GroundedMetricSummary(
        total_queries=total,
        answer_pass_rate=_mean([1.0 if r.passed else 0.0 for r in results]),
        answer_fact_recall=_mean(fact_recalls),
        citation_validity=_mean(citation_rates),
        unsupported_claim_rate=(
            sum(1 for r in results if r.unsupported_claims) / total if total else 0.0
        ),
        correct_abstention_rate=(
            _mean([1.0 if r.abstention_correct else 0.0 for r in unanswerable])
            if unanswerable else None
        ),
        retrieval_attributed_failures=sum(
            1 for r in results if r.attribution == Attribution.RETRIEVAL
        ),
        generation_attributed_failures=sum(
            1 for r in results if r.attribution == Attribution.GENERATION
        ),
        per_query=[r.model_dump(mode="json") for r in results],
    )
