"""Retrieval metrics — deterministic, computed from ranked chunk ids and relevance labels.

Retrieval quality is measured separately from generation quality (principle #4): these functions
take only the ranked result ids and the case's relevant-chunk labels, so a retrieval regression
is attributable to retrieval alone. All are pure functions; the aggregate reports means with
explicit denominators.
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RetrievalCase(BaseModel):
    """Labels for one query."""

    model_config = ConfigDict(extra="forbid")

    query_id: str
    query: str
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    graded_relevance: dict[str, float] = Field(default_factory=dict)
    answerable: bool = True


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float | None:
    if not relevant:
        return None
    top = set(ranked[:k])
    return len(top & relevant) / len(relevant)


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if k == 0:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for c in top if c in relevant)
    return hits / min(k, len(top)) if top else 0.0


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    for i, chunk_id in enumerate(ranked, start=1):
        if chunk_id in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[str], graded: dict[str, float], k: int) -> float | None:
    if not graded:
        return None
    dcg = sum(
        graded.get(chunk_id, 0.0) / math.log2(i + 1)
        for i, chunk_id in enumerate(ranked[:k], start=1)
    )
    ideal = sorted(graded.values(), reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 1) for i, rel in enumerate(ideal, start=1))
    return (dcg / idcg) if idcg > 0 else 0.0


def duplicate_chunk_rate(ranked: list[str]) -> float:
    if not ranked:
        return 0.0
    return 1.0 - (len(set(ranked)) / len(ranked))


class RetrievalMetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    k: int
    total_queries: int
    recall_at_k: float | None
    precision_at_k: float | None
    mrr: float | None
    ndcg_at_k: float | None
    empty_retrieval_rate: float
    duplicate_chunk_rate: float
    per_query: list[dict[str, Any]] = Field(default_factory=list)


def _mean(values: list[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def evaluate_retrieval(
    pairs: list[tuple[RetrievalCase, list[str]]], *, k: int
) -> RetrievalMetricSummary:
    """Score ``(case, ranked_chunk_ids)`` pairs into an aggregate summary + per-query drill-down."""
    recalls: list[float] = []
    precisions: list[float] = []
    rrs: list[float] = []
    ndcgs: list[float] = []
    empties = 0
    dup_rates: list[float] = []
    per_query: list[dict[str, Any]] = []

    for case, ranked in pairs:
        relevant = set(case.relevant_chunk_ids)
        r = recall_at_k(ranked, relevant, k)
        p = precision_at_k(ranked, relevant, k)
        rr = reciprocal_rank(ranked, relevant)
        nd = ndcg_at_k(ranked, case.graded_relevance, k)
        dup = duplicate_chunk_rate(ranked)
        if not ranked:
            empties += 1
        if r is not None:
            recalls.append(r)
        precisions.append(p)
        rrs.append(rr)
        if nd is not None:
            ndcgs.append(nd)
        dup_rates.append(dup)
        per_query.append({
            "query_id": case.query_id, "recall_at_k": r, "precision_at_k": p,
            "reciprocal_rank": rr, "ndcg_at_k": nd, "retrieved": len(ranked),
            "relevant": len(relevant),
        })

    total = len(pairs)
    return RetrievalMetricSummary(
        k=k,
        total_queries=total,
        recall_at_k=_mean(recalls),
        precision_at_k=_mean(precisions),
        mrr=_mean(rrs),
        ndcg_at_k=_mean(ndcgs),
        empty_retrieval_rate=(empties / total) if total else 0.0,
        duplicate_chunk_rate=_mean(dup_rates) or 0.0,
        per_query=per_query,
    )
