from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

import pytest

from alicebot_api.vnext_evals import (
    RETRIEVAL_QUALITY_SUITE_KEY,
    SUBSET_LEXICAL_OVERLAP,
    SUBSET_PARAPHRASE,
    VNEXT_BENCHMARK_EXPECTED_COUNTS,
    VNEXT_EVAL_DATABASE_URL_ENV,
    VNEXT_EVAL_MEMORY_KEY_PREFIX,
    VNEXT_EVAL_SUITE_ORDER,
    eval_token_overlap,
    generate_vnext_benchmark_corpus,
    latency_percentile,
    recall_at_k,
    reciprocal_rank,
    run_retrieval_quality_eval,
    run_vnext_evals,
    seed_retrieval_corpus,
    write_vnext_benchmark_corpus,
    write_vnext_eval_report,
)
from alicebot_api.vnext_retrieval import reciprocal_rank_fusion


@pytest.fixture(autouse=True)
def _clear_eval_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VNEXT_EVAL_DATABASE_URL_ENV, raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)


def _memory_lookup(corpus: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(memory["memory_key"]): memory for memory in corpus["memories"]}


def _perfect_retrieval_fn(corpus: dict[str, object]):
    expected_by_query = {str(query["query"]): str(query["expected_memory_key"]) for query in corpus["queries"]}

    def _retrieve(query: str, *, limit: int) -> dict[str, object]:
        return {
            "ranked_memory_keys": [expected_by_query[query]],
            "vector_stage": "enabled",
        }

    return _retrieve


def _hopeless_retrieval_fn(query: str, *, limit: int) -> dict[str, object]:
    return {"ranked_memory_keys": [], "vector_stage": "enabled"}


# --------------------------------------------------------------------------
# Corpus properties
# --------------------------------------------------------------------------


def test_benchmark_corpus_is_deterministic_and_meets_size_floor() -> None:
    corpus = generate_vnext_benchmark_corpus()

    assert corpus == generate_vnext_benchmark_corpus()
    assert corpus["schema_version"] == "vnext_eval_corpus_v1"
    assert corpus["counts"] == VNEXT_BENCHMARK_EXPECTED_COUNTS
    assert len(corpus["memories"]) >= 200
    assert len(corpus["queries"]) >= 40

    memory_keys = [str(memory["memory_key"]) for memory in corpus["memories"]]
    assert len(memory_keys) == len(set(memory_keys))
    assert all(key.startswith(VNEXT_EVAL_MEMORY_KEY_PREFIX) for key in memory_keys)
    lookup = set(memory_keys)
    assert all(str(query["expected_memory_key"]) in lookup for query in corpus["queries"])

    query_count = len(corpus["queries"])
    paraphrase_count = sum(1 for query in corpus["queries"] if query["subset"] == SUBSET_PARAPHRASE)
    assert 0.20 <= paraphrase_count / query_count <= 0.40


def test_queries_are_phrased_differently_from_their_target_memories() -> None:
    corpus = generate_vnext_benchmark_corpus()
    memories = _memory_lookup(corpus)

    for query in corpus["queries"]:
        target = memories[str(query["expected_memory_key"])]
        target_text = f"{target['canonical_text']} {target['title']}"
        overlap = eval_token_overlap(str(query["query"]), target_text)
        assert str(query["query"]).casefold() != str(target["canonical_text"]).casefold()
        if query["subset"] == SUBSET_PARAPHRASE:
            # Pure paraphrases: near-zero verbatim vocabulary overlap, so
            # lexical search alone should struggle on this subset.
            assert overlap < 0.40, f"{query['query_key']} overlaps too much ({overlap:.2f})"
        else:
            # Reworded but vocabulary-sharing: FTS should still cope.
            assert 0.50 <= overlap <= 0.90, f"{query['query_key']} outside overlap band ({overlap:.2f})"


# --------------------------------------------------------------------------
# Metric math
# --------------------------------------------------------------------------


