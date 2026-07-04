"""LongMemEval dataset loading and validation.

Dataset format (confirmed against the official repo and the published files,
see docs/plans/longmemeval.md): each variant file is a JSON array of 500
instances with the fields ``question_id``, ``question_type``, ``question``,
``answer``, ``question_date``, ``haystack_dates``, ``haystack_session_ids``,
``haystack_sessions``, and ``answer_session_ids``. Sessions are lists of
``{"role": "user"|"assistant", "content": str}`` turns; evidence turns carry
an extra ``has_answer: true``. A ``question_id`` ending in ``_abs`` marks an
abstention question (the ``answer`` field then holds the explanation the
judge sees). ``answer`` is a string for most instances and an int for 32 of
them, so it is coerced to ``str`` here.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterator, Mapping


HARNESS_DIR = Path(__file__).resolve().parent
DATA_DIR = HARNESS_DIR / "data"
RESULTS_DIR = HARNESS_DIR / "results"
WORK_DIR = HARNESS_DIR / "work"
FIXTURES_DIR = HARNESS_DIR / "fixtures"
SYNTHETIC_FIXTURE_PATH = FIXTURES_DIR / "synthetic_two_questions.json"

VARIANTS = ("s", "m", "oracle")
ABSTENTION_SUFFIX = "_abs"
QUESTION_TYPES = (
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "multi-session",
    "temporal-reasoning",
    "knowledge-update",
)

# Post-2025/09 "cleaned" file names first; the pre-cleanup names are accepted
# for locally present copies of the original release.
_VARIANT_FILENAMES: dict[str, tuple[str, ...]] = {
    "s": ("longmemeval_s_cleaned.json", "longmemeval_s.json", "longmemeval_s"),
    "m": ("longmemeval_m_cleaned.json", "longmemeval_m.json", "longmemeval_m"),
    "oracle": ("longmemeval_oracle.json", "longmemeval_oracle"),
}


class LongMemEvalDatasetError(ValueError):
    """Raised when a dataset file is missing fields or malformed."""


@dataclass(frozen=True, slots=True)
class SessionTurn:
    role: str
    content: str
    has_answer: bool = False


@dataclass(frozen=True, slots=True)
class LongMemEvalQuestion:
    question_id: str
    question_type: str
    question: str
    answer: str
    question_date: str
    haystack_session_ids: tuple[str, ...]
    haystack_dates: tuple[str, ...]
    haystack_sessions: tuple[tuple[SessionTurn, ...], ...]
    answer_session_ids: tuple[str, ...]

    @property
    def is_abstention(self) -> bool:
        return self.question_id.endswith(ABSTENTION_SUFFIX)

    def sessions_with_metadata(self) -> Iterator[tuple[str, str, tuple[SessionTurn, ...]]]:
        """Yield ``(session_id, date, turns)`` triples in haystack order."""
        for session_id, date, turns in zip(self.haystack_session_ids, self.haystack_dates, self.haystack_sessions):
            yield session_id, date, turns


def preferred_dataset_filename(variant: str) -> str:
    if variant not in _VARIANT_FILENAMES:
        raise LongMemEvalDatasetError(f"unknown LongMemEval variant: {variant!r} (expected one of {VARIANTS})")
    return _VARIANT_FILENAMES[variant][0]


def resolve_dataset_path(variant: str, *, data_dir: Path = DATA_DIR) -> Path | None:
    """Locate a downloaded dataset file for ``variant``, or ``None``."""
    if variant not in _VARIANT_FILENAMES:
        raise LongMemEvalDatasetError(f"unknown LongMemEval variant: {variant!r} (expected one of {VARIANTS})")
    for filename in _VARIANT_FILENAMES[variant]:
        candidate = data_dir / filename
        if candidate.is_file():
            return candidate
    return None


def _require_str(record: Mapping[str, object], field_name: str, *, question_index: int) -> str:
    value = record.get(field_name)
    if isinstance(value, (int, float)) and field_name == "answer":
        return str(value)
    if not isinstance(value, str) or value == "":
        raise LongMemEvalDatasetError(
            f"question #{question_index} is missing a non-empty {field_name!r} field"
        )
    return value


def _parse_turn(value: object, *, question_index: int) -> SessionTurn:
    if not isinstance(value, Mapping):
        raise LongMemEvalDatasetError(f"question #{question_index} has a non-object session turn")
    role = value.get("role")
    content = value.get("content")
    return SessionTurn(
        role=str(role) if isinstance(role, str) and role else "unknown",
        content=content if isinstance(content, str) else "",
        has_answer=bool(value.get("has_answer", False)),
    )


def parse_question(record: Mapping[str, object], *, question_index: int = 0) -> LongMemEvalQuestion:
    question_id = _require_str(record, "question_id", question_index=question_index)
    sessions_raw = record.get("haystack_sessions")
    session_ids_raw = record.get("haystack_session_ids")
    dates_raw = record.get("haystack_dates")
    if not isinstance(sessions_raw, list) or not isinstance(session_ids_raw, list) or not isinstance(dates_raw, list):
        raise LongMemEvalDatasetError(
            f"question {question_id!r} is missing haystack_sessions/haystack_session_ids/haystack_dates lists"
        )
    if not (len(sessions_raw) == len(session_ids_raw) == len(dates_raw)):
        raise LongMemEvalDatasetError(
            f"question {question_id!r} has mismatched haystack lengths "
            f"(sessions={len(sessions_raw)}, ids={len(session_ids_raw)}, dates={len(dates_raw)})"
        )
    sessions: list[tuple[SessionTurn, ...]] = []
    for session in sessions_raw:
        if not isinstance(session, list):
            raise LongMemEvalDatasetError(f"question {question_id!r} has a non-list haystack session")
        sessions.append(tuple(_parse_turn(turn, question_index=question_index) for turn in session))
    answer_session_ids = record.get("answer_session_ids")
    return LongMemEvalQuestion(
        question_id=question_id,
        question_type=_require_str(record, "question_type", question_index=question_index),
        question=_require_str(record, "question", question_index=question_index),
        answer=_require_str(record, "answer", question_index=question_index),
        question_date=_require_str(record, "question_date", question_index=question_index),
        haystack_session_ids=tuple(str(session_id) for session_id in session_ids_raw),
        haystack_dates=tuple(str(date) for date in dates_raw),
        haystack_sessions=tuple(sessions),
        answer_session_ids=tuple(str(session_id) for session_id in answer_session_ids)
        if isinstance(answer_session_ids, list)
        else (),
    )


def load_dataset(path: str | Path, *, limit: int | None = None) -> tuple[LongMemEvalQuestion, ...]:
    dataset_path = Path(path)
    try:
        payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise LongMemEvalDatasetError(f"dataset file does not exist: {dataset_path}") from None
    except json.JSONDecodeError as exc:
        raise LongMemEvalDatasetError(f"dataset file is not valid JSON: {dataset_path} ({exc})") from exc
    if not isinstance(payload, list):
        raise LongMemEvalDatasetError(f"dataset file must be a JSON array of questions: {dataset_path}")
    records = payload if limit is None else payload[:limit]
    questions = tuple(
        parse_question(record, question_index=index)
        for index, record in enumerate(records)
        if isinstance(record, Mapping)
    )
    if len(questions) != len(records):
        raise LongMemEvalDatasetError(f"dataset file contains non-object entries: {dataset_path}")
    return questions


__all__ = [
    "ABSTENTION_SUFFIX",
    "DATA_DIR",
    "FIXTURES_DIR",
    "HARNESS_DIR",
    "LongMemEvalDatasetError",
    "LongMemEvalQuestion",
    "QUESTION_TYPES",
    "RESULTS_DIR",
    "SYNTHETIC_FIXTURE_PATH",
    "SessionTurn",
    "VARIANTS",
    "WORK_DIR",
    "load_dataset",
    "parse_question",
    "preferred_dataset_filename",
    "resolve_dataset_path",
]
