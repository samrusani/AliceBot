from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alicebot_api.vnext_temporal_query import (
    WINDOW_CEILING,
    WINDOW_FLOOR,
    TemporalAnchor,
    parse_event_datetime,
    parse_temporal_anchor,
)


# Fixed reference so every case is deterministic: Tuesday 2023-04-18.
REF = datetime(2023, 4, 18, 3, 31, tzinfo=UTC)


def _utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


# (query, expected window_start, expected window_end, expected parsed_from)
EXPLICIT_CASES = [
    # Numeric year-first dates -> one-day windows.
    ("what happened on 2023/05/30?", _utc(2023, 5, 30), _utc(2023, 5, 31), "2023/05/30"),
    ("notes from the 2022-12-19 standup", _utc(2022, 12, 19), _utc(2022, 12, 20), "2022-12-19"),
    # Month-name dates with a year.
    ("dinner on May 3, 2023 with Sam", _utc(2023, 5, 3), _utc(2023, 5, 4), "May 3, 2023"),
    ("dinner on May 3rd 2023 with Sam", _utc(2023, 5, 3), _utc(2023, 5, 4), "May 3rd 2023"),
    ("dinner on 3 May 2023 with Sam", _utc(2023, 5, 3), _utc(2023, 5, 4), "3 May 2023"),
    # Month-day without a year: most recent occurrence at or before REF
    # (May 3, 2023 is after the April reference, so it resolves to 2022).
    ("what did we plan on May 3?", _utc(2022, 5, 3), _utc(2022, 5, 4), "May 3"),
    ("what did we plan on March 3?", _utc(2023, 3, 3), _utc(2023, 3, 4), "March 3"),
    # Month + year -> that calendar month.
    ("what did I decide in March 2023?", _utc(2023, 3, 1), _utc(2023, 4, 1), "March 2023"),
    ("the March of 2023 numbers", _utc(2023, 3, 1), _utc(2023, 4, 1), "March of 2023"),
    # Preposition-anchored month without a year: most recent occurrence.
    ("doctor's appointments in March", _utc(2023, 3, 1), _utc(2023, 4, 1), "March"),
    ("museums I visited in December", _utc(2022, 12, 1), _utc(2023, 1, 1), "December"),
    ("workshops during April", _utc(2023, 4, 1), _utc(2023, 5, 1), "April"),
    # early/mid/late widen to the whole month.
    ("the trip in early May 2023", _utc(2023, 5, 1), _utc(2023, 6, 1), "early May 2023"),
    ("the trip in late May", _utc(2022, 5, 1), _utc(2022, 6, 1), "late May"),
    # Month pair spans both months, wrapping the year when needed.
    ("airlines I flew in March and April", _utc(2023, 3, 1), _utc(2023, 5, 1), "March and April"),
    ("novels I finished in January and March", _utc(2023, 1, 1), _utc(2023, 4, 1), "January and March"),
    ("events in December and January", _utc(2022, 12, 1), _utc(2023, 2, 1), "December and January"),
    # Preposition-anchored bare year.
    ("conferences I attended in 2022", _utc(2022, 1, 1), _utc(2023, 1, 1), "2022"),
]

RANGE_CASES = [
    (
        "trips between March 2023 and May 2023",
        _utc(2023, 3, 1),
        _utc(2023, 6, 1),
        "between March 2023 and May 2023",
    ),
    # Yearless first month borrows the second point's year.
    ("trips between March and May 2023", _utc(2023, 3, 1), _utc(2023, 6, 1), "between March and May 2023"),
    # ...wrapping back one year when the range would run backwards.
    ("between November and May 2023", _utc(2022, 11, 1), _utc(2023, 6, 1), "between November and May 2023"),
    ("from 2023-01-05 to 2023-01-10", _utc(2023, 1, 5), _utc(2023, 1, 11), "from 2023-01-05 to 2023-01-10"),
    ("logs from March 2023 through May 2023", _utc(2023, 3, 1), _utc(2023, 6, 1), "from March 2023 through May 2023"),
    # Open ranges.
    ("everything before March 2023", WINDOW_FLOOR, _utc(2023, 3, 1), "before March 2023"),
    ("decisions since March 2023", _utc(2023, 3, 1), WINDOW_CEILING, "since March 2023"),
    ("changes after May 3, 2023", _utc(2023, 5, 4), WINDOW_CEILING, "after May 3, 2023"),
    # "by X" is a deadline: through the end of X itself.
    ("tasks due by March 2023", WINDOW_FLOOR, _utc(2023, 4, 1), "by March 2023"),
    ("history until March 2023", WINDOW_FLOOR, _utc(2023, 3, 1), "until March 2023"),
]

