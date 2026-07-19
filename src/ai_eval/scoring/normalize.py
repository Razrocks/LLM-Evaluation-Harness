"""Versioned, deterministic deadline normalization.

Two jobs: (1) parse an explicit ``YYYY-MM-DD`` value into a ``date`` for exact comparison, and
(2) resolve a relative weekday expression ("by Friday") against the case's own ``received_at``
and ``reference_timezone`` — never the wall clock. Both are pure functions of their inputs, so
tests are reproducible across week / month / year boundaries.

Bump ``NORMALIZER_VERSION`` when the rules change; scorers record it in their evidence.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

NORMALIZER_VERSION = "v1"

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class DateNormalizationError(ValueError):
    """Raised when a value cannot be normalized under the versioned rules."""


def normalize_iso_date(value: str | None) -> date | None:
    """Strictly parse a ``YYYY-MM-DD`` string into a ``date`` (or ``None`` for a null date).

    Rejects any other shape — no locale guessing, no partial dates. ``date.fromisoformat``
    also rejects impossible calendar dates such as ``2026-02-30``.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not _ISO_DATE.match(value.strip()):
        raise DateNormalizationError(f"not a YYYY-MM-DD date: {value!r}")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:  # impossible calendar date
        raise DateNormalizationError(f"invalid calendar date: {value!r}") from exc


def resolve_relative_weekday(
    received_at: datetime,
    reference_timezone: str,
    weekday: str,
    *,
    week_offset: int = 0,
) -> date:
    """Resolve a named weekday to the next on-or-after date, relative to ``received_at``.

    ``week_offset`` shifts by whole weeks ("Friday next week" -> ``week_offset=1``). The
    received timestamp is first converted into ``reference_timezone`` so the local calendar
    day is correct regardless of the stored offset.
    """
    key = weekday.strip().lower()
    if key not in _WEEKDAYS:
        raise DateNormalizationError(f"unknown weekday: {weekday!r}")
    local_date = received_at.astimezone(ZoneInfo(reference_timezone)).date()
    delta = (_WEEKDAYS[key] - local_date.weekday()) % 7
    return local_date + timedelta(days=delta + 7 * week_offset)
