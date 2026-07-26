from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

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


def test_out_of_supported_range_date_does_not_overflow() -> None:
    assert parse_temporal_anchor("events on 9999-12-31", reference_time=REF) is None


@pytest.mark.parametrize(
    ("reference", "expected_year"),
    [
        (_utc(2023, 4, 18), 2020),
        (_utc(2024, 2, 28), 2020),
        (_utc(2024, 2, 29, 12), 2024),
    ],
)
def test_yearless_leap_day_resolves_to_most_recent_valid_occurrence(
    reference: datetime,
    expected_year: int,
) -> None:
    anchor = parse_temporal_anchor("what happened on February 29?", reference_time=reference)

    assert anchor is not None
    assert anchor.window_start == _utc(expected_year, 2, 29)
    assert anchor.window_end == _utc(expected_year, 3, 1)


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


# ---------------------------------------------------------------------------
# Relative past windows: a span running from an offset up to the reference.
#
# The window is the whole units of calendar time ENDING with the reference
# day: half-open [start, end) as everywhere else in this module, end at the
# midnight that closes the reference day (matching "today", which already
# spans that day end to end), start exactly N units before that bound. So
# "the past two weeks" is 14 calendar days and the day exactly fourteen days
# back is outside it.
# ---------------------------------------------------------------------------


# REF is Tuesday 2023-04-18, so every window below ends 2023-04-19 00:00.
PAST_WINDOW_CASES = [
    ("how many times did I bake in the past two weeks?", _utc(2023, 4, 5), "the past two weeks"),
    ("what did I cook in the past week", _utc(2023, 4, 12), "the past week"),
    ("dinner parties in the past month", _utc(2023, 3, 19), "the past month"),
    ("everything over the past year", _utc(2022, 4, 19), "the past year"),
    ("what happened during the past three days", _utc(2023, 4, 16), "the past three days"),
    ("bills within the last 6 weeks", _utc(2023, 3, 8), "the last 6 weeks"),
    ("I have been ill for the past 2 months", _utc(2023, 2, 19), "the past 2 months"),
    ("meetings throughout the past week", _utc(2023, 4, 12), "the past week"),
    ("jewelry I acquired in the last two months", _utc(2023, 2, 19), "the last two months"),
    # Bare singular means one unit.
    ("what did I spend in the past day", _utc(2023, 4, 18), "the past day"),
    ("what did I spend in the past 1 day", _utc(2023, 4, 18), "the past 1 day"),
    # Spelled-out, digit, and multiword counts all resolve the same way.
    ("trips in the past twelve months", _utc(2022, 4, 19), "the past twelve months"),
    ("trips in the past 12 months", _utc(2022, 4, 19), "the past 12 months"),
    ("trips in the past couple of weeks", _utc(2023, 4, 5), "the past couple of weeks"),
    ("trips in the last one year", _utc(2022, 4, 19), "the last one year"),
    # Case and surrounding text do not matter.
    ("IN THE PAST TWO WEEKS", _utc(2023, 4, 5), "THE PAST TWO WEEKS"),
    ("in the past three months, what did I buy?", _utc(2023, 1, 19), "the past three months"),
]