RELATIVE_CASES = [
    ("what did I eat yesterday?", _utc(2023, 4, 17), _utc(2023, 4, 18), "yesterday"),
    ("what is on my plate today", _utc(2023, 4, 18), _utc(2023, 4, 19), "today"),
    # REF is a Tuesday; ISO weeks run Monday..Monday.
    ("what did I do last week", _utc(2023, 4, 10), _utc(2023, 4, 17), "last week"),
    ("meetings this week", _utc(2023, 4, 17), _utc(2023, 4, 24), "this week"),
    ("expenses last month", _utc(2023, 3, 1), _utc(2023, 4, 1), "last month"),
    ("expenses this month", _utc(2023, 4, 1), _utc(2023, 5, 1), "this month"),
    ("goals last year", _utc(2022, 1, 1), _utc(2023, 1, 1), "last year"),
    # "N units ago" maps to the calendar unit containing the shifted point.
    ("the chandelier I got two months ago", _utc(2023, 2, 1), _utc(2023, 3, 1), "two months ago"),
    ("the call 3 days ago", _utc(2023, 4, 15), _utc(2023, 4, 16), "3 days ago"),
    ("the sale a week ago", _utc(2023, 4, 10), _utc(2023, 4, 17), "a week ago"),
    ("the sale a couple of weeks ago", _utc(2023, 4, 3), _utc(2023, 4, 10), "a couple of weeks ago"),
    ("the move one year ago", _utc(2022, 1, 1), _utc(2023, 1, 1), "one year ago"),
    # Open-range keywords apply to relative phrases too: "before today"
    # means everything up to today, never today itself.
    ("airlines I flew with before today", WINDOW_FLOOR, _utc(2023, 4, 18), "before today"),
    ("what changed since yesterday", _utc(2023, 4, 17), WINDOW_CEILING, "since yesterday"),
    ("anything after last week", _utc(2023, 4, 17), WINDOW_CEILING, "after last week"),
    ("everything until two months ago", WINDOW_FLOOR, _utc(2023, 2, 1), "until two months ago"),
]

# Conservatism: ambiguous or date-free text parses to nothing.
NONE_CASES = [
    "May I ask about the roadmap?",  # bare month with no anchoring preposition
    "the March budget compared to plan",  # month preceded by a plain article
    "How many pre-1920 American coins do I have?",  # no preposition before the year
    "we walked 2023 steps",  # bare year with no preposition
    "How many weeks ago did I meet up with my aunt?",  # "many weeks ago" has no count
    "what happened recently",
    "a while ago we discussed pricing",
    "kubernetes deployment pipeline",
    "the may pole dance troupe",
    "",
    "   ",
]


@pytest.mark.parametrize(("query", "start", "end", "parsed_from"), EXPLICIT_CASES)
def test_parse_explicit_dates_and_months(query: str, start: datetime, end: datetime, parsed_from: str) -> None:
    anchor = parse_temporal_anchor(query, reference_time=REF)

    assert anchor is not None, query
    assert anchor.window_start == start
    assert anchor.window_end == end
    assert anchor.parsed_from == parsed_from


@pytest.mark.parametrize(("query", "start", "end", "parsed_from"), RANGE_CASES)
def test_parse_closed_and_open_ranges(query: str, start: datetime, end: datetime, parsed_from: str) -> None:
    anchor = parse_temporal_anchor(query, reference_time=REF)

    assert anchor is not None, query
    assert anchor.window_start == start
    assert anchor.window_end == end
    assert anchor.parsed_from == parsed_from


