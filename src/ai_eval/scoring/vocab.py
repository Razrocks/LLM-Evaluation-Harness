"""Controlled missing-information vocabulary and its versioned alias map.

Scoring uses stable canonical keys, never free-text sentences. The alias map normalizes a
small set of reviewed synonyms onto canonical keys; it is conservative and visible in scorer
evidence. It never turns a genuinely different item into a match — unknown keys stay unknown
and count against precision.
"""

from __future__ import annotations

MISSING_INFO_VOCAB_VERSION = "v1"

CANONICAL_MISSING_INFO_KEYS: frozenset[str] = frozenset(
    {
        "request_identifier",
        "requester_identity",
        "desired_outcome",
        "responsible_owner",
        "approval_status",
        "target_resource",
        "source_document",
        "governing_terms",
        "amount_or_scope_breakdown",
        "deadline_basis",
        "previous_correspondence",
        "risk_acceptance_owner",
    }
)

# Reviewed synonyms -> canonical key. Keys are lower-cased before lookup.
MISSING_INFO_ALIASES: dict[str, str] = {
    "line_item_detail": "amount_or_scope_breakdown",
    "line-item detail": "amount_or_scope_breakdown",
    "cost_breakdown": "amount_or_scope_breakdown",
    "scope_breakdown": "amount_or_scope_breakdown",
    "signed_agreement": "governing_terms",
    "contract_terms": "governing_terms",
    "approver": "risk_acceptance_owner",
    "sign_off_owner": "risk_acceptance_owner",
    "owner": "responsible_owner",
    "request_id": "request_identifier",
    "requester": "requester_identity",
    "attached_document": "source_document",
    "supporting_document": "source_document",
}


def normalize_missing_info_key(raw: str) -> tuple[str, str | None]:
    """Return ``(canonical_key, alias_used)``.

    If ``raw`` is already canonical it is returned unchanged with ``alias_used=None``. If it
    matches a known alias, the canonical key is returned with the alias recorded for evidence.
    Otherwise the lower-cased raw value is returned unchanged (and will not match any expected
    canonical key), with ``alias_used=None``.
    """
    key = raw.strip().lower()
    if key in CANONICAL_MISSING_INFO_KEYS:
        return key, None
    if key in MISSING_INFO_ALIASES:
        return MISSING_INFO_ALIASES[key], key
    return key, None