PAST_WINDOW_NONE_CASES = [
    # No definite quantity: the module refuses rather than picking one.
    "what did I bake in the past few weeks",
    "what did I bake in the past several months",
    "what did I bake in the past couple weeks",
    "what did I bake in the past weeks",
    "what did I bake in the past many days",
    "what did I bake in the past",
    # A vague tail is the same problem stated at the end of the phrase.
    "what did I bake in the past month or so",
    "what did I bake in the past year and a half",
    "what did I bake in the past day or two",
    "what did I bake in the past week and a bit",
    # A RE-ANCHORED span ends somewhere other than now: at a named period's
    # edge, at a named event, or starting from one. Every one of these is a
    # wrong span rather than a narrow one if resolved as a window ending
    # today.
    "what did I bake in the last 3 months of 2022",
    "what did I bake in the past two weeks of the trip",
    "what did I bake in the last 2 weeks before the wedding",
    "what did I bake in the past 6 months prior to surgery",
    "what did I bake in the last three months leading up to the show",
    "what did I bake in the past two weeks leading to the show",
    "what did I bake in the past two weeks running up to the show",
    "what did I bake in the past two weeks up to the wedding",
    "what did I bake in the past two weeks preceding the wedding",
    "what did I bake in the past two weeks ahead of the wedding",
    "what did I bake in the past two weeks following surgery",
    "what did I bake in the past two weeks after surgery",
    "what did I bake in the past two weeks since surgery",
    "what did I bake in the past two weeks until the wedding",
    "what did I bake in the past two weeks till the wedding",
    "what did I bake in the past two weeks ending Friday",
    "what did I bake in the past two weeks starting Monday",
    "what did I bake in the past two weeks beginning Monday",
    "what did I bake in the past two weeks from Monday",
    # An EXCLUSION in front of the phrase asks about the complement of the
    # span, so resolving the span answers the opposite question.
    "what did I bake except for the past two weeks",
    "what did I bake, not in the past two weeks",
    "what did I bake other than in the past two weeks",
    "what did I bake excluding the past two weeks",
    "what did I bake apart from the past two weeks",
    "what did I bake outside of the past two weeks",
    "what did I bake ignoring the past two weeks",
    "what did I bake without the past two weeks",
    "what did I bake rather than in the past two weeks",
    "everything but not in the past two weeks",
    # A plural count with a SINGULAR unit is an attributive compound, not a
    # span: the noun it modifies is the head and this pattern never saw it.
    "what did I bake in the past 3 day trip",
    "what did I bake in the past 2 week holiday",
    "what did I bake in the past 6 month lease",
    "what did I bake in the past 12 month period",
    "what did I bake in the past two week break",
    # Units this module does not carry anywhere else, plus the ambiguous one.
    "what did I bake in the past 24 hours",
    "what did I bake in the past fortnight",
    "what did I bake in the past quarter",
    "what did I bake in the past decade",
    # A zero-length or unrepresentable span is never invented.
    "what did I bake in the past 0 days",
    "what did I bake in the past 999 years",
    # The phrase needs both an anchoring preposition and the article.
    "what did I bake in past two weeks",
    "the past two weeks were busy",
    "these past two weeks were busy",
    "what did I bake in this past week",
    "what did I bake in these past two weeks",
    "what did I bake since the past two weeks",
    # Not a temporal phrase at all.
    "what did I bake in the past monthly report",
]


@pytest.mark.parametrize(("query", "start", "parsed_from"), PAST_WINDOW_CASES)
def test_a_relative_past_window_spans_the_offset_up_to_the_reference_day(
    query: str, start: datetime, parsed_from: str
) -> None:
    anchor = parse_temporal_anchor(query, reference_time=REF)

    assert anchor is not None, query
    assert anchor.window_start == start
    # Every one of these ends with the reference day, never open-ended.
    assert anchor.window_end == _utc(2023, 4, 19)
    assert anchor.window_end != WINDOW_CEILING
    assert anchor.parsed_from == parsed_from


@pytest.mark.parametrize("query", PAST_WINDOW_NONE_CASES)
def test_a_span_that_pins_down_no_single_window_is_refused(query: str) -> None:
    assert parse_temporal_anchor(query, reference_time=REF) is None


def test_past_window_boundaries_are_half_open_and_exactly_n_units_long() -> None:
    """The reference day is in; the day exactly N units back is out."""

    anchor = parse_temporal_anchor("what did I bake in the past two weeks", reference_time=REF)

    assert anchor is not None
    # 14 calendar days, not 15.
    assert (anchor.window_end - anchor.window_start).days == 14
    # The reference day is inside the window.
    assert anchor.window_start <= REF < anchor.window_end
    # The first instant of the window is included, the last excluded.
    assert anchor.window_start == _utc(2023, 4, 5)
    assert anchor.window_end == _utc(2023, 4, 19)
    # The day exactly fourteen days before the reference day is outside.
    assert _utc(2023, 4, 4) < anchor.window_start

    week = parse_temporal_anchor("what did I bake in the past week", reference_time=REF)
    assert week is not None
    assert (week.window_end - week.window_start).days == 7


def test_a_past_window_is_never_the_offset_window_of_the_same_unit_count() -> None:
    """A span phrase and an offset phrase name different periods.

    "in the past two weeks" runs up to now; "two weeks ago" names the
    calendar week holding the point two weeks back, which closes before the
    reference day. Answering either with the other counts over a period
    nobody asked about.
    """

    span = parse_temporal_anchor("what did I bake in the past two weeks", reference_time=REF)
    offset = parse_temporal_anchor("what did I bake two weeks ago", reference_time=REF)

    assert span is not None and offset is not None
    assert (span.window_start, span.window_end) == (_utc(2023, 4, 5), _utc(2023, 4, 19))
    assert (offset.window_start, offset.window_end) == (_utc(2023, 4, 3), _utc(2023, 4, 10))
    assert offset.window_end < span.window_end
    # The offset window reaches back further than the span does.
    assert offset.window_start < span.window_start


