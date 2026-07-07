"""Paired comparison of two LongMemEval per-question JSONL result files.

Joins a baseline and a candidate run on ``question_id`` over the INTERSECTION
of judged questions and reports flips (wrong→right, right→wrong), the exact
two-sided McNemar p-value (binomial over the discordant pairs — no scipy),
a per-type breakdown, and the abstention-subset delta. Either file may be a
full-run export (e.g. docs/benchmarks/longmemeval/per-question-results.jsonl)
or a slice checkpoint; duplicate rows per question_id keep the LAST one, so
resumed checkpoints compare correctly.

Usage:

    python eval/longmemeval/compare_runs.py BASELINE.jsonl CANDIDATE.jsonl [--json]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys


EXIT_OK = 0
EXIT_CONFIG_ERROR = 2

ABSTENTION_SUFFIX = "_abs"


def read_jsonl_records(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"[compare] skipping corrupt line {line_number} in {path}", file=sys.stderr)
                continue
            if isinstance(record, dict):
                records.append(record)
    return records


def dedupe_last(records: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    """``question_id -> record``, keeping the LAST occurrence of each id."""
    by_id: dict[str, dict[str, object]] = {}
    for record in records:
        question_id = record.get("question_id")
        if isinstance(question_id, str) and question_id:
            by_id[question_id] = record
    return by_id


def judged_correct(record: dict[str, object]) -> bool | None:
    """The judge verdict for a record, or ``None`` if it was not judged."""
    judge = record.get("judge")
    if isinstance(judge, dict) and isinstance(judge.get("correct"), bool):
        return bool(judge["correct"])
    return None


def exact_mcnemar_p(b: int, c: int) -> float:
    """Exact two-sided McNemar p-value.

    ``b`` and ``c`` are the discordant-pair counts (wrong→right, right→wrong).
    Under H0 each discordant pair flips either way with probability 1/2, so
    the p-value is the two-sided exact binomial: ``2 * P(X <= min(b, c))``
    with ``X ~ Binomial(b + c, 1/2)``, capped at 1.0.
    """
    if b < 0 or c < 0:
        raise ValueError("discordant counts must be non-negative")
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2.0 * tail)


def _is_abstention(record: dict[str, object], question_id: str) -> bool:
    if record.get("is_abstention") is True:
        return True
    return question_id.endswith(ABSTENTION_SUFFIX)


def compare_records(
    baseline: dict[str, dict[str, object]],
    candidate: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Paired comparison over the intersection of judged question ids."""
    joint_ids = sorted(
        question_id
        for question_id in baseline.keys() & candidate.keys()
        if judged_correct(baseline[question_id]) is not None
        and judged_correct(candidate[question_id]) is not None
    )

    both_right = both_wrong = flips_gained = flips_lost = 0
    per_type: dict[str, dict[str, int]] = {}
    abstention = {"n": 0, "baseline_correct": 0, "candidate_correct": 0}
    baseline_correct_total = candidate_correct_total = 0

    for question_id in joint_ids:
        base_record = baseline[question_id]
        cand_record = candidate[question_id]
        base_ok = judged_correct(base_record)
        cand_ok = judged_correct(cand_record)
        assert base_ok is not None and cand_ok is not None  # filtered above
        baseline_correct_total += int(base_ok)
        candidate_correct_total += int(cand_ok)
        if base_ok and cand_ok:
            both_right += 1
        elif not base_ok and not cand_ok:
            both_wrong += 1
        elif cand_ok:
            flips_gained += 1
        else:
            flips_lost += 1

        question_type = str(cand_record.get("question_type") or base_record.get("question_type") or "unknown")
        bucket = per_type.setdefault(
            question_type,
            {"n": 0, "baseline_correct": 0, "candidate_correct": 0, "gained": 0, "lost": 0},
        )
        bucket["n"] += 1
        bucket["baseline_correct"] += int(base_ok)
        bucket["candidate_correct"] += int(cand_ok)
        bucket["gained"] += int(cand_ok and not base_ok)
        bucket["lost"] += int(base_ok and not cand_ok)

        if _is_abstention(cand_record, question_id) or _is_abstention(base_record, question_id):
            abstention["n"] += 1
            abstention["baseline_correct"] += int(base_ok)
            abstention["candidate_correct"] += int(cand_ok)

    n = len(joint_ids)
    per_type_summary = {
        question_type: {
            **bucket,
            "net": bucket["gained"] - bucket["lost"],
            "baseline_accuracy": round(bucket["baseline_correct"] / bucket["n"], 4),
            "candidate_accuracy": round(bucket["candidate_correct"] / bucket["n"], 4),
        }
        for question_type, bucket in sorted(per_type.items())
    }
    return {
        "n_compared": n,
        "baseline_judged": sum(1 for record in baseline.values() if judged_correct(record) is not None),
        "candidate_judged": sum(1 for record in candidate.values() if judged_correct(record) is not None),
        "baseline_correct": baseline_correct_total,
        "candidate_correct": candidate_correct_total,
        "baseline_accuracy": round(baseline_correct_total / n, 4) if n else None,
        "candidate_accuracy": round(candidate_correct_total / n, 4) if n else None,
        "both_right": both_right,
        "both_wrong": both_wrong,
        "flips_gained": flips_gained,
        "flips_lost": flips_lost,
        "net": flips_gained - flips_lost,
        "mcnemar_p": exact_mcnemar_p(flips_gained, flips_lost),
        "per_type": per_type_summary,
        "abstention": {
            **abstention,
            "delta": abstention["candidate_correct"] - abstention["baseline_correct"],
        },
    }


