"""Evidence resolution — turn an ``evidence_ref`` string into a real source span.

An evidence reference looks like ``"<source_id>#<marker>"`` (e.g. ``message#span-1`` or
``quote_001#span-1``). A reference is *valid* when it resolves to a known evidence unit in the
case's ``source_context`` or, failing that, names a real source (the message or a document id).
Span bounds are validated against the underlying text so an out-of-range span is caught.
"""

from __future__ import annotations

from ai_eval.domain import EvalCase, EvidenceUnit


class EvidenceIndex:
    """A lookup over one case's source context and input documents."""

    def __init__(self, case: EvalCase) -> None:
        self._by_evidence_id: dict[str, EvidenceUnit] = {
            e.evidence_id: e for e in case.source_context
        }
        self._source_text: dict[str, str] = {}
        message = case.input.get("message")
        if isinstance(message, str):
            self._source_text["message"] = message
        for doc in case.input.get("documents", []) or []:
            if isinstance(doc, dict) and "document_id" in doc:
                self._source_text[str(doc["document_id"])] = str(doc.get("text", ""))

    @property
    def known_sources(self) -> set[str]:
        return set(self._source_text)

    def resolve(self, ref: str) -> EvidenceUnit | None:
        """Return the evidence unit for ``ref`` if it is a known evidence id."""
        return self._by_evidence_id.get(ref)

    def source_of(self, ref: str) -> str:
        """The source id portion of a reference (``message#span-1`` -> ``message``)."""
        return ref.split("#", 1)[0]

    def is_valid_ref(self, ref: str) -> bool:
        """Valid if the exact evidence id is known, or the reference names a real source."""
        if ref in self._by_evidence_id:
            return True
        return self.source_of(ref) in self._source_text

    def span_in_bounds(self, unit: EvidenceUnit) -> bool:
        """True if the unit's span lies within its source text (or has no span)."""
        if unit.start is None or unit.end is None:
            return True
        text = self._source_text.get(unit.source_id)
        if text is None:
            return False
        return 0 <= unit.start <= unit.end <= len(text)

    def supports_value(self, ref: str, value: str) -> bool:
        """Deterministic support check: the referenced source text contains ``value``.

        Case- and whitespace-insensitive containment. Conservative by design — it can confirm
        support but never fabricates it; unresolved references are unsupported.
        """
        needle = " ".join(value.split()).lower()
        if not needle:
            return False
        unit = self._by_evidence_id.get(ref)
        source_id = unit.source_id if unit is not None else self.source_of(ref)
        text = self._source_text.get(source_id)
        if text is None:
            return False
        return needle in " ".join(text.split()).lower()