def test_phrases_that_already_resolved_keep_the_window_they_always_had() -> None:
    """Relative past windows are additive: they never retarget an old parse.

    "in the last month" has always meant the previous CALENDAR month here,
    through ``_LAST_THIS_UNIT``, and it still does. Only forms that parsed
    to nothing before ("in the past month", "in the last 1 month") reach the
    new span rule, which is why the two now differ.
    """

    calendar = parse_temporal_anchor("expenses in the last month", reference_time=REF)
    assert calendar is not None
    assert (calendar.window_start, calendar.window_end) == (_utc(2023, 3, 1), _utc(2023, 4, 1))
    assert calendar.parsed_from == "last month"

    for query in ("expenses in the last week", "expenses in this week", "expenses in the last year"):
        anchor = parse_temporal_anchor(query, reference_time=REF)
        assert anchor is not None
        assert anchor.parsed_from in ("last week", "this week", "last year")

    span = parse_temporal_anchor("expenses in the past month", reference_time=REF)
    assert span is not None
    assert (span.window_start, span.window_end) == (_utc(2023, 3, 19), _utc(2023, 4, 19))

    explicit = parse_temporal_anchor("expenses in the last 1 month", reference_time=REF)
    assert explicit is not None
    assert (explicit.window_start, explicit.window_end) == (_utc(2023, 3, 19), _utc(2023, 4, 19))


def test_an_explicit_calendar_point_still_outranks_a_relative_past_window() -> None:
    anchor = parse_temporal_anchor(
        "what did I buy in March 2023 and in the past two weeks",
        reference_time=REF,
    )

    assert anchor is not None
    assert anchor.parsed_from == "March 2023"
    assert (anchor.window_start, anchor.window_end) == (_utc(2023, 3, 1), _utc(2023, 4, 1))


@pytest.mark.parametrize(
    ("reference", "start", "end"),
    [
        # Month arithmetic goes through _add_months, so a month-end
        # reference clamps rather than overflowing into the next month.
        (_utc(2023, 3, 31), _utc(2023, 3, 1), _utc(2023, 4, 1)),
        (_utc(2023, 3, 30), _utc(2023, 2, 28), _utc(2023, 3, 31)),
        (_utc(2024, 3, 30), _utc(2024, 2, 29), _utc(2024, 3, 31)),
        (_utc(2023, 1, 31), _utc(2023, 1, 1), _utc(2023, 2, 1)),
        (_utc(2023, 12, 31), _utc(2023, 12, 1), _utc(2024, 1, 1)),
    ],
)
def test_a_one_month_span_clamps_at_month_ends_without_inverting(
    reference: datetime, start: datetime, end: datetime
) -> None:
    anchor = parse_temporal_anchor("what did I bake in the past month", reference_time=reference)

    assert anchor is not None
    assert (anchor.window_start, anchor.window_end) == (start, end)
    assert anchor.window_start < anchor.window_end


@pytest.mark.parametrize(
    ("reference", "start", "end"),
    [
        (_utc(2024, 2, 28), _utc(2023, 2, 28), _utc(2024, 2, 29)),
        (_utc(2024, 2, 29), _utc(2023, 3, 1), _utc(2024, 3, 1)),
        (_utc(2023, 2, 28), _utc(2022, 3, 1), _utc(2023, 3, 1)),
    ],
)
def test_a_one_year_span_crosses_a_leap_day_without_inverting(
    reference: datetime, start: datetime, end: datetime
) -> None:
    anchor = parse_temporal_anchor("what did I bake in the past year", reference_time=reference)

    assert anchor is not None
    assert (anchor.window_start, anchor.window_end) == (start, end)
    assert anchor.window_start < anchor.window_end


def test_no_reference_day_or_count_produces_an_inverted_or_open_window() -> None:
    """Swept, not argued: every day of two years crossed with every unit."""

    checked = 0
    day = date(2023, 1, 1)
    while day < date(2025, 1, 1):
        reference = datetime(day.year, day.month, day.day, 13, 45, tzinfo=UTC)
        for count in (1, 2, 3, 7, 12, 52, 99):
            for unit in ("day", "week", "month", "year"):
                anchor = parse_temporal_anchor(
                    f"what did I bake in the past {count} {unit}s",
                    reference_time=reference,
                )
                assert anchor is not None, (reference, count, unit)
                assert anchor.window_start < anchor.window_end
                assert anchor.window_start >= WINDOW_FLOOR
                assert anchor.window_end != WINDOW_CEILING
                # The span always covers the reference day and never runs on
                # past it.
                assert anchor.window_start <= reference < anchor.window_end
                day_start = datetime(day.year, day.month, day.day, tzinfo=UTC)
                assert anchor.window_end == day_start + timedelta(days=1)
                checked += 1
        day += timedelta(days=1)

    assert checked == 731 * 28

    # Reaching back past WINDOW_FLOOR refuses instead of clamping to it:
    # clamping would turn a bounded span into an effectively open-ended one.
    assert parse_temporal_anchor("what did I bake in the past 300 years", reference_time=REF) is None
    assert parse_temporal_anchor("what did I bake in the past 99 years", reference_time=REF) is not None


