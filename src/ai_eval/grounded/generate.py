"""Answer generation from retrieved context.

An :class:`AnswerGenerator` turns a query plus the retrieved context into a
:class:`GroundedAnswer`. The recorded generators are deterministic test doubles (they may read
the case's labels, exactly like the recorded triage targets) used to prove the grounding scorers
offline. The provider generator uses a real model behind the M5 adapter and is not run offline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .models import Citation, GroundedAnswer, GroundedQACase


@dataclass(frozen=True)
class ContextChunk:
    chunk_id: str
    document_id: str
    text: str


#: A recorded generator sees the case (it is a test double); a real generator would not.
RecordedGenerator = Callable[[GroundedQACase, list[ContextChunk]], GroundedAnswer]


def _cite(chunk_ids: set[str], context: list[ContextChunk]) -> list[Citation]:
    return [
        Citation(document_id=c.document_id, chunk_id=c.chunk_id)
        for c in context
        if c.chunk_id in chunk_ids
    ]


def grounded_pass(case: GroundedQACase, context: list[ContextChunk]) -> GroundedAnswer:
    """A faithful answer: states the expected facts, cites required evidence, abstains correctly."""
    if not case.answerable:
        return GroundedAnswer(answer="", citations=[], answerable=False, confidence=0.2)
    answer = " ".join(case.expected_answer_facts) or "See cited policy."
    cited = set(case.required_evidence_chunk_ids) or set(case.relevant_chunk_ids)
    return GroundedAnswer(
        answer=answer, citations=_cite(cited, context), answerable=True, confidence=0.9
    )


def grounded_invented_fact(case: GroundedQACase, context: list[ContextChunk]) -> GroundedAnswer:
    """Valid-looking answer that injects a prohibited (unsupported) fact."""
    base = grounded_pass(case, context)
    injected = case.prohibited_facts[0] if case.prohibited_facts else "an unsupported claim"
    return base.model_copy(update={"answer": f"{base.answer} {injected}".strip()})


def grounded_bad_citation(case: GroundedQACase, context: list[ContextChunk]) -> GroundedAnswer:
    """Correct facts, but cites a chunk that was not retrieved."""
    base = grounded_pass(case, context)
    bogus = Citation(document_id="ghost_doc", chunk_id="ghost_doc:1:chunk-0")
    return base.model_copy(update={"citations": [bogus]})


def grounded_no_abstain(case: GroundedQACase, context: list[ContextChunk]) -> GroundedAnswer:
    """Answers even an unanswerable question instead of abstaining."""
    return GroundedAnswer(
        answer="Yes, that is allowed.", citations=[], answerable=True, confidence=0.8
    )


RECORDED_GENERATORS: dict[str, RecordedGenerator] = {
    "grounded_pass": grounded_pass,
    "grounded_invented_fact": grounded_invented_fact,
    "grounded_bad_citation": grounded_bad_citation,
    "grounded_no_abstain": grounded_no_abstain,
}


def get_recorded_generator(name: str) -> RecordedGenerator:
    if name not in RECORDED_GENERATORS:
        raise KeyError(f"unknown grounded generator '{name}'; known: {sorted(RECORDED_GENERATORS)}")
    return RECORDED_GENERATORS[name]
