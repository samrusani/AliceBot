from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_evals import (
    CORRECTION_SUPPRESSION_SUITE_KEY,
    DECISION_MEMORY_KEY_PREFIX,
    DECISION_RECOVERY_SUITE_KEY,
    PROVENANCE_EXPLANATION_SUITE_KEY,
    RETRIEVAL_QUALITY_SUITE_KEY,
    SUBSET_LEXICAL_OVERLAP,
    SUBSET_PARAPHRASE,
    VNEXT_BENCHMARK_EXPECTED_COUNTS,
    VNEXT_EVAL_DATABASE_URL_ENV,
    VNEXT_EVAL_DEFAULT_USER_ID,
    VNEXT_EVAL_FIXED_VALID_TO,
    VNEXT_EVAL_MEMORY_KEY_PREFIX,
    VNEXT_EVAL_SUITE_ORDER,
    eval_token_overlap,
    generate_correction_suppression_corpus,
    generate_decision_recovery_corpus,
    generate_provenance_explanation_corpus,
    generate_vnext_benchmark_corpus,
    latency_percentile,
    recall_at_k,
    reciprocal_rank,
    retrieval_request_supports_memory_types,
    run_correction_suppression_eval,
    run_decision_recovery_eval,
    run_provenance_explanation_eval,
    run_retrieval_quality_eval,
    run_vnext_evals,
    seed_retrieval_corpus,
    write_vnext_benchmark_corpus,
    write_vnext_eval_report,
)
from alicebot_api.vnext_retrieval import reciprocal_rank_fusion

MEMORY_QUALITY_SUITE_KEYS = (
    CORRECTION_SUPPRESSION_SUITE_KEY,
    DECISION_RECOVERY_SUITE_KEY,
    PROVENANCE_EXPLANATION_SUITE_KEY,
)


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
    assert report["summary"]["skipped_suite_count"] == len(VNEXT_EVAL_SUITE_ORDER)
    assert [entry["suite_key"] for entry in report["skipped_suites"]] == list(VNEXT_EVAL_SUITE_ORDER)
    assert all(suite["status"] == "skipped" for suite in report["suites"])


def test_memory_quality_suites_without_store_report_skipped() -> None:
    for runner, suite_key in (
        (run_correction_suppression_eval, CORRECTION_SUPPRESSION_SUITE_KEY),
        (run_decision_recovery_eval, DECISION_RECOVERY_SUITE_KEY),
        (run_provenance_explanation_eval, PROVENANCE_EXPLANATION_SUITE_KEY),
    ):
        suite = runner(None)
        assert suite["suite_key"] == suite_key
        assert suite["status"] == "skipped"
        assert "live store" in str(suite["reason"])
        assert suite["cases"] == []


def test_memory_quality_suite_skips_with_reason_when_store_surface_missing() -> None:
    class _BareStore:
        def create_memory(self, memory, *, actor_type="system"):
            return dict(memory)

    suite = run_provenance_explanation_eval(_BareStore())

    assert suite["status"] == "skipped"
    assert "required surface" in str(suite["reason"])


# --------------------------------------------------------------------------
# Report semantics and shape compatibility
# --------------------------------------------------------------------------


def test_report_passes_only_when_executed_suites_pass() -> None:
    corpus = generate_vnext_benchmark_corpus()

    passing = run_vnext_evals(suite="all", retrieval_fn=_perfect_retrieval_fn(corpus))
    failing = run_vnext_evals(suite="all", retrieval_fn=_hopeless_retrieval_fn)

    # retrieval_fn injection only drives the retrieval-quality suite; the
    # commit-flow suites cannot run without a store and skip honestly.
    assert passing["status"] == "pass"
    assert passing["summary"]["suite_count"] == len(VNEXT_EVAL_SUITE_ORDER)
    assert passing["summary"]["executed_suite_count"] == 1
    assert passing["summary"]["skipped_suite_count"] == len(VNEXT_EVAL_SUITE_ORDER) - 1
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


# --------------------------------------------------------------------------
# Memory-quality suites: suite order and deterministic corpora
# --------------------------------------------------------------------------


