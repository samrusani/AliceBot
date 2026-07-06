"""Generate the fixed stage-1 LongMemEval slice (``stage1-150.txt``).

Selection rule (deterministic, documented here and in the slice file header):

1. Per question type, take every question_id of that type from the dataset
   (abstention questions included), sort the ids lexicographically, and
   stratify: with ``n_type`` ids in the pool and ``n_wanted`` to select,
   ``k = floor(n_type / n_wanted)`` (min 1) and the picks are the ids at
   indices ``0, k, 2k, ..., (n_wanted - 1) * k`` — spanning the sorted list.
2. Type quotas: multi-session 50, temporal-reasoning 40, knowledge-update 20,
   single-session-assistant 15, single-session-preference 15,
   single-session-user 10 (150 total).
3. All abstention questions (question_id ending in ``_abs``) are appended in
   lexicographic order, deduplicated against the per-type picks (an
   abstention id already selected in step 1 is not repeated).

The output file lists the per-type picks first (quota order below), then the
remaining abstention ids. Regenerate with:

    .venv/bin/python eval/longmemeval/slices/generate_stage1.py

The rule is pure over (question_id, question_type) pairs: rerunning against
the same dataset always yields byte-identical output.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Mapping, Sequence

_EVAL_DIR = Path(__file__).resolve().parent.parent.parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

from longmemeval.dataset import ABSTENTION_SUFFIX, resolve_dataset_path

import json


SLICE_PATH = Path(__file__).resolve().parent / "stage1-150.txt"

# Quota order is also the output-file section order.
STAGE1_TYPE_QUOTAS: tuple[tuple[str, int], ...] = (
    ("multi-session", 50),
    ("temporal-reasoning", 40),
    ("knowledge-update", 20),
    ("single-session-assistant", 15),
    ("single-session-preference", 15),
    ("single-session-user", 10),
)


def stratified_picks(pool: Sequence[str], n_wanted: int) -> list[str]:
    """Every k-th id from the lexicographically sorted pool, k=floor(n/n_wanted)."""
    ordered = sorted(pool)
    if len(ordered) < n_wanted:
        raise ValueError(f"pool has {len(ordered)} ids but {n_wanted} were requested")
    k = max(1, len(ordered) // n_wanted)
    return [ordered[i * k] for i in range(n_wanted)]


def select_stage1_ids(
    records: Sequence[Mapping[str, object]],
    *,
    quotas: tuple[tuple[str, int], ...] = STAGE1_TYPE_QUOTAS,
) -> tuple[str, ...]:
    """Deterministic stage-1 selection over (question_id, question_type) pairs."""
    by_type: dict[str, list[str]] = {}
    for record in records:
        by_type.setdefault(str(record["question_type"]), []).append(str(record["question_id"]))
    selected: list[str] = []
    for question_type, n_wanted in quotas:
        selected.extend(stratified_picks(by_type.get(question_type, []), n_wanted))
    abstention = sorted(
        str(record["question_id"])
        for record in records
        if str(record["question_id"]).endswith(ABSTENTION_SUFFIX)
    )
    seen: set[str] = set()
    ordered: list[str] = []
    for question_id in [*selected, *abstention]:
        if question_id not in seen:
            seen.add(question_id)
            ordered.append(question_id)
    return tuple(ordered)


def render_slice_file(records: Sequence[Mapping[str, object]], *, dataset_name: str) -> str:
    ids = select_stage1_ids(records)
    id_set = set(ids)
    type_of = {str(record["question_id"]): str(record["question_type"]) for record in records}
    abstention_count = sum(1 for question_id in ids if question_id.endswith(ABSTENTION_SUFFIX))
    lines = [
        "# LongMemEval stage-1 slice — FIXED, do not regenerate casually.",
        f"# Source dataset: {dataset_name}",
        "# Selection rule (deterministic): per question type, sort question_ids",
        "# lexicographically and stratify — k = floor(n_type / n_wanted), pick indices",
        "# 0, k, 2k, ..., (n_wanted - 1) * k. Quotas: multi-session 50,",
        "# temporal-reasoning 40, knowledge-update 20, single-session-assistant 15,",
        "# single-session-preference 15, single-session-user 10 (150 total). Then ALL",
        "# abstention questions (_abs suffix) are appended in lexicographic order,",
        "# deduplicated against the per-type picks.",
        f"# Totals: {len(ids)} ids ({abstention_count} abstention).",
        "# Regenerate: .venv/bin/python eval/longmemeval/slices/generate_stage1.py",
    ]
    per_type_end = sum(n_wanted for _, n_wanted in STAGE1_TYPE_QUOTAS)
    cursor = 0
    for question_type, n_wanted in STAGE1_TYPE_QUOTAS:
        lines.append(f"# -- {question_type} ({n_wanted}) --")
        lines.extend(ids[cursor : cursor + n_wanted])
        cursor += n_wanted
    extra_abstention = ids[per_type_end:]
    lines.append(f"# -- additional abstention ({len(extra_abstention)}) --")
    lines.extend(extra_abstention)
    # Sanity: every listed id exists in the dataset.
    for question_id in ids:
        if question_id not in type_of:
            raise ValueError(f"selected id missing from dataset: {question_id}")
    assert len(ids) == len(id_set)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the fixed stage-1 LongMemEval slice file.")
    parser.add_argument("--dataset-file", type=Path, default=None, help="dataset JSON (default: variant s lookup)")
    parser.add_argument("--output", type=Path, default=SLICE_PATH, help=f"output path (default: {SLICE_PATH})")
    args = parser.parse_args(argv)

    dataset_path = args.dataset_file if args.dataset_file is not None else resolve_dataset_path("s")
    if dataset_path is None or not dataset_path.is_file():
        print("[stage1] dataset not found; pass --dataset-file", file=sys.stderr)
        return 2
    records = json.loads(dataset_path.read_text(encoding="utf-8"))
    content = render_slice_file(records, dataset_name=dataset_path.name)
    args.output.write_text(content, encoding="utf-8")
    id_count = sum(1 for line in content.splitlines() if line and not line.startswith("#"))
    print(f"[stage1] wrote {id_count} question ids to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SLICE_PATH",
    "STAGE1_TYPE_QUOTAS",
    "render_slice_file",
    "select_stage1_ids",
    "stratified_picks",
]
