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


def resolve_selector(document: Any, selector: str) -> Any:
    """Resolve ``selector`` against ``document``. Returns a value, a list, or :data:`MISSING`."""
    if selector in ("$", "$."):
        return document
    if not selector.startswith("$."):
        raise ValueError(f"selector must start with '$.': {selector!r}")

    current: Any = document
    for token in selector[2:].split("."):
        field, wildcard = (token[:-3], True) if token.endswith("[*]") else (token, False)
        if wildcard:
            if not isinstance(current, dict) or field not in current:
                return MISSING
            seq = current[field]
            if not isinstance(seq, list):
                return MISSING
            # Remaining tokens (if any) are applied to each element by the caller pattern;
            # here we return the list and let a trailing field token pluck from each element.
            current = seq
        elif isinstance(current, list):
            # pluck ``field`` from each element (supports ``items[*].key``)
            plucked = []
            for el in current:
                if isinstance(el, dict) and field in el:
                    plucked.append(el[field])
                else:
                    plucked.append(MISSING)
            current = plucked
        elif isinstance(current, dict):
            if field not in current:
                return MISSING
            current = current[field]
        else:
            return MISSING
    return current
