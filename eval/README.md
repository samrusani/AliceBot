# AliceBot evals

This page documents what each eval in this repository actually measures, what
requires a live database, and which historical numbers should *not* be read
as benchmarks.

## vNext eval harness (`alicebot eval ...`)

Implemented in `apps/api/src/alicebot_api/vnext_evals.py`. The harness was
rewritten to measure the real system: every suite either executes production
code or reports `status: "skipped"` with a reason. The overall report status
is `pass` only when every *executed* suite passed; skipped suites are listed
under `skipped_suites` and never counted as a pass. If nothing could execute,
the report status is `skipped`.

> The previous revision of this harness ran 12 suites ("recall", "temporal",
> "privacy", "prompt_injection", "context_efficiency", ...) that scored a
> synthetic fixture generator against its own invariants — no production
> retrieval, policy, or sanitization code was ever invoked, and several
> metrics (e.g. `tool_write_executed: False`) were hard-coded so they could
> not fail. Those suites and their always-green reports were deleted. Any
> historical `vnext_eval_latest.json` produced by that harness (schema
> `vnext_eval_report_v0`, generated_at `2026-05-11T00:00:00Z`) is meaningless
> and should be discarded.

### Suite: `retrieval_quality`

The one current suite. It executes the production retrieval pipeline
end-to-end against either backend — Postgres (`PostgresVNextStore`) or the
zero-infrastructure SQLite on-ramp (`SQLiteVNextStore`), selected by the
URL in `ALICEBOT_EVAL_DATABASE_URL`:

1. Seeds a deterministic 216-memory corpus through the real store
   `create_memory` write path (inside a rolled-back transaction — nothing
   persists after the run on either backend).
2. If an embedding provider is configured (`ALICE_EMBEDDINGS_BASE_URL` +
   `ALICE_EMBEDDINGS_MODEL`), embeds every memory through the real provider
   and writes vectors into the store (pgvector column on Postgres, float32
   blob on SQLite).
3. Runs 48 queries through `VNextRetrievalService.compile_context_pack` —
   the same hybrid FTS + vector KNN + reciprocal-rank-fusion path the
   product uses (Postgres FTS + pgvector, or SQLite FTS5 + numpy cosine) —
   and scores the fused ranking.

The report labels which backend ran (`metrics.backend`:
`"postgres"` / `"sqlite"`).

Every query is phrased differently from its target memory:

- **`lexical_overlap` subset (32 queries)** — reworded questions that keep
  most of the memory's vocabulary (word order changes, inflection changes,
  dropped words). Verbatim token overlap with the target is in the ~0.6–0.85
  band. The FTS stage (Postgres FTS or SQLite FTS5) should handle these on
  its own.
