"""LongMemEval run orchestration: worker pool, checkpoints, and reports.

Entry point is ``scripts/run_longmemeval.py`` (repo root), which puts
``eval/`` on ``sys.path`` and calls :func:`main`. Long runs checkpoint one
JSONL record per question so ``--resume`` can pick up where a run stopped;
the final report aggregates overall and per-question-type accuracy plus
retrieval statistics and a config fingerprint.

``--dry-run`` ingests and retrieves only (no chat model, no judge) and fails
if retrieval comes back empty for a non-abstention question. It skips
cleanly (exit 0) when the dataset has not been fetched, so it is safe in CI.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import threading
import time

_EVAL_DIR = Path(__file__).resolve().parent.parent
if str(_EVAL_DIR) not in sys.path:  # direct execution: python eval/longmemeval/runner.py
    sys.path.insert(0, str(_EVAL_DIR))

from alicebot_api import __version__ as alicebot_version
from alicebot_api.vnext_embeddings import EMBEDDINGS_BASE_URL_ENV, EMBEDDINGS_MODEL_ENV

from longmemeval.adapter import (
    ANSWER_MAX_TOKENS,
    ANSWER_MAX_TOKENS_COT,
    DEFAULT_CONTEXT_CHAR_BUDGET,
    DEFAULT_MAX_ITEMS,
    build_answer_prompt,
    context_char_budget_from_env,
    max_items_from_env,
    question_run,
)
from longmemeval.chat import ChatModelConfig, chat_completion, judge_config_from_env, model_config_from_env
from longmemeval.dataset import (
    RESULTS_DIR,
    VARIANTS,
    WORK_DIR,
    LongMemEvalDatasetError,
    LongMemEvalQuestion,
    load_dataset,
    resolve_dataset_path,
)
from longmemeval.judge import judge_hypothesis


RESULT_SCHEMA = "longmemeval_result_v1"
REPORT_SCHEMA = "longmemeval_report_v1"
HARNESS_VERSION = "1.0"
GENERATION_TEMPERATURE = 0.0

EXIT_OK = 0
EXIT_RUN_FAILURES = 1
EXIT_CONFIG_ERROR = 2

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class RunnerConfig:
    variant: str
    dataset_path: Path
    limit: int | None
    question_ids: tuple[str, ...] | None
    question_ids_file: str | None
    resume: bool
    dry_run: bool
    cot: bool
    workers: int
    max_items: int
    context_char_budget: int
    work_dir: Path
    checkpoint_path: Path
    report_path: Path
    keep_stores: bool

    @property
    def mode(self) -> str:
        return "dry_run" if self.dry_run else "scored"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_prefix(path: Path, *, length: int = 16) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:length]


def config_fingerprint(
    config: RunnerConfig,
    *,
    model: ChatModelConfig | None,
    judge: ChatModelConfig | None,
) -> dict[str, object]:
    """Everything needed to interpret a score; digest detects config drift."""
    embeddings_base_url = os.environ.get(EMBEDDINGS_BASE_URL_ENV, "").strip()
    embeddings_model = os.environ.get(EMBEDDINGS_MODEL_ENV, "").strip()
    fingerprint: dict[str, object] = {
        "harness_version": HARNESS_VERSION,
        "alicebot_version": alicebot_version,
        "mode": config.mode,
        "variant": config.variant,
        "dataset_file": config.dataset_path.name,
        "dataset_sha256_prefix": _sha256_prefix(config.dataset_path),
        "answer_model": model.redacted() if model is not None else None,
        "judge_model": judge.redacted() if judge is not None else None,
        "embeddings_enabled": bool(embeddings_base_url and embeddings_model),
        "embeddings_model": embeddings_model or None,
        "reading_style": "cot" if config.cot else "standard",
        "generation_temperature": GENERATION_TEMPERATURE,
        "max_items": config.max_items,
        "context_char_budget": config.context_char_budget,
        # A slice run must never masquerade as a full run: the subset (file
        # name, count, digest of the sorted ids) feeds the fingerprint digest.
        "question_subset": None
        if config.question_ids is None
        else {
            "file": config.question_ids_file,
            "count": len(config.question_ids),
            "ids_sha256_prefix": hashlib.sha256(
                "\n".join(sorted(config.question_ids)).encode("utf-8")
            ).hexdigest()[:16],
        },
    }
    digest_source = json.dumps(fingerprint, sort_keys=True, ensure_ascii=True)
    fingerprint["digest"] = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:16]
    return fingerprint


def load_question_ids(path: Path) -> tuple[str, ...]:
    """Read a slice file: one question_id per line.

    Blank lines and ``#`` comment lines are skipped; duplicates keep the
    first occurrence. Raises ``ValueError`` for a missing or empty file.
    """
    if not path.is_file():
        raise ValueError(f"question-ids file does not exist: {path}")
    ids: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped not in seen:
            seen.add(stripped)
            ids.append(stripped)
    if not ids:
        raise ValueError(f"question-ids file contains no question ids: {path}")
    return tuple(ids)


# -- checkpointing -----------------------------------------------------------


def load_checkpoint(path: Path) -> dict[str, dict[str, object]]:
    """Read a checkpoint JSONL into ``question_id -> record``, last one wins."""
    records: dict[str, dict[str, object]] = {}
    if not path.is_file():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"[runner] skipping corrupt checkpoint line {line_number} in {path}", file=sys.stderr)
                continue
            if isinstance(record, dict) and isinstance(record.get("question_id"), str):
                records[record["question_id"]] = record
    return records


def completed_question_ids(records: dict[str, dict[str, object]], *, mode: str) -> set[str]:
    """Question ids that do not need re-running for this mode."""
    return {
        question_id
        for question_id, record in records.items()
        if record.get("status") == "ok" and record.get("mode") == mode
    }


class CheckpointWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, object]) -> None:
        line = json.dumps(record, ensure_ascii=True, sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()


# -- per-question pipeline ----------------------------------------------------


def _db_path_for(config: RunnerConfig, question_id: str) -> Path:
    return config.work_dir / f"{_FILENAME_SAFE.sub('_', question_id)}.sqlite3"


def _cleanup_store(db_path: Path) -> None:
    for suffix in ("", "-journal", "-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)


def run_question(
    question: LongMemEvalQuestion,
    config: RunnerConfig,
    *,
    model: ChatModelConfig | None,
    judge: ChatModelConfig | None,
    fingerprint_digest: str,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "mode": config.mode,
        "question_id": question.question_id,
        "question_type": question.question_type,
        "is_abstention": question.is_abstention,
        "gold_answer": question.answer,
        "fingerprint_digest": fingerprint_digest,
        "status": "ok",
        "error": None,
        "hypothesis": None,
        "judge": None,
        "generation": None,
    }
    db_path = _db_path_for(config, question.question_id)
    try:
        _cleanup_store(db_path)
        with question_run(question, db_path) as run:
            ingest_stats = run.ingest()
            outcome = run.retrieve(
                max_items=config.max_items,
                context_char_budget=config.context_char_budget,
            )
        record["ingest"] = ingest_stats.to_record()
        record["retrieval"] = outcome.to_record()

        if not config.dry_run:
            assert model is not None and judge is not None  # validated in main()
            prompt = build_answer_prompt(
                context_block=outcome.context_block,
                question=question.question,
                question_date=question.question_date,
                cot=config.cot,
            )
            completion = chat_completion(
                model,
                [{"role": "user", "content": prompt}],
                temperature=GENERATION_TEMPERATURE,
                max_tokens=ANSWER_MAX_TOKENS_COT if config.cot else ANSWER_MAX_TOKENS,
            )
            record["hypothesis"] = completion.text.strip()
            record["generation"] = {
                "prompt_chars": len(prompt),
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
                "latency_seconds": round(completion.latency_seconds, 3),
                "retries": completion.retries,
            }
            judge_result = judge_hypothesis(
                judge,
                question_type=question.question_type,
                question=question.question,
                gold_answer=question.answer,
                hypothesis=completion.text.strip(),
                is_abstention=question.is_abstention,
            )
            record["judge"] = judge_result.to_record()
    except Exception as exc:  # noqa: BLE001 - a bad question must not kill the run
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if not config.keep_stores:
            _cleanup_store(db_path)
    record["completed_at"] = _utc_now_iso()
    return record


# -- aggregation --------------------------------------------------------------


def _percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percent / 100.0 * len(ordered)) - 1))
    return ordered[index]


def _accuracy_bucket(records: list[dict[str, object]]) -> dict[str, object]:
    judged = [record for record in records if isinstance(record.get("judge"), dict)]
    correct = sum(1 for record in judged if record["judge"].get("correct") is True)  # type: ignore[index]
    return {
        "questions": len(judged),
        "correct": correct,
        "accuracy": round(correct / len(judged), 4) if judged else None,
    }


def aggregate_records(records: list[dict[str, object]]) -> dict[str, object]:
    ok_records = [record for record in records if record.get("status") == "ok"]
    error_records = [record for record in records if record.get("status") != "ok"]

    per_type: dict[str, dict[str, object]] = {}
    for record in ok_records:
        question_type = str(record.get("question_type"))
        per_type.setdefault(question_type, {"records": []})["records"].append(record)  # type: ignore[union-attr]
    per_type_summary = {
        question_type: _accuracy_bucket(bucket["records"])  # type: ignore[arg-type]
        for question_type, bucket in sorted(per_type.items())
    }

    retrieval_seconds = [
        float(record["retrieval"]["retrieval_seconds"])  # type: ignore[index]
        for record in ok_records
        if isinstance(record.get("retrieval"), dict)
    ]
    context_chars = [
        int(record["retrieval"]["context_chars"])  # type: ignore[index]
        for record in ok_records
        if isinstance(record.get("retrieval"), dict)
    ]
    approx_tokens = [
        int(record["retrieval"]["approx_context_tokens"])  # type: ignore[index]
        for record in ok_records
        if isinstance(record.get("retrieval"), dict)
    ]
    ingest_seconds = [
        float(record["ingest"]["ingest_seconds"])  # type: ignore[index]
        for record in ok_records
        if isinstance(record.get("ingest"), dict)
    ]
    vector_enabled_count = sum(
        1
        for record in ok_records
        if isinstance(record.get("retrieval"), dict) and record["retrieval"].get("vector_enabled") is True  # type: ignore[index]
    )

    overall = _accuracy_bucket(ok_records)
    return {
        "totals": {
            "questions": len(records),
            "ok": len(ok_records),
            "errors": len(error_records),
            "correct": overall["correct"],
            "accuracy": overall["accuracy"],
        },
        "abstention": _accuracy_bucket([record for record in ok_records if record.get("is_abstention") is True]),
        "non_abstention": _accuracy_bucket([record for record in ok_records if record.get("is_abstention") is not True]),
        "per_type": per_type_summary,
        "retrieval": {
            "context_chars_mean": round(sum(context_chars) / len(context_chars), 1) if context_chars else None,
            "approx_context_tokens_mean": round(sum(approx_tokens) / len(approx_tokens), 1) if approx_tokens else None,
            "retrieval_seconds_p50": _percentile(retrieval_seconds, 50),
            "retrieval_seconds_p95": _percentile(retrieval_seconds, 95),
            "ingest_seconds_mean": round(sum(ingest_seconds) / len(ingest_seconds), 3) if ingest_seconds else None,
            "vector_enabled_share": round(vector_enabled_count / len(ok_records), 4) if ok_records else None,
        },
        "failures": [
            {"question_id": record.get("question_id"), "error": record.get("error")} for record in error_records
        ],
    }


def build_report(
    config: RunnerConfig,
    fingerprint: dict[str, object],
    records: list[dict[str, object]],
    *,
    resumed_count: int,
) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": _utc_now_iso(),
        "config": fingerprint,
        "resumed_from_checkpoint": resumed_count,
        **aggregate_records(records),
    }


# -- CLI -----------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_longmemeval.py",
        description="Score Alice's capture + retrieval pipeline on LongMemEval.",
    )
    parser.add_argument("--variant", choices=VARIANTS, default="s", help="dataset variant (default: s)")
    parser.add_argument("--dataset-file", type=Path, default=None, help="explicit dataset JSON path (overrides --variant lookup)")
    parser.add_argument("--data-dir", type=Path, default=None, help="dataset directory (default: eval/longmemeval/data)")
    subset = parser.add_mutually_exclusive_group()
    subset.add_argument("--limit", type=int, default=None, help="only run the first N questions")
    subset.add_argument(
        "--question-ids",
        type=Path,
        default=None,
        help="file with one question_id per line (blank lines and # comments skipped); "
        "run only those questions — mutually exclusive with --limit",
    )
    parser.add_argument("--resume", action="store_true", help="skip questions already completed in the checkpoint")
    parser.add_argument("--report", type=Path, default=None, help="report JSON path (default: eval/longmemeval/results/)")
    parser.add_argument("--checkpoint", type=Path, default=None, help="checkpoint JSONL path (default: eval/longmemeval/results/)")
    parser.add_argument("--workers", type=int, default=2, help="parallel questions in flight (default: 2; keep small for rate limits)")
    parser.add_argument("--dry-run", action="store_true", help="ingest + retrieval only; no chat model, no judge")
    parser.add_argument("--cot", action="store_true", help="use the official chain-of-thought reading template")
    parser.add_argument("--max-items", type=int, default=None, help=f"context-pack max_items (default: ${'{'}ALICE_LME_MAX_ITEMS{'}'} or {DEFAULT_MAX_ITEMS})")
    parser.add_argument(
        "--context-char-budget",
        type=int,
        default=None,
        help=f"rendered context budget in characters (default: ${'{'}ALICE_LME_CONTEXT_CHAR_BUDGET{'}'} or {DEFAULT_CONTEXT_CHAR_BUDGET})",
    )
    parser.add_argument("--work-dir", type=Path, default=WORK_DIR, help="scratch dir for per-question SQLite stores")
    parser.add_argument("--keep-stores", action="store_true", help="keep per-question SQLite files for inspection")
    return parser


def _resolve_config(args: argparse.Namespace, *, question_ids: tuple[str, ...] | None = None) -> RunnerConfig | None:
    if args.dataset_file is not None:
        dataset_path = args.dataset_file
        if not dataset_path.is_file():
            print(f"[runner] dataset file does not exist: {dataset_path}", file=sys.stderr)
            return None
    else:
        resolved = (
            resolve_dataset_path(args.variant, data_dir=args.data_dir)
            if args.data_dir is not None
            else resolve_dataset_path(args.variant)
        )
        if resolved is None:
            return None
        dataset_path = resolved
    stem = f"longmemeval_{args.variant}" if args.dataset_file is None else dataset_path.stem
    return RunnerConfig(
        variant=args.variant,
        dataset_path=dataset_path,
        limit=args.limit,
        question_ids=question_ids,
        question_ids_file=args.question_ids.name if args.question_ids is not None else None,
        resume=args.resume,
        dry_run=args.dry_run,
        cot=args.cot,
        workers=max(1, args.workers),
        max_items=args.max_items if args.max_items is not None else max_items_from_env(),
        context_char_budget=(
            args.context_char_budget if args.context_char_budget is not None else context_char_budget_from_env()
        ),
        work_dir=args.work_dir,
        checkpoint_path=args.checkpoint or RESULTS_DIR / f"{stem}_checkpoint.jsonl",
        report_path=args.report or RESULTS_DIR / f"{stem}_report.json",
        keep_stores=args.keep_stores,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    question_ids: tuple[str, ...] | None = None
    if args.question_ids is not None:
        try:
            question_ids = load_question_ids(args.question_ids)
        except ValueError as exc:
            print(f"[runner] {exc}", file=sys.stderr)
            return EXIT_CONFIG_ERROR
    config = _resolve_config(args, question_ids=question_ids)
    if config is None:
        if args.dataset_file is not None:
            return EXIT_CONFIG_ERROR
        message = (
            f"[runner] dataset for variant {args.variant!r} not found under eval/longmemeval/data/. "
            "Fetch it with: python eval/longmemeval/fetch.py --variant " + args.variant
        )
        if args.dry_run:
            print(message + " — dry run skipped cleanly.")
            return EXIT_OK
        print(message, file=sys.stderr)
        return EXIT_CONFIG_ERROR

    model = model_config_from_env()
    judge = judge_config_from_env()
    if not config.dry_run and (model is None or judge is None):
        print(
            "[runner] a scored run needs ALICE_LME_MODEL_BASE_URL and ALICE_LME_MODEL "
            "(plus optional ALICE_LME_JUDGE_* overrides); use --dry-run for a model-free smoke.",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR
    if config.dry_run:
        model = None
        judge = None

    limit = config.limit
    if config.dry_run and limit is None and config.question_ids is None:
        limit = 2
    try:
        questions = load_dataset(config.dataset_path, limit=limit)
    except LongMemEvalDatasetError as exc:
        print(f"[runner] {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    if config.question_ids is not None:
        wanted = set(config.question_ids)
        questions = tuple(question for question in questions if question.question_id in wanted)
        missing = sorted(wanted - {question.question_id for question in questions})
        if missing:
            preview = ", ".join(missing[:5]) + (" ..." if len(missing) > 5 else "")
            print(
                f"[runner] {len(missing)} question ids from {args.question_ids} are not in the dataset: {preview}",
                file=sys.stderr,
            )
            return EXIT_CONFIG_ERROR
    if not questions:
        print("[runner] dataset contained no questions after --limit", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    fingerprint = config_fingerprint(config, model=model, judge=judge)
    fingerprint_digest = str(fingerprint["digest"])

    existing_records = load_checkpoint(config.checkpoint_path) if config.resume else {}
    done_ids = completed_question_ids(existing_records, mode=config.mode)
    if config.resume and existing_records:
        stale = {
            question_id
            for question_id in done_ids
            if existing_records[question_id].get("fingerprint_digest") != fingerprint_digest
        }
        if stale:
            print(
                f"[runner] warning: {len(stale)} resumed records were produced with a different config "
                "fingerprint; the report mixes configs. Delete the checkpoint for a clean run.",
                file=sys.stderr,
            )
    pending = [question for question in questions if question.question_id not in done_ids]

    config.work_dir.mkdir(parents=True, exist_ok=True)
    writer = CheckpointWriter(config.checkpoint_path)
    subset_note = f" subset={config.question_ids_file}({len(config.question_ids)})" if config.question_ids else ""
    print(
        f"[runner] mode={config.mode} variant={config.variant} questions={len(questions)}{subset_note} "
        f"pending={len(pending)} resumed={len(questions) - len(pending)} workers={config.workers} "
        f"fingerprint={fingerprint_digest}"
    )

    fresh_records: list[dict[str, object]] = []
    started = time.monotonic()
    if pending:
        with ThreadPoolExecutor(max_workers=config.workers) as pool:
            futures = {
                pool.submit(
                    run_question,
                    question,
                    config,
                    model=model,
                    judge=judge,
                    fingerprint_digest=fingerprint_digest,
                ): question
                for question in pending
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                record = future.result()
                writer.append(record)
                fresh_records.append(record)
                status = record["status"]
                verdict = ""
                if isinstance(record.get("judge"), dict):
                    verdict = " correct" if record["judge"].get("correct") else " wrong"  # type: ignore[index]
                print(
                    f"[runner] {completed}/{len(pending)} {record['question_id']} "
                    f"({record['question_type']}) {status}{verdict}",
                    flush=True,
                )

    resumed_records = [existing_records[question_id] for question_id in sorted(done_ids) if question_id in existing_records]
    all_records = resumed_records + fresh_records
    report = build_report(config, fingerprint, all_records, resumed_count=len(resumed_records))
    config.report_path.parent.mkdir(parents=True, exist_ok=True)
    config.report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    totals = report["totals"]
    print(
        f"[runner] done in {time.monotonic() - started:.1f}s — ok={totals['ok']} errors={totals['errors']} "
        f"accuracy={totals['accuracy']} report={config.report_path}"
    )

    if config.dry_run:
        empty_context_ids = [
            str(record["question_id"])
            for record in all_records
            if record.get("status") == "ok"
            and isinstance(record.get("retrieval"), dict)
            and int(record["retrieval"].get("context_chars") or 0) == 0  # type: ignore[index]
            and record.get("is_abstention") is not True
        ]
        if empty_context_ids:
            print(
                f"[runner] dry-run FAILED: empty retrieval context for {sorted(empty_context_ids)}",
                file=sys.stderr,
            )
            return EXIT_RUN_FAILURES
        if int(totals["errors"]) > 0:
            return EXIT_RUN_FAILURES
        print("[runner] dry-run OK: retrieval produced non-empty context for every non-abstention question.")
        return EXIT_OK

    return EXIT_OK if int(totals["errors"]) == 0 else EXIT_RUN_FAILURES


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CheckpointWriter",
    "EXIT_CONFIG_ERROR",
    "EXIT_OK",
    "EXIT_RUN_FAILURES",
    "HARNESS_VERSION",
    "REPORT_SCHEMA",
    "RESULT_SCHEMA",
    "RunnerConfig",
    "aggregate_records",
    "build_arg_parser",
    "build_report",
    "completed_question_ids",
    "config_fingerprint",
    "load_checkpoint",
    "load_question_ids",
    "main",
    "run_question",
]
