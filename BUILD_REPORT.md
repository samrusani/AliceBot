# BUILD_REPORT

## sprint objective

Implement Sprint 5D: Local Artifact Ingestion V0 by adding a narrow, deterministic ingestion path that reads one registered local text artifact from its persisted task workspace boundary, chunks normalized text into durable ordered records, and exposes stable chunk reads without adding retrieval, embeddings, connectors, runners, or UI scope.

## completed work

- Added migration `apps/api/alembic/versions/20260314_0024_task_artifact_chunks.py`.
- Expanded `task_artifacts.ingestion_status` from `pending` to `pending | ingested`.
- Added durable `task_artifact_chunks` storage with user scoping, RLS, and ordered per-artifact uniqueness.
- Added artifact-ingestion contracts in `apps/api/src/alicebot_api/contracts.py`:
  - `TaskArtifactIngestInput`
  - `TaskArtifactChunkRecord`
  - `TaskArtifactChunkListSummary`
  - `TaskArtifactChunkListResponse`
  - `TaskArtifactIngestionResponse`
  - `TASK_ARTIFACT_CHUNK_LIST_ORDER = ["sequence_no_asc", "id_asc"]`
  - `TaskArtifactIngestionStatus = "pending" | "ingested"`
- Added artifact-ingestion service behavior in `apps/api/src/alicebot_api/artifacts.py`:
  - rooted file resolution from persisted workspace `local_path` plus artifact `relative_path`
  - explicit supported media types only: `text/plain`, `text/markdown`
  - strict UTF-8 text decoding
  - line-ending normalization to `\n`
  - deterministic fixed-window chunking rule
  - durable ordered chunk persistence
  - deterministic `ingestion_status` transition to `ingested`
- Added store support in `apps/api/src/alicebot_api/store.py`:
  - `TaskArtifactChunkRow`
  - advisory lock for per-artifact ingestion
  - create/list chunk methods
  - artifact ingestion-status update method
- Added API routes in `apps/api/src/alicebot_api/main.py`:
  - `POST /v0/task-artifacts/{task_artifact_id}/ingest`
  - `GET /v0/task-artifacts/{task_artifact_id}/chunks`
- Added unit and integration coverage for:
  - supported text ingestion
  - direct `text/markdown` ingestion
  - deterministic chunk ordering and boundaries
  - rooted-path enforcement during ingestion
  - invalid UTF-8 rejection
  - idempotent re-ingestion
  - unsupported media-type rejection
  - per-user isolation
  - stable ingestion and chunk-list response shapes
- Refreshed `ARCHITECTURE.md` and `.ai/handoff/CURRENT_STATE.md` so the documented shipped slice now matches Sprint 5D ingestion behavior and deferred scope.

Exact chunk schema introduced:

- `id uuid PRIMARY KEY`
- `user_id uuid NOT NULL`
- `task_artifact_id uuid NOT NULL`
- `sequence_no integer NOT NULL CHECK (sequence_no >= 1)`
- `char_start integer NOT NULL CHECK (char_start >= 0)`
- `char_end_exclusive integer NOT NULL CHECK (char_end_exclusive > char_start)`
- `text text NOT NULL CHECK (length(text) > 0)`
- `created_at timestamptz NOT NULL`
- `updated_at timestamptz NOT NULL`
- foreign key to `(task_artifacts.id, user_id)` with `ON DELETE CASCADE`
- unique index on `(user_id, task_artifact_id, sequence_no)`
- user-owned RLS policy
- runtime grants limited to `SELECT, INSERT` on `task_artifact_chunks`
- runtime `UPDATE` added on `task_artifacts` so ingestion can set `ingestion_status`

Supported file types and chunking rule:

- Supported media types: `text/plain`, `text/markdown`
- Text decoding: UTF-8 only
- Line-ending normalization: `\r\n` and `\r` become `\n`
- Chunking rule: `normalized_utf8_text_fixed_window_1000_chars_v1`
- Chunk boundary rule: split normalized text into contiguous, non-overlapping 1000-character windows with zero-based `char_start` and exclusive `char_end_exclusive`