@pytest.mark.parametrize(("query", "start", "end", "parsed_from"), RELATIVE_CASES)
def test_parse_relative_phrases_against_reference_time(
    query: str, start: datetime, end: datetime, parsed_from: str
) -> None:
    anchor = parse_temporal_anchor(query, reference_time=REF)

    assert anchor is not None, query
    assert anchor.window_start == start
    assert anchor.window_end == end
    assert anchor.parsed_from == parsed_from


@pytest.mark.parametrize("query", NONE_CASES)
def test_ambiguous_and_garbage_queries_parse_to_none(query: str) -> None:
    assert parse_temporal_anchor(query, reference_time=REF) is None


def test_explicit_points_win_over_relative_phrases() -> None:
    anchor = parse_temporal_anchor("compare May 3, 2023 with yesterday", reference_time=REF)

    assert anchor is not None
    assert anchor.parsed_from == "May 3, 2023"
    assert anchor.window_start == _utc(2023, 5, 3)


def test_windows_are_always_utc_and_forward() -> None:
    for query, *_rest in [*EXPLICIT_CASES, *RANGE_CASES, *RELATIVE_CASES]:
        anchor = parse_temporal_anchor(query, reference_time=REF)
        assert anchor is not None
        assert anchor.window_start.tzinfo is UTC
        assert anchor.window_end.tzinfo is UTC
        assert anchor.window_start < anchor.window_end


def test_naive_reference_time_is_treated_as_utc() -> None:
    aware = parse_temporal_anchor("what did I do last week", reference_time=REF)
    naive = parse_temporal_anchor("what did I do last week", reference_time=REF.replace(tzinfo=None))

    assert aware == naive


def test_invalid_calendar_dates_are_rejected() -> None:
    # 2023/15/30 is not a date; the anchored bare year still parses (wide,
    # honest window) rather than inventing a bogus tight one.
    anchor = parse_temporal_anchor("the export on 2023/15/30", reference_time=REF)
    assert anchor is not None
    assert (anchor.window_start, anchor.window_end) == (_utc(2023, 1, 1), _utc(2024, 1, 1))

    assert parse_temporal_anchor("logs for 0000/13/99 build", reference_time=REF) is None


def test_window_center_is_the_midpoint_for_closed_windows() -> None:
    anchor = TemporalAnchor(_utc(2023, 3, 1), _utc(2023, 3, 3), "test")

    assert anchor.window_center == _utc(2023, 3, 2)


def test_window_center_pivots_on_the_closed_edge_for_open_windows() -> None:
    # The midpoint of a century-spanning open window orders matches
    # meaninglessly; the closed edge ranks events nearest the boundary.
    before = TemporalAnchor(WINDOW_FLOOR, _utc(2023, 3, 1), "before March 2023")
    since = TemporalAnchor(_utc(2023, 3, 1), WINDOW_CEILING, "since March 2023")

    assert before.window_center == _utc(2023, 3, 1)
    assert since.window_center == _utc(2023, 3, 1)


def test_parse_event_datetime_accepts_store_and_connector_formats() -> None:
    assert parse_event_datetime("2023-05-30T10:00:00Z") == _utc(2023, 5, 30, 10, 0)
    assert parse_event_datetime("2023-05-30T10:00:00+00:00") == _utc(2023, 5, 30, 10, 0)
    # Chat-session connector form: date, decoration, then a clock time.
    assert parse_event_datetime("2023/05/30 (Tue) 02:01") == _utc(2023, 5, 30, 2, 1)
    assert parse_event_datetime("2023/05/30") == _utc(2023, 5, 30)
    assert parse_event_datetime(_utc(2023, 5, 30, 4, 5)) == _utc(2023, 5, 30, 4, 5)
    # Naive datetimes are treated as UTC.
    assert parse_event_datetime(datetime(2023, 5, 30, 4, 5)) == _utc(2023, 5, 30, 4, 5)


def test_parse_event_datetime_rejects_garbage() -> None:
    assert parse_event_datetime(None) is None
    assert parse_event_datetime("") is None
    assert parse_event_datetime("undated") is None
    assert parse_event_datetime("2023/15/40 (Xxx) 09:99") is None
    assert parse_event_datetime(12345) is None
