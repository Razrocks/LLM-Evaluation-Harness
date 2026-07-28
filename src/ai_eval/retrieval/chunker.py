"""Deterministic chunking.

Same document version + same params -> byte-identical chunk manifest, every time. Chunk IDs
are stable and resolvable (``<document_id>:<document_version>:chunk-<n>``) and each chunk records
its character span and a content hash, so a chunk can always be traced back to immutable source
text. Chunking is word-based with a fixed window and overlap; no randomness, no wall clock.

Bump ``CHUNKER_VERSION`` when the algorithm changes — it is pinned in the retrieval config.
"""

from __future__ import annotations

from ai_eval.domain import content_hash, sha256_hex

from .models import Chunk, ChunkManifest, Corpus, DocumentVersion

CHUNKER_VERSION = "v1"


def _chunk_document(
    doc: DocumentVersion, corpus_id: str, corpus_version: str, *, window: int, overlap: int
) -> list[Chunk]:
    words = doc.text.split()
    if not words:
        return []
    step = max(window - overlap, 1)
    chunks: list[Chunk] = []
    for index, start_word in enumerate(range(0, len(words), step)):
        window_words = words[start_word : start_word + window]
        if not window_words:
            break
        text = " ".join(window_words)
        # Character span of this chunk within the original text (first/last word positions).
        first = _word_char_offset(doc.text, words, start_word)
        last_word_idx = min(start_word + len(window_words), len(words)) - 1
        end = _word_char_offset(doc.text, words, last_word_idx) + len(words[last_word_idx])
        chunk_id = f"{doc.document_id}:{doc.document_version}:chunk-{index}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                corpus_id=corpus_id,
                corpus_version=corpus_version,
                document_id=doc.document_id,
                document_version=doc.document_version,
                index=index,
                start=first,
                end=end,
                text=text,
                chunk_hash=f"sha256:{sha256_hex(text)}",
            )
        )
        if start_word + window >= len(words):
            break
    return chunks


def _word_char_offset(text: str, words: list[str], word_index: int) -> int:
    """Character offset of the Nth whitespace-split word (deterministic left-to-right scan)."""
    offset = 0
    count = 0
    for token in text.split(" "):
        if token == "":
            offset += 1
            continue
        if count == word_index:
            return offset
        offset += len(token) + 1
        count += 1
    return offset


def chunk_corpus(corpus: Corpus, *, window: int = 40, overlap: int = 10) -> ChunkManifest:
    """Produce a deterministic chunk manifest for every document version in the corpus."""
    all_chunks: list[Chunk] = []
    for doc in sorted(corpus.documents, key=lambda d: (d.document_id, d.document_version)):
        all_chunks.extend(
            _chunk_document(doc, corpus.corpus_id, corpus.corpus_version,
                            window=window, overlap=overlap)
        )
    manifest = ChunkManifest(
        corpus_id=corpus.corpus_id,
        corpus_version=corpus.corpus_version,
        chunker_version=CHUNKER_VERSION,
        params={"window": window, "overlap": overlap},
        chunks=all_chunks,
    )
    body = manifest.model_dump(mode="json", exclude={"content_hash"})
    return manifest.model_copy(update={"content_hash": content_hash(body)})