Exact ingestion contract changes introduced:

- Request input: `TaskArtifactIngestInput(task_artifact_id)`
- Ingestion response: `{"artifact": TaskArtifactRecord, "summary": TaskArtifactChunkListSummary}`
- Chunk list response: `{"items": list[TaskArtifactChunkRecord], "summary": TaskArtifactChunkListSummary}`
- Artifact detail payload remains stable except `ingestion_status` can now be `ingested`

Example artifact-ingestion response:

```json
{
  "artifact": {
    "id": "11111111-1111-1111-1111-111111111111",
    "task_id": "22222222-2222-2222-2222-222222222222",
    "task_workspace_id": "33333333-3333-3333-3333-333333333333",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "docs/spec.txt",
    "media_type_hint": "text/plain",
    "created_at": "2026-03-14T10:00:00+00:00",
    "updated_at": "2026-03-14T10:00:01+00:00"
  },
  "summary": {
    "total_count": 2,
    "total_characters": 1006,
    "media_type": "text/plain",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

Example artifact-chunk list response:

```json
{
  "items": [
    {
      "id": "44444444-4444-4444-4444-444444444444",
      "task_artifact_id": "11111111-1111-1111-1111-111111111111",
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 4,
      "text": "abc\n",
      "created_at": "2026-03-14T10:00:01+00:00",
      "updated_at": "2026-03-14T10:00:01+00:00"
    },
    {
      "id": "55555555-5555-5555-5555-555555555555",
      "task_artifact_id": "11111111-1111-1111-1111-111111111111",
      "sequence_no": 2,
      "char_start": 4,
      "char_end_exclusive": 7,
      "text": "def",
      "created_at": "2026-03-14T10:00:01+00:00",
      "updated_at": "2026-03-14T10:00:01+00:00"
    }
  ],
  "summary": {
    "total_count": 2,
    "total_characters": 7,
    "media_type": "text/plain",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## incomplete work

- None within Sprint 5D scope.

## files changed

- `apps/api/alembic/versions/20260314_0024_task_artifact_chunks.py`
- `apps/api/src/alicebot_api/artifacts.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `ARCHITECTURE.md`
- `.ai/handoff/CURRENT_STATE.md`
- `tests/integration/test_migrations.py`
- `tests/integration/test_task_artifacts_api.py`
- `tests/unit/test_20260314_0024_task_artifact_chunks.py`
- `tests/unit/test_artifacts.py`
- `tests/unit/test_artifacts_main.py`
- `tests/unit/test_main.py`
- `tests/unit/test_task_artifact_store.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_artifacts.py tests/unit/test_artifacts_main.py tests/unit/test_task_artifact_store.py tests/unit/test_20260314_0024_task_artifact_chunks.py tests/unit/test_main.py`
  - result: `63 passed in 0.77s`
- `./.venv/bin/python -m pytest tests/unit/test_artifacts.py`
  - result: `16 passed in 0.11s`
- `./.venv/bin/python -m pytest tests/integration/test_task_artifacts_api.py`
  - rerun with local access: `5 passed in 1.72s`
- `./.venv/bin/python -m pytest tests/unit`
  - result: `347 passed in 0.56s`
- `./.venv/bin/python -m pytest tests/integration`
  - first sandboxed attempt failed to reach local Postgres and open a local socket
  - rerun with local access: `104 passed in 30.87s`
- `git diff --check`
  - result: passed

## blockers/issues

- No remaining implementation blockers.
- Local Postgres-backed integration tests required running outside the default sandbox; after rerun with local access, the full suite passed.

## recommended next step

Build the next milestone on top of these durable chunk records by adding retrieval over ingested chunks only, while still keeping embeddings, ranking, rich-document parsing, connectors, orchestration, and UI changes out of scope until separately sprinted.

## intentionally deferred

- Retrieval or search over artifact chunks
- Embeddings for artifact chunks
- Ranking or chunk selection
- PDF, DOCX, OCR, or rich document parsing
- Connector ingestion
- Runner/orchestration behavior
- UI changes
