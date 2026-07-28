"""Grounded question answering (`reference.grounded_qa.v1`): retrieval + generation, scored
separately, with retrieval-vs-generation failure attribution."""

from __future__ import annotations

from .generate import (
    RECORDED_GENERATORS,
    ContextChunk,
    get_recorded_generator,
    grounded_bad_citation,
    grounded_invented_fact,
    grounded_no_abstain,
    grounded_pass,
)
from .models import Citation, GroundedAnswer, GroundedQACase
from .pipeline import (
    GroundedEvaluation,
    chunk_text_index,
    evaluate_grounded_qa,
    load_grounded_cases,
)
from .score import (
    Attribution,
    GroundedCaseResult,
    GroundedMetricSummary,
    evaluate_grounded,
    score_grounded,
)

__all__ = [
    "RECORDED_GENERATORS",
    "Attribution",
    "Citation",
    "ContextChunk",
    "GroundedAnswer",
    "GroundedCaseResult",
    "GroundedEvaluation",
    "GroundedMetricSummary",
    "GroundedQACase",
    "chunk_text_index",
    "evaluate_grounded",
    "evaluate_grounded_qa",
    "get_recorded_generator",
    "grounded_bad_citation",
    "grounded_invented_fact",
    "grounded_no_abstain",
    "grounded_pass",
    "load_grounded_cases",
    "score_grounded",
]
