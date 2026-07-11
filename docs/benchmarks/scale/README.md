# Alice scale envelope: core-operation latency at 1k / 10k / 100k memories

Measured 2026-07-06 on an Apple Silicon laptop (single machine, no
concurrency), seeded with a deterministic synthetic corpus and embeddings
from a deterministic in-process provider (so the vector stage runs at every
scale without network calls). The tables report p50 over the operation-specific
iteration counts recorded in each raw result (20–50 after warmup; slow
operations stop at a disclosed time budget). Reproduction command below. Raw
results are in [results/](results/).

## The two numbers that matter for agents

| Operation | Backend | 1k | 10k | 100k |
|---|---|---|---|---|
| **recall (context pack)** | SQLite | 18.4ms | 198.5ms | 2253.7ms |
| | Postgres | 22.9ms | 98.4ms | 393.6ms |
| **memory commit** | SQLite | 2.3ms | 2.3ms | 2.4ms |
| | Postgres | 15.5ms | 17.7ms | 20.1ms |

## Full matrix (p50)

| Operation | Backend | 1k | 10k | 100k |
|---|---|---|---|---|
| capture (single text) | SQLite | 1.3ms | 2.7ms | 18.3ms |
| | Postgres | 9.0ms | 9.2ms | 14.3ms |
| review queue list | SQLite | 0.5ms | 6.3ms | 72.0ms |
| | Postgres | 1.7ms | 6.4ms | 69.1ms |
| entity lookup (by names) | SQLite | 0.1ms | 0.2ms | 1.9ms |
| | Postgres | 0.5ms | 0.4ms | 1.2ms |
| graph one-hop (hot entity) | SQLite | 0.3ms | 2.2ms | 34.1ms |
| | Postgres | 1.2ms | 1.7ms | 11.8ms |
| staleness sweep (full pass) | SQLite | 12.9ms | 138.8ms | 1786.6ms |
| | Postgres | 13.3ms | 179.8ms | 1856.5ms |
| consolidation clustering pass | SQLite | 154.4ms | 1373.6ms | 4682.3ms |
| | Postgres | 174.1ms | 1348.4ms | 2684.6ms |

Ingest throughput: SQLite ~1,000–1,300 memories/sec at every scale;
Postgres ~65–137 memories/sec (per-row round-trips; bulk import is not yet
optimized).

## What this means in practice

- **SQLite (the `uvx alice-memory` trial path)**: writes are effectively
  instant at any scale, and recall is excellent through ~10k memories
  (~200ms). Beyond ~20–30k memories **with embeddings**, the deliberate
  brute-force vector design (no ANN index in SQLite) makes recall slow —
  2.3s at 100k. That is the documented boundary: move to Postgres for large
  corpora, or run FTS-only.
- **Postgres**: production-viable across the board — ~20ms commits and
  ~400ms recall at 100k memories. Recall's growth (23 → 98 → 394ms) is a
  known optimization candidate, not a wall.
- **Scheduled jobs** are nightly-cadence work, not request-path latency.
  Staleness is a full-corpus scan. Consolidation clustering is worst-case
  quadratic; the current implementation bounds its corpus to 2,000 memories,
  its float32 matrix to 16 MB, and unique comparisons to 1,999,000. These
  historical 2026-07-06 measurements used the then-current implementation and
  should not be read as proof of linear consolidation scaling.

## Found and fixed by this benchmark

The first measurement run caught a real production bug: SQLite memory
commits ran an O(N) Python idempotency scan (18ms at 1k → 222ms at 10k →
3.5s at 100k) because the indexed `get_memory_by_commit_digest` fast path
existed only on Postgres. The fix (store method + partial indexes) took
commits to a flat 2.3ms at every scale. Pre-fix results are archived in
[results-prefix-archive/](results-prefix-archive/) as the before/after
record. The run also added post-ingest `ANALYZE` so Postgres is measured on
realistic query plans rather than stale statistics.

## Caveats

- Single machine, single connection, no concurrent load — this is an
  envelope, not a load test.
- Deterministic synthetic corpus and embeddings; real text and real
  embedding endpoints change absolute numbers (not the shapes).
- Postgres runs in a local Docker container (pgvector/pgvector:pg16) with
  fsync-default settings.

## Reproduce

```bash
.venv/bin/python scripts/run_scale_benchmark.py \
    --scales 1000,10000,100000 --backends sqlite,postgres
```

Roughly 35 minutes total; no network or API keys required.