def test_recall_at_k_and_reciprocal_rank_math() -> None:
    ranked = ["m-2", "m-7", "m-1", "m-9"]

    assert recall_at_k(ranked, "m-2", 1) == 1.0
    assert recall_at_k(ranked, "m-1", 1) == 0.0
    assert recall_at_k(ranked, "m-1", 5) == 1.0
    assert recall_at_k(ranked, "missing", 5) == 0.0
    assert reciprocal_rank(ranked, "m-2") == 1.0
    assert reciprocal_rank(ranked, "m-1") == pytest.approx(1.0 / 3.0)
    assert reciprocal_rank(ranked, "missing") == 0.0
    with pytest.raises(ValueError):
        recall_at_k(ranked, "m-2", 0)


def test_latency_percentile_nearest_rank() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

    assert latency_percentile(values, 50) == 50.0
    assert latency_percentile(values, 95) == 100.0
    assert latency_percentile([42.0], 95) == 42.0
    assert latency_percentile([], 50) == 0.0
    with pytest.raises(ValueError):
        latency_percentile(values, 0)


def test_retrieval_quality_metrics_against_known_rankings() -> None:
    corpus = {
        "queries": [
            {"query_key": "q-1", "query": "alpha", "expected_memory_key": "m-1", "subset": SUBSET_LEXICAL_OVERLAP},
            {"query_key": "q-2", "query": "beta", "expected_memory_key": "m-2", "subset": SUBSET_LEXICAL_OVERLAP},
            {"query_key": "q-3", "query": "gamma", "expected_memory_key": "m-3", "subset": SUBSET_PARAPHRASE},
        ]
    }
    rankings = {
        "alpha": ["m-1", "m-9"],  # rank 1
        "beta": ["m-9", "m-8", "m-2"],  # rank 3
        "gamma": ["m-9", "m-8", "m-7"],  # not found
    }

    def fake_retrieval(query: str, *, limit: int) -> dict[str, object]:
        return {"ranked_memory_keys": rankings[query], "vector_stage": "enabled"}

    suite = run_retrieval_quality_eval(None, retrieval_fn=fake_retrieval, corpus=corpus)

    assert suite["status"] == "fail"  # paraphrase recall 0.0 < 0.70 with vector enabled
    assert suite["metrics"]["query_count"] == 3
    assert suite["metrics"]["recall_at_1"] == pytest.approx(1.0 / 3.0)
    assert suite["metrics"]["recall_at_5"] == pytest.approx(2.0 / 3.0)
    assert suite["metrics"]["mrr"] == pytest.approx((1.0 + 1.0 / 3.0 + 0.0) / 3.0)
    assert suite["metrics"]["retrieval_mode"] == "hybrid"
    assert suite["metrics"]["subsets"][SUBSET_LEXICAL_OVERLAP]["recall_at_5"] == pytest.approx(1.0)
    assert suite["metrics"]["subsets"][SUBSET_PARAPHRASE]["recall_at_5"] == 0.0
    assert suite["metrics"]["target_checks"]["paraphrase_recall_at_5"] == "fail"
    case_statuses = {case["case_key"]: case["status"] for case in suite["cases"]}
    assert case_statuses == {"q-1": "pass", "q-2": "pass", "q-3": "fail"}
    assert all(case["metrics"]["latency_ms"] >= 0.0 for case in suite["cases"])


