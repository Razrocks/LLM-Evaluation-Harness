"""Deadline normalizer: strict ISO parsing + relative-weekday resolution across boundaries.

All dates are computed relative to an explicit ``received_at`` — never the wall clock. The
anchor Monday 2026-07-13 is used throughout (the canonical case's received date).
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from ai_eval.scoring import DateNormalizationError, normalize_iso_date, resolve_relative_weekday

TZ = "America/Toronto"


def _at(day: int, month: int = 7, year: int = 2026) -> datetime:
    return datetime(year, month, day, 10, 0, tzinfo=ZoneInfo(TZ))


def test_normalize_iso_date_valid() -> None:
    assert normalize_iso_date("2026-07-17") == date(2026, 7, 17)


def test_normalize_iso_date_null() -> None:
    assert normalize_iso_date(None) is None


@pytest.mark.parametrize("bad", ["2026-13-40", "17/07/2026", "July 17", "2026-7-7", "soon"])
def test_normalize_iso_date_rejects_non_iso(bad: str) -> None:
    with pytest.raises(DateNormalizationError):
        normalize_iso_date(bad)


def test_friday_relative_to_monday() -> None:
    # Mon 2026-07-13 -> "Friday" = 2026-07-17
    assert resolve_relative_weekday(_at(13), TZ, "Friday") == date(2026, 7, 17)


def test_same_week_midweek() -> None:
    assert resolve_relative_weekday(_at(13), TZ, "Wednesday") == date(2026, 7, 15)


def test_week_offset_next_week() -> None:
    assert resolve_relative_weekday(_at(13), TZ, "Friday", week_offset=1) == date(2026, 7, 24)


def test_month_boundary() -> None:
    # Thu 2026-07-30 -> next "Monday" = 2026-08-03
    assert resolve_relative_weekday(_at(30), TZ, "Monday") == date(2026, 8, 3)


def test_year_boundary() -> None:
    # Mon 2026-12-28 -> "Friday" = 2027-01-01
    assert resolve_relative_weekday(_at(28, month=12), TZ, "Friday") == date(2027, 1, 1)


def test_unknown_weekday_raises() -> None:
    with pytest.raises(DateNormalizationError):
        resolve_relative_weekday(_at(13), TZ, "Someday")
