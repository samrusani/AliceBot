"""Judge-free stale-pick metric for knowledge-update-style questions.

LongMemEval's knowledge-update questions plant an update chain in the
haystack: an earlier session states an old value ("my 5K best is 27:12"),
a later one states the current value ("my best is 25:50"), and the gold
answer is the current value. A memory system whose retrieval surfaces both
can still answer with the OLD value — the judge scores that "no", but the
judge is an LLM and costs money. This module measures the same failure
programmatically: it extracts the update chain from the dataset's evidence
structure (``has_answer`` turns) by value-shape matching, then classifies a
run's hypothesis as GOLD-VALUE, STALE-VALUE, or OTHER by normalized value
matching (numbers, durations, money, weekdays, dates, entities). No LLM,
no judge, no network — replayable over any checkpoint JSONL for free.

BOUNDARY STATEMENT — eval tooling, not product code. This module reads
benchmark labels from the DATASET (``question_type`` for reporting slices,
``answer`` and ``has_answer`` evidence flags for chain extraction). That is
permitted here because it runs strictly POST-HOC over completed run
checkpoints: nothing in this module is imported by the product answer path
(``apps/api/src``), by the harness's generation/retrieval path
(``runner.run_question`` / ``adapter``), or by anything that could shape a
hypothesis before it is scored. A test in ``test_harness.py`` pins that
isolation.

CLI (replay a checkpoint):

    PYTHONPATH=eval python -m longmemeval.stale_pick \
        --dataset eval/longmemeval/data/longmemeval_s_cleaned.json \
        --checkpoint <run>/checkpoint.jsonl [--checkpoint <run2>/checkpoint.jsonl ...] \
        [--json out.json] [--per-question]

Classification rule (deterministic; mirrors the official knowledge-update
judge template's intent, which accepts mentions of the previous value as
long as the UPDATED answer is the one given): scan the hypothesis's
sentences from the END — chain-of-thought answers conclude with their
answer — and the first sentence (from the end) that contains any
chain-relevant value decides:

- GOLD-VALUE  — the deciding sentence contains a gold value (gold wins ties
  in the same sentence, e.g. "improved from 27:12 to 25:50");
- STALE-VALUE — the deciding sentence contains a superseded value from the
  question's update chain and no gold value;
- OTHER       — the deciding sentence contains a same-shape value that is
  neither (wrong value from elsewhere), or no sentence contains any
  chain-relevant value (abstention, refusal, ...).

The stale-pick rate is STALE-VALUE / questions-with-extractable-chain. A
chain is "extractable" when at least one gold value and at least one
same-shape stale value were recovered from the evidence turns; questions
where extraction fails are reported separately (``no_chain``) and excluded
from the denominator, so the metric's own coverage is always visible.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence

from longmemeval.compare_runs import dedupe_last, read_jsonl_records
from longmemeval.dataset import LongMemEvalQuestion, load_dataset


# --------------------------------------------------------------------------
# Value extraction
# --------------------------------------------------------------------------

_STOPWORDS = frozenset(
    """a an and are as at be but by did do does for from had has have he her his how i in is it its
    me my of on or our she so that the their them they this to was we were what when where which who
    whom why will with you your yes no not now am pm o'clock too also very
    likely probably approximately about""".split()
)

# Question words that carry no anchoring power for proximity matching.
_GENERIC_QUESTION_WORDS = frozenset(
    """what when where which who how many much most recent recently currently often long time times
    day week month year today number amount kind type still initially latest last first new old
    same each every per does need reach spent spend own use using""".split()
)

_WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "twice": 2,
}

_WEEKDAYS = {
    "monday": "mon", "tuesday": "tue", "wednesday": "wed", "thursday": "thu",
    "friday": "fri", "saturday": "sat", "sunday": "sun",
}

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

_ENTITY_SKIP = frozenset(
    """i i'm i've i'll i'd the a an my your that this it it's he she they we you yes no monday tuesday
    wednesday thursday friday saturday sunday january february march april may june july august
    september october november december ok okay ai since if when while after before during although
    though because so but and or as however therefore additionally also note remember thanks hello
    hey based given according""".split()
)

_NUMBER_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b")
_WORD_NUMBER_RE = re.compile(r"\b(" + "|".join(sorted(_WORD_NUMBERS)) + r")\b", re.IGNORECASE)
_SLASH_DATE_RE = re.compile(r"\b\d{4}/(\d{1,2})/(\d{1,2})\b")
_PAIR_RE = re.compile(r"\b(\d{1,2}):([0-5]\d)\b")
_MIN_SEC_RE = re.compile(
    r"\b(\d{1,3})\s*(?:minutes?|mins?)\s*(?:and\s+)?(\d{1,2})\s*(?:seconds?|secs?)\b", re.IGNORECASE
)
_HR_MIN_RE = re.compile(
    r"\b(\d{1,3})\s*(?:hours?|hrs?)\s*(?:and\s+)?(\d{1,2})\s*(?:minutes?|mins?)\b", re.IGNORECASE
)
_MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(k)?\b", re.IGNORECASE)
_MONEY_WORD_RE = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\s+dollars\b", re.IGNORECASE)
_WEEKDAY_RE = re.compile(r"\b(" + "|".join(sorted(_WEEKDAYS)) + r")s?\b", re.IGNORECASE)
_MONTH_DAY_RE = re.compile(
    r"\b(" + "|".join(sorted(_MONTHS)) + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.IGNORECASE
)
_RANGE_RE = re.compile(r"\b(\d+)\s*[-–]\s*(\d+)\s*(?:[a-z]{0,4})\b", re.IGNORECASE)
_ENTITY_RE = re.compile(r"\b([A-Z][a-zA-Z'’]+(?:\s+[A-Z][a-zA-Z'’]+)*)\b")
_WORD_RE = re.compile(r"[a-z']+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def _canonical_number(raw: str) -> str:
    cleaned = raw.replace(",", "")
    if "." in cleaned:
        cleaned = cleaned.rstrip("0").rstrip(".")
    return cleaned or "0"


def _is_year_like(canonical: str) -> bool:
    try:
        number = float(canonical)
    except ValueError:
        return False
    return number == int(number) and 1900 <= number <= 2100


@dataclass(frozen=True, slots=True)
class Value:
    """One normalized value occurrence in a text."""

    family: str  # "num" | "pair" | "money" | "day" | "date" | "ent" | "phrase"
    canonical: str
    surface: str
    position: int  # character offset of the occurrence, for proximity checks


def extract_values(text: str, *, assume_phrase: bool = False) -> list[Value]:
    """Extract every typed value occurrence from ``text`` (all families).

    ``assume_phrase=True`` treats the text as a bare noun phrase (a dataset
    answer string like "Kansas City Masterpiece"), so leading capitalized
    words are never discarded as sentence-initial noise.
    """
    values: list[Value] = []
    consumed: list[tuple[int, int]] = []

    def claim(match: re.Match[str]) -> bool:
        span = match.span()
        for start, end in consumed:
            if span[0] < end and span[1] > start:
                return False
        consumed.append(span)
        return True

    for match in _SLASH_DATE_RE.finditer(text):
        if not claim(match):
            continue
        values.append(
            Value("date", f"date:{int(match.group(1))}:{int(match.group(2))}", match.group(0), match.start())
        )
    for pattern in (_MIN_SEC_RE, _HR_MIN_RE, _PAIR_RE):
        for match in pattern.finditer(text):
            if not claim(match):
                continue
            a, b = int(match.group(1)), int(match.group(2))
            values.append(Value("pair", f"pair:{a}:{b:02d}", match.group(0), match.start()))
    for pattern in (_MONEY_RE, _MONEY_WORD_RE):
        for match in pattern.finditer(text):
            if not claim(match):
                continue
            canonical = _canonical_number(match.group(1))
            if pattern is _MONEY_RE and match.group(2):
                canonical = _canonical_number(str(int(float(canonical) * 1000)))
            values.append(Value("money", f"money:{canonical}", match.group(0), match.start()))
    for match in _MONTH_DAY_RE.finditer(text):
        if not claim(match):
            continue
        month = _MONTHS[match.group(1).lower()]
        values.append(Value("date", f"date:{month}:{int(match.group(2))}", match.group(0), match.start()))
    for match in _WEEKDAY_RE.finditer(text):
        values.append(Value("day", f"day:{_WEEKDAYS[match.group(1).lower()]}", match.group(0), match.start()))
    for match in _RANGE_RE.finditer(text):
        if not claim(match):
            continue
        low, high = _canonical_number(match.group(1)), _canonical_number(match.group(2))
        if _is_year_like(low) or _is_year_like(high):
            continue
        values.append(Value("num", f"range:{low}:{high}", match.group(0), match.start()))
        values.append(Value("num", f"num:{low}", match.group(1), match.start()))
        values.append(Value("num", f"num:{high}", match.group(2), match.start()))
    for match in _NUMBER_RE.finditer(text):
        if not claim(match):
            continue
        canonical = _canonical_number(match.group(0))
        if _is_year_like(canonical):
            continue
        values.append(Value("num", f"num:{canonical}", match.group(0), match.start()))
    for match in _WORD_NUMBER_RE.finditer(text):
        number = _WORD_NUMBERS[match.group(1).lower()]
        values.append(Value("num", f"num:{number}", match.group(0), match.start()))
    for match in _ENTITY_RE.finditer(text):
        words = match.group(1).split()
        start_offset = match.start()
        while words and words[0].lower() in _ENTITY_SKIP:
            start_offset += len(words[0]) + 1
            words = words[1:]
        if not words:
            continue
        # A lone sentence-initial capitalized word ("Therefore", "Adding") is
        # indistinguishable from a proper noun without a lexicon: drop it.
        # Multi-word runs ("Kansas City Masterpiece") are kept even there.
        if len(words) == 1 and not assume_phrase and _looks_sentence_initial(text, start_offset):
            continue
        cleaned = " ".join(words)
        if cleaned.lower() in _ENTITY_SKIP or len(cleaned) < 3:
            continue
        values.append(Value("ent", f"ent:{cleaned.lower()}", cleaned, start_offset))
    return values


def _looks_sentence_initial(text: str, position: int) -> bool:
    index = position - 1
    while index >= 0 and text[index] in " \t\"'“‘(*#":
        index -= 1
    return index < 0 or text[index] in ".!?\n:;-"


def _content_words(text: str) -> tuple[str, ...]:
    words = _WORD_RE.findall(text.lower())
    return tuple(w for w in words if len(w) >= 3 and w not in _STOPWORDS)


def question_keywords(question: str) -> tuple[str, ...]:
    """Content words of the question that can anchor proximity matching."""
    return tuple(
        w for w in _content_words(question) if w not in _GENERIC_QUESTION_WORDS and len(w) >= 4
    )


def _keyword_positions(text: str, keywords: Sequence[str]) -> list[int]:
    positions: list[int] = []
    lowered = text.lower()
    for keyword in keywords:
        stem = keyword.rstrip("s") or keyword
        for match in re.finditer(re.escape(stem), lowered):
            positions.append(match.start())
    return positions


_PROXIMITY_RADIUS = 160  # characters


def _near_any(position: int, anchor_positions: Sequence[int], radius: int = _PROXIMITY_RADIUS) -> bool:
    return any(abs(position - anchor) <= radius for anchor in anchor_positions)


def _phrase_present(text: str, phrase: str) -> bool:
    """Word-bounded, case-insensitive containment; final word may vary in number."""
    stem = re.escape(phrase.lower().rstrip("s") or phrase.lower())
    return re.search(rf"\b{stem}s?\b", text.lower()) is not None


def _word_sets_nested(a: str, b: str) -> bool:
    """True when one phrase's word set contains the other's."""
    words_a, words_b = set(a.lower().split()), set(b.lower().split())
    return words_a <= words_b or words_b <= words_a


# --------------------------------------------------------------------------
# Update-chain extraction (dataset side)
# --------------------------------------------------------------------------

# Families whose shape is specific enough to trust anywhere in an evidence
# turn; the noisier families additionally require proximity to a question
# keyword before a value is accepted as part of the update chain.
_PROXIMITY_FAMILIES = frozenset({"num", "ent", "date"})


@dataclass(frozen=True, slots=True)
class UpdateChain:
    question_id: str
    question_type: str
    gold_values: tuple[Value, ...]
    stale_values: tuple[Value, ...]
    phrase_gold: tuple[str, ...] = ()  # all-words fallback for untyped answers

    @property
    def extractable(self) -> bool:
        return bool(self.gold_values or self.phrase_gold) and bool(self.stale_values)

    @property
    def families(self) -> frozenset[str]:
        typed = frozenset(value.family for value in self.gold_values)
        if typed:
            return typed
        return frozenset({"ent"}) if self.phrase_gold else frozenset()


def extract_gold_values(answer: str) -> tuple[tuple[Value, ...], tuple[str, ...]]:
    """Typed gold values from the answer string, plus a phrase fallback."""
    typed = tuple(extract_values(answer, assume_phrase=True))
    if typed:
        return typed, ()
    return (), _content_words(answer)


def build_update_chain(question: LongMemEvalQuestion) -> UpdateChain:
    """Extract the (gold, stale) value chain from a question's evidence turns."""
    gold_values, phrase_gold = extract_gold_values(question.answer)
    gold_canonicals = _expanded_canonicals(gold_values)
    gold_entity_phrases = [v.surface for v in gold_values if v.family == "ent"]
    keywords = question_keywords(question.question)
    answer_ids = set(question.answer_session_ids)
    question_lower = question.question.lower()
    families = frozenset(v.family for v in gold_values) or (frozenset({"ent"}) if phrase_gold else frozenset())

    stale: dict[str, Value] = {}
    for session_id, _date, turns in question.sessions_with_metadata():
        if session_id not in answer_ids:
            continue
        for turn in turns:
            if not turn.has_answer:
                continue
            anchors = _keyword_positions(turn.content, keywords)
            for value in extract_values(turn.content):
                if value.family not in families:
                    continue
                if value.canonical in gold_canonicals:
                    continue
                if value.family in _PROXIMITY_FAMILIES and not _near_any(value.position, anchors):
                    continue
                if value.family == "ent":
                    if value.surface.lower() in question_lower:
                        continue
                    # Skip gold-equivalent entity variants ("Kansas City
                    # Masterpiece BBQ" vs gold "Kansas City Masterpiece").
                    if any(_word_sets_nested(value.surface, gold) for gold in gold_entity_phrases):
                        continue
                    if phrase_gold and set(value.surface.lower().split()) & set(phrase_gold):
                        continue
                stale.setdefault(value.canonical, value)
    return UpdateChain(
        question_id=question.question_id,
        question_type=question.question_type,
        gold_values=gold_values,
        stale_values=tuple(stale[key] for key in sorted(stale)),
        phrase_gold=phrase_gold,
    )


