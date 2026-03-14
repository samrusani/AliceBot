# BUILD_REPORT

## sprint objective

Implement Sprint 5C: Task Artifact Records and Registration by adding durable user-scoped `task_artifacts` records on top of existing `task_workspaces`, plus a narrow rooted local-file registration path and deterministic artifact reads.

## completed work

- Added `task_artifacts` schema via `apps/api/alembic/versions/20260313_0023_task_artifacts.py`.
- Added artifact contracts in `apps/api/src/alicebot_api/contracts.py`:
  - `TaskArtifactRegisterInput`
  - `TaskArtifactRecord`
  - `TaskArtifactCreateResponse`
  - `TaskArtifactListResponse`
  - `TaskArtifactDetailResponse`
  - `TaskArtifactStatus = "registered"`
  - `TaskArtifactIngestionStatus = "pending"`
  - `TASK_ARTIFACT_LIST_ORDER = ["created_at_asc", "id_asc"]`
- Added artifact persistence and reads in `apps/api/src/alicebot_api/store.py`:
  - `TaskArtifactRow`
  - create/get/list/duplicate-lookup methods
  - advisory lock for per-workspace artifact registration
- Added narrow artifact registration service in `apps/api/src/alicebot_api/artifacts.py`.
- Added API routes in `apps/api/src/alicebot_api/main.py`:
  - `POST /v0/task-workspaces/{task_workspace_id}/artifacts`
  - `GET /v0/task-artifacts`
  - `GET /v0/task-artifacts/{task_artifact_id}`
- Added unit and integration coverage for rooted path validation, duplicate behavior, deterministic ordering, response shape, migration coverage, and per-user isolation.

Artifact schema introduced:

- `id uuid PRIMARY KEY`
- `user_id uuid NOT NULL`
- `task_id uuid NOT NULL`
- `task_workspace_id uuid NOT NULL`
- `status text NOT NULL CHECK (status IN ('registered'))`
- `ingestion_status text NOT NULL CHECK (ingestion_status IN ('pending'))`
- `relative_path text NOT NULL`
- `media_type_hint text NULL`
- `created_at timestamptz NOT NULL`
- `updated_at timestamptz NOT NULL`
- foreign keys to `(tasks.id, user_id)` and `(task_workspaces.id, user_id)`
- unique index on `(user_id, task_workspace_id, relative_path)`
- user-owned RLS policy with runtime grants limited to `SELECT, INSERT`

Artifact-path rooting and duplicate-handling rule:

- Registration accepts one existing regular file path.
- The file path is resolved locally and must stay rooted under the persisted workspace `local_path`.
- The persisted record stores only the workspace-relative POSIX path, not an absolute artifact path.
- Duplicate registration for the same `(user_id, task_workspace_id, relative_path)` is rejected with HTTP `409`.

Example artifact registration response:

```json
{
  "artifact": {
    "id": "11111111-1111-1111-1111-111111111111",
    "task_id": "22222222-2222-2222-2222-222222222222",
    "task_workspace_id": "33333333-3333-3333-3333-333333333333",
    "status": "registered",
    "ingestion_status": "pending",
    "relative_path": "docs/spec.txt",
    "media_type_hint": "text/plain",
    "created_at": "2026-03-13T10:00:00+00:00",
    "updated_at": "2026-03-13T10:00:00+00:00"
  }
}
```

Example artifact detail response:

```json
{
  "artifact": {
    "id": "11111111-1111-1111-1111-111111111111",
    "task_id": "22222222-2222-2222-2222-222222222222",
    "task_workspace_id": "33333333-3333-3333-3333-333333333333",
    "status": "registered",
    "ingestion_status": "pending",
    "relative_path": "docs/spec.txt",
    "media_type_hint": "text/plain",
    "created_at": "2026-03-13T10:00:00+00:00",
    "updated_at": "2026-03-13T10:00:00+00:00"
  }
}
```

## incomplete work

- None within Sprint 5C scope.

## files changed

- `apps/api/alembic/versions/20260313_0023_task_artifacts.py`
- `apps/api/src/alicebot_api/artifacts.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/integration/test_migrations.py`
- `tests/integration/test_task_artifacts_api.py`
- `tests/unit/test_20260313_0023_task_artifacts.py`
- `tests/unit/test_artifacts.py`
- `tests/unit/test_artifacts_main.py`
- `tests/unit/test_main.py`
- `tests/unit/test_task_artifact_store.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_artifacts.py tests/unit/test_artifacts_main.py tests/unit/test_task_artifact_store.py tests/unit/test_20260313_0023_task_artifacts.py tests/unit/test_main.py tests/integration/test_task_artifacts_api.py tests/integration/test_migrations.py`
  - result: `54 passed, 3 errors`
  - note: the 3 errors were sandboxed local-Postgres connection failures before rerunning with elevated access
- `./.venv/bin/python -m pytest tests/unit`
  - result: `332 passed`
- `./.venv/bin/python -m pytest tests/integration`
  - result: `100 passed in 29.55s`
- `git diff --check`
  - result: passed

## blockers/issues

- No remaining implementation blockers.
- Document ingestion, chunking, embeddings over artifacts, retrieval, connectors, scanning, UI work, and broader side effects remain intentionally deferred.

## recommended next step

Build the next milestone on top of these explicit artifact records by adding a separate ingestion workflow that consumes `task_artifacts` metadata without weakening the task-workspace boundary or reintroducing implicit directory scanning.
