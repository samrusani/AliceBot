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
import sys

import pytest

_EVAL_DIR = Path(__file__).resolve().parent.parent
_API_SRC = _EVAL_DIR.parent / "apps" / "api" / "src"
for _path in (_EVAL_DIR, _API_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from longmemeval import adapter, chat, coverage_probe, judge, runner  # noqa: E402
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


# -- judge protocol --------------------------------------------------------------


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


def test_context_block_respects_char_budget(tmp_path: Path) -> None:
    question = load_dataset(SYNTHETIC_FIXTURE_PATH)[0]
    with adapter.question_run(question, tmp_path / "q.sqlite3") as run:
        run.ingest()
        small = run.retrieve(max_items=8, context_char_budget=600)
        large = run.retrieve(max_items=8, context_char_budget=20_000)
    assert small.context_chars <= 600
    assert small.context_chars < large.context_chars


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
