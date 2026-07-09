"""Deterministic temporal-anchor parsing for retrieval queries.

``parse_temporal_anchor`` turns date-bearing query text ("in March 2023",
"on May 3", "two months ago", "between March and May 2023") into one UTC
``[window_start, window_end)`` window that the retrieval service feeds RRF
fusion as ONE MORE ranked list — never a hard filter, so a wrong parse
cannot evict lexical/vector/graph hits. Everything here is pure string
matching and calendar arithmetic: no LLM, no store access, no benchmark
metadata, and no wall-clock reads — ``reference_time`` always comes from
the caller (tests pass fixed values; the service passes the request's now).

Conservatism rule: a wrong tight window is worse than none. Phrases that
do not pin down one window deterministically ("recently", a bare month
name with no anchoring preposition or year — think "May I ask") return
``None``. Month/day mentions without a year resolve to the most recent
occurrence at or before ``reference_time``, matching how people query a
memory system about the past.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import re


# Bounds for the open side of "before X" / "since X" windows. Wide enough
# for any honest memory timestamp while staying inside every backend's
# sane timestamp range.
WINDOW_FLOOR = datetime(1900, 1, 1, tzinfo=UTC)
WINDOW_CEILING = datetime(2200, 1, 1, tzinfo=UTC)

# Bare 4-digit numbers only count as years inside this range ("in 1962",
# "since 2021") so counts like "in 3000 steps" never parse as dates.
_YEAR_MIN = 1900
_YEAR_MAX = 2099

_MONTHS_BY_NAME = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_MONTH_NAMES = "|".join(_MONTHS_BY_NAME)

_NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "a couple of": 2,
    "couple of": 2,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
# Longest alternatives first so "a couple of" wins over bare "a".
_NUMBER_WORD_PATTERN = "|".join(
    re.escape(word).replace("\\ ", r"\s+")
    for word in sorted(_NUMBER_WORDS, key=len, reverse=True)
)

_ORDINAL_SUFFIX = r"(?:st|nd|rd|th)?"

# -- point-expression patterns (explicit calendar references) ---------------
# Numeric year-first dates only (2023/05/30, 2023-05-30); day-first and
# US-style numeric dates are skipped as ambiguous. Month-led patterns
# accept an "early/mid/late" modifier, which widens to the whole month:
# the modifier is recognized (so it lands in parsed_from and the longest
# span wins overlap resolution), then ignored.
_MODIFIER_PREFIX = r"(?:(?:early|mid|late)\s+)?"
_NUMERIC_DATE = re.compile(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b")
_MONTH_DAY_YEAR = re.compile(
    rf"\b{_MODIFIER_PREFIX}({_MONTH_NAMES})\s+(\d{{1,2}}){_ORDINAL_SUFFIX}(?:\s*,\s*|\s+)(\d{{4}})\b",
    re.IGNORECASE,
)
_DAY_MONTH_YEAR = re.compile(
    rf"\b(\d{{1,2}}){_ORDINAL_SUFFIX}\s+(?:of\s+)?({_MONTH_NAMES})(?:\s*,\s*|\s+)(\d{{4}})\b",
    re.IGNORECASE,
)
_MONTH_DAY = re.compile(rf"\b({_MONTH_NAMES})\s+(\d{{1,2}}){_ORDINAL_SUFFIX}\b", re.IGNORECASE)
_DAY_MONTH = re.compile(rf"\b(\d{{1,2}}){_ORDINAL_SUFFIX}\s+of\s+({_MONTH_NAMES})\b", re.IGNORECASE)
_MONTH_YEAR = re.compile(rf"\b{_MODIFIER_PREFIX}({_MONTH_NAMES})\s+(?:of\s+)?(\d{{4}})\b", re.IGNORECASE)
_BARE_MONTH = re.compile(rf"\b{_MODIFIER_PREFIX}({_MONTH_NAMES})\b", re.IGNORECASE)
_BARE_YEAR = re.compile(r"\b(\d{4})\b")

# Prepositions that anchor a bare month or bare year as a temporal
# reference when they immediately precede it ("in March", "during 2022").
# Bare months/years without one never parse — "May I ask" stays a modal.
_STANDALONE_ANCHOR_WORDS = ("in", "during", "on", "since", "before", "after", "until", "by", "from")
_ANCHOR_BEFORE = re.compile(r"(?:^|[\s(,;:])(" + "|".join(_STANDALONE_ANCHOR_WORDS) + r")\s+$", re.IGNORECASE)

# Range/open-window keywords examined around parsed points.
_RANGE_CONNECTOR = re.compile(r"^\s*(?:and|to|until|through)\s*$", re.IGNORECASE)
_BETWEEN_BEFORE = re.compile(r"\b(between|from)\s+$", re.IGNORECASE)
_OPEN_BEFORE = re.compile(r"\b(before|until|prior\s+to|since|after|by)\s+$", re.IGNORECASE)

# Month pair: "in March and April" spans both months.
_MONTH_PAIR_AFTER = re.compile(rf"^\s+and\s+({_MONTH_NAMES})\b", re.IGNORECASE)

# -- relative phrases (need reference_time) ---------------------------------
_YESTERDAY = re.compile(r"\byesterday\b", re.IGNORECASE)
_TODAY = re.compile(r"\btoday\b", re.IGNORECASE)
_LAST_THIS_UNIT = re.compile(r"\b(last|this)\s+(week|month|year)\b", re.IGNORECASE)
_UNITS_AGO = re.compile(
    rf"\b({_NUMBER_WORD_PATTERN}|\d{{1,3}})\s+(day|week|month|year)s?\s+ago\b", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class TemporalAnchor:
    """One UTC ``[window_start, window_end)`` window parsed from a query."""

    window_start: datetime
    window_end: datetime
    parsed_from: str

    @property
    def window_center(self) -> datetime:
        """Proximity pivot for ordering matches inside the window.

        Closed windows pivot on their midpoint. Open windows ("before X",
        "since X") pivot on the closed edge — the midpoint of a
        century-spanning range orders matches meaninglessly, while the
        edge ranks the events nearest the named boundary first.
        """
        if self.window_start == WINDOW_FLOOR and self.window_end != WINDOW_CEILING:
            return self.window_end
        if self.window_end == WINDOW_CEILING and self.window_start != WINDOW_FLOOR:
            return self.window_start
        return self.window_start + (self.window_end - self.window_start) / 2


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _day_window(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    return start, start + timedelta(days=1)


def _week_window(day: date) -> tuple[datetime, datetime]:
    """ISO week (Monday-start) containing ``day``."""
    monday = day - timedelta(days=day.weekday())
    start = datetime(monday.year, monday.month, monday.day, tzinfo=UTC)
    return start, start + timedelta(days=7)


def _month_window(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        return start, datetime(year + 1, 1, 1, tzinfo=UTC)
    return start, datetime(year, month + 1, 1, tzinfo=UTC)


def _year_window(year: int) -> tuple[datetime, datetime]:
    return datetime(year, 1, 1, tzinfo=UTC), datetime(year + 1, 1, 1, tzinfo=UTC)


def _months_back(reference: datetime, months: int) -> tuple[int, int]:
    index = reference.year * 12 + (reference.month - 1) - months
    return index // 12, index % 12 + 1


def _resolve_month_year(month: int, reference: datetime) -> int:
    """Most recent occurrence of ``month`` starting at or before the reference."""
    return reference.year if month <= reference.month else reference.year - 1


def parse_event_datetime(value: object) -> datetime | None:
    """Best-effort UTC timestamp for stored date-ish values.

    Accepts ``datetime`` objects, ISO-8601 strings (``Z`` suffix included),
    and connector-style date strings that lead with ``YYYY/MM/DD`` or
    ``YYYY-MM-DD`` and may carry trailing decoration (e.g. the chat-session
    form ``"2023/05/30 (Tue) 02:01"``). Anything else returns ``None``.
    Naive inputs are treated as UTC.
    """
    if isinstance(value, datetime):
        return _utc(value)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        return _utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        pass
    match = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:\D+?(\d{1,2}):(\d{2}))?", text)
    if match is None:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    hour = int(match.group(4)) if match.group(4) else 0
    minute = int(match.group(5)) if match.group(5) else 0
    try:
        return datetime(year, month, day, hour, minute, tzinfo=UTC)
    except ValueError:
        return None


# Point kinds, most to least specific. Bare months/years are "weak":
# they only anchor with a preposition or range keyword next to them.
_KIND_DATE = "date"
_KIND_MONTH_YEAR = "month_year"
_KIND_MONTH = "month"
_KIND_YEAR = "year"


@dataclass(frozen=True, slots=True)
class _Point:
    """One explicit calendar reference found in the query text."""

    start: int
    end: int
    text: str
    kind: str
    window: tuple[datetime, datetime]
    month: int | None = None  # set for month-bearing kinds

    @property
    def weak(self) -> bool:
        return self.kind in (_KIND_MONTH, _KIND_YEAR)


def _valid_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _find_points(text: str, reference: datetime) -> list[_Point]:
    """Explicit calendar references, longest-match-wins on overlaps."""
    candidates: list[_Point] = []

    for match in _NUMERIC_DATE.finditer(text):
        day = _valid_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if day is None:
            continue
        candidates.append(
            _Point(match.start(), match.end(), match.group(0), _KIND_DATE, _day_window(day), day.month)
        )

    for pattern, month_group, day_group, year_group in (
        (_MONTH_DAY_YEAR, 1, 2, 3),
        (_DAY_MONTH_YEAR, 2, 1, 3),
    ):
        for match in pattern.finditer(text):
            month = _MONTHS_BY_NAME[match.group(month_group).casefold()]
            day = _valid_date(int(match.group(year_group)), month, int(match.group(day_group)))
            if day is None:
                continue
            candidates.append(
                _Point(match.start(), match.end(), match.group(0), _KIND_DATE, _day_window(day), month)
            )

    for match in _MONTH_YEAR.finditer(text):
        year = int(match.group(2))
        if not (_YEAR_MIN <= year <= _YEAR_MAX):
            continue
        month = _MONTHS_BY_NAME[match.group(1).casefold()]
        candidates.append(
            _Point(match.start(), match.end(), match.group(0), _KIND_MONTH_YEAR, _month_window(year, month), month)
        )

    for pattern, month_group, day_group in ((_MONTH_DAY, 1, 2), (_DAY_MONTH, 2, 1)):
        for match in pattern.finditer(text):
            month = _MONTHS_BY_NAME[match.group(month_group).casefold()]
            day_number = int(match.group(day_group))
            day = _valid_date(_resolve_month_year(month, reference), month, day_number)
            if day is None:
                continue
            if datetime(day.year, day.month, day.day, tzinfo=UTC) > reference:
                day = _valid_date(day.year - 1, month, day_number)
                if day is None:
                    continue
            candidates.append(
                _Point(match.start(), match.end(), match.group(0), _KIND_DATE, _day_window(day), month)
            )

    for match in _BARE_MONTH.finditer(text):
        month = _MONTHS_BY_NAME[match.group(1).casefold()]
        window = _month_window(_resolve_month_year(month, reference), month)
        candidates.append(_Point(match.start(), match.end(), match.group(0), _KIND_MONTH, window, month))

    for match in _BARE_YEAR.finditer(text):
        year = int(match.group(1))
        if not (_YEAR_MIN <= year <= _YEAR_MAX):
            continue
        candidates.append(_Point(match.start(), match.end(), match.group(0), _KIND_YEAR, _year_window(year)))

    # Longest match wins where spans overlap ("May 3, 2023" beats "May 3"
    # beats "May"); earlier start wins between disjoint groups.
    candidates.sort(key=lambda point: (point.start, -(point.end - point.start)))
    accepted: list[_Point] = []
    for point in candidates:
        if any(point.start < other.end and other.start < point.end for other in accepted):
            continue
        accepted.append(point)
    return accepted


def _anchored(text: str, point: _Point) -> bool:
    """Weak points (bare months/years) need a preposition right before."""
    if not point.weak:
        return True
    return _ANCHOR_BEFORE.search(text[: point.start]) is not None


def _closed_range(text: str, points: list[_Point]) -> TemporalAnchor | None:
    """First "between X and Y" / "from X to Y" over adjacent points."""
    for first, second in zip(points, points[1:]):
        keyword = _BETWEEN_BEFORE.search(text[: first.start])
        if keyword is None or _RANGE_CONNECTOR.match(text[first.end : second.start]) is None:
            continue
        first_window, second_window = first.window, second.window
        if first.kind == _KIND_MONTH and first.month is not None and second.month is not None:
            # A yearless first month borrows the second point's year,
            # wrapping back one year when the range would run backwards
            # ("between November and May 2023").
            second_start = second_window[0]
            year = second_start.year if first.month <= second_start.month else second_start.year - 1
            first_window = _month_window(year, first.month)
        start, end = first_window[0], second_window[1]
        if start < end:
            return TemporalAnchor(start, end, text[keyword.start(1) : second.end])
    return None


def _open_range(text: str, points: list[_Point]) -> TemporalAnchor | None:
    """First point with before/until/prior to/since/after/by right before it."""
    for point in points:
        keyword_match = _OPEN_BEFORE.search(text[: point.start])
        if keyword_match is None:
            continue
        keyword = " ".join(keyword_match.group(1).casefold().split())
        parsed_from = text[keyword_match.start(1) : point.end]
        if keyword in ("before", "until", "prior to"):
            # Everything strictly before the point begins.
            if WINDOW_FLOOR < point.window[0]:
                return TemporalAnchor(WINDOW_FLOOR, point.window[0], parsed_from)
        elif keyword == "by":
            # Deadline semantics: through the end of the point itself.
            if WINDOW_FLOOR < point.window[1]:
                return TemporalAnchor(WINDOW_FLOOR, point.window[1], parsed_from)
        elif keyword == "after":
            if point.window[1] < WINDOW_CEILING:
                return TemporalAnchor(point.window[1], WINDOW_CEILING, parsed_from)
        else:  # since: the point itself onward
            if point.window[0] < WINDOW_CEILING:
                return TemporalAnchor(point.window[0], WINDOW_CEILING, parsed_from)
    return None


def _single_point(text: str, points: list[_Point]) -> TemporalAnchor | None:
    for point in points:
        if not _anchored(text, point):
            continue
        if point.kind == _KIND_MONTH and point.month is not None:
            pair = _MONTH_PAIR_AFTER.match(text[point.end :])
            if pair is not None:
                # "in March and April": one window spanning both months,
                # wrapping the year when the second month precedes the
                # first ("in December and January").
                second_month = _MONTHS_BY_NAME[pair.group(1).casefold()]
                first_start = point.window[0]
                year = first_start.year if second_month >= point.month else first_start.year + 1
                _, end = _month_window(year, second_month)
                return TemporalAnchor(first_start, end, text[point.start : point.end + pair.end()])
        return TemporalAnchor(point.window[0], point.window[1], point.text)
    return None


def _open_adjusted(
    text: str, match: re.Match[str], start: datetime, end: datetime
) -> TemporalAnchor:
    """Apply an open-range keyword sitting right before a relative phrase.

    "before today" means everything up to today, not today itself — the
    same keyword semantics ``_open_range`` gives explicit points. Without
    a keyword the phrase's own window stands.
    """
    keyword_match = _OPEN_BEFORE.search(text[: match.start()])
    if keyword_match is None:
        return TemporalAnchor(start, end, match.group(0))
    keyword = " ".join(keyword_match.group(1).casefold().split())
    parsed_from = text[keyword_match.start(1) : match.end()]
    if keyword in ("before", "until", "prior to") and WINDOW_FLOOR < start:
        return TemporalAnchor(WINDOW_FLOOR, start, parsed_from)
    if keyword == "by" and WINDOW_FLOOR < end:
        return TemporalAnchor(WINDOW_FLOOR, end, parsed_from)
    if keyword == "after" and end < WINDOW_CEILING:
        return TemporalAnchor(end, WINDOW_CEILING, parsed_from)
    if keyword == "since" and start < WINDOW_CEILING:
        return TemporalAnchor(start, WINDOW_CEILING, parsed_from)
    return TemporalAnchor(start, end, match.group(0))


def _relative_window(text: str, reference: datetime) -> TemporalAnchor | None:
    match = _YESTERDAY.search(text)
    if match is not None:
        start, end = _day_window((reference - timedelta(days=1)).date())
        return _open_adjusted(text, match, start, end)
    match = _TODAY.search(text)
    if match is not None:
        start, end = _day_window(reference.date())
        return _open_adjusted(text, match, start, end)
    match = _LAST_THIS_UNIT.search(text)
    if match is not None:
        which, unit = match.group(1).casefold(), match.group(2).casefold()
        if unit == "week":
            start, end = _week_window(reference.date() - timedelta(days=7 if which == "last" else 0))
        elif unit == "month":
            year, month = _months_back(reference, 1 if which == "last" else 0)
            start, end = _month_window(year, month)
        else:
            start, end = _year_window(reference.year - (1 if which == "last" else 0))
        return _open_adjusted(text, match, start, end)
    match = _UNITS_AGO.search(text)
    if match is not None:
        raw_count = " ".join(match.group(1).casefold().split())
        count = _NUMBER_WORDS.get(raw_count)
        if count is None:
            try:
                count = int(raw_count)
            except ValueError:
                return None
        unit = match.group(2).casefold()
        if unit == "day":
            start, end = _day_window((reference - timedelta(days=count)).date())
        elif unit == "week":
            start, end = _week_window(reference.date() - timedelta(days=7 * count))
        elif unit == "month":
            year, month = _months_back(reference, count)
            start, end = _month_window(year, month)
        else:
            start, end = _year_window(reference.year - count)
        return _open_adjusted(text, match, start, end)
    return None


def parse_temporal_anchor(query: str, *, reference_time: datetime) -> TemporalAnchor | None:
    """Parse one UTC ``[start, end)`` window from date-bearing query text.

    Recognized, in priority order (first hit wins):

    1. Closed ranges over two explicit points: "between March and May
       2023", "from 2023-01-05 to 2023-01-10". A yearless first month
       borrows the second point's year.
    2. Open ranges: "before/until/prior to X" -> ``[WINDOW_FLOOR,
       start(X))``; "by X" -> ``[WINDOW_FLOOR, end(X))``; "since X" ->
       ``[start(X), WINDOW_CEILING)``; "after X" -> ``[end(X),
       WINDOW_CEILING)``.
    3. Explicit dates and months: "2023/05/30", "May 3, 2023", "March
       2023", "on May 3" (yearless forms resolve to the most recent
       occurrence at or before ``reference_time``), "in March" /
       "in March and April" (a bare month or year needs an anchoring
       preposition immediately before it).
    4. Relative phrases resolved against ``reference_time``: "yesterday",
       "today", "last/this week|month|year", "two months ago" — each maps
       to the calendar day/week/month/year containing the shifted point.

    Ambiguity returns ``None``: bare months or years without an anchoring
    preposition ("May I ask", "pre-1920 coins"), "recently", "a while
    ago", and any text with no recognized phrase. ``reference_time`` may
    be naive (treated as UTC); the result is always UTC-aware with
    ``window_start < window_end``.
    """
    text = " ".join(str(query).split())
    if not text:
        return None
    reference = _utc(reference_time)

    points = _find_points(text, reference)
    if points:
        anchor = (
            _closed_range(text, points)
            or _open_range(text, points)
            or _single_point(text, points)
        )
        if anchor is not None:
            return anchor
    return _relative_window(text, reference)


__all__ = [
    "TemporalAnchor",
    "WINDOW_CEILING",
    "WINDOW_FLOOR",
    "parse_event_datetime",
    "parse_temporal_anchor",
]
