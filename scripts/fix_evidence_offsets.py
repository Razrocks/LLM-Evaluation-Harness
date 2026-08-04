"""Recompute exact char offsets for a case's evidence spans.

Authoring evidence spans by hand is error-prone: ``start``/``end`` must be the precise character
indices of the span text within its source. This tool takes a case file whose ``source_context``
entries carry the correct ``text`` and ``source_id`` (offsets may be placeholders), locates each
span in the named source (the message or a document), and writes back the true offsets.

It refuses to guess: a span whose text is absent, or appears more than once, is reported as an
error and left unchanged, so a mislabelled span never silently gets a plausible-looking offset.

Usage:
  python scripts/fix_evidence_offsets.py datasets/reference/request_triage/v2/cases/request_triage_013.json
  python scripts/fix_evidence_offsets.py datasets/reference/request_triage/v2/cases/*.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _source_text(case: dict, source_id: str) -> str | None:
    if source_id == "message":
        return case["input"].get("message", "")
    for doc in case["input"].get("documents", []):
        if doc.get("document_id") == source_id:
            return doc.get("text", "")
    return None


def fix_case(path: Path) -> list[str]:
    """Rewrite one case's span offsets. Return a list of error strings (empty = clean)."""
    case = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for span in case.get("source_context", []):
        source_id = span.get("source_id")
        text = span.get("text", "")
        source = _source_text(case, source_id)
        if source is None:
            errors.append(f"{span.get('evidence_id')}: no source '{source_id}'")
            continue
        first = source.find(text)
        if first < 0:
            errors.append(f"{span.get('evidence_id')}: text {text!r} not found in {source_id}")
            continue
        if source.find(text, first + 1) >= 0:
            errors.append(
                f"{span.get('evidence_id')}: text {text!r} appears >1x in {source_id} (ambiguous)"
            )
            continue
        span["start"], span["end"] = first, first + len(text)
    if not errors:
        path.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: fix_evidence_offsets.py <case.json> [<case.json> ...]", file=sys.stderr)
        return 2
    any_error = False
    for arg in argv:
        path = Path(arg)
        errs = fix_case(path)
        if errs:
            any_error = True
            print(f"ERR  {path.name}")
            for e in errs:
                print(f"       {e}")
        else:
            print(f"ok   {path.name}")
    return 1 if any_error else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