def test_retrieval_quality_matches_reciprocal_rank_fusion_ordering() -> None:
    # A paraphrase target missed by FTS but ranked first by the vector stage
    # must land at the top after RRF, exactly as the production fusion does.
    fts_rows = [{"id": "m-lex"}, {"id": "m-noise"}]
    vector_rows = [{"id": "m-para"}, {"id": "m-lex"}]
    fused = reciprocal_rank_fusion({"fts": fts_rows, "vector": vector_rows})
    fused_ids = [str(item["id"]) for item, _score, _stages in fused]
    assert fused_ids[0] == "m-lex"  # appears in both stages
    assert "m-para" in fused_ids[:2]

    corpus = {
        "queries": [
            {"query_key": "q-1", "query": "fused", "expected_memory_key": "m-para", "subset": SUBSET_PARAPHRASE},
        ]
    }

    def fused_retrieval(query: str, *, limit: int) -> dict[str, object]:
        return {"ranked_memory_keys": fused_ids[:limit], "vector_stage": "enabled"}

    suite = run_retrieval_quality_eval(None, retrieval_fn=fused_retrieval, corpus=corpus)
    case = suite["cases"][0]

    assert case["metrics"]["recall_at_5"] == 1.0
    assert case["metrics"]["reciprocal_rank"] == pytest.approx(1.0 / (fused_ids.index("m-para") + 1))


def test_paraphrase_target_not_enforced_when_vector_stage_degraded() -> None:
    corpus = {
        "queries": [
            {"query_key": "q-1", "query": "alpha", "expected_memory_key": "m-1", "subset": SUBSET_LEXICAL_OVERLAP},
            {"query_key": "q-2", "query": "gamma", "expected_memory_key": "m-3", "subset": SUBSET_PARAPHRASE},
        ]
    }

    def fts_only_retrieval(query: str, *, limit: int) -> dict[str, object]:
        ranked = ["m-1"] if query == "alpha" else []
        return {"ranked_memory_keys": ranked, "vector_stage": "disabled: no embedding provider configured"}

    suite = run_retrieval_quality_eval(None, retrieval_fn=fts_only_retrieval, corpus=corpus)

    assert suite["metrics"]["retrieval_mode"] == "fts_only"
    assert suite["metrics"]["paraphrase_targets_enforced"] is False
    assert "paraphrase_recall_at_5" not in suite["metrics"]["target_checks"]
    # The degraded paraphrase numbers are still reported, not hidden.
    assert suite["metrics"]["subsets"][SUBSET_PARAPHRASE]["recall_at_5"] == 0.0
    assert suite["status"] == "pass"  # lexical subset met its target


# --------------------------------------------------------------------------
# Skip semantics: no live store means skipped, never a fabricated pass
# --------------------------------------------------------------------------


def test_retrieval_quality_eval_without_store_reports_skipped() -> None:
    suite = run_retrieval_quality_eval(None)

    assert suite["suite_key"] == RETRIEVAL_QUALITY_SUITE_KEY
    assert suite["status"] == "skipped"
    assert "live store" in str(suite["reason"])
    assert suite["cases"] == []


def test_run_vnext_evals_without_live_store_reports_skipped_not_pass() -> None:
    report = run_vnext_evals(suite="all")

    assert report["status"] == "skipped"
    assert report["summary"]["status"] == "skipped"
    assert report["summary"]["executed_suite_count"] == 0
    assert report["summary"]["skipped_suite_count"] == 1
    assert [entry["suite_key"] for entry in report["skipped_suites"]] == [RETRIEVAL_QUALITY_SUITE_KEY]
    assert report["suites"][0]["status"] == "skipped"


# --------------------------------------------------------------------------
# Report semantics and shape compatibility
# --------------------------------------------------------------------------


def test_report_passes_only_when_executed_suites_pass() -> None:
    corpus = generate_vnext_benchmark_corpus()

    passing = run_vnext_evals(suite="all", retrieval_fn=_perfect_retrieval_fn(corpus))
    failing = run_vnext_evals(suite="all", retrieval_fn=_hopeless_retrieval_fn)

    assert passing["status"] == "pass"
    assert passing["summary"]["executed_suite_count"] == 1
    assert passing["summary"]["failed_case_count"] == 0
    assert failing["status"] == "fail"
    assert failing["summary"]["passed_case_count"] == 0
    assert failing["suites"][0]["metrics"]["recall_at_5"] == 0.0