def test_suite_order_contains_all_four_suites() -> None:
    assert VNEXT_EVAL_SUITE_ORDER == (
        RETRIEVAL_QUALITY_SUITE_KEY,
        CORRECTION_SUPPRESSION_SUITE_KEY,
        DECISION_RECOVERY_SUITE_KEY,
        PROVENANCE_EXPLANATION_SUITE_KEY,
    )
    # Each new key is individually dispatchable (the CLI passes --suite through).
    for suite_key in MEMORY_QUALITY_SUITE_KEYS:
        report = run_vnext_evals(suite=suite_key)
        assert report["suite"] == suite_key
        assert [suite["suite_key"] for suite in report["suites"]] == [suite_key]


def test_memory_quality_corpora_are_deterministic() -> None:
    for generator, expected_kind in (
        (generate_correction_suppression_corpus, CORRECTION_SUPPRESSION_SUITE_KEY),
        (generate_decision_recovery_corpus, DECISION_RECOVERY_SUITE_KEY),
        (generate_provenance_explanation_corpus, PROVENANCE_EXPLANATION_SUITE_KEY),
    ):
        corpus = generator()
        assert corpus == generator()
        assert corpus["kind"] == expected_kind
        assert str(corpus["corpus_digest"]).startswith("sha256:")


def test_correction_corpus_probes_are_lexically_bound_to_their_targets() -> None:
    corpus = generate_correction_suppression_corpus()
    cases = corpus["cases"]

    assert len(cases) >= 5
    for case in cases:
        # The main query must be able to surface both A and B (AND-semantics
        # FTS): the query's content tokens appear in each text. The overlap
        # measure is verbatim while FTS stems (ship/ships), so allow a small
        # inflection gap.
        for text_key in ("original_text", "replacement_text"):
            overlap = eval_token_overlap(str(case["query"]), str(case[text_key]))
            assert overlap >= 0.7, f"{case['case_key']}: query does not cover {text_key} ({overlap:.2f})"
        # The old-fact probe must be satisfiable only by A: at least one of
        # its content tokens is missing from B's text.
        old_probe_overlap_with_b = eval_token_overlap(str(case["old_probe"]), str(case["replacement_text"]))
        assert old_probe_overlap_with_b < 1.0, f"{case['case_key']}: old probe cannot discriminate A from B"


def test_decision_corpus_mixes_memory_types_and_covers_queries() -> None:
    corpus = generate_decision_recovery_corpus()

    decision_types = {str(row["memory_type"]) for row in corpus["decisions"]}
    distractor_types = {str(row["memory_type"]) for row in corpus["distractors"]}
    assert decision_types == {"decision"}
    assert len(distractor_types) >= 4  # genuinely mixed-type distractor pool
    assert "decision" not in distractor_types
    assert len(corpus["distractors"]) >= 2 * len(corpus["decisions"])

    lookup = {str(row["memory_key"]): row for row in corpus["decisions"]}
    for query in corpus["queries"]:
        target = lookup[str(query["expected_memory_key"])]
        overlap = eval_token_overlap(str(query["query"]), str(target["canonical_text"]))
        # Decision-intent phrasing shares vocabulary but is not verbatim.
        assert str(query["query"]).casefold() != str(target["canonical_text"]).casefold()
        assert overlap >= 0.5, f"{query['query_key']} shares too little vocabulary ({overlap:.2f})"


# --------------------------------------------------------------------------
# Live sqlite execution of the memory-quality suites (full production code:
# commit service, review paths, retrieval pipeline, rollback -- no mocks).
# --------------------------------------------------------------------------

_LIVE_USER_ID = VNEXT_EVAL_DEFAULT_USER_ID


@contextmanager
def _live_sqlite_store() -> Iterator[SQLiteVNextStore]:
    conn = sqlite3.connect(":memory:")
    conn.isolation_level = None
    conn.row_factory = sqlite3.Row
    bootstrap_sqlite_schema(conn)
    conn.execute("BEGIN")
    ensure_sqlite_user(conn, _LIVE_USER_ID, "vnext-eval-test@example.invalid", "vNext Eval Test")
    try:
        yield SQLiteVNextStore(conn, _LIVE_USER_ID)
    finally:
        conn.rollback()
        conn.close()


