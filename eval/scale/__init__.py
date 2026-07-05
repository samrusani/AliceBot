"""Scale-envelope benchmark harness for Alice's core store operations.

Measures p50/p95 latency of the product read/write paths (capture, commit,
recall, review queue, entity lookup, graph hop, staleness sweep,
consolidation) against synthetic-but-realistic corpora of 1k/10k/100k
memories on both the SQLite on-ramp store and the Postgres store.

Everything is deterministic (seeded corpus, hash-derived embeddings) so runs
are reproducible; see docs/benchmarks/scale/README.md for methodology and
published results.
"""
