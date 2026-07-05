# Alice on LongMemEval

**Overall accuracy: 64.6% (323/500) on LongMemEval_s** — run 2026-07-05 at
commit `eda49da` with GPT-4o generation and the benchmark's official judge
protocol. All 500 questions answered and judged; the complete per-question
evidence is in [per-question-results.jsonl](per-question-results.jsonl) and
the aggregate report in [report.json](report.json).

## Results

| Question type | Accuracy | Correct |
|---|---|---|
| single-session-user | 90.0% | 63/70 |
| single-session-assistant | 75.0% | 42/56 |
| knowledge-update | 74.4% | 58/78 |
| temporal-reasoning | 61.7% | 82/133 |
| single-session-preference | 60.0% | 18/30 |
| multi-session | 45.1% | 60/133 |
| **Overall** | **64.6%** | **323/500** |

Non-abstention subset (the figure most reports quote): **63.4%** (298/470).
Abstention subset: 83.3% (25/30).

Published reference points on the same benchmark: Zep reports 63.8% and
Mem0 has been reported around 49% (both with GPT-4o-class generators).
**Direct comparison carries caveats** — see below.

## What was measured

The full Alice pipeline, per question, in an isolated store:

1. Every haystack session is ingested through Alice's real capture service
   (chunking, candidate extraction, provenance) into a fresh SQLite store,
   with embed-on-write via `text-embedding-3-small`.
2. At answer time, Alice's production retrieval (`compile_context_pack`:
   SQLite FTS5 + vector cosine fused with reciprocal-rank fusion, token
   budget enforced) builds the context block — mean ~3.0k tokens of context
   per question, retrieval p50 ~0.2s.
3. `gpt-4o` (temperature 0) answers from that context using the benchmark's
   official reading templates.
4. `gpt-4o-2024-08-06` judges with the benchmark's official per-type judge
   prompts (ported verbatim).

Config fingerprint `798c10822f50a667`; dataset
`longmemeval_s_cleaned.json` (sha256 prefix `d6f21ea9d60a0d56`, the
post-2025/09 cleaned release).

## Reproduce

```bash
python eval/longmemeval/fetch.py --variant s
export ALICE_LME_MODEL_BASE_URL=https://api.openai.com/v1 \
       ALICE_LME_MODEL=gpt-4o \
       ALICE_LME_MODEL_API_KEY=... \
       ALICE_LME_JUDGE_MODEL=gpt-4o-2024-08-06 \
       ALICE_EMBEDDINGS_BASE_URL=https://api.openai.com/v1 \
       ALICE_EMBEDDINGS_MODEL=text-embedding-3-small \
       ALICE_EMBEDDINGS_API_KEY=...
python scripts/run_longmemeval.py --variant s --workers 8 --resume
```

Roughly 2.5 hours and under $10 of API usage with this configuration.

## Honest caveats

- **Run-to-run variance is real; treat single-run deltas under ~2 points as
  noise.** Three full 500-question runs have been completed: 64.2% and
  64.6% on the quoted release, and 63.0% on a later build that added
  entity-graph retrieval. The spread (63.0–64.6, mean ≈ 63.9) is consistent
  with binomial variance at n=500 under non-bit-deterministic temperature-0
  inference. We quote 64.6% because it is the run with the complete archived
  per-question evidence; the honest summary is "approximately 64%".
- **Negative result, disclosed:** the entity-graph retrieval stage (which
  provably lifts entity-name queries in `graph_hop_retrieval` from 0.0 to
  1.0 recall) did **not** move this benchmark's multi-session category
  (45.1% → 42.1%, within noise). Diagnosis: LongMemEval's multi-session
  questions aggregate everyday facts with no named entities to hop through.
  The mechanism is real; this benchmark's weakest category needs retrieval
  breadth, not graphs.
- **Breadth ablation (multi-session only):** re-running just the 133
  multi-session questions with widened retrieval (16 items, ~6k context
  tokens instead of ~3k) scored **49.2%** — a directional +4–7 point lift
  over the 42.1%/45.1% full-run readings at double the context cost. This
  motivates the planned aggregation mode (query-shape-aware breadth
  defaults); it is reported here as an ablation with its config disclosed,
  not folded into the headline number.
- **Cross-system comparisons are approximate.** Published numbers for other
  systems use their own ingestion, retrieval, prompt, and (sometimes) judge
  variations. The judge model and prompts here are the benchmark's official
  ones; the generator matches the model class used in the published Zep
  figure.
- **Dataset variant.** These numbers use the cleaned 2025-09 dataset
  release; older reports may use the original files.

## What the breakdown says about Alice

Knowledge-update (74.4%) validates the correction/supersession machinery:
when facts change across sessions, Alice's retrieval surfaces the current
truth. Temporal-reasoning (61.7%) benefits from event-time capture. The
clear frontier is **multi-session synthesis (45.1%)** — questions whose
answers must be assembled from evidence scattered across many sessions.
That is a retrieval-breadth and consolidation problem, and it is exactly
what the consolidation engine (embedding clustering → merge candidates)
was built to start addressing. Improving it is the top benchmark-driven
roadmap item.
