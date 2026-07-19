"""The immutable inputs a scorer sees for one case execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_eval.domain import EvalCase
from ai_eval.evidence import EvidenceIndex
from ai_eval.parsing import ParseOutcome


@dataclass(frozen=True)
class ScoringContext:
    """Everything a scorer may read: the case, the parse outcome, and an evidence index.

    A scorer is a pure function of this context and an assertion — no I/O, no clock, no
    network — so results are reproducible.
    """

    case: EvalCase
    parse: ParseOutcome
    evidence: EvidenceIndex

    @property
    def output(self) -> dict[str, Any] | None:
        """The parsed candidate output, or ``None`` when parsing/validation failed."""
        return self.parse.value if self.parse.ok else None

    @classmethod
    def build(cls, case: EvalCase, parse: ParseOutcome) -> ScoringContext:
        return cls(case=case, parse=parse, evidence=EvidenceIndex(case))