def render_table(summary: dict[str, object]) -> str:
    lines: list[str] = []
    n = summary["n_compared"]
    lines.append(
        f"compared {n} judged questions "
        f"(baseline judged {summary['baseline_judged']}, candidate judged {summary['candidate_judged']})"
    )
    if not n:
        lines.append("no overlapping judged questions — nothing to compare.")
        return "\n".join(lines)
    lines.append(
        f"accuracy: baseline {summary['baseline_correct']}/{n} ({summary['baseline_accuracy']}) -> "
        f"candidate {summary['candidate_correct']}/{n} ({summary['candidate_accuracy']})"
    )
    lines.append(
        f"flips: +{summary['flips_gained']} gained (wrong->right), -{summary['flips_lost']} lost (right->wrong), "
        f"net {summary['net']:+d}"
    )
    p_value = summary["mcnemar_p"]
    lines.append(
        f"McNemar exact two-sided p = {p_value:.6f}" if p_value >= 1e-6 else f"McNemar exact two-sided p = {p_value:.3g}"
    )
    lines.append("")
    header = f"{'question_type':28s} {'n':>4s} {'base':>6s} {'cand':>6s} {'gained':>6s} {'lost':>5s} {'net':>4s}"
    lines.append(header)
    lines.append("-" * len(header))
    for question_type, bucket in summary["per_type"].items():  # type: ignore[union-attr]
        lines.append(
            f"{question_type:28s} {bucket['n']:>4d} {bucket['baseline_correct'] / bucket['n']:>6.3f} "
            f"{bucket['candidate_correct'] / bucket['n']:>6.3f} {bucket['gained']:>6d} {bucket['lost']:>5d} {bucket['net']:>+4d}"
        )
    abstention = summary["abstention"]
    lines.append("")
    lines.append(
        f"abstention subset: n={abstention['n']} baseline_correct={abstention['baseline_correct']} "
        f"candidate_correct={abstention['candidate_correct']} delta={abstention['delta']:+d}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compare_runs.py",
        description="Paired comparison of two LongMemEval per-question JSONL files.",
    )
    parser.add_argument("baseline", type=Path, help="baseline per-question JSONL (full run or checkpoint)")
    parser.add_argument("candidate", type=Path, help="candidate per-question JSONL (e.g. a slice checkpoint)")
    parser.add_argument("--json", action="store_true", help="emit the summary as JSON instead of a table")
    args = parser.parse_args(argv)

    for path in (args.baseline, args.candidate):
        if not path.is_file():
            print(f"[compare] file does not exist: {path}", file=sys.stderr)
            return EXIT_CONFIG_ERROR

    baseline = dedupe_last(read_jsonl_records(args.baseline))
    candidate = dedupe_last(read_jsonl_records(args.candidate))
    summary = compare_records(baseline, candidate)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_table(summary))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EXIT_CONFIG_ERROR",
    "EXIT_OK",
    "compare_records",
    "dedupe_last",
    "exact_mcnemar_p",
    "judged_correct",
    "main",
    "read_jsonl_records",
    "render_table",
]