def test_a_past_window_is_deterministic_and_reference_driven() -> None:
    query = "what did I bake in the past two weeks"

    assert parse_temporal_anchor(query, reference_time=REF) == parse_temporal_anchor(
        query, reference_time=REF.replace(tzinfo=None)
    )
    later = parse_temporal_anchor(query, reference_time=REF + timedelta(days=1))
    assert later is not None
    assert later.window_end == _utc(2023, 4, 20)


def test_past_window_cases_are_utc_and_forward() -> None:
    for query, *_rest in PAST_WINDOW_CASES:
        anchor = parse_temporal_anchor(query, reference_time=REF)
        assert anchor is not None
        assert anchor.window_start.tzinfo is UTC
        assert anchor.window_end.tzinfo is UTC
        assert anchor.window_start < anchor.window_end


def test_a_reference_time_at_the_edge_of_the_datetime_range_refuses_rather_than_raising() -> None:
    """This runs inside pack compilation, so it must not propagate.

    The offset phrases already raise on the same inputs (``"two weeks ago"``
    overflows at year 1, ``"today"`` overflows at year 9999); that is
    pre-existing and untouched here. The span rule refuses instead.
    """

    for reference in (
        datetime(1, 1, 2, tzinfo=UTC),
        datetime(1, 1, 1, tzinfo=UTC),
        datetime(9999, 12, 31, tzinfo=UTC),
    ):
        for query in (
            "what did I bake in the past two weeks",
            "what did I bake in the past month",
            "what did I bake in the past 3 years",
            "what did I bake in the past day",
        ):
            assert parse_temporal_anchor(query, reference_time=reference) is None


def test_the_span_count_bound_is_three_digits_and_refuses_beyond_it() -> None:
    """The count width matches ``_UNITS_AGO``'s, and nothing wider parses.

    Without this pin the digit bound is free to widen silently, and a wider
    one would take "in the past 1000 days" (a typo, or a number that means
    something else entirely) for a span nearly three years long.
    """

    inside = parse_temporal_anchor("what did I bake in the past 999 days", reference_time=REF)
    assert inside is not None
    assert inside.window_start == _utc(2020, 7, 24)
    assert inside.window_end == _utc(2023, 4, 19)

    for query in (
        "what did I bake in the past 1000 days",
        "what did I bake in the past 1234 weeks",
        "what did I bake in the past 10000 years",
        "what did I bake in the past 0999 days",
    ):
        assert parse_temporal_anchor(query, reference_time=REF) is None, query


def test_a_re_anchored_or_excluded_span_never_becomes_a_window_ending_now() -> None:
    """The two classes above, asserted against the windows they would take.

    Each case is checked against the window the phrase's own span WOULD have
    resolved to, so a future edit that admits any of them fails here with the
    wrong window in hand rather than merely with a non-None anchor.
    """

    plain = parse_temporal_anchor("what did I bake in the past two weeks", reference_time=REF)
    assert plain is not None
    span = (plain.window_start, plain.window_end)

    for query in (
        "what did I bake in the past two weeks before the wedding",
        "what did I bake in the past two weeks prior to surgery",
        "what did I bake in the past two weeks leading up to the show",
        "what did I bake except for the past two weeks",
        "what did I bake, not in the past two weeks",
    ):
        anchor = parse_temporal_anchor(query, reference_time=REF)
        assert anchor is None, (query, anchor, span)

    # The same sentence WITHOUT the re-anchoring tail still resolves, so the
    # refusals above come from the tail and not from breaking the family.
    assert parse_temporal_anchor("what did I bake in the past two weeks", reference_time=REF) is not None


def test_an_exclusion_guard_never_swallows_an_ordinary_verb() -> None:
    """The exclusion words fire on the phrase's preposition, not on a verb.

    "not" is the one that could over-reach, so it is pinned from both sides:
    it refuses "not IN the past two weeks" and leaves an ordinary negated
    clause alone, because there the verb sits between "not" and "in".
    """

    for query in (
        "what did I save in the past two weeks",
        "I did not bake in the past two weeks",
        "how many times did I not visit the museum in the past two weeks",
        "what did I spend but forgot in the past two weeks",
    ):
        anchor = parse_temporal_anchor(query, reference_time=REF)
        assert anchor is not None, query
        assert (anchor.window_start, anchor.window_end) == (_utc(2023, 4, 5), _utc(2023, 4, 19))
