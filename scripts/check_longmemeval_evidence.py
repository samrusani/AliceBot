#!/usr/bin/env python3
"""Verify that committed LongMemEval comparisons match their checkpoints.

This gate is deliberately offline.  It does not bless the experimental
design or incomplete historical fingerprints; it proves only that every
comparison cited by the technical report is reproducible byte-for-byte from
the committed baseline and candidate rows.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = REPO_ROOT / "eval"
if str(EVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(EVAL_ROOT))

from longmemeval.compare_runs import (  # noqa: E402
    compare_records,
    dedupe_last,
    read_jsonl_records,
    render_table,
)


BASELINE = REPO_ROOT / "docs/benchmarks/longmemeval/per-question-results-2026-07-07.jsonl"
EVIDENCE_DIR = REPO_ROOT / "docs/benchmarks/longmemeval/saturation-evidence"
ARMS = (
    "vectors-reranker-rollups",
    "vectors-reranker",
    "vectors-only",
    "vectors-gpt41-reader",
    "round6-prose",
    "round6-json",
    "vectors-o4mini-reader",
)


def validate() -> list[str]:
    failures: list[str] = []
    baseline = dedupe_last(read_jsonl_records(BASELINE))
    for arm in ARMS:
        checkpoint = EVIDENCE_DIR / f"{arm}-checkpoint.jsonl"
        comparison = EVIDENCE_DIR / f"{arm}-compare.txt"
        if not checkpoint.is_file() or not comparison.is_file():
            failures.append(f"{arm}: missing checkpoint or comparison")
            continue
        candidate = dedupe_last(read_jsonl_records(checkpoint))
        summary = compare_records(baseline, candidate)
        rendered = render_table(summary) + "\n"
        if comparison.read_text(encoding="utf-8") != rendered:
            failures.append(f"{arm}: comparison does not match checkpoint")
        digests = {
            str(row.get("fingerprint_digest"))
            for row in candidate.values()
            if row.get("status") == "ok"
        }
        if len(digests) != 1:
            failures.append(f"{arm}: candidate rows contain {len(digests)} fingerprints")
        if int(summary["candidate_judged"]) == 0:
            failures.append(f"{arm}: no judged candidate rows")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print(json.dumps({"status": "FAIL", "failures": failures}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "arms": len(ARMS), "baseline": BASELINE.name}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