class _OverrideStore:
    """Delegating wrapper that breaks selected store methods for failure tests."""

    def __init__(self, inner: object, **overrides: object) -> None:
        self._inner = inner
        self._overrides = overrides

    def __getattr__(self, name: str) -> object:
        overrides = self.__dict__["_overrides"]
        if name in overrides:
            return overrides[name]
        return getattr(self.__dict__["_inner"], name)


def test_live_correction_suppression_locks_in_regression_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, "sqlite:///:memory:")

    report = run_vnext_evals(suite=CORRECTION_SUPPRESSION_SUITE_KEY)

    assert report["status"] == "pass"
    suite = report["suites"][0]
    metrics = suite["metrics"]
    assert suite["status"] == "pass"
    assert metrics["backend"] == "sqlite"
    assert metrics["pre_correction_visibility"] == 1.0  # non-vacuous: A ranked before correction
    assert metrics["suppression_rate"] == 1.0
    assert metrics["replacement_recall_at_5"] == 1.0
    assert metrics["audit_completeness"] == 1.0
    for case in suite["cases"]:
        evidence = case["evidence"]
        assert case["status"] == "pass"
        # A surfaced pre-correction, then vanished from every probe.
        assert evidence["original_memory_key"] in evidence["pre_correction_top_keys"]
        assert evidence["original_memory_key"] not in evidence["post_correction_top_keys"]
        assert evidence["original_memory_key"] not in evidence["old_probe_top_keys"]
        assert evidence["rejected_memory_key"] not in evidence["post_correction_top_keys"]
        assert evidence["rejected_memory_key"] not in evidence["reject_probe_top_keys"]
        # The supersession on A points at its replacement.
        assert evidence["replacement_memory_key"] in str(evidence["superseded_revision_reason"])


def test_live_decision_recovery_measures_recall_and_filter_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, "sqlite:///:memory:")

    report = run_vnext_evals(suite=DECISION_RECOVERY_SUITE_KEY)

    assert report["status"] == "pass"
    suite = report["suites"][0]
    metrics = suite["metrics"]
    assert suite["status"] == "pass"
    assert metrics["backend"] == "sqlite"
    assert metrics["decision_recall_at_5"] >= 0.8
    assert metrics["target_checks"]["decision_recall_at_5"] == "pass"
    filter_state = metrics["memory_types_filter"]
    if retrieval_request_supports_memory_types():
        # The sibling workstream's filter parameter has landed: both the
        # unfiltered and filtered variants must be measured and reported.
        assert filter_state["available"] is True
        assert metrics["filtered_decision_recall_at_5"] >= 0.8
        assert metrics["target_checks"]["filtered_decision_recall_at_5"] == "pass"
    else:
        assert filter_state["available"] is False
        assert "TODO" in str(filter_state["note"])
        assert "filtered_decision_recall_at_5" not in metrics["target_checks"]


def test_live_provenance_explanation_audits_real_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, "sqlite:///:memory:")

    report = run_vnext_evals(suite=PROVENANCE_EXPLANATION_SUITE_KEY)

    assert report["status"] == "pass"
    suite = report["suites"][0]
    metrics = suite["metrics"]
    assert suite["status"] == "pass"
    assert metrics["backend"] == "sqlite"
    assert metrics["explain_completeness_rate"] == 1.0
    assert metrics["orphan_provenance_count"] == 0
    assert metrics["provenance_link_count"] >= metrics["audited_memory_count"]
    assert metrics["corrected_memory_count"] >= 1
    corrected_cases = [case for case in suite["cases"] if "correction_reflected" in case["checks"]]
    assert len(corrected_cases) == metrics["corrected_memory_count"]
    for case in corrected_cases:
        assert case["checks"]["correction_reflected"] == "pass"
        assert "corrected" in case["evidence"]["revision_types"]
        assert "agent.memory_corrected" in case["evidence"]["event_types"]
    for case in suite["cases"]:
        assert "agent.memory_committed" in case["evidence"]["event_types"]
        assert any(reason.strip() for reason in case["evidence"]["revision_reasons"])


