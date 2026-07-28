"""The RAG demo is self-verifying: it returns 0 only if retrieval and generation are scored
separately and the invented-fact regression is attributed to generation."""

from __future__ import annotations

from pathlib import Path

from ai_eval.rag_demo import run_rag_demo

REPO = Path(__file__).resolve().parents[2]


def test_rag_demo_holds() -> None:
    lines: list[str] = []
    code = run_rag_demo(repo_root=REPO, echo=lines.append)
    output = "\n".join(lines)
    assert code == 0, output
    assert "retrieval UNCHANGED" in output
    assert "refused stale index" in output
    assert "generation=" in output
