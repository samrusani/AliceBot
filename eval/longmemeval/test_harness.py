"""Tests for the LongMemEval harness — model-free and network-free.

Deliberately NOT under ``tests/unit`` so the main suite stays service-free
and this file can exercise real SQLite ingestion + retrieval end-to-end.

Run from the repo root:

    .venv/bin/python -m pytest eval/longmemeval/test_harness.py -q

Covers prompt construction, judge parsing, checkpoint/resume logic,
aggregation math, and the full dry-run pipeline (real ``vnext_capture``
ingest + ``vnext_retrieval`` context packs against a temp SQLite store)
using the checked-in two-question synthetic fixture.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import pytest

_EVAL_DIR = Path(__file__).resolve().parent.parent
_API_SRC = _EVAL_DIR.parent / "apps" / "api" / "src"
for _path in (_EVAL_DIR, _API_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from longmemeval import adapter, chat, compare_runs, coverage_probe, judge, runner  # noqa: E402
from longmemeval.dataset import (  # noqa: E402
    SYNTHETIC_FIXTURE_PATH,
    LongMemEvalDatasetError,
    load_dataset,
    parse_question,
    resolve_dataset_path,
)
from longmemeval.fetch import LongMemEvalFetchError, sha256_of_file, verify_file  # noqa: E402


@pytest.fixture(autouse=True)
def _no_ambient_model_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests hermetic: no embedding or chat endpoints from the user env."""
    for name in (
        "ALICE_EMBEDDINGS_BASE_URL",
        "ALICE_EMBEDDINGS_MODEL",
        "ALICE_EMBEDDINGS_API_KEY",
        chat.MODEL_BASE_URL_ENV,
        chat.MODEL_NAME_ENV,
        chat.MODEL_API_KEY_ENV,
        chat.JUDGE_BASE_URL_ENV,
        chat.JUDGE_NAME_ENV,
        chat.JUDGE_API_KEY_ENV,
        adapter.CONTEXT_CHAR_BUDGET_ENV,
        adapter.MAX_ITEMS_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


# -- dataset -------------------------------------------------------------------


def test_load_synthetic_fixture() -> None:
    questions = load_dataset(SYNTHETIC_FIXTURE_PATH)
    assert len(questions) == 2
    first, second = questions
    assert first.question_id == "synthetic_1"
    assert first.question_type == "single-session-user"
    assert not first.is_abstention
    assert len(first.haystack_sessions) == len(first.haystack_session_ids) == len(first.haystack_dates) == 3
    assert any(turn.has_answer for session in first.haystack_sessions for turn in session)
    assert second.is_abstention
    assert second.answer_session_ids == ()


def test_load_dataset_respects_limit() -> None:
    questions = load_dataset(SYNTHETIC_FIXTURE_PATH, limit=1)
    assert [question.question_id for question in questions] == ["synthetic_1"]


def test_parse_question_coerces_int_answer() -> None:
    question = parse_question(
        {
            "question_id": "q_int",
            "question_type": "temporal-reasoning",
            "question": "How many days?",
            "answer": 18,
            "question_date": "2023/06/01 (Thu) 10:00",
            "haystack_dates": ["2023/05/01 (Mon) 10:00"],
            "haystack_session_ids": ["s1"],
            "haystack_sessions": [[{"role": "user", "content": "hello"}]],
            "answer_session_ids": ["s1"],
        }
    )
    assert question.answer == "18"


def test_parse_question_rejects_mismatched_haystack_lengths() -> None:
    with pytest.raises(LongMemEvalDatasetError, match="mismatched haystack lengths"):
        parse_question(
            {
                "question_id": "q_bad",
                "question_type": "multi-session",
                "question": "?",
                "answer": "a",
                "question_date": "2023/06/01 (Thu) 10:00",
                "haystack_dates": ["2023/05/01 (Mon) 10:00"],
                "haystack_session_ids": ["s1", "s2"],
                "haystack_sessions": [[{"role": "user", "content": "hello"}]],
                "answer_session_ids": [],
            }
        )


def test_resolve_dataset_path_prefers_cleaned_name(tmp_path: Path) -> None:
    assert resolve_dataset_path("s", data_dir=tmp_path) is None
    legacy = tmp_path / "longmemeval_s.json"
    legacy.write_text("[]", encoding="utf-8")
    assert resolve_dataset_path("s", data_dir=tmp_path) == legacy
    cleaned = tmp_path / "longmemeval_s_cleaned.json"
    cleaned.write_text("[]", encoding="utf-8")
    assert resolve_dataset_path("s", data_dir=tmp_path) == cleaned


# -- session rendering and answer prompt ----------------------------------------


def test_render_session_text_tags_speakers_one_paragraph_per_turn() -> None:
    questions = load_dataset(SYNTHETIC_FIXTURE_PATH)
    session_id, date, turns = next(questions[0].sessions_with_metadata())
    text = adapter.render_session_text(session_id, date, turns)
    paragraphs = text.split("\n\n")
    assert paragraphs[0] == f"Chat session {session_id} on {date}."
    assert paragraphs[1].startswith("[USER]: ")
    assert paragraphs[2].startswith("[ASSISTANT]: ")
    assert len(paragraphs) == 1 + len(turns)


def test_render_session_text_collapses_blank_lines_inside_turns() -> None:
    from longmemeval.dataset import SessionTurn

    turns = (SessionTurn(role="user", content="first line\n\n\nsecond line"),)
    text = adapter.render_session_text("s1", "2023/05/01 (Mon) 10:00", turns)
    assert "\n\n" not in text.split("\n\n", 1)[1]  # single paragraph after the header
    assert "first line\nsecond line" in text


def test_build_answer_prompt_uses_official_template() -> None:
    prompt = adapter.build_answer_prompt(
        context_block="CONTEXT",
        question="What breed is the dog?",
        question_date="2023/06/01 (Thu) 10:00",
    )
    assert prompt == adapter.ANSWER_PROMPT_TEMPLATE.format(
        "CONTEXT", "2023/06/01 (Thu) 10:00", "What breed is the dog?"
    )
    assert prompt.endswith("Answer:")
    cot_prompt = adapter.build_answer_prompt(
        context_block="CONTEXT",
        question="What breed is the dog?",
        question_date="2023/06/01 (Thu) 10:00",
        cot=True,
    )
    assert cot_prompt.endswith("Answer (step by step):")
    assert "step by step" in cot_prompt


def test_build_answer_prompt_placeholder_for_empty_context() -> None:
    prompt = adapter.build_answer_prompt(context_block="  ", question="q", question_date="d")
    assert adapter.EMPTY_CONTEXT_PLACEHOLDER in prompt


def test_answer_prompt_templates_are_byte_identical_to_official() -> None:
    # HONESTY GUARD: the official LongMemEval reading templates must never
    # drift. Validity annotations render inside the history slot's fact
    # lines only; the prompt text itself stays verbatim.
    assert adapter.ANSWER_PROMPT_TEMPLATE == (
        "I will give you several history chats between you and a user. "
        "Please answer the question based on the relevant chat history.\n\n\n"
        "History Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer:"
    )
    assert adapter.ANSWER_PROMPT_TEMPLATE_COT == (
        "I will give you several history chats between you and a user. "
        "Please answer the question based on the relevant chat history. "
        "Answer the question step by step: first extract all the relevant information, "
        "and then reason over the information to get the answer.\n\n\n"
        "History Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer (step by step):"
    )


# -- judge protocol --------------------------------------------------------------


def test_reading_templates_are_byte_frozen() -> None:
    # The official LongMemEval reading templates are byte-frozen: context
    # CONTENT may change (it is retrieval output), instruction text may not.
    assert adapter.ANSWER_PROMPT_TEMPLATE == (
        "I will give you several history chats between you and a user. "
        "Please answer the question based on the relevant chat history.\n\n\n"
        "History Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer:"
    )
    assert adapter.ANSWER_PROMPT_TEMPLATE_COT == (
        "I will give you several history chats between you and a user. "
        "Please answer the question based on the relevant chat history. "
        "Answer the question step by step: first extract all the relevant information, "
        "and then reason over the information to get the answer.\n\n\n"
        "History Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer (step by step):"
    )


def test_get_anscheck_prompt_selects_official_templates() -> None:
    base = judge.get_anscheck_prompt("multi-session", "Q", "A", "R")
    assert base.startswith("I will give you a question, a correct answer, and a response from a model.")
    assert "Question: Q" in base and "Correct Answer: A" in base and "Model Response: R" in base
    assert base.endswith("Answer yes or no only.")

    temporal = judge.get_anscheck_prompt("temporal-reasoning", "Q", "A", "R")
    assert "do not penalize off-by-one errors" in temporal

    update = judge.get_anscheck_prompt("knowledge-update", "Q", "A", "R")
    assert "updated answer is the required answer" in update

    preference = judge.get_anscheck_prompt("single-session-preference", "Q", "A", "R")
    assert "Rubric: A" in preference

    abstention = judge.get_anscheck_prompt("multi-session", "Q", "A", "R", abstention=True)
    assert "unanswerable" in abstention and "Explanation: A" in abstention

    with pytest.raises(judge.LongMemEvalJudgeError):
        judge.get_anscheck_prompt("not-a-type", "Q", "A", "R")


def test_parse_judge_label_matches_official_rule() -> None:
    assert judge.parse_judge_label("Yes")
    assert judge.parse_judge_label("yes.")
    assert judge.parse_judge_label("The answer is YES")
    assert not judge.parse_judge_label("No")
    assert not judge.parse_judge_label("Absolutely not")
    assert not judge.parse_judge_label("")


# -- chat client -----------------------------------------------------------------


def test_parse_chat_completion_payload() -> None:
    text, prompt_tokens, completion_tokens = chat.parse_chat_completion_payload(
        {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
        }
    )
    assert (text, prompt_tokens, completion_tokens) == ("hello", 12, 3)
    with pytest.raises(chat.ChatCompletionError):
        chat.parse_chat_completion_payload({"choices": []})
    with pytest.raises(chat.ChatCompletionError):
        chat.parse_chat_completion_payload({"choices": [{"message": {}}]})


def test_model_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert chat.model_config_from_env() is None
    monkeypatch.setenv(chat.MODEL_BASE_URL_ENV, "https://api.example.test/v1/")
    monkeypatch.setenv(chat.MODEL_NAME_ENV, "test-model")
    config = chat.model_config_from_env()
    assert config is not None
    assert config.base_url == "https://api.example.test/v1"
    assert config.redacted() == {
        "base_url": "https://api.example.test/v1",
        "model": "test-model",
        "api_key_configured": False,
    }
    # Judge falls back to the answer-model envs, overridable per field.
    judge_config = chat.judge_config_from_env()
    assert judge_config is not None and judge_config.model == "test-model"
    monkeypatch.setenv(chat.JUDGE_NAME_ENV, "judge-model")
    judge_config = chat.judge_config_from_env()
    assert judge_config is not None and judge_config.model == "judge-model"


# -- fetch checksums --------------------------------------------------------------


def test_verify_file_checksum(tmp_path: Path) -> None:
    payload = tmp_path / "file.json"
    payload.write_text("[]", encoding="utf-8")
    digest = sha256_of_file(payload)
    assert verify_file(payload, expected_sha256=digest) == digest
    with pytest.raises(LongMemEvalFetchError, match="checksum mismatch"):
        verify_file(payload, expected_sha256="0" * 64)


# -- checkpoint / resume -----------------------------------------------------------


def test_checkpoint_roundtrip_and_resume_filtering(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.jsonl"
    writer = runner.CheckpointWriter(path)
    writer.append({"question_id": "q1", "status": "ok", "mode": "scored"})
    writer.append({"question_id": "q2", "status": "error", "mode": "scored"})
    writer.append({"question_id": "q3", "status": "ok", "mode": "dry_run"})
    writer.append({"question_id": "q1", "status": "error", "mode": "scored"})  # last one wins
    path.open("a", encoding="utf-8").write("not json\n")

    records = runner.load_checkpoint(path)
    assert set(records) == {"q1", "q2", "q3"}
    assert records["q1"]["status"] == "error"
    assert runner.completed_question_ids(records, mode="scored") == set()
    writer.append({"question_id": "q1", "status": "ok", "mode": "scored"})
    records = runner.load_checkpoint(path)
    assert runner.completed_question_ids(records, mode="scored") == {"q1"}
    assert runner.completed_question_ids(records, mode="dry_run") == {"q3"}


def test_load_checkpoint_missing_file(tmp_path: Path) -> None:
    assert runner.load_checkpoint(tmp_path / "missing.jsonl") == {}


# -- aggregation --------------------------------------------------------------------


def _record(
    question_id: str,
    question_type: str,
    *,
    correct: bool | None,
    is_abstention: bool = False,
    status: str = "ok",
) -> dict[str, object]:
    return {
        "question_id": question_id,
        "question_type": question_type,
        "is_abstention": is_abstention,
        "status": status,
        "error": None if status == "ok" else "SomeError: boom",
        "judge": {"correct": correct} if correct is not None else None,
        "retrieval": {
            "retrieval_seconds": 0.05,
            "context_chars": 4_000,
            "approx_context_tokens": 1_000,
            "vector_enabled": False,
        },
        "ingest": {"ingest_seconds": 1.5},
    }


def test_aggregate_records_accuracy_math() -> None:
    records = [
        _record("q1", "multi-session", correct=True),
        _record("q2", "multi-session", correct=False),
        _record("q3", "temporal-reasoning", correct=True),
        _record("q4_abs", "temporal-reasoning", correct=True, is_abstention=True),
        _record("q5", "knowledge-update", correct=None, status="error"),
    ]
    summary = runner.aggregate_records(records)
    assert summary["totals"]["questions"] == 5
    assert summary["totals"]["ok"] == 4
    assert summary["totals"]["errors"] == 1
    assert summary["totals"]["correct"] == 3
    assert summary["totals"]["accuracy"] == 0.75
    assert summary["per_type"]["multi-session"] == {"questions": 2, "correct": 1, "accuracy": 0.5}
    assert summary["per_type"]["temporal-reasoning"]["accuracy"] == 1.0
    assert summary["abstention"] == {"questions": 1, "correct": 1, "accuracy": 1.0}
    assert summary["non_abstention"]["questions"] == 3
    assert summary["failures"] == [{"question_id": "q5", "error": "SomeError: boom"}]
    assert summary["retrieval"]["approx_context_tokens_mean"] == 1_000.0


def test_aggregate_records_empty() -> None:
    summary = runner.aggregate_records([])
    assert summary["totals"] == {"questions": 0, "ok": 0, "errors": 0, "correct": 0, "accuracy": None}
    assert summary["retrieval"]["retrieval_seconds_p50"] is None


# -- excerpt packing ---------------------------------------------------------------

_PACKING_SESSIONS = {
    "src-a": ("session_a", "2023/05/20 (Sat) 14:10"),
    "src-b": ("session_b", "2023/05/01 (Mon) 09:00"),
    "src-c": ("session_c", "2023/06/02 (Fri) 18:30"),
}
_EXCERPT_HEADER_PATTERN = r"\[Session (session_[a-c]) \| ([^|]+) \| excerpt \d+\]"


class _StubChunkStore:
    """Just enough store surface for ``_render_context_block``."""

    def __init__(self, chunks_by_source: dict[str, list[str]]) -> None:
        self._chunks_by_source = chunks_by_source

    def list_source_chunks(self, source_id: str) -> list[dict[str, object]]:
        return [
            {"text": text, "chunk_index": index}
            for index, text in enumerate(self._chunks_by_source.get(source_id, []))
        ]

    def get_source(self, source_id: str) -> dict[str, object] | None:
        if source_id not in _PACKING_SESSIONS:
            return None
        session_id, date = _PACKING_SESSIONS[source_id]
        return {"metadata_json": {"session_id": session_id, "session_date": date}}


def _padded(text: str, length: int = 150) -> str:
    return (text + " " + "lorem ipsum " * 30)[:length]


def _packing_run() -> adapter.QuestionRun:
    """Source A: 10 high-overlap chunks; sources B and C: one relevant chunk each."""
    question = parse_question(
        {
            "question_id": "q_packing",
            "question_type": "multi-session",
            "question": "Did I adopt a golden retriever puppy from the shelter?",
            "answer": "yes",
            "question_date": "2023/07/01 (Sat) 10:00",
            "haystack_dates": ["2023/05/20 (Sat) 14:10"],
            "haystack_session_ids": ["session_a"],
            "haystack_sessions": [[{"role": "user", "content": "hello"}]],
            "answer_session_ids": ["session_a"],
        }
    )
    store = _StubChunkStore(
        {
            "src-a": [
                _padded(f"chunk {index}: adopt the golden retriever puppy near the shelter downtown")
                for index in range(10)
            ],
            "src-b": [_padded("the golden retriever went to training class on Monday morning")],
            "src-c": [_padded("the puppy came home from the shelter and slept all afternoon")],
        }
    )
    return adapter.QuestionRun(question, store)  # type: ignore[arg-type]


def _packing_pack() -> dict[str, object]:
    return {
        "relevant_memories": [],
        "sources": [{"id": "src-a"}, {"id": "src-b"}, {"id": "src-c"}],
    }


def test_render_context_block_guarantees_each_source_an_excerpt() -> None:
    run = _packing_run()
    # Tight budget: roughly three excerpt entries. The old greedy-by-score
    # packer would spend all of it on source A's high-overlap chunks.
    block, excerpt_count = run._render_context_block(_packing_pack(), budget=700)
    headers = re.findall(_EXCERPT_HEADER_PATTERN, block)
    assert excerpt_count == len(headers) == 3
    sessions = [session_id for session_id, _date in headers]
    assert sessions.count("session_b") == 1
    assert sessions.count("session_c") == 1
    assert sessions.count("session_a") == 1
    # Rendered oldest-session-first regardless of retrieval rank.
    dates = [date.strip() for _session_id, date in headers]
    assert dates == sorted(dates)
    assert sessions == ["session_b", "session_a", "session_c"]


def test_render_context_block_spends_leftover_budget_by_score() -> None:
    run = _packing_run()
    block, excerpt_count = run._render_context_block(_packing_pack(), budget=1_500)
    headers = re.findall(_EXCERPT_HEADER_PATTERN, block)
    assert excerpt_count == len(headers)
    sessions = [session_id for session_id, _date in headers]
    # B and C still hold their guaranteed excerpt; the leftover budget goes
    # to A's next-best chunks (highest overlap globally).
    assert sessions.count("session_b") == 1
    assert sessions.count("session_c") == 1
    assert sessions.count("session_a") >= 2
    dates = [date.strip() for _session_id, date in headers]
    assert dates == sorted(dates)
    # Determinism: identical inputs render the identical block.
    repeat_block, repeat_count = run._render_context_block(_packing_pack(), budget=1_500)
    assert (repeat_block, repeat_count) == (block, excerpt_count)


def test_render_context_block_appends_validity_annotations_to_fact_lines() -> None:
    run = _packing_run()
    pack = {
        "relevant_memories": [
            {
                "canonical_text": "The user's favorite color is green.",
                "metadata_json": {"source_id": "src-a"},
                "validity": {
                    "supersedes_memory_id": "mem-old",
                    "corrected_at": "2023-08-01T00:00:00+00:00",
                },
            },
            {
                "canonical_text": "The user's favorite color is blue.",
                "metadata_json": {"source_id": "src-b"},
                "validity": {"superseded": True, "superseded_by_memory_id": "mem-new"},
            },
            {
                "canonical_text": "The gym membership offer lasts the summer.",
                "metadata_json": {"source_id": "src-c"},
                "validity": {
                    "valid_from": "2023-05-30T00:00:00+00:00",
                    "valid_to": "2023-08-01T00:00:00+00:00",
                },
            },
            {
                "canonical_text": "The user lives in Denver.",
                "metadata_json": {"source_id": "src-a"},
            },
        ],
        "sources": [],
    }

    block, _excerpt_count = run._render_context_block(pack, budget=4_000)

    lines = block.splitlines()
    assert lines[0] == "### Facts Alice remembers (with session dates):"
    assert lines[1].endswith("The user's favorite color is green. [updated 2023-08-01; supersedes an earlier value]")
    assert lines[2].endswith("The user's favorite color is blue. [superseded by a newer entry]")
    assert lines[3].endswith("The gym membership offer lasts the summer. [valid 2023-05-30 → 2023-08-01]")
    # No annotation, no suffix: the plain fact line is byte-identical to the
    # pre-validity rendering.
    assert lines[4].endswith("The user lives in Denver.")


def test_validity_suffix_is_empty_without_annotation() -> None:
    assert adapter._validity_suffix({"canonical_text": "plain"}) == ""
    assert adapter._validity_suffix({"validity": {}}) == ""
    assert adapter._validity_suffix({"validity": "not-a-dict"}) == ""


def test_validity_suffix_formats_each_annotation_shape_compactly() -> None:
    assert adapter._validity_suffix(
        {"validity": {"valid_to": "2023-08-01T00:00:00+00:00"}}
    ) == " [valid until 2023-08-01]"
    assert adapter._validity_suffix(
        {"validity": {"valid_from": "2023-05-30T00:00:00+00:00"}}
    ) == " [valid from 2023-05-30]"
    # In-place correction: the shown text is current; the date says since when.
    assert adapter._validity_suffix(
        {"validity": {"corrected_at": "2023-08-01T00:00:00+00:00"}}
    ) == " [corrected 2023-08-01]"
    # A superseded row never renders as merely "corrected".
    assert adapter._validity_suffix(
        {
            "validity": {
                "superseded": True,
                "superseded_by_memory_id": "mem-new",
                "corrected_at": "2023-08-01T00:00:00+00:00",
            }
        }
    ) == " [superseded by a newer entry]"
    # Replacement rows fall back to their created_at for the update date.
    assert adapter._validity_suffix(
        {
            "created_at": "2023-08-02T09:00:00Z",
            "validity": {"supersedes_memory_id": "mem-old"},
        }
    ) == " [updated 2023-08-02; supersedes an earlier value]"
    assert adapter._validity_suffix(
        {"validity": {"supersedes_memory_id": "mem-old"}}
    ) == " [supersedes an earlier value]"
    # Window plus supersession state compose in one bracket.
    assert adapter._validity_suffix(
        {
            "validity": {
                "valid_from": "2023-05-30T00:00:00+00:00",
                "valid_to": "2023-08-01T00:00:00+00:00",
                "superseded": True,
            }
        }
    ) == " [valid 2023-05-30 → 2023-08-01; superseded by a newer entry]"
def test_render_context_block_appends_grounding_note_within_budget() -> None:
    run = _packing_run()
    pack = _packing_pack() | {
        "grounding": {"unsupported_entities": ["Marcus Chen", "Sapiens"], "checked": 3}
    }
    budget = 700
    block, _excerpt_count = run._render_context_block(pack, budget=budget)
    # A factual retrieval statistic, one line per unsupported entity,
    # rendered after the excerpts it summarizes.
    assert 'Note: no stored memories mention "Marcus Chen".' in block
    assert block.rstrip().endswith('Note: no stored memories mention "Sapiens".')
    assert block.index("### Retrieved chat history excerpts:") < block.index("Note: no stored")
    # The note's cost is reserved up front, so the budget still holds.
    assert len(block) <= budget


def test_render_context_block_ignores_absent_or_malformed_grounding() -> None:
    run = _packing_run()
    baseline, _count = run._render_context_block(_packing_pack(), budget=700)
    assert "no stored memories" not in baseline
    malformed, _count = run._render_context_block(
        _packing_pack() | {"grounding": "not-a-dict"}, budget=700
    )
    assert malformed == baseline
# -- query-anchored excerpt windows ---------------------------------------------


class _AnchorStubStore(_StubChunkStore):
    """`_StubChunkStore` with a per-test session map instead of the shared one."""

    def __init__(self, chunks_by_source: dict[str, list[str]], sessions: dict[str, tuple[str, str]]) -> None:
        super().__init__(chunks_by_source)
        self._sessions = sessions

    def get_source(self, source_id: str) -> dict[str, object] | None:
        if source_id not in self._sessions:
            return None
        session_id, date = self._sessions[source_id]
        return {"metadata_json": {"session_id": session_id, "session_date": date}}


def _anchoring_run(
    question_text: str,
    chunks_by_source: dict[str, list[str]],
    sessions: dict[str, tuple[str, str]],
) -> adapter.QuestionRun:
    question = parse_question(
        {
            "question_id": "q_anchor",
            "question_type": "multi-session",
            "question": question_text,
            "answer": "unused",
            "question_date": "2023/07/01 (Sat) 10:00",
            "haystack_dates": ["2023/05/21 (Sun) 13:30"],
            "haystack_session_ids": ["session_stub"],
            "haystack_sessions": [[{"role": "user", "content": "hello"}]],
            "answer_session_ids": ["session_stub"],
        }
    )
    return adapter.QuestionRun(question, _AnchorStubStore(chunks_by_source, sessions))  # type: ignore[arg-type]


def _entry_cost(chunk_text: str, session_id: str, date: str, excerpt_ordinal: int) -> int:
    header = f"[Session {session_id} | {date} | excerpt {excerpt_ordinal}]"
    return len(header) + len(chunk_text) + 3


_CHESS_DATE = "2023/05/21 (Sun) 13:30"
_CHESS_QUESTION = "In our previous chess game, what was the move you made after 27. Kg2 Bd5+?"
_CHESS_FILLER_MOVES = "\n".join(f"{number}. Qd{number % 8 + 1} Rf{number % 8 + 1}" for number in range(1, 27))
_CHESS_CHUNK_0 = (
    f"Chat session session_chess on {_CHESS_DATE}.\n"
    "\n"
    "[USER]: let's keep playing our chess game from last week\n"
    "\n"
    "[ASSISTANT]: Gladly! Here is the full record of our game so far:\n"
    f"{_CHESS_FILLER_MOVES}\n"
    "27. Kg2 Bd5+"
)
_CHESS_CHUNK_1 = (
    "[ASSISTANT]: 28. Kg3 would be my reply here, stepping out of the check.\n"
    "\n"
    "[USER]: nice, that escapes the check cleanly and keeps the pawn shield together\n"
    "\n"
    "[ASSISTANT]: Exactly. From here I would look at rook activity on the open file next."
)


def _chess_run() -> adapter.QuestionRun:
    return _anchoring_run(
        _CHESS_QUESTION,
        {"src-chess": [_CHESS_CHUNK_0, _CHESS_CHUNK_1]},
        {"src-chess": ("session_chess", _CHESS_DATE)},
    )


def _chess_pack() -> dict[str, object]:
    return {"relevant_memories": [], "sources": [{"id": "src-chess"}]}


def test_anchored_excerpt_recovers_late_chess_move(monkeypatch: pytest.MonkeyPatch) -> None:
    """Long move record, query about a late move: the excerpt keeps the reply."""
    run = _chess_run()
    # Tight budget: exactly one guaranteed excerpt, no pass-2 room for chunk 1.
    budget = _entry_cost(_CHESS_CHUNK_0, "session_chess", _CHESS_DATE, 1) + 60
    block, excerpt_count = run._render_context_block(_chess_pack(), budget=budget)
    assert excerpt_count == 1
    assert "27. Kg2 Bd5+" in block  # the anchor line survives
    assert "28. Kg3" in block  # the answer past the chunk boundary is now visible
    # Determinism: identical inputs render the identical block.
    assert run._render_context_block(_chess_pack(), budget=budget) == (block, excerpt_count)
    # Control: the head-biased path (anchoring off) cuts the game at the boundary.
    monkeypatch.setattr(adapter, "_query_anchored_excerpt", lambda *args, **kwargs: None)
    head_block, head_count = run._render_context_block(_chess_pack(), budget=budget)
    assert head_count == 1
    assert "28. Kg3" not in head_block


_LIST_DATE = "2023/05/26 (Fri) 12:40"
_LIST_QUESTION = "What was the 7th job in the list of work from home jobs for seniors you provided?"
_LIST_JOBS = (
    "Customer service representative",
    "Virtual assistant",
    "Bookkeeper",
    "Online tutor",
    "Freelance writer",
    "Survey taker",
    "Transcriptionist",
    "Data entry clerk",
    "Social media manager",
    "Proofreader",
    "Resume writer",
    "Online juror",
)
_LIST_CHUNK_0 = (
    f"Chat session session_list on {_LIST_DATE}.\n"
    "\n"
    "[USER]: I retired last spring and I want something flexible to keep busy\n"
    "\n"
    "[ASSISTANT]: Congratulations! Staying engaged part-time is a great goal.\n"
    "\n"
    "[USER]: please list some work from home jobs for seniors"
)
_LIST_CHUNK_1 = (
    "[ASSISTANT]: Here are some options:\n"
    + "\n".join(f"{number}. {job}" for number, job in enumerate(_LIST_JOBS, start=1))
    + "\n"
    "\n"
    "[USER]: thanks, that gives me plenty of ideas to explore this month"
)


def _list_run() -> adapter.QuestionRun:
    return _anchoring_run(
        _LIST_QUESTION,
        {"src-list": [_LIST_CHUNK_0, _LIST_CHUNK_1]},
        {"src-list": ("session_list", _LIST_DATE)},
    )


def _list_pack() -> dict[str, object]:
    return {"relevant_memories": [], "sources": [{"id": "src-list"}]}


def test_anchored_excerpt_keeps_buried_list_item(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer at item 7 of a 12-item assistant list: the enumeration stays intact."""
    run = _list_run()
    # Room for one guaranteed excerpt plus the enumeration extension, but not
    # for chunk 1 as a whole pass-2 entry.
    budget = _entry_cost(_LIST_CHUNK_0, "session_list", _LIST_DATE, 1) + 260
    block, excerpt_count = run._render_context_block(_list_pack(), budget=budget)
    assert excerpt_count == 1
    assert "7. Transcriptionist" in block
    assert run._render_context_block(_list_pack(), budget=budget) == (block, excerpt_count)
    # Control: with anchoring off the head-biased excerpt never reaches item 7.
    monkeypatch.setattr(adapter, "_query_anchored_excerpt", lambda *args, **kwargs: None)
    head_block, _head_count = run._render_context_block(_list_pack(), budget=budget)
    assert "7. Transcriptionist" not in head_block


def test_head_matched_prose_takes_byte_identical_old_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prose whose match already sits in the best chunk is untouched by anchoring."""
    run = _packing_run()
    for budget in (700, 1_500, 12_000):
        block, excerpt_count = run._render_context_block(_packing_pack(), budget=budget)
        with monkeypatch.context() as patch:
            patch.setattr(adapter, "_query_anchored_excerpt", lambda *args, **kwargs: None)
            old_block, old_count = run._render_context_block(_packing_pack(), budget=budget)
        assert (block, excerpt_count) == (old_block, old_count)


def test_anchoring_preserves_round_robin_guarantee() -> None:
    """An anchored window never costs more than the chunk it replaces, so the
    marginal source keeps its guaranteed excerpt."""
    sessions = {
        "src-chess": ("session_chess", _CHESS_DATE),
        "src-b": ("session_b", "2023/05/01 (Mon) 09:00"),
        "src-c": ("session_c", "2023/06/02 (Fri) 18:30"),
    }
    filler_b = _padded("the golden retriever went to training class on Monday morning")
    filler_c = _padded("the puppy came home from the shelter and slept all afternoon")
    run = _anchoring_run(
        _CHESS_QUESTION,
        {"src-chess": [_CHESS_CHUNK_0, _CHESS_CHUNK_1], "src-b": [filler_b], "src-c": [filler_c]},
        sessions,
    )
    pack = {"relevant_memories": [], "sources": [{"id": "src-chess"}, {"id": "src-b"}, {"id": "src-c"}]}
    budget = (
        _entry_cost(_CHESS_CHUNK_0, "session_chess", _CHESS_DATE, 1)
        + _entry_cost(filler_b, "session_b", "2023/05/01 (Mon) 09:00", 1)
        + _entry_cost(filler_c, "session_c", "2023/06/02 (Fri) 18:30", 1)
        + 10
    )
    block, excerpt_count = run._render_context_block(pack, budget=budget)
    assert excerpt_count >= 3
    assert "28. Kg3" in block  # anchored source shows the answer window
    for session_id in ("session_chess", "session_b", "session_c"):
        assert f"[Session {session_id} " in block  # nobody got evicted


def test_query_anchored_excerpt_gates() -> None:
    terms = frozenset(["chess", "game", "move", "27", "kg2", "bd5", "the", "you"])
    # Single-chunk sources always take the old path.
    assert adapter._query_anchored_excerpt(
        [(0, _CHESS_CHUNK_0)], terms, baseline_chunk_index=0, baseline_text=_CHESS_CHUNK_0
    ) is None
    # No query terms: nothing to anchor on.
    assert adapter._query_anchored_excerpt(
        [(0, _CHESS_CHUNK_0), (1, _CHESS_CHUNK_1)], frozenset(), baseline_chunk_index=0, baseline_text=_CHESS_CHUNK_0
    ) is None
    # Weak stopwordy matches stay below the anchor threshold.
    weak_terms = frozenset(["the", "you"])
    assert adapter._query_anchored_excerpt(
        [(0, _CHESS_CHUNK_0), (1, _CHESS_CHUNK_1)],
        weak_terms,
        baseline_chunk_index=0,
        baseline_text=_CHESS_CHUNK_0,
    ) is None
    # Prose match inside the baseline chunk with no enumeration nearby: old path.
    prose_0 = "[USER]: my dentist appointment in Portland went smoothly yesterday afternoon\n\n[ASSISTANT]: Glad to hear the appointment went well."
    prose_1 = "[USER]: and the follow-up is booked for next month\n\n[ASSISTANT]: Noted."
    prose_terms = frozenset(["dentist", "appointment", "portland"])
    assert adapter._query_anchored_excerpt(
        [(0, prose_0), (1, prose_1)], prose_terms, baseline_chunk_index=0, baseline_text=prose_0
    ) is None
    # Fires when the best-matching line is outside the baseline best chunk.
    anchored = adapter._query_anchored_excerpt(
        [(0, prose_0), (1, prose_1)],
        frozenset(["follow-up", "booked", "month"]),
        baseline_chunk_index=0,
        baseline_text=prose_0,
    )
    assert anchored is not None
    assert "follow-up is booked" in anchored.text
    assert len(anchored.text) <= len(prose_0)


def test_enumeration_signal_shapes() -> None:
    assert adapter._has_enumeration_signal("7. Transcriptionist")
    assert adapter._has_enumeration_signal("27. Kg2 Bd5+")
    assert adapter._has_enumeration_signal("bxc3 exd4 9. cxd4 Bb4 10. Rb1 a5")
    assert not adapter._has_enumeration_signal("[ASSISTANT]: Glad to hear the appointment went well.")
    assert not adapter._has_enumeration_signal("we met at 10.30 in the lobby")  # lone inline number
    assert not adapter._has_enumeration_signal("")


def test_line_anchor_score_weights_distinctive_terms() -> None:
    terms = frozenset(["27", "kg2", "bd5", "move", "the", "previous"])
    assert adapter._line_anchor_score("27. Kg2 Bd5+", terms) == 6  # digit-bearing terms count double
    assert adapter._line_anchor_score("I will make the move now", terms) == 2  # move + the
    assert adapter._line_anchor_score("no overlap here", frozenset()) == 0


def test_reading_templates_byte_frozen() -> None:
    """The official LongMemEval reading templates must never drift."""
    assert adapter.ANSWER_PROMPT_TEMPLATE == (
        "I will give you several history chats between you and a user. "
        "Please answer the question based on the relevant chat history.\n\n\n"
        "History Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer:"
    )
    assert adapter.ANSWER_PROMPT_TEMPLATE_COT == (
        "I will give you several history chats between you and a user. "
        "Please answer the question based on the relevant chat history. "
        "Answer the question step by step: first extract all the relevant information, "
        "and then reason over the information to get the answer.\n\n\n"
        "History Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer (step by step):"
    )


# -- end-to-end (real SQLite ingest + retrieval, no model) ---------------------------


def test_question_run_ingests_and_retrieves_evidence(tmp_path: Path) -> None:
    question = load_dataset(SYNTHETIC_FIXTURE_PATH)[0]
    with adapter.question_run(question, tmp_path / "q.sqlite3") as run:
        stats = run.ingest()
        assert stats.session_count == 3
        assert stats.source_count == 3
        assert stats.chunk_count >= 3
        assert stats.promoted_memory_count == stats.candidate_memory_count
        outcome = run.retrieve(max_items=8, context_char_budget=12_000)
    assert outcome.context_chars > 0
    assert "Biscuit" in outcome.context_block
    assert "golden retriever" in outcome.context_block
    assert "2023/05/20 (Sat) 14:10" in outcome.context_block  # session date visible for temporal questions
    assert not outcome.vector_enabled  # no embedding provider configured in tests
    assert outcome.retrieval_seconds >= 0.0


def test_knowledge_update_shaped_pack_renders_correction_above_annotated_stale_fact(
    tmp_path: Path,
) -> None:
    """Knowledge-update shape through the real adapter and store.

    Value A is committed, correction B supersedes it, but only the pointer
    lands (A's status stays active -- the one-sided state the read path
    cannot filter). The rendered facts section must put B above the
    surviving A, annotate A as superseded, and leave the prompt templates
    untouched.
    """
    question = parse_question(
        {
            "question_id": "q_knowledge_update_shape",
            "question_type": "knowledge-update",
            "question": "What is my favorite color?",
            "answer": "green",
            "question_date": "2023/09/01 (Fri) 10:00",
            "haystack_dates": ["2023/05/01 (Mon) 10:00"],
            "haystack_session_ids": ["s_color"],
            "haystack_sessions": [[{"role": "user", "content": "hello there"}]],
            "answer_session_ids": ["s_color"],
        }
    )
    with adapter.question_run(question, tmp_path / "q.sqlite3") as run:
        run.ingest()
        stale = run.store.create_memory(
            {
                "memory_key": "preference.favorite-color",
                "memory_type": "preference",
                "title": "Favorite color",
                "canonical_text": (
                    "Favorite color: the user's favorite color is blue. "
                    "Favorite color blue came up again while shopping."
                ),
                "status": "active",
                "domain": "unknown",
                "sensitivity": "internal",
                "value": {"text": "favorite color blue"},
            }
        )
        correction = run.store.create_memory(
            {
                "memory_key": "preference.favorite-color.corrected",
                "memory_type": "preference",
                "title": "Favorite color (corrected)",
                "canonical_text": "Correction: the user's favorite color is green now.",
                "status": "active",
                "supersedes": str(stale["id"]),
                "domain": "unknown",
                "sensitivity": "internal",
                "value": {"text": "favorite color green"},
            }
        )
        run.store.update_memory(
            memory_id=str(stale["id"]),
            patch={"superseded_by": str(correction["id"])},
            actor_type="system",
        )
        outcome = run.retrieve(max_items=8, context_char_budget=12_000)

    fact_lines = [line for line in outcome.context_block.splitlines() if line.startswith("- [")]
    green_index = next(i for i, line in enumerate(fact_lines) if "green" in line)
    blue_index = next(i for i, line in enumerate(fact_lines) if "blue" in line)
    assert green_index < blue_index
    assert "supersedes an earlier value" in fact_lines[green_index]
    assert fact_lines[blue_index].endswith("[superseded by a newer entry]")
    # The history slot carries the annotations; the official template around
    # it is still applied verbatim.
    prompt = adapter.build_answer_prompt(
        context_block=outcome.context_block,
        question=question.question,
        question_date=question.question_date,
    )
    assert prompt == adapter.ANSWER_PROMPT_TEMPLATE.format(
        outcome.context_block, question.question_date, question.question
    )


def test_context_block_respects_char_budget(tmp_path: Path) -> None:
    question = load_dataset(SYNTHETIC_FIXTURE_PATH)[0]
    with adapter.question_run(question, tmp_path / "q.sqlite3") as run:
        run.ingest()
        small = run.retrieve(max_items=8, context_char_budget=600)
        large = run.retrieve(max_items=8, context_char_budget=20_000)
    assert small.context_chars <= 600
    assert small.context_chars < large.context_chars


def test_unseen_entity_question_gets_a_grounding_note(tmp_path: Path) -> None:
    # The abstention-shaped scenario: the query names a person the store
    # has never seen, so the block must carry the retrieval statistic.
    question = parse_question(
        {
            "question_id": "q_grounding",
            "question_type": "multi-session",
            "question": "Did Marcus Chen recommend a fertilizer brand for my roses?",
            "answer": "The user never mentioned Marcus Chen.",
            "question_date": "2023/07/01 (Sat) 10:00",
            "haystack_dates": ["2023/05/20 (Sat) 14:10"],
            "haystack_session_ids": ["session_a"],
            "haystack_sessions": [
                [
                    {"role": "user", "content": "My roses keep wilting in the afternoon heat."},
                    {"role": "assistant", "content": "Try watering them at dawn and mulching the beds."},
                ]
            ],
            "answer_session_ids": [],
        }
    )
    with adapter.question_run(question, tmp_path / "q.sqlite3") as run:
        run.ingest()
        outcome = run.retrieve(max_items=8, context_char_budget=12_000)
    assert 'Note: no stored memories mention "Marcus Chen".' in outcome.context_block


def test_supported_entity_question_gets_no_grounding_note(tmp_path: Path) -> None:
    # synthetic_1 asks about Biscuit, who IS in the haystack: no note.
    question = load_dataset(SYNTHETIC_FIXTURE_PATH)[0]
    with adapter.question_run(question, tmp_path / "q.sqlite3") as run:
        run.ingest()
        outcome = run.retrieve(max_items=8, context_char_budget=12_000)
    assert "no stored memories" not in outcome.context_block


def test_runner_dry_run_end_to_end(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    exit_code = runner.main(
        [
            "--dry-run",
            "--dataset-file",
            str(SYNTHETIC_FIXTURE_PATH),
            "--work-dir",
            str(tmp_path / "work"),
            "--checkpoint",
            str(checkpoint_path),
            "--report",
            str(report_path),
            "--workers",
            "1",
        ]
    )
    assert exit_code == runner.EXIT_OK
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema"] == runner.REPORT_SCHEMA
    assert report["totals"] == {"questions": 2, "ok": 2, "errors": 0, "correct": 0, "accuracy": None}
    assert report["config"]["mode"] == "dry_run"
    assert report["config"]["embeddings_enabled"] is False
    records = runner.load_checkpoint(checkpoint_path)
    assert records["synthetic_1"]["retrieval"]["context_chars"] > 0
    assert records["synthetic_2_abs"]["retrieval"]["context_chars"] > 0
    assert not list((tmp_path / "work").glob("*.sqlite3"))  # scratch stores cleaned up

    # Resume: nothing pending, still exits 0 and reports both records.
    exit_code = runner.main(
        [
            "--dry-run",
            "--resume",
            "--dataset-file",
            str(SYNTHETIC_FIXTURE_PATH),
            "--work-dir",
            str(tmp_path / "work"),
            "--checkpoint",
            str(checkpoint_path),
            "--report",
            str(report_path),
        ]
    )
    assert exit_code == runner.EXIT_OK
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["resumed_from_checkpoint"] == 2
    assert report["totals"]["ok"] == 2


# -- coverage probe -------------------------------------------------------------------


def _coverage_question(question_id: str, question_type: str, answer_session_ids: list[str]):
    return parse_question(
        {
            "question_id": question_id,
            "question_type": question_type,
            "question": "What breed is the dog?",
            "answer": "golden retriever",
            "question_date": "2023/06/01 (Thu) 10:00",
            "haystack_dates": ["2023/05/01 (Mon) 10:00"] * 3,
            "haystack_session_ids": ["s1", "s2", "s3"],
            "haystack_sessions": [[{"role": "user", "content": "hello"}]] * 3,
            "answer_session_ids": answer_session_ids,
        }
    )


def test_coverage_row_math() -> None:
    question = _coverage_question("q_cov", "multi-session", ["s1", "s2"])
    # All evidence retrieved (extra retrieved sessions do not hurt).
    row = coverage_probe.coverage_row(question, {"s1", "s2", "s3"})
    assert (row["n_evidence"], row["n_hit"]) == (2, 2)
    assert row["any_coverage"] is True and row["all_coverage"] is True
    assert row["missed_session_ids"] == []
    # Partial: any but not all.
    row = coverage_probe.coverage_row(question, {"s2", "s3"})
    assert (row["n_evidence"], row["n_hit"]) == (2, 1)
    assert row["any_coverage"] is True and row["all_coverage"] is False
    assert row["missed_session_ids"] == ["s1"]
    # Miss: neither.
    row = coverage_probe.coverage_row(question, {"s3"})
    assert row["n_hit"] == 0
    assert row["any_coverage"] is False and row["all_coverage"] is False
    # No evidence ids: coverage undefined, excluded from percentages.
    row = coverage_probe.coverage_row(_coverage_question("q_abs", "multi-session", []), {"s1"})
    assert row["any_coverage"] is None and row["all_coverage"] is None


def test_summarize_rows_per_type_percentages() -> None:
    q_all = _coverage_question("q1", "multi-session", ["s1", "s2"])
    q_partial = _coverage_question("q2", "multi-session", ["s1", "s2"])
    q_miss = _coverage_question("q3", "temporal-reasoning", ["s1"])
    q_unscored = _coverage_question("q4", "temporal-reasoning", [])
    rows = [
        coverage_probe.coverage_row(q_all, {"s1", "s2"}),
        coverage_probe.coverage_row(q_partial, {"s1"}),
        coverage_probe.coverage_row(q_miss, {"s3"}),
        coverage_probe.coverage_row(q_unscored, {"s3"}),
    ]
    summary = coverage_probe.summarize_rows(rows)
    assert summary["overall"] == {"questions": 4, "scored": 3, "any_coverage": 0.6667, "all_coverage": 0.3333}
    assert summary["per_type"]["multi-session"] == {
        "questions": 2,
        "scored": 2,
        "any_coverage": 1.0,
        "all_coverage": 0.5,
    }
    assert summary["per_type"]["temporal-reasoning"] == {
        "questions": 2,
        "scored": 1,
        "any_coverage": 0.0,
        "all_coverage": 0.0,
    }
    table = coverage_probe.format_summary_table(summary)
    assert "multi-session" in table and "overall" in table


def test_coverage_probe_end_to_end_and_store_reuse(tmp_path: Path) -> None:
    work_dir = tmp_path / "stores"
    out_path = tmp_path / "rows.jsonl"
    exit_code = coverage_probe.main(
        [
            "--dataset-file",
            str(SYNTHETIC_FIXTURE_PATH),
            "--work-dir",
            str(work_dir),
            "--out",
            str(out_path),
            "--workers",
            "1",
        ]
    )
    assert exit_code == coverage_probe.EXIT_OK
    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    assert [row["question_id"] for row in rows] == ["synthetic_1", "synthetic_2_abs"]
    first, second = rows
    # synthetic_1's single evidence session (answer_synth_1) is retrieved.
    assert first["n_evidence"] == 1 and first["n_hit"] == 1
    assert first["any_coverage"] is True and first["all_coverage"] is True
    assert first["reused_store"] is False
    assert first["vector_stage"].startswith("disabled")  # keyless FTS-only by default
    # The abstention fixture has no evidence ids: unscored.
    assert second["any_coverage"] is None and second["all_coverage"] is None
    summary = json.loads(out_path.with_suffix(".summary.json").read_text(encoding="utf-8"))
    assert summary["overall"] == {"questions": 2, "scored": 1, "any_coverage": 1.0, "all_coverage": 1.0}
    assert summary["vectors"] == "disabled"

    # Rerun over the same work dir: ingest skipped, identical coverage.
    rerun_path = tmp_path / "rows2.jsonl"
    exit_code = coverage_probe.main(
        [
            "--dataset-file",
            str(SYNTHETIC_FIXTURE_PATH),
            "--work-dir",
            str(work_dir),
            "--out",
            str(rerun_path),
            "--workers",
            "1",
        ]
    )
    assert exit_code == coverage_probe.EXIT_OK
    rerun_rows = [json.loads(line) for line in rerun_path.read_text(encoding="utf-8").splitlines()]
    assert all(row["reused_store"] is True and row["ingest_seconds"] is None for row in rerun_rows)
    volatile = ("reused_store", "ingest_seconds", "retrieval_seconds")
    stable = [{key: value for key, value in row.items() if key not in volatile} for row in rows]
    rerun_stable = [{key: value for key, value in row.items() if key not in volatile} for row in rerun_rows]
    assert rerun_stable == stable  # determinism: same inputs, same coverage numbers


def test_coverage_probe_question_ids_and_limit(tmp_path: Path) -> None:
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text("synthetic_2_abs\n", encoding="utf-8")
    out_path = tmp_path / "rows.jsonl"
    exit_code = coverage_probe.main(
        [
            "--dataset-file",
            str(SYNTHETIC_FIXTURE_PATH),
            "--question-ids",
            str(ids_file),
            "--work-dir",
            str(tmp_path / "stores"),
            "--out",
            str(out_path),
            "--workers",
            "1",
        ]
    )
    assert exit_code == coverage_probe.EXIT_OK
    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    assert [row["question_id"] for row in rows] == ["synthetic_2_abs"]

    exit_code = coverage_probe.main(
        [
            "--dataset-file",
            str(SYNTHETIC_FIXTURE_PATH),
            "--limit",
            "1",
            "--work-dir",
            str(tmp_path / "stores_limit"),
            "--out",
            str(tmp_path / "rows_limit.jsonl"),
            "--workers",
            "1",
        ]
    )
    assert exit_code == coverage_probe.EXIT_OK
    rows = [json.loads(line) for line in (tmp_path / "rows_limit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["question_id"] for row in rows] == ["synthetic_1"]


def test_coverage_probe_missing_dataset(tmp_path: Path) -> None:
    exit_code = coverage_probe.main(
        ["--dataset-file", str(tmp_path / "missing.json"), "--work-dir", str(tmp_path / "stores")]
    )
    assert exit_code == coverage_probe.EXIT_CONFIG_ERROR


def test_runner_dry_run_skips_cleanly_without_dataset(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = runner.main(["--dry-run", "--variant", "s", "--data-dir", str(tmp_path)])
    assert exit_code == runner.EXIT_OK
    assert "dry run skipped cleanly" in capsys.readouterr().out


def test_runner_scored_requires_model_config(tmp_path: Path) -> None:
    exit_code = runner.main(["--dataset-file", str(SYNTHETIC_FIXTURE_PATH), "--work-dir", str(tmp_path)])
    assert exit_code == runner.EXIT_CONFIG_ERROR


# -- --question-ids slicing --------------------------------------------------------


def test_load_question_ids_skips_comments_and_dedupes(tmp_path: Path) -> None:
    ids_file = tmp_path / "slice.txt"
    ids_file.write_text("# header\n\nq1\nq2\n  q1  \n# trailing comment\nq3\n", encoding="utf-8")
    assert runner.load_question_ids(ids_file) == ("q1", "q2", "q3")
    with pytest.raises(ValueError, match="does not exist"):
        runner.load_question_ids(tmp_path / "missing.txt")
    empty = tmp_path / "empty.txt"
    empty.write_text("# only comments\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no question ids"):
        runner.load_question_ids(empty)


def test_question_ids_mutually_exclusive_with_limit(tmp_path: Path) -> None:
    ids_file = tmp_path / "slice.txt"
    ids_file.write_text("q1\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        runner.build_arg_parser().parse_args(["--limit", "3", "--question-ids", str(ids_file)])


def test_runner_question_ids_unknown_id_is_config_error(tmp_path: Path) -> None:
    ids_file = tmp_path / "slice.txt"
    ids_file.write_text("synthetic_1\nnot_a_real_id\n", encoding="utf-8")
    exit_code = runner.main(
        [
            "--dry-run",
            "--dataset-file",
            str(SYNTHETIC_FIXTURE_PATH),
            "--question-ids",
            str(ids_file),
            "--work-dir",
            str(tmp_path / "work"),
            "--checkpoint",
            str(tmp_path / "checkpoint.jsonl"),
            "--report",
            str(tmp_path / "report.json"),
        ]
    )
    assert exit_code == runner.EXIT_CONFIG_ERROR


def test_fingerprint_records_question_subset(tmp_path: Path) -> None:
    def config_with(question_ids: tuple[str, ...] | None) -> runner.RunnerConfig:
        return runner.RunnerConfig(
            variant="s",
            dataset_path=SYNTHETIC_FIXTURE_PATH,
            limit=None,
            question_ids=question_ids,
            question_ids_file="slice.txt" if question_ids else None,
            resume=False,
            dry_run=True,
            cot=False,
            workers=1,
            max_items=8,
            context_char_budget=12_000,
            work_dir=tmp_path,
            checkpoint_path=tmp_path / "c.jsonl",
            report_path=tmp_path / "r.json",
            keep_stores=False,
        )

    full = runner.config_fingerprint(config_with(None), model=None, judge=None)
    sliced = runner.config_fingerprint(config_with(("synthetic_1",)), model=None, judge=None)
    assert full["question_subset"] is None
    assert sliced["question_subset"] == {
        "file": "slice.txt",
        "count": 1,
        "ids_sha256_prefix": sliced["question_subset"]["ids_sha256_prefix"],  # type: ignore[index]
    }
    # A slice run can never masquerade as a full run: the digests differ.
    assert full["digest"] != sliced["digest"]


def test_runner_question_ids_filters_and_resumes(tmp_path: Path) -> None:
    ids_file = tmp_path / "slice.txt"
    ids_file.write_text("# one-question slice\nsynthetic_2_abs\n", encoding="utf-8")
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    report_path = tmp_path / "report.json"
    common = [
        "--dry-run",
        "--dataset-file",
        str(SYNTHETIC_FIXTURE_PATH),
        "--question-ids",
        str(ids_file),
        "--work-dir",
        str(tmp_path / "work"),
        "--checkpoint",
        str(checkpoint_path),
        "--report",
        str(report_path),
        "--workers",
        "1",
    ]
    assert runner.main(common) == runner.EXIT_OK
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["totals"]["questions"] == 1
    assert report["config"]["question_subset"]["count"] == 1
    assert report["config"]["question_subset"]["file"] == "slice.txt"
    records = runner.load_checkpoint(checkpoint_path)
    assert set(records) == {"synthetic_2_abs"}

    # Resume keys on question_id: the completed id is skipped, nothing re-runs.
    assert runner.main([*common, "--resume"]) == runner.EXIT_OK
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["resumed_from_checkpoint"] == 1
    assert report["totals"] == {"questions": 1, "ok": 1, "errors": 0, "correct": 0, "accuracy": None}

    # Widening the slice re-runs only the new id.
    ids_file.write_text("synthetic_2_abs\nsynthetic_1\n", encoding="utf-8")
    assert runner.main([*common, "--resume"]) == runner.EXIT_OK
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["resumed_from_checkpoint"] == 1
    assert report["totals"]["questions"] == 2
    records = runner.load_checkpoint(checkpoint_path)
    assert set(records) == {"synthetic_1", "synthetic_2_abs"}


# -- compare_runs -------------------------------------------------------------------


def test_exact_mcnemar_hand_computed() -> None:
    # b=1, c=5: n=6 discordant, P(X<=1) = (C(6,0)+C(6,1))/2^6 = 7/64; p = 14/64.
    assert compare_runs.exact_mcnemar_p(1, 5) == pytest.approx(14 / 64)
    assert compare_runs.exact_mcnemar_p(5, 1) == pytest.approx(14 / 64)  # symmetric
    # b=0, c=8: p = 2 * C(8,0)/2^8 = 2/256.
    assert compare_runs.exact_mcnemar_p(0, 8) == pytest.approx(2 / 256)
    # Balanced discordance saturates at 1.0 (2 * P(X<=3, n=6) = 84/64 -> capped).
    assert compare_runs.exact_mcnemar_p(3, 3) == 1.0
    assert compare_runs.exact_mcnemar_p(0, 0) == 1.0
    with pytest.raises(ValueError):
        compare_runs.exact_mcnemar_p(-1, 2)


def _result_row(question_id: str, question_type: str, *, correct: bool | None) -> dict[str, object]:
    return {
        "question_id": question_id,
        "question_type": question_type,
        "is_abstention": question_id.endswith("_abs"),
        "status": "ok",
        "judge": {"correct": correct} if correct is not None else None,
    }


def test_dedupe_last_keeps_final_record_per_question_id() -> None:
    rows = [
        _result_row("q1", "multi-session", correct=False),
        _result_row("q2", "multi-session", correct=True),
        _result_row("q1", "multi-session", correct=True),  # re-run after resume: last wins
        {"question_id": "", "judge": {"correct": True}},  # no usable id -> dropped
    ]
    deduped = compare_runs.dedupe_last(rows)
    assert set(deduped) == {"q1", "q2"}
    assert compare_runs.judged_correct(deduped["q1"]) is True


def test_compare_records_flips_types_and_abstention() -> None:
    baseline = compare_runs.dedupe_last(
        [
            _result_row("q1", "multi-session", correct=True),
            _result_row("q2", "multi-session", correct=False),
            _result_row("q3", "temporal-reasoning", correct=False),
            _result_row("q4_abs", "knowledge-update", correct=False),
            _result_row("q5", "knowledge-update", correct=True),
            _result_row("q6", "multi-session", correct=True),  # judged only in baseline
            _result_row("q7", "multi-session", correct=None),  # unjudged -> excluded
        ]
    )
    candidate = compare_runs.dedupe_last(
        [
            _result_row("q1", "multi-session", correct=True),  # both right
            _result_row("q2", "multi-session", correct=True),  # gained
            _result_row("q3", "temporal-reasoning", correct=True),  # gained
            _result_row("q4_abs", "knowledge-update", correct=True),  # gained (abstention)
            _result_row("q5", "knowledge-update", correct=False),  # lost
            _result_row("q7", "multi-session", correct=True),
            _result_row("q8", "multi-session", correct=True),  # candidate-only
        ]
    )
    summary = compare_runs.compare_records(baseline, candidate)
    assert summary["n_compared"] == 5
    assert summary["flips_gained"] == 3
    assert summary["flips_lost"] == 1
    assert summary["net"] == 2
    assert summary["baseline_correct"] == 2
    assert summary["candidate_correct"] == 4
    assert summary["mcnemar_p"] == pytest.approx(compare_runs.exact_mcnemar_p(3, 1))
    assert summary["per_type"]["multi-session"] == {
        "n": 2,
        "baseline_correct": 1,
        "candidate_correct": 2,
        "gained": 1,
        "lost": 0,
        "net": 1,
        "baseline_accuracy": 0.5,
        "candidate_accuracy": 1.0,
    }
    assert summary["abstention"] == {"n": 1, "baseline_correct": 0, "candidate_correct": 1, "delta": 1}


def test_compare_runs_cli_table_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    baseline_path = tmp_path / "baseline.jsonl"
    candidate_path = tmp_path / "candidate.jsonl"
    baseline_rows = [
        _result_row("q1", "multi-session", correct=False),
        _result_row("q1", "multi-session", correct=True),  # dedupe keeps this one
        _result_row("q2_abs", "temporal-reasoning", correct=False),
    ]
    candidate_rows = [
        _result_row("q1", "multi-session", correct=True),
        _result_row("q2_abs", "temporal-reasoning", correct=True),
    ]
    baseline_path.write_text("".join(json.dumps(row) + "\n" for row in baseline_rows), encoding="utf-8")
    candidate_path.write_text("".join(json.dumps(row) + "\n" for row in candidate_rows), encoding="utf-8")

    assert compare_runs.main([str(baseline_path), str(candidate_path)]) == compare_runs.EXIT_OK
    table = capsys.readouterr().out
    assert "compared 2 judged questions" in table
    assert "net +1" in table
    assert "abstention subset: n=1" in table

    assert compare_runs.main([str(baseline_path), str(candidate_path), "--json"]) == compare_runs.EXIT_OK
    summary = json.loads(capsys.readouterr().out)
    assert summary["n_compared"] == 2
    assert summary["flips_gained"] == 1  # q1 dedupe-last means baseline was already right
    assert summary["flips_lost"] == 0

    assert compare_runs.main([str(tmp_path / "nope.jsonl"), str(candidate_path)]) == compare_runs.EXIT_CONFIG_ERROR


# -- stage-1 slice selection ---------------------------------------------------------


def _load_stage1_module():
    import importlib.util

    module_path = Path(__file__).resolve().parent / "slices" / "generate_stage1.py"
    spec = importlib.util.spec_from_file_location("generate_stage1", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stratified_picks_hand_computed() -> None:
    stage1 = _load_stage1_module()
    pool = [f"id{i:02d}" for i in range(10)]
    # n=10, wanted=3 -> k=3 -> indices 0, 3, 6.
    assert stage1.stratified_picks(pool, 3) == ["id00", "id03", "id06"]
    # Input order must not matter: the pool is sorted first.
    assert stage1.stratified_picks(list(reversed(pool)), 3) == ["id00", "id03", "id06"]
    # n == wanted -> k=1 -> the whole sorted pool.
    assert stage1.stratified_picks(["b", "a"], 2) == ["a", "b"]
    with pytest.raises(ValueError, match="pool has 2 ids but 3 were requested"):
        stage1.stratified_picks(["a", "b"], 3)


def test_stage1_selection_deterministic_and_dedupes_abstention() -> None:
    stage1 = _load_stage1_module()
    quotas = (("multi-session", 2), ("temporal-reasoning", 1))
    records = [
        {"question_id": "m1", "question_type": "multi-session"},
        {"question_id": "m2_abs", "question_type": "multi-session"},
        {"question_id": "m3", "question_type": "multi-session"},
        {"question_id": "m4", "question_type": "multi-session"},
        {"question_id": "t1", "question_type": "temporal-reasoning"},
        {"question_id": "t2_abs", "question_type": "temporal-reasoning"},
    ]
    first = stage1.select_stage1_ids(records, quotas=quotas)
    second = stage1.select_stage1_ids(records, quotas=quotas)
    assert first == second  # running selection twice yields identical lists
    shuffled = stage1.select_stage1_ids(list(reversed(records)), quotas=quotas)
    assert shuffled == first  # dataset order must not matter
    # multi-session: sorted pool [m1, m2_abs, m3, m4], k=2 -> m1, m3.
    # temporal: sorted pool [t1, t2_abs], k=2 -> t1. Then all _abs ids, deduped.
    assert first == ("m1", "m3", "t1", "m2_abs", "t2_abs")
    assert len(first) == len(set(first))


def test_checked_in_stage1_slice_matches_dataset() -> None:
    """Regenerating from the real dataset reproduces the checked-in slice exactly."""
    stage1 = _load_stage1_module()
    dataset_path = resolve_dataset_path("s")
    if dataset_path is None:
        pytest.skip("LongMemEval s dataset not fetched")
    records = json.loads(dataset_path.read_text(encoding="utf-8"))
    expected = stage1.render_slice_file(records, dataset_name=dataset_path.name)
    checked_in = stage1.SLICE_PATH.read_text(encoding="utf-8")
    assert checked_in == expected
    ids = runner.load_question_ids(stage1.SLICE_PATH)
    assert len(ids) == len(set(ids))
    abstention_ids = {record["question_id"] for record in records if str(record["question_id"]).endswith("_abs")}
    assert abstention_ids <= set(ids)  # every abstention question is in the slice
