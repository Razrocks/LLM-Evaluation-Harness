"""Deterministic content hashing.

Content addressing underpins every immutability guarantee in the platform: a case version, a
dataset release, and a run manifest are all identified by a hash of their canonical bytes.
"Canonical" means keys sorted, no insignificant whitespace, UTF-8 — so the same logical
content always produces the same hash regardless of field order or formatting.

Kept dependency-free (stdlib only) so it never pulls domain models into a cycle. Callers pass
already-serialized data (e.g. ``model.model_dump(mode="json")``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

_DEFAULT_EXCLUDE: tuple[str, ...] = ("content_hash",)


def canonical_json(data: Any) -> str:
    """Serialize ``data`` to canonical JSON: sorted keys, compact separators, UTF-8 text."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(
    data: Mapping[str, Any],
    *,
    exclude: Iterable[str] = _DEFAULT_EXCLUDE,
) -> str:
    """Return ``sha256:<hex>`` over ``data``'s canonical JSON, dropping ``exclude`` top-level keys.

    The default exclusion of ``content_hash`` lets an object carry its own hash without the hash
    depending on itself.
    """
    excluded = set(exclude)
    payload = {k: v for k, v in data.items() if k not in excluded}
    return f"sha256:{sha256_hex(canonical_json(payload))}"