def test_report_keeps_top_level_shape_for_cli_seam() -> None:
    report = run_vnext_evals(suite="all")

    # cli.py serializes the report as-is; these keys are the stable contract.
    for key in ("schema_version", "generated_at", "suite", "status", "targets", "suites", "summary"):
        assert key in report
    assert report["suite"] == "all"
    assert isinstance(report["suites"], list)
    assert isinstance(report["targets"], dict)
    assert report["summary"]["suite_order"] == list(VNEXT_EVAL_SUITE_ORDER)


def test_generated_at_is_real_time_not_hardcoded() -> None:
    fixed = datetime(2026, 7, 4, 12, 30, 0, tzinfo=timezone.utc)

    stamped = run_vnext_evals(suite="all", now_fn=lambda: fixed)
    defaulted = run_vnext_evals(suite="all")

    assert stamped["generated_at"] == "2026-07-04T12:30:00Z"
    assert defaulted["generated_at"] != "2026-05-11T00:00:00Z"
    parsed = datetime.fromisoformat(str(defaulted["generated_at"]).replace("Z", "+00:00"))
    assert abs((parsed - datetime.now(timezone.utc)).total_seconds()) < 60
    # Wall-clock time must not leak into the digest.
    assert stamped["report_digest"] == defaulted["report_digest"]


def test_vnext_eval_rejects_unknown_suite() -> None:
    with pytest.raises(ValueError, match="unknown vNext eval suite"):
        run_vnext_evals(suite="recall")


# --------------------------------------------------------------------------
# Seeding writes through the real store surface
# --------------------------------------------------------------------------


class RecordingStore:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []

    def create_memory(self, memory: dict[str, object], *, actor_type: str = "system") -> dict[str, object]:
        row = dict(memory)
        row["id"] = f"row-{len(self.created):03d}"
        self.created.append(row)
        return row


def test_seed_retrieval_corpus_writes_active_memories_via_store() -> None:
    corpus = generate_vnext_benchmark_corpus()
    store = RecordingStore()

    seeding = seed_retrieval_corpus(store, corpus)

    assert seeding["seeded_memory_count"] == len(corpus["memories"])
    assert seeding["embedded_memory_count"] == 0  # no provider configured
    assert "vector stage inactive" in str(seeding["embedding_note"])
    assert all(row["status"] == "active" for row in store.created)
    assert all(str(row["memory_key"]).startswith(VNEXT_EVAL_MEMORY_KEY_PREFIX) for row in store.created)
    assert all(row["canonical_text"] for row in store.created)


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------


def test_backend_label_reported_for_injected_runs() -> None:
    corpus = {
        "queries": [
            {"query_key": "q-1", "query": "alpha", "expected_memory_key": "m-1", "subset": SUBSET_LEXICAL_OVERLAP},
        ]
    }

    def retrieval(query: str, *, limit: int) -> dict[str, object]:
        return {"ranked_memory_keys": ["m-1"], "vector_stage": "enabled"}

    suite = run_retrieval_quality_eval(None, retrieval_fn=retrieval, corpus=corpus)

    assert suite["metrics"]["backend"] == "injected"


# --------------------------------------------------------------------------
# Live sqlite backend: the full production pipeline runs with no services.
# This is the CI-runnable live path -- seeding, FTS5 retrieval, RRF fusion,
# and rollback all execute for real against sqlite:///:memory: or a file.
# --------------------------------------------------------------------------