def _expanded_canonicals(values: Iterable[Value]) -> frozenset[str]:
    """Canonicals plus range endpoints, so '10-12 hours' matches '10' or '12'."""
    out: set[str] = set()
    for value in values:
        out.add(value.canonical)
        if value.canonical.startswith("range:"):
            _, low, high = value.canonical.split(":")
            out.add(f"num:{low}")
            out.add(f"num:{high}")
    return frozenset(out)


def build_chains(
    questions: Iterable[LongMemEvalQuestion],
    *,
    question_types: Sequence[str] = ("knowledge-update",),
) -> dict[str, UpdateChain]:
    """Chains for every non-abstention question of the requested types."""
    wanted = set(question_types)
    chains: dict[str, UpdateChain] = {}
    for question in questions:
        if question.question_type not in wanted or question.is_abstention:
            continue
        chains[question.question_id] = build_update_chain(question)
    return chains


# --------------------------------------------------------------------------
# Hypothesis classification (run side)
# --------------------------------------------------------------------------

GOLD = "gold"
STALE = "stale"
OTHER = "other"
NO_CHAIN = "no-chain"


def _gold_in(text: str, chain: UpdateChain) -> bool:
    canonicals = _expanded_canonicals(v for v in chain.gold_values if v.family != "ent")
    if canonicals & _expanded_canonicals(extract_values(text)):
        return True
    for value in chain.gold_values:
        if value.family == "ent" and _phrase_present(text, value.surface):
            return True
    if chain.phrase_gold and all(_phrase_present(text, word) for word in chain.phrase_gold):
        return True
    return False


