"""Corpus ingestion.

Snapshots source files into immutable :class:`DocumentVersion`s and assembles a content-hashed
:class:`Corpus`. Plain text and Markdown are read directly; PDF and DOCX use ``pypdf`` /
``python-docx`` (lazy-imported, part of the ``rag`` extra). Ingestion is deterministic: documents
are sorted by id, and the corpus hash covers the document set, so the same sources always produce
the same corpus version.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_eval.domain import content_hash, sha256_hex

from .metrics import RetrievalCase
from .models import Corpus, DocumentVersion

_TEXT_SUFFIXES = {".txt", ".md"}


def _read_pdf(path: Path) -> str:  # pragma: no cover - exercised only with a real PDF
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf not installed; run: uv sync --extra rag") from exc
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def _read_docx(path: Path) -> str:  # pragma: no cover - exercised only with a real DOCX
    try:
        import docx
    except ImportError as exc:
        raise RuntimeError("python-docx not installed; run: uv sync --extra rag") from exc
    return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)


def read_document_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    raise ValueError(f"unsupported document type: {path.name}")


def ingest_document(path: Path, *, document_version: str = "1") -> DocumentVersion:
    text = read_document_text(path).strip()
    return DocumentVersion(
        document_id=path.stem,
        document_version=document_version,
        text=text,
        content_hash=f"sha256:{sha256_hex(text)}",
    )


def build_corpus_from_dir(
    documents_dir: Path, *, corpus_id: str, corpus_version: str
) -> Corpus:
    docs = [
        ingest_document(p)
        for p in sorted(documents_dir.iterdir())
        if p.is_file() and p.suffix.lower() in _TEXT_SUFFIXES | {".pdf", ".docx"}
    ]
    corpus = Corpus(corpus_id=corpus_id, corpus_version=corpus_version, documents=docs)
    body = corpus.model_dump(mode="json", exclude={"content_hash"})
    return corpus.model_copy(update={"content_hash": content_hash(body)})


def load_corpus(path: Path) -> Corpus:
    return Corpus.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_retrieval_cases(path: Path) -> list[RetrievalCase]:
    cases: list[RetrievalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(RetrievalCase.model_validate(json.loads(line)))
    return cases


def corpus_to_dict(corpus: Corpus) -> dict[str, Any]:
    return corpus.model_dump(mode="json")