def _assert_live_sqlite_suite_shape(report: dict[str, object]) -> dict[str, object]:
    assert report["status"] == "pass"
    assert report["summary"]["executed_suite_count"] == 1
    assert report["summary"]["skipped_suite_count"] == 0
    suite = report["suites"][0]
    metrics = suite["metrics"]

    assert suite["status"] == "pass"
    assert metrics["backend"] == "sqlite"
    # No embedding provider in unit tests: FTS5-only, degraded honestly.
    assert metrics["retrieval_mode"] == "fts_only"
    assert metrics["paraphrase_targets_enforced"] is False
    assert "paraphrase_recall_at_5" not in metrics["target_checks"]

    # FTS5 (porter + stopword-filtered MATCH) must recover every reworded
    # lexical query; pure paraphrases share no vocabulary, so without an
    # embedding provider their recall is honestly 0.0 -- not hidden.
    assert metrics["subsets"][SUBSET_LEXICAL_OVERLAP]["recall_at_5"] == 1.0
    assert metrics["target_checks"]["lexical_overlap_recall_at_5"] == "pass"
    assert metrics["target_checks"]["lexical_overlap_mrr"] == "pass"
    assert metrics["subsets"][SUBSET_PARAPHRASE]["recall_at_5"] == 0.0

    seeding = metrics["seeding"]
    assert seeding["seeded_memory_count"] == VNEXT_BENCHMARK_EXPECTED_COUNTS["memories"]
    assert seeding["embedded_memory_count"] == 0
    assert "vector stage inactive" in str(seeding["embedding_note"])
    return metrics


def test_live_suite_runs_against_sqlite_memory_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, "sqlite:///:memory:")

    report = run_vnext_evals(suite="retrieval_quality")

    metrics = _assert_live_sqlite_suite_shape(report)
    assert metrics["query_count"] == VNEXT_BENCHMARK_EXPECTED_COUNTS["queries"]


def test_live_sqlite_file_run_persists_no_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "eval.db"
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, f"sqlite:///{db_path}")

    report = run_vnext_evals(suite="retrieval_quality")

    _assert_live_sqlite_suite_shape(report)
    # The rollback must leave zero rows behind -- including the FTS5
    # shadow tables written by the external-content sync triggers.
    conn = sqlite3.connect(str(db_path))
    try:
        for table in ("users", "memories", "event_log"):
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0, table
        fts_hits = conn.execute(
            "SELECT count(*) FROM memories_fts WHERE memories_fts MATCH 'launch'"
        ).fetchone()[0]
        assert fts_hits == 0
    finally:
        conn.close()


def test_live_sqlite_file_run_is_repeatable_on_the_same_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Bootstrap is idempotent and each run rolls back, so re-running against
    # the same file must not hit duplicate-key errors or skew metrics.
    db_path = tmp_path / "eval.db"
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, f"sqlite:///{db_path}")

    first = run_vnext_evals(suite="retrieval_quality")
    second = run_vnext_evals(suite="retrieval_quality")

    _assert_live_sqlite_suite_shape(first)
    _assert_live_sqlite_suite_shape(second)
    assert first["report_digest"] == second["report_digest"]


def test_unsupported_sqlite_url_reports_skipped_not_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    # sqlite3.connect("") would create a throwaway temp database; a malformed
    # URL must skip with a reason instead of silently "passing" against it.
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, "sqlite://missing-slash.db")

    report = run_vnext_evals(suite="retrieval_quality")

    assert report["status"] == "skipped"
    assert report["summary"]["executed_suite_count"] == 0
    assert "unsupported sqlite eval URL" in str(report["skipped_suites"][0]["reason"])


def test_corpus_and_report_writers_round_trip(tmp_path: Path) -> None:
    corpus_path = tmp_path / "vnext_corpus.json"
    report_path = tmp_path / "vnext_report.json"

    written_corpus_path = write_vnext_benchmark_corpus(corpus_path)
    report = run_vnext_evals(suite="all", corpus_path=written_corpus_path)
    written_report_path = write_vnext_eval_report(report=report, report_path=report_path)

    assert written_corpus_path == corpus_path.resolve()
    assert json.loads(corpus_path.read_text(encoding="utf-8"))["counts"] == VNEXT_BENCHMARK_EXPECTED_COUNTS
    assert written_report_path == report_path.resolve()
    assert json.loads(report_path.read_text(encoding="utf-8")) == report