def _stale_in(text: str, chain: UpdateChain) -> bool:
    canonicals = frozenset(v.canonical for v in chain.stale_values if v.family != "ent")
    if canonicals & _expanded_canonicals(extract_values(text)):
        return True
    return any(
        _phrase_present(text, value.surface) for value in chain.stale_values if value.family == "ent"
    )


def _family_value_in(text: str, families: frozenset[str]) -> bool:
    return any(value.family in families for value in extract_values(text))


def classify_hypothesis(hypothesis: str, chain: UpdateChain) -> str:
    """Conclusion-first classification; see the module docstring for the rule."""
    if not chain.extractable:
        return NO_CHAIN
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(hypothesis) if s.strip()]
    for sentence in reversed(sentences):
        if _gold_in(sentence, chain):
            return GOLD
        if _stale_in(sentence, chain):
            return STALE
        if _family_value_in(sentence, chain.families):
            return OTHER
    return OTHER


# --------------------------------------------------------------------------
# Checkpoint replay
# --------------------------------------------------------------------------

@dataclass(slots=True)
class RunStalePickReport:
    label: str
    considered: int = 0  # questions of the requested types present in the run
    no_chain: int = 0
    classified: int = 0
    gold: int = 0
    stale: int = 0
    other: int = 0
    stale_and_judged_correct: int = 0
    gold_and_judged_wrong: int = 0
    judged: int = 0
    per_question: list[dict[str, object]] = field(default_factory=list)

    @property
    def stale_pick_rate(self) -> float | None:
        return round(self.stale / self.classified, 4) if self.classified else None

    def to_record(self) -> dict[str, object]:
        return {
            "label": self.label,
            "considered": self.considered,
            "no_chain": self.no_chain,
            "classified": self.classified,
            "gold": self.gold,
            "stale": self.stale,
            "other": self.other,
            "stale_pick_rate": self.stale_pick_rate,
            "judged": self.judged,
            "stale_and_judged_correct": self.stale_and_judged_correct,
            "gold_and_judged_wrong": self.gold_and_judged_wrong,
            "schema": "longmemeval_stale_pick_v1",
        }


