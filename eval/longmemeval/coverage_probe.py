"""LongMemEval retrieval-coverage probe: ingest + retrieve, no chat, no judge.

Free (keyless) gate for retrieval changes. For every question the probe
replays the harness's ingest + retrieval pipeline (the same
``adapter.question_run`` machinery ``runner.py --dry-run`` uses), then
compares the *sessions* Alice retrieved against the dataset's ground-truth
evidence sessions (``answer_session_ids``; see ``dataset.py`` — evidence
turns additionally carry ``has_answer: true``).

Retrieved sessions come from two places in the context pack:

* ``sources`` — each retrieved source row carries the originating
  ``session_id`` in its ``metadata_json`` (written by the adapter's ingest).
* ``relevant_memories`` — provenance: each memory's ``metadata_json``
  carries the ``source_id`` it was extracted from, which resolves back to a
  session via that source's metadata.

Per question the probe emits one JSONL row with ``any_coverage`` (at least
one evidence session retrieved) and ``all_coverage`` (every evidence session
retrieved), then prints an any/all coverage table per question type.
Questions without evidence ids (e.g. synthetic abstention fixtures) get
``null`` coverage and are excluded from the percentages.

Embeddings are DISABLED by default (the ``ALICE_EMBEDDINGS_*`` variables are
scrubbed from the environment) so the probe is deterministic and needs no
API key; pass ``--with-vectors`` to keep the ambient embedding config. The
reranker stage (``ALICE_RERANKER_*``, see ``vnext_reranker``) is scrubbed
the same way for the same reason; pass ``--with-reranker`` to keep the
ambient reranker config (requires a live scoring endpoint).

Store reuse: per-question SQLite stores use the runner's naming scheme
inside ``--work-dir`` and are kept, with a ``*.ingested.json`` marker
written after a committed ingest. A rerun over the same work dir skips
ingest for marked stores, so iterating on retrieval is cheap.

Run from the repo root:

    .venv/bin/python eval/longmemeval/coverage_probe.py --limit 50
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import sys
import time

_EVAL_DIR = Path(__file__).resolve().parent.parent
if str(_EVAL_DIR) not in sys.path:  # direct execution
    sys.path.insert(0, str(_EVAL_DIR))

from alicebot_api.vnext_embeddings import (
    EMBEDDINGS_API_KEY_ENV,
    EMBEDDINGS_BASE_URL_ENV,
    EMBEDDINGS_MODEL_ENV,
)

# ---- reranker (disclosed precision stage) begin ---------------------------
from alicebot_api.vnext_reranker import (
    RERANKER_API_KEY_ENV,
    RERANKER_BASE_URL_ENV,
    RERANKER_MODEL_ENV,
)

# ---- reranker (disclosed precision stage) end -----------------------------
from alicebot_api.vnext_retrieval import VNextRetrievalRequest, VNextRetrievalService
from alicebot_api.vnext_temporal_query import parse_event_datetime

from longmemeval.adapter import max_items_from_env, question_run
from longmemeval.chat import redacted_base_url
from longmemeval.dataset import (
    RESULTS_DIR,
    WORK_DIR,
    LongMemEvalDatasetError,
    LongMemEvalQuestion,
    load_dataset,
    resolve_dataset_path,
)
from longmemeval.runner import (
    INGEST_MARKER_SCHEMA,
    _FILENAME_SAFE,
    _build_ingest_marker_payload,
    _cleanup_store,
    _sha256_prefix,
)


COVERAGE_SCHEMA = "longmemeval_coverage_v2"
DEFAULT_WORK_DIR = WORK_DIR / "coverage"
GOVERNED_NON_COUNT_SLICE = Path(__file__).resolve().parent / "slices" / "phase6-non-count-101.txt"
GOVERNED_NON_COUNT_QUESTION_COUNT = 101
GOVERNED_NON_COUNT_MANIFEST_SHA256 = "c660317b20610f578087dc1042b5454eed871cd395c558333fd927637e1627f0"
GOVERNED_DATASET_PATH = Path(__file__).resolve().parent / "data" / "longmemeval_s_cleaned.json"
GOVERNED_DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
GOVERNED_MAX_ITEMS = 16
FROZEN_NON_COUNT_COVERAGE_FLOORS = {
    "overall": {
        "any_coverage": 0.9505,
        "all_coverage": 0.8812,
    },
    "multi-session": {
        "any_coverage": 0.9643,
        "all_coverage": 0.8571,
    },
}

EXIT_OK = 0
EXIT_RUN_FAILURES = 1
EXIT_CONFIG_ERROR = 2
EXIT_STRATUM_FAILURES = 3

_EMBEDDINGS_ENV_VARS = (EMBEDDINGS_BASE_URL_ENV, EMBEDDINGS_MODEL_ENV, EMBEDDINGS_API_KEY_ENV)
# ---- reranker (disclosed precision stage) begin ---------------------------
_RERANKER_ENV_VARS = (RERANKER_BASE_URL_ENV, RERANKER_MODEL_ENV, RERANKER_API_KEY_ENV)
# ---- reranker (disclosed precision stage) end -----------------------------


def question_id_manifest_sha256(question_ids: Sequence[str]) -> str:
    """Digest an exact, ordered question-id manifest including its final LF."""
    return hashlib.sha256(("\n".join(question_ids) + "\n").encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def provider_summary_metadata() -> dict[str, str | None]:
    embeddings_base_url = os.environ.get(EMBEDDINGS_BASE_URL_ENV, "").strip()
    reranker_base_url = os.environ.get(RERANKER_BASE_URL_ENV, "").strip()
    return {
        "embeddings_model": os.environ.get(EMBEDDINGS_MODEL_ENV, "").strip() or None,
        "embeddings_base_url": (redacted_base_url(embeddings_base_url) if embeddings_base_url else None),
        "reranker_model": os.environ.get(RERANKER_MODEL_ENV, "").strip() or None,
        "reranker_base_url": (redacted_base_url(reranker_base_url) if reranker_base_url else None),
    }


def is_governed_non_count_manifest(path: Path | None, question_ids: Sequence[str]) -> bool:
    """Require both the checked-in path and its frozen ordered content."""
    return bool(
        path is not None
        and path.resolve() == GOVERNED_NON_COUNT_SLICE.resolve()
        and len(question_ids) == GOVERNED_NON_COUNT_QUESTION_COUNT
        and question_id_manifest_sha256(question_ids) == GOVERNED_NON_COUNT_MANIFEST_SHA256
    )


def coverage_release_input_checks(
    *,
    dataset_path: Path,
    dataset_sha256: str,
    question_id_file: Path | None,
    question_ids: Sequence[str],
    limit: int | None,
    max_items: int,
    with_vectors: bool,
    with_reranker: bool,
) -> dict[str, bool]:
    return {
        "dataset_path_matches": dataset_path.resolve() == GOVERNED_DATASET_PATH.resolve(),
        "dataset_sha256_matches": dataset_sha256 == GOVERNED_DATASET_SHA256,
        "question_manifest_matches": is_governed_non_count_manifest(
            question_id_file,
            question_ids,
        ),
        "limit_disabled": limit is None,
        "max_items_matches": max_items == GOVERNED_MAX_ITEMS,
        "vectors_disabled": not with_vectors,
        "reranker_disabled": not with_reranker,
    }


def all_probe_stores_fresh(rows: Sequence[Mapping[str, object]], *, expected_count: int) -> bool:
    return bool(len(rows) == expected_count and all(row.get("reused_store") is False for row in rows))


def coverage_release_gate(
    summary: Mapping[str, object],
    *,
    release_eligible: bool,
    has_errors: bool = False,
) -> dict[str, object]:
    """Build explicit frozen-floor gate metadata for the governed slice."""
    checks: dict[str, dict[str, object]] = {}
    overall = summary.get("overall")
    per_type = summary.get("per_type")
    for scope, floors in FROZEN_NON_COUNT_COVERAGE_FLOORS.items():
        bucket: object
        if scope == "overall":
            bucket = overall
        else:
            bucket = per_type.get(scope) if isinstance(per_type, Mapping) else None
        for metric, floor in floors.items():
            observed = bucket.get(metric) if isinstance(bucket, Mapping) else None
            passed = bool(
                isinstance(observed, (int, float)) and not isinstance(observed, bool) and float(observed) >= floor
            )
            checks[f"{scope}.{metric}"] = {
                "observed": observed,
                "floor": floor,
                "passed": passed,
            }
    floors_passed = all(bool(check["passed"]) for check in checks.values())
    return {
        "mode": "release" if release_eligible else "diagnostic",
        "eligible": release_eligible,
        "governed_question_id_file": str(GOVERNED_NON_COUNT_SLICE),
        "governed_question_id_count": GOVERNED_NON_COUNT_QUESTION_COUNT,
        "governed_question_id_manifest_sha256": GOVERNED_NON_COUNT_MANIFEST_SHA256,
        "frozen_floors": FROZEN_NON_COUNT_COVERAGE_FLOORS,
        "checks": checks,
        "passed": bool(release_eligible and not has_errors and floors_passed),
    }


def exit_code_for_release_gate(
    gate: Mapping[str, object],
    *,
    has_errors: bool,
) -> int:
    if has_errors:
        return EXIT_RUN_FAILURES
    return EXIT_OK if gate.get("passed") is True else EXIT_STRATUM_FAILURES


def disable_embeddings_env() -> None:
    """Scrub embedding provider config so retrieval runs FTS-only (keyless)."""
    for name in _EMBEDDINGS_ENV_VARS:
        os.environ.pop(name, None)


# ---- reranker (disclosed precision stage) begin ---------------------------
def disable_reranker_env() -> None:
    """Scrub reranker config so the probe keeps its keyless-determinism promise.

    An ambient ``ALICE_RERANKER_*`` config would otherwise silently turn a
    provider-side scoring stage on inside the free probe, making baseline
    comparisons nondeterministic. ``--with-reranker`` opts in explicitly.
    """
    for name in _RERANKER_ENV_VARS:
        os.environ.pop(name, None)


# ---- reranker (disclosed precision stage) end -----------------------------


# -- coverage math ---------------------------------------------------------


def coverage_row(question: LongMemEvalQuestion, retrieved_session_ids: set[str]) -> dict[str, object]:
    """One JSONL row comparing retrieved sessions against evidence sessions."""
    evidence = set(question.answer_session_ids)
    hits = evidence & retrieved_session_ids
    n_evidence = len(evidence)
    return {
        "schema": COVERAGE_SCHEMA,
        "question_id": question.question_id,
        "question_type": question.question_type,
        "is_abstention": question.is_abstention,
        "n_evidence": n_evidence,
        "n_hit": len(hits),
        "any_coverage": (len(hits) > 0) if n_evidence else None,
        "all_coverage": (hits == evidence) if n_evidence else None,
        "missed_session_ids": sorted(evidence - retrieved_session_ids),
        "retrieved_session_count": len(retrieved_session_ids),
    }


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    """Any/all coverage percentages per question type plus overall."""

    def bucket(bucket_rows: list[dict[str, object]]) -> dict[str, object]:
        scored = [row for row in bucket_rows if row.get("any_coverage") is not None]
        any_hits = sum(1 for row in scored if row["any_coverage"] is True)
        all_hits = sum(1 for row in scored if row["all_coverage"] is True)
        return {
            "questions": len(bucket_rows),
            "scored": len(scored),
            "any_coverage": round(any_hits / len(scored), 4) if scored else None,
            "all_coverage": round(all_hits / len(scored), 4) if scored else None,
        }

    per_type: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        per_type.setdefault(str(row.get("question_type")), []).append(row)
    return {
        "overall": bucket(rows),
        "per_type": {question_type: bucket(bucket_rows) for question_type, bucket_rows in sorted(per_type.items())},
    }


def format_summary_table(summary: dict[str, object]) -> str:
    def pct(value: object) -> str:
        return f"{float(value) * 100:5.1f}" if isinstance(value, (int, float)) else "    -"

    lines = [f"{'question_type':<28} {'scored':>6} {'any%':>6} {'all%':>6}"]
    per_type = summary.get("per_type")
    assert isinstance(per_type, dict)
    for question_type, bucket in per_type.items():
        lines.append(
            f"{question_type:<28} {bucket['scored']:>6} {pct(bucket['any_coverage']):>6} {pct(bucket['all_coverage']):>6}"
        )
    overall = summary["overall"]
    assert isinstance(overall, dict)
    lines.append(
        f"{'overall':<28} {overall['scored']:>6} {pct(overall['any_coverage']):>6} {pct(overall['all_coverage']):>6}"
    )
    return "\n".join(lines)


# -- retrieved-session extraction --------------------------------------------


def _session_id_from_source_row(source: object) -> str | None:
    if not isinstance(source, dict):
        return None
    metadata = source.get("metadata_json")
    if not isinstance(metadata, dict):
        return None
    session_id = metadata.get("session_id")
    return session_id if isinstance(session_id, str) and session_id else None


def retrieved_sessions_from_pack(pack: dict[str, object], store: object) -> set[str]:
    """Session ids behind the pack's sources plus its memories' provenance."""
    retrieved: set[str] = set()
    for source in pack.get("sources") or []:  # type: ignore[union-attr]
        session_id = _session_id_from_source_row(source)
        if session_id is not None:
            retrieved.add(session_id)
    for memory in pack.get("relevant_memories") or []:  # type: ignore[union-attr]
        if not isinstance(memory, dict):
            continue
        metadata = memory.get("metadata_json")
        source_id = metadata.get("source_id") if isinstance(metadata, dict) else None
        if not isinstance(source_id, str) or not source_id:
            continue
        session_id = _session_id_from_source_row(store.get_source(source_id))  # type: ignore[attr-defined]
        if session_id is not None:
            retrieved.add(session_id)
    return retrieved


# -- per-question probe --------------------------------------------------------


def _db_path_for(work_dir: Path, question_id: str) -> Path:
    """Same store naming as the runner, so work dirs are interchangeable."""
    return work_dir / f"{_FILENAME_SAFE.sub('_', question_id)}.sqlite3"


def _marker_path_for(db_path: Path) -> Path:
    return Path(str(db_path) + ".ingested.json")


def _marker_matches(
    marker_path: Path,
    question: LongMemEvalQuestion,
    dataset_path: Path,
) -> bool:
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(marker, dict) and marker == _build_ingest_marker_payload(
        question,
        dataset_path=dataset_path,
        accept_rollups=False,
    )


def probe_question(
    question: LongMemEvalQuestion,
    *,
    work_dir: Path,
    dataset_path: Path,
    max_items: int,
) -> dict[str, object]:
    db_path = _db_path_for(work_dir, question.question_id)
    marker_path = _marker_path_for(db_path)
    reuse = db_path.is_file() and _marker_matches(marker_path, question, dataset_path)
    if not reuse:
        marker_path.unlink(missing_ok=True)
        _cleanup_store(db_path)
    started = time.monotonic()
    ingest_seconds: float | None = None
    with question_run(question, db_path) as run:
        if not reuse:
            run.ingest()
            ingest_seconds = time.monotonic() - started
        service = VNextRetrievalService(run.store)
        # Same request the harness's retrieve step builds: the raw benchmark
        # question is the query; no benchmark taxonomy reaches retrieval.
        request = VNextRetrievalRequest(
            query=question.question,
            max_items=max_items,
            include_sources=True,
            actor_type="system",
            reference_time=parse_event_datetime(question.question_date),
        )
        retrieval_started = time.monotonic()
        pack = service.compile_context_pack(request)
        retrieval_seconds = time.monotonic() - retrieval_started
        retrieved = retrieved_sessions_from_pack(pack, run.store)
        trace = pack.get("trace") if isinstance(pack.get("trace"), dict) else {}
        vector_stage = str(trace.get("vector_stage", "unknown"))
    if not reuse:
        # The store transaction committed on clean question_run exit; only
        # now is the ingested store safe to reuse.
        marker_path.write_text(
            json.dumps(
                _build_ingest_marker_payload(
                    question,
                    dataset_path=dataset_path,
                    accept_rollups=False,
                ),
                ensure_ascii=True,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    row = coverage_row(question, retrieved)
    row["reused_store"] = reuse
    row["vector_stage"] = vector_stage
    row["ingest_seconds"] = round(ingest_seconds, 3) if ingest_seconds is not None else None
    row["retrieval_seconds"] = round(retrieval_seconds, 3)
    return row


# -- CLI -------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coverage_probe.py",
        description="Retrieval-coverage probe: which ground-truth evidence sessions does Alice retrieve?",
    )
    parser.add_argument(
        "--dataset-file",
        type=Path,
        default=None,
        help="dataset JSON path (default: eval/longmemeval/data/longmemeval_s_cleaned.json)",
    )
    parser.add_argument("--limit", type=int, default=None, help="only probe the first N selected questions")
    parser.add_argument(
        "--question-ids",
        type=Path,
        default=None,
        help="file with one question_id per line; comments ignored; probe only those (dataset order)",
    )
    parser.add_argument("--max-items", type=int, default=None, help="context-pack max_items (default: runner default)")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_WORK_DIR,
        help="per-question SQLite stores; kept and reused across probes (default: eval/longmemeval/work/coverage)",
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="per-question JSONL path (default: eval/longmemeval/results/)"
    )
    parser.add_argument("--workers", type=int, default=2, help="parallel questions in flight (default: 2)")
    parser.add_argument(
        "--with-vectors",
        action="store_true",
        help="keep ambient ALICE_EMBEDDINGS_* config (default: scrubbed, FTS-only)",
    )
    # ---- reranker (disclosed precision stage) begin -----------------------
    parser.add_argument(
        "--with-reranker",
        action="store_true",
        help="keep ambient ALICE_RERANKER_* config (default: scrubbed, fusion order only)",
    )
    # ---- reranker (disclosed precision stage) end -------------------------
    return parser


def _load_question_ids(path: Path) -> list[str] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[coverage] cannot read --question-ids file: {exc}", file=sys.stderr)
        return None
    return [line for raw_line in text.splitlines() if (line := raw_line.strip()) and not line.startswith("#")]


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.with_vectors:
        disable_embeddings_env()
    # ---- reranker (disclosed precision stage) begin -----------------------
    if not args.with_reranker:
        disable_reranker_env()
    # ---- reranker (disclosed precision stage) end -------------------------

    dataset_path = args.dataset_file if args.dataset_file is not None else resolve_dataset_path("s")
    if dataset_path is None or not dataset_path.is_file():
        print(
            "[coverage] dataset not found; fetch it with: python eval/longmemeval/fetch.py --variant s "
            "or pass --dataset-file",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR
    dataset_sha256 = file_sha256(dataset_path)
    try:
        questions = load_dataset(dataset_path)
    except LongMemEvalDatasetError as exc:
        print(f"[coverage] {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    requested_question_ids: list[str]
    if args.question_ids is not None:
        wanted_ids = _load_question_ids(args.question_ids)
        if wanted_ids is None:
            return EXIT_CONFIG_ERROR
        wanted = set(wanted_ids)
        available = {question.question_id for question in questions}
        missing = wanted - available
        if missing:
            print(
                f"[coverage] {len(missing)} requested question ids not in dataset: {sorted(missing)[:5]}...",
                file=sys.stderr,
            )
            return EXIT_CONFIG_ERROR
        requested_question_ids = wanted_ids
        questions = tuple(question for question in questions if question.question_id in wanted)
    else:
        requested_question_ids = [question.question_id for question in questions]
    if args.limit is not None:
        questions = questions[: args.limit]
    if not questions:
        print("[coverage] no questions selected", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    selected_question_ids = [question.question_id for question in questions]

    max_items = args.max_items if args.max_items is not None else max_items_from_env()
    release_input_checks = coverage_release_input_checks(
        dataset_path=dataset_path,
        dataset_sha256=dataset_sha256,
        question_id_file=args.question_ids,
        question_ids=requested_question_ids,
        limit=args.limit,
        max_items=max_items,
        with_vectors=args.with_vectors,
        with_reranker=args.with_reranker,
    )
    release_candidate = bool(
        all(release_input_checks.values())
        and len(selected_question_ids) == GOVERNED_NON_COUNT_QUESTION_COUNT
        and set(selected_question_ids) == set(requested_question_ids)
    )
    dataset_sha256_prefix = _sha256_prefix(dataset_path)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out or RESULTS_DIR / f"coverage_{dataset_path.stem}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    vectors = "ambient" if args.with_vectors else "disabled"
    reranker = "ambient" if args.with_reranker else "disabled"
    print(
        f"[coverage] dataset={dataset_path.name} questions={len(questions)} max_items={max_items} "
        f"vectors={vectors} reranker={reranker} gate={'release-candidate' if release_candidate else 'diagnostic'} "
        f"work_dir={args.work_dir} workers={max(1, args.workers)}"
    )

    rows_by_id: dict[str, dict[str, object]] = {}
    errors: list[tuple[str, str]] = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                probe_question,
                question,
                work_dir=args.work_dir,
                dataset_path=dataset_path,
                max_items=max_items,
            ): question
            for question in questions
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            question = futures[future]
            try:
                row = future.result()
            except Exception as exc:  # noqa: BLE001 - one bad question must not kill the probe
                errors.append((question.question_id, f"{type(exc).__name__}: {exc}"))
                print(
                    f"[coverage] {completed}/{len(questions)} {question.question_id} ERROR: {exc}",
                    flush=True,
                    file=sys.stderr,
                )
                continue
            rows_by_id[question.question_id] = row
            if completed % 25 == 0 or completed == len(questions):
                print(f"[coverage] {completed}/{len(questions)} probed ({time.monotonic() - started:.0f}s)", flush=True)

    rows = [rows_by_id[question.question_id] for question in questions if question.question_id in rows_by_id]
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")

    summary = summarize_rows(rows)
    all_stores_fresh = all_probe_stores_fresh(
        rows,
        expected_count=len(selected_question_ids),
    )
    release_eligible = bool(release_candidate and all_stores_fresh)
    release_gate = coverage_release_gate(
        summary,
        release_eligible=release_eligible,
        has_errors=bool(errors),
    )
    release_gate["required_vectors"] = "disabled"
    release_gate["required_reranker"] = "disabled"
    release_gate["governed_dataset_path"] = str(GOVERNED_DATASET_PATH)
    release_gate["governed_dataset_sha256"] = GOVERNED_DATASET_SHA256
    release_gate["required_max_items"] = GOVERNED_MAX_ITEMS
    release_gate["vectors"] = vectors
    release_gate["reranker"] = reranker
    release_gate["input_checks"] = release_input_checks
    release_gate["all_stores_fresh"] = all_stores_fresh
    release_gate["reused_store_count"] = sum(1 for row in rows if row.get("reused_store") is True)
    exit_code = exit_code_for_release_gate(release_gate, has_errors=bool(errors))
    summary_path = out_path.with_suffix(".summary.json")
    summary_payload = {
        "schema": COVERAGE_SCHEMA + "_summary",
        "dataset_file": dataset_path.name,
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha256,
        "dataset_sha256_prefix": dataset_sha256_prefix,
        "question_id_file": str(args.question_ids) if args.question_ids is not None else None,
        "question_id_manifest_count": len(requested_question_ids),
        "question_id_manifest_sha256": question_id_manifest_sha256(requested_question_ids),
        "selected_question_id_count": len(selected_question_ids),
        "selected_question_id_manifest_sha256": question_id_manifest_sha256(selected_question_ids),
        "limit": args.limit,
        "max_items": max_items,
        "vectors": vectors,
        "reranker": reranker,
        **provider_summary_metadata(),
        "questions": len(rows),
        "errors": [{"question_id": question_id, "error": error} for question_id, error in errors],
        "release_gate": release_gate,
        **summary,
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(format_summary_table(summary))
    print(f"[coverage] done in {time.monotonic() - started:.1f}s rows={out_path} summary={summary_path}")
    if errors:
        print(f"[coverage] {len(errors)} questions failed", file=sys.stderr)
    elif not release_eligible:
        print(
            "[coverage] diagnostic run only; release-green requires the canonical dataset, exact governed "
            "phase6-non-count-101 manifest, max_items=16, fresh stores, no --limit, and disabled providers",
            file=sys.stderr,
        )
    elif exit_code != EXIT_OK:
        print("[coverage] frozen non-count coverage floors not met", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COVERAGE_SCHEMA",
    "DEFAULT_WORK_DIR",
    "GOVERNED_DATASET_PATH",
    "GOVERNED_DATASET_SHA256",
    "GOVERNED_MAX_ITEMS",
    "EXIT_STRATUM_FAILURES",
    "EXIT_CONFIG_ERROR",
    "EXIT_OK",
    "EXIT_RUN_FAILURES",
    "INGEST_MARKER_SCHEMA",
    "build_arg_parser",
    "all_probe_stores_fresh",
    "coverage_release_input_checks",
    "coverage_release_gate",
    "coverage_row",
    "disable_embeddings_env",
    "disable_reranker_env",
    "format_summary_table",
    "file_sha256",
    "exit_code_for_release_gate",
    "is_governed_non_count_manifest",
    "main",
    "probe_question",
    "provider_summary_metadata",
    "question_id_manifest_sha256",
    "retrieved_sessions_from_pack",
    "summarize_rows",
]