def test_live_all_suites_execute_against_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, "sqlite:///:memory:")

    report = run_vnext_evals(suite="all")

    assert report["status"] == "pass"
    assert report["summary"]["executed_suite_count"] == len(VNEXT_EVAL_SUITE_ORDER)
    assert report["summary"]["skipped_suite_count"] == 0
    assert [suite["suite_key"] for suite in report["suites"]] == list(VNEXT_EVAL_SUITE_ORDER)
    assert all(suite["status"] == "pass" for suite in report["suites"])


def test_live_all_suites_file_run_persists_no_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "eval_all.db"
    monkeypatch.setenv(VNEXT_EVAL_DATABASE_URL_ENV, f"sqlite:///{db_path}")

    report = run_vnext_evals(suite="all")

    assert report["status"] == "pass"
    conn = sqlite3.connect(str(db_path))
    try:
        for table in ("users", "memories", "event_log", "sources", "memory_revisions", "provenance_links"):
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0, table
    finally:
        conn.close()


def test_seeded_decision_rows_pin_explicit_status_and_validity() -> None:
    # A sibling workstream is adding staleness demotion to the search SQL;
    # seeded rows must carry explicit active status and far-future validity
    # so that change cannot silently demote them.
    with _live_sqlite_store() as store:
        suite = run_decision_recovery_eval(store)

        assert suite["status"] == "pass"
        assert suite["metrics"]["backend"] == "sqlite"  # injected stores are still labelled
        seeded = [
            row
            for row in store.list_memories(status=None)
            if str(row["memory_key"]).startswith(DECISION_MEMORY_KEY_PREFIX)
        ]
        assert seeded
        assert all(row["status"] == "active" for row in seeded)
        assert all(str(row["valid_to"]).startswith(VNEXT_EVAL_FIXED_VALID_TO[:10]) for row in seeded)


# --------------------------------------------------------------------------
# The suites can genuinely FAIL: break one production behavior at a time
# through a delegating store wrapper and watch the right metric collapse.
# --------------------------------------------------------------------------


def test_correction_suppression_fails_when_status_transitions_are_lost() -> None:
    # Simulates a store regression where supersede/reject no longer demote
    # the memory status: the stale memory keeps surfacing and the audit
    # trail no longer shows a superseded row.
    with _live_sqlite_store() as store:
        def update_memory_dropping_status(*, memory_id: str, patch: dict, actor_type: str = "system") -> dict:
            stripped = {key: value for key, value in patch.items() if key != "status"}
            if not stripped:
                return store.get_memory(memory_id)
            return store.update_memory(memory_id=memory_id, patch=stripped, actor_type=actor_type)

        broken = _OverrideStore(store, update_memory=update_memory_dropping_status)
        suite = run_correction_suppression_eval(broken)

        assert suite["status"] == "fail"
        assert suite["metrics"]["suppression_rate"] < 1.0
        assert suite["metrics"]["target_checks"]["suppression_rate"] == "fail"
        assert suite["metrics"]["audit_completeness"] < 1.0


def test_decision_recovery_fails_when_retrieval_goes_blind() -> None:
    with _live_sqlite_store() as store:
        broken = _OverrideStore(
            store,
            search_memories_fts=lambda **_kwargs: [],
            search_memories=lambda **_kwargs: [],
        )
        suite = run_decision_recovery_eval(broken)

        assert suite["status"] == "fail"
        assert suite["metrics"]["decision_recall_at_5"] == 0.0
        assert suite["metrics"]["target_checks"]["decision_recall_at_5"] == "fail"


def test_provenance_explanation_fails_when_revisions_disappear() -> None:
    with _live_sqlite_store() as store:
        broken = _OverrideStore(store, list_revisions=lambda memory_id: [])
        suite = run_provenance_explanation_eval(broken)

        assert suite["status"] == "fail"
        assert suite["metrics"]["explain_completeness_rate"] == 0.0
        assert suite["metrics"]["target_checks"]["explain_completeness_rate"] == "fail"


def test_provenance_explanation_fails_on_orphaned_provenance_links() -> None:
    with _live_sqlite_store() as store:
        broken = _OverrideStore(store, get_source=lambda source_id: None)
        suite = run_provenance_explanation_eval(broken)

        assert suite["status"] == "fail"
        assert suite["metrics"]["orphan_provenance_count"] > 0
        assert suite["metrics"]["target_checks"]["orphan_provenance_count"] == "fail"