def replay_checkpoint(
    checkpoint_path: Path,
    chains: Mapping[str, UpdateChain],
    *,
    label: str | None = None,
    keep_per_question: bool = False,
) -> RunStalePickReport:
    """Score one checkpoint JSONL against pre-built update chains."""
    report = RunStalePickReport(label=label or str(checkpoint_path))
    records = dedupe_last(read_jsonl_records(checkpoint_path))
    for question_id in sorted(records):
        chain = chains.get(question_id)
        if chain is None:
            continue
        record = records[question_id]
        hypothesis = record.get("hypothesis")
        if not isinstance(hypothesis, str) or record.get("status") not in (None, "ok"):
            continue
        report.considered += 1
        verdict = classify_hypothesis(hypothesis, chain)
        judge = record.get("judge")
        judged_correct: bool | None = None
        if isinstance(judge, Mapping) and isinstance(judge.get("correct"), bool):
            judged_correct = bool(judge["correct"])
        if verdict == NO_CHAIN:
            report.no_chain += 1
        else:
            report.classified += 1
            if verdict == GOLD:
                report.gold += 1
            elif verdict == STALE:
                report.stale += 1
            else:
                report.other += 1
            if judged_correct is not None:
                report.judged += 1
                if verdict == STALE and judged_correct:
                    report.stale_and_judged_correct += 1
                if verdict == GOLD and not judged_correct:
                    report.gold_and_judged_wrong += 1
        if keep_per_question:
            report.per_question.append(
                {
                    "question_id": question_id,
                    "question_type": chain.question_type,
                    "verdict": verdict,
                    "judged_correct": judged_correct,
                    "gold_values": [v.canonical for v in chain.gold_values] + list(chain.phrase_gold),
                    "stale_values": [v.canonical for v in chain.stale_values],
                }
            )
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

