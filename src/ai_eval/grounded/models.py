"""Models for grounded question answering (`reference.grounded_qa.v1`).

Retrieval quality and generation quality are scored separately, so a wrong answer can be
attributed to the stage that caused it. A grounded-QA case therefore carries *both* retrieval
labels (which chunks are relevant / must be cited) and generation labels (which facts the answer
must contain, which it must not, and whether the question is answerable at all).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(_Base):
    document_id: str
    chunk_id: str
    quote_span: tuple[int, int] | None = None


class GroundedAnswer(_Base):
    """The parsed candidate output — mirrors ``grounded_answer.v1``."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    answerable: bool = True
    confidence: float | None = None


class GroundedQACase(_Base):
    """One grounded-QA scenario: retrieval labels + generation labels."""

    query_id: str
    query: str
    # retrieval labels
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    graded_relevance: dict[str, float] = Field(default_factory=dict)
    # generation labels
    required_evidence_chunk_ids: list[str] = Field(default_factory=list)
    expected_answer_facts: list[str] = Field(default_factory=list)
    prohibited_facts: list[str] = Field(default_factory=list)
    answerable: bool = True
