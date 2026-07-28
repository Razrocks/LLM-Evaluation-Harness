"""Grounded-QA evaluation pipeline: retrieve -> generate -> score, retrieval and generation
reported separately."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_eval.retrieval import Chunk, Retriever
from ai_eval.retrieval.metrics import (
    RetrievalCase,
    RetrievalMetricSummary,
    evaluate_retrieval,
)

from .generate import ContextChunk, RecordedGenerator
from .models import GroundedQACase
from .score import GroundedCaseResult, GroundedMetricSummary, evaluate_grounded, score_grounded


@dataclass
class GroundedEvaluation:
    retrieval: RetrievalMetricSummary
    grounded: GroundedMetricSummary
    results: list[GroundedCaseResult]


def chunk_text_index(chunks: list[Chunk]) -> dict[str, str]:
    return {c.chunk_id: c.text for c in chunks}


def load_grounded_cases(path: Path) -> list[GroundedQACase]:
    return [
        GroundedQACase.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def evaluate_grounded_qa(
    cases: list[GroundedQACase],
    retriever: Retriever,
    generator: RecordedGenerator,
    chunk_text: dict[str, str],
    *,
    k: int = 3,
) -> GroundedEvaluation:
    retrieval_pairs: list[tuple[RetrievalCase, list[str]]] = []
    results: list[GroundedCaseResult] = []

    for case in cases:
        run = retriever.retrieve(case.query)
        ranked = [r.chunk_id for r in run.results]
        context = [
            ContextChunk(
                chunk_id=r.chunk_id,
                document_id=r.document_version_id.split(":", 1)[0],
                text=chunk_text.get(r.chunk_id, ""),
            )
            for r in run.results
        ]
        answer = generator(case, context)
        results.append(score_grounded(case, ranked, answer, chunk_text))
        retrieval_pairs.append(
            (
                RetrievalCase(
                    query_id=case.query_id, query=case.query,
                    relevant_chunk_ids=case.relevant_chunk_ids,
                    graded_relevance=case.graded_relevance, answerable=case.answerable,
                ),
                ranked,
            )
        )

    return GroundedEvaluation(
        retrieval=evaluate_retrieval(retrieval_pairs, k=k),
        grounded=evaluate_grounded(results),
        results=results,
    )