_TABLE_HEADER = (
    f"{'run':<44} {'n':>4} {'chain':>5} {'gold':>5} {'stale':>5} {'other':>5} {'stale-rate':>10}"
)


def render_table(reports: Sequence[RunStalePickReport]) -> str:
    lines = [_TABLE_HEADER, "-" * len(_TABLE_HEADER)]
    for report in reports:
        rate = f"{report.stale_pick_rate:.4f}" if report.stale_pick_rate is not None else "n/a"
        lines.append(
            f"{report.label:<44} {report.considered:>4} {report.classified:>5} "
            f"{report.gold:>5} {report.stale:>5} {report.other:>5} {rate:>10}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stale_pick",
        description="Judge-free stale-pick metric: replay run checkpoints against dataset update chains.",
    )
    parser.add_argument("--dataset", type=Path, required=True, help="LongMemEval dataset JSON file")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        action="append",
        required=True,
        help="checkpoint JSONL to replay (repeatable)",
    )
    parser.add_argument(
        "--question-type",
        action="append",
        default=None,
        help="dataset question_type slice(s) to score (default: knowledge-update)",
    )
    parser.add_argument("--label", action="append", default=None, help="label per checkpoint (repeatable)")
    parser.add_argument("--json", type=Path, default=None, help="also write reports as JSON")
    parser.add_argument("--per-question", action="store_true", help="include per-question rows in --json output")
    args = parser.parse_args(argv)

    labels = args.label or []
    if labels and len(labels) != len(args.checkpoint):
        parser.error("--label must be given once per --checkpoint")
    question_types = tuple(args.question_type or ("knowledge-update",))

    questions = load_dataset(args.dataset)
    chains = build_chains(questions, question_types=question_types)
    reports = [
        replay_checkpoint(
            checkpoint,
            chains,
            label=labels[index] if labels else checkpoint.name if len(args.checkpoint) > 1 else str(checkpoint),
            keep_per_question=args.per_question,
        )
        for index, checkpoint in enumerate(args.checkpoint)
    ]

    print(f"question types: {', '.join(question_types)}; chains extracted: "
          f"{sum(1 for c in chains.values() if c.extractable)}/{len(chains)}")
    print(render_table(reports))
    for report in reports:
        if report.judged:
            print(
                f"  {report.label}: judged={report.judged} "
                f"stale&judged-correct={report.stale_and_judged_correct} "
                f"gold&judged-wrong={report.gold_and_judged_wrong}"
            )

    if args.json is not None:
        payload = {
            "question_types": list(question_types),
            "chains_total": len(chains),
            "chains_extractable": sum(1 for c in chains.values() if c.extractable),
            "runs": [
                {**report.to_record(), **({"per_question": report.per_question} if args.per_question else {})}
                for report in reports
            ],
        }
        args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "GOLD",
    "NO_CHAIN",
    "OTHER",
    "STALE",
    "RunStalePickReport",
    "UpdateChain",
    "Value",
    "build_chains",
    "build_update_chain",
    "classify_hypothesis",
    "extract_gold_values",
    "extract_values",
    "main",
    "question_keywords",
    "render_table",
    "replay_checkpoint",
]