- **`paraphrase` subset (16 queries)** — pure paraphrases (synonyms, reworded
  intent, e.g. memory "Q3 board pack is due Thursday..." vs. query "when is
  the quarterly board deck deadline") with near-zero verbatim overlap
  (< 0.4, mostly 0.0). FTS alone is expected to struggle here; the vector
  stage is what should recover them.

Reported metrics: recall@1, recall@5, MRR (overall and per subset), per-query
latency with p50/p95/max (wall-clock around the full context-pack compile),
`retrieval_mode` (`hybrid` / `fts_only` / `mixed`), and seeding/embedding
counts.

Enforced targets (`RETRIEVAL_QUALITY_TARGETS`):

| Target | Threshold | Enforced |
| --- | --- | --- |
| `lexical_overlap_recall_at_5` | >= 0.80 | always |
| `lexical_overlap_mrr` | >= 0.60 | always |
| `paraphrase_recall_at_5` | >= 0.70 | only when the vector stage ran (`retrieval_mode: hybrid`) |

When no embedding provider is configured the run degrades to FTS-only: the
paraphrase numbers are still measured and reported (expect ~0.0 recall — that
is the honest signal, not a bug), but the paraphrase target is not enforced.
The report always says which mode ran (`paraphrase_targets_enforced`).

The corpus is derived from hand-authored template pairs expanded by index
arithmetic — fully deterministic, no randomness at runtime. `alicebot eval
seed` writes it to `eval/fixtures/vnext_benchmark_corpus.json` if you want to
inspect it; the harness generates it in memory otherwise.

### Running against SQLite (no services)

The fastest live run needs nothing but the repo checkout — no Docker, no
Postgres:

```bash
ALICEBOT_EVAL_DATABASE_URL="sqlite:///:memory:" alicebot eval run --suite retrieval_quality
```

A file path (`sqlite:///eval.db`) works too and behaves the same: the
harness bootstraps the schema, seeds and queries inside one explicit
transaction, and rolls it back — zero rows persist afterwards (a file-backed
run leaves only the empty schema; the FTS5 index writes roll back with the
transaction, which is unit-tested). Embeddings work the same way as on
Postgres: configure `ALICE_EMBEDDINGS_BASE_URL` + `ALICE_EMBEDDINGS_MODEL`
to activate the vector stage; without them the run is FTS5-only and the
paraphrase target is reported but not enforced.

### Comparing backends

There is no special orchestration — run the suite twice with different URLs
and compare the two reports; each is labelled via `metrics.backend`:

```bash
ALICEBOT_EVAL_DATABASE_URL="postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot" \
  alicebot eval run --suite retrieval_quality --report-path eval/reports/vnext_eval_postgres.json
ALICEBOT_EVAL_DATABASE_URL="sqlite:///:memory:" \
  alicebot eval run --suite retrieval_quality --report-path eval/reports/vnext_eval_sqlite.json
```

### Running against a local Postgres

The suite needs a live, migrated Postgres (it is *skipped*, never faked,
without one):

```bash
# 1. Start the local stack (pgvector image + role bootstrap):
docker compose up -d postgres

# 2. Migrate (admin URL):
alembic upgrade head   # or your usual migration entrypoint

# 3. Point the eval at the app-role URL and run:
export ALICEBOT_EVAL_DATABASE_URL="postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
# optional, enables the vector stage / paraphrase target:
export ALICE_EMBEDDINGS_BASE_URL="http://localhost:11434/v1"   # any OpenAI-compatible /embeddings
export ALICE_EMBEDDINGS_MODEL="nomic-embed-text"

alicebot eval run --suite all --report-path eval/reports/vnext_eval_latest.json
```

Notes:

- `ALICEBOT_EVAL_DATABASE_URL` is a deliberate opt-in, separate from
  `DATABASE_URL`, so unit tests and unrelated CLI use never write eval
  corpora into a working database by accident. All seeded rows (memories,
  the eval user, event-log entries) are rolled back at the end of the run
  regardless.
- `ALICEBOT_AUTH_USER_ID` selects the acting user id if you need a specific
  one; otherwise a fixed default is used.
- Programmatic use: `run_retrieval_quality_eval(store)` accepts any live
  store handle directly; `run_vnext_evals(...)` also accepts `store=` /
  `retrieval_fn=` injection.
- The `--suite` help text in `cli.py` still lists the deleted v0 suite names;
  passing one of them now raises `unknown vNext eval suite`. Only `all` and
  `retrieval_quality` are valid.

### What the unit tests cover (and don't)

`tests/unit/test_vnext_evals.py` validates the metric math (recall@k, MRR,
percentiles, RRF-ordering consistency) against fake retrieval functions with
known rankings, the corpus paraphrase properties (token-overlap bands), the
skip semantics, and the report shape. Since the SQLite backend landed, the
unit tests **also execute the full live pipeline** against
`sqlite:///:memory:` and a temp file — real seeding, FTS5 retrieval, RRF
fusion, and rollback — so the live eval path runs in CI with no external
services. They assert lexical recall@5 == 1.0 on FTS5 alone and paraphrase
recall == 0.0 without embeddings (the honest degraded number). What unit
tests still cannot tell you is how the Postgres backend or a configured
embedding provider performs — for that, run the CLI against the real thing
as above.

## Legacy baselines in `eval/baselines/` — read with caution

These files are historical snapshots, **not benchmarks**:

- **`public_eval_harness_v1.json`** / **`eval/fixtures/public_eval_suites.json`**
  (the `alicebot evals ...` public harness, `public_evals.py`): the recall
  suite is 7 hand-authored fixtures with only 0–3 candidate memories each —
  far too small to measure retrieval quality. One case
  (`entity_edge_expansion_recovers_related_owner`) scores **0.0** yet is
  counted as `pass` because the fixture sets
  `require_expected_top_result: false`. The headline "pass rate 1.0 /
  average score 0.857" therefore includes a case that found nothing.
- **`retrieval_eval_hybrid_v2.json`**: 6 fixtures with 1–3 candidates each;
  `precision_at_1_mean: 1.0` over a candidate pool this small says nothing
  about ranking at realistic corpus sizes.
- **`phase9_s37_baseline.json`**: an importer/dedupe smoke snapshot, not a
  quality eval.

None of these numbers should be quoted as retrieval quality. For an actual
measurement, run the `retrieval_quality` suite above against a live store
with embeddings configured.
