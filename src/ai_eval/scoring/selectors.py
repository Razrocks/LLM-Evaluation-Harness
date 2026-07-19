"""A tiny, deterministic selector resolver for the handful of paths the scorers use.

Not a general JSONPath engine — deliberately small and predictable. Supported forms:

- ``$``                         -> the whole document
- ``$.a.b``                     -> nested object access
- ``$.items[*]``               -> the list at ``items`` (each element)
- ``$.items[*].key``           -> the ``key`` field of each element in ``items``

A missing intermediate key yields :data:`MISSING` (distinct from a present ``None``), so a
scorer can tell "field absent" from "field present and null".
"""

from __future__ import annotations

from typing import Any

MISSING = object()


def _pluck(seq: list[Any], field: str) -> list[Any]:
    """Pluck ``field`` from each element of ``seq`` (supports ``items[*].key``)."""
    return [el[field] if isinstance(el, dict) and field in el else MISSING for el in seq]


def resolve_selector(document: Any, selector: str) -> Any:
    """Resolve ``selector`` against ``document``. Returns a value, a list, or :data:`MISSING`."""
    if selector in ("$", "$."):
        return document
    if not selector.startswith("$."):
        raise ValueError(f"selector must start with '$.': {selector!r}")

    current: Any = document
    for token in selector[2:].split("."):
        wildcard = token.endswith("[*]")
        field = token[:-3] if wildcard else token
        if wildcard:
            if not isinstance(current, dict) or not isinstance(current.get(field), list):
                return MISSING
            current = current[field]
        elif isinstance(current, list):
            current = _pluck(current, field)
        elif isinstance(current, dict) and field in current:
            current = current[field]
        else:
            return MISSING
    return current
