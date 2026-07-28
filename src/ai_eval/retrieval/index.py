"""Vector indexes behind one interface.

- :class:`InMemoryVectorIndex` — exact cosine search, no service. The offline default for tests
  and the recorded RAG path.
- :class:`QdrantVectorIndex` — the real store (lazy ``qdrant-client``), used for the live
  integration test and demo against ``docker compose up -d qdrant``.

Both require every point payload to carry the canonical references (`chunk_id`,
`document_version_id`, `corpus_version_id`, `chunk_hash`, `embedding_config_id`). A retrieved
result missing them, or carrying the wrong `corpus_version_id`, is how the harness detects a
wrong or stale index rather than scoring against it.
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

REQUIRED_PAYLOAD_KEYS = frozenset(
    {"chunk_id", "document_version_id", "corpus_version_id", "chunk_hash", "embedding_config_id"}
)

_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-00000000a1e0")


class IndexPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    vector: list[float]
    payload: dict[str, Any]

    def validated_payload(self) -> dict[str, Any]:
        missing = REQUIRED_PAYLOAD_KEYS - set(self.payload)
        if missing:
            raise ValueError(f"point '{self.chunk_id}' payload missing {sorted(missing)}")
        return self.payload


class ScoredPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    score: float
    payload: dict[str, Any]


class VectorIndex(Protocol):
    collection: str

    def upsert(self, points: list[IndexPoint]) -> None: ...

    def query(self, vector: list[float], *, top_k: int) -> list[ScoredPoint]: ...

    def count(self) -> int: ...


def _cosine(a: list[float], b: list[float]) -> float:
    # Vectors are pre-normalized by the embedder, so dot product is cosine similarity.
    return sum(x * y for x, y in zip(a, b, strict=False))


class InMemoryVectorIndex:
    """Exact cosine index. Deterministic ties broken by chunk_id for reproducible ranking."""

    def __init__(self, collection: str) -> None:
        self.collection = collection
        self._points: list[IndexPoint] = []

    def upsert(self, points: list[IndexPoint]) -> None:
        for point in points:
            point.validated_payload()
        by_id = {p.chunk_id: p for p in self._points}
        for point in points:
            by_id[point.chunk_id] = point
        self._points = list(by_id.values())

    def query(self, vector: list[float], *, top_k: int) -> list[ScoredPoint]:
        scored = [
            ScoredPoint(chunk_id=p.chunk_id, score=_cosine(vector, p.vector), payload=p.payload)
            for p in self._points
        ]
        scored.sort(key=lambda s: (-s.score, s.chunk_id))
        return scored[:top_k]

    def count(self) -> int:
        return len(self._points)


class QdrantVectorIndex:
    """Qdrant-backed index (lazy client). Live path only."""

    def __init__(
        self,
        collection: str,
        *,
        dimension: int,
        distance: str = "cosine",
        url: str = "http://localhost:6333",
        client: Any | None = None,
    ) -> None:
        self.collection = collection
        self._dimension = dimension
        self._distance = distance
        self._url = url
        self._client = client

    def _ensure(self) -> Any:
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError as exc:  # pragma: no cover - only without the rag extra
                raise RuntimeError("qdrant-client not installed; run: uv sync --extra rag") from exc
            self._client = QdrantClient(url=self._url)
        return self._client

    def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        client = self._ensure()
        distance = {"cosine": Distance.COSINE, "dot": Distance.DOT, "euclid": Distance.EUCLID}[
            self._distance
        ]
        if not client.collection_exists(self.collection):
            client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self._dimension, distance=distance),
            )

    def upsert(self, points: list[IndexPoint]) -> None:
        from qdrant_client.models import PointStruct

        client = self._ensure()
        self.ensure_collection()
        structs = [
            PointStruct(
                id=str(uuid.uuid5(_NAMESPACE, p.chunk_id)),
                vector=p.vector,
                payload=p.validated_payload(),
            )
            for p in points
        ]
        client.upsert(collection_name=self.collection, points=structs)

    def query(self, vector: list[float], *, top_k: int) -> list[ScoredPoint]:
        client = self._ensure()
        hits = client.query_points(
            collection_name=self.collection, query=vector, limit=top_k, with_payload=True
        ).points
        return [
            ScoredPoint(
                chunk_id=str((h.payload or {}).get("chunk_id", h.id)),
                score=float(h.score),
                payload=dict(h.payload or {}),
            )
            for h in hits
        ]

    def count(self) -> int:
        client = self._ensure()
        return int(client.count(collection_name=self.collection).count)
