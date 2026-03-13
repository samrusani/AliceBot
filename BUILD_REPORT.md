# BUILD_REPORT

## sprint objective

Implement Sprint 5A: Task Workspace Records and Provisioning by adding user-scoped `task_workspaces`, deterministic local workspace provisioning under one configured root, duplicate-active protection per task, and stable workspace create/list/detail reads.

## completed work

- Added workspace schema and migration:
  - new migration `apps/api/alembic/versions/20260313_0022_task_workspaces.py`
  - new table `task_workspaces` with `id`, `user_id`, `task_id`, `status`, `local_path`, `created_at`, and `updated_at`
  - user/task foreign key `(task_id, user_id) -> tasks(id, user_id)`
  - partial unique index enforcing one active workspace per task and user
  - RLS policy plus runtime grants limited to `SELECT, INSERT`
- Added workspace configuration and deterministic pathing:
  - new setting `TASK_WORKSPACE_ROOT`
  - default workspace root: `/tmp/alicebot/task-workspaces`
  - path-generation rule: `<resolved TASK_WORKSPACE_ROOT>/<user_id>/<task_id>`
  - workspace provisioning validates the resolved path stays rooted under the resolved workspace root before creating the directory
- Added typed contracts and service behavior:
  - `TaskWorkspaceStatus`
  - `TaskWorkspaceCreateInput`
  - `TaskWorkspaceRecord`
  - `TaskWorkspaceCreateResponse`
  - `TaskWorkspaceListResponse`
  - `TaskWorkspaceDetailResponse`
  - new workspace service in `apps/api/src/alicebot_api/workspaces.py`
  - duplicate active workspace creation for the same visible task now raises a deterministic conflict
- Added minimal API paths:
  - `POST /v0/tasks/{task_id}/workspace`
  - `GET /v0/task-workspaces`
  - `GET /v0/task-workspaces/{task_workspace_id}`
- Added coverage for:
  - deterministic path generation
  - rooted path safety validation
  - workspace creation
  - duplicate-create rejection
  - per-user isolation
  - stable response shape
  - migration upgrade/downgrade expectations including the new table, RLS, and privileges

## exact workspace schema and contract changes introduced

- Schema:
  - `task_workspaces.id uuid PRIMARY KEY DEFAULT gen_random_uuid()`
  - `task_workspaces.user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE`
  - `task_workspaces.task_id uuid NOT NULL`
  - `task_workspaces.status text NOT NULL CHECK (status IN ('active'))`
  - `task_workspaces.local_path text NOT NULL CHECK (length(local_path) > 0)`
  - `task_workspaces.created_at timestamptz NOT NULL DEFAULT now()`
  - `task_workspaces.updated_at timestamptz NOT NULL DEFAULT now()`
  - `CONSTRAINT task_workspaces_task_user_fk FOREIGN KEY (task_id, user_id) REFERENCES tasks(id, user_id) ON DELETE CASCADE`
  - `CREATE UNIQUE INDEX task_workspaces_active_task_idx ON task_workspaces (user_id, task_id) WHERE status = 'active'`
- Store layer:
  - `TaskWorkspaceRow`
  - `ContinuityStore.lock_task_workspaces(...)`
  - `ContinuityStore.create_task_workspace(...)`
  - `ContinuityStore.get_task_workspace_optional(...)`
  - `ContinuityStore.get_active_task_workspace_for_task_optional(...)`
  - `ContinuityStore.list_task_workspaces(...)`
- Contracts:
  - `TaskWorkspaceStatus = Literal["active"]`
  - `TaskWorkspaceCreateInput.task_id`
  - `TaskWorkspaceCreateInput.status`
  - `TaskWorkspaceRecord.id`
  - `TaskWorkspaceRecord.task_id`
  - `TaskWorkspaceRecord.status`
  - `TaskWorkspaceRecord.local_path`
  - `TaskWorkspaceRecord.created_at`
  - `TaskWorkspaceRecord.updated_at`
  - `TaskWorkspaceCreateResponse.workspace`
  - `TaskWorkspaceListResponse.items`
  - `TaskWorkspaceListResponse.summary`
  - `TaskWorkspaceDetailResponse.workspace`

## configured workspace root and path-generation rule used

- Default configured workspace root: `/tmp/alicebot/task-workspaces`
- Test override root: per-test temp directory via `Settings(task_workspace_root=...)`
- Deterministic path rule: `resolved_root / str(user_id) / str(task_id)`
- Safety rule: the resolved workspace path must remain under the resolved configured root or provisioning fails before persistence

## incomplete work

- None inside Sprint 5A scope.

## files changed

- `apps/api/alembic/versions/20260313_0022_task_workspaces.py`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/workspaces.py`
- `tests/integration/test_migrations.py`
- `tests/integration/test_task_workspaces_api.py`
- `tests/unit/test_20260313_0022_task_workspaces.py`
- `tests/unit/test_config.py`
- `tests/unit/test_main.py`
- `tests/unit/test_task_workspace_store.py`
- `tests/unit/test_workspaces.py`
- `tests/unit/test_workspaces_main.py`
- `BUILD_REPORT.md`

## exact commands run

- `./.venv/bin/python -m pytest tests/unit/test_workspaces.py tests/unit/test_workspaces_main.py tests/unit/test_task_workspace_store.py tests/unit/test_20260313_0022_task_workspaces.py tests/unit/test_config.py tests/unit/test_main.py`
- `./.venv/bin/python -m pytest tests/integration/test_task_workspaces_api.py tests/integration/test_migrations.py`
  - initial sandbox run failed because sandboxed localhost Postgres access was blocked
- `./.venv/bin/python -m pytest tests/unit`
- `./.venv/bin/python -m pytest tests/integration`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_workspaces.py tests/unit/test_workspaces_main.py tests/unit/test_task_workspace_store.py tests/unit/test_20260313_0022_task_workspaces.py tests/unit/test_config.py tests/unit/test_main.py`
  - passed: `56 passed in 0.50s`
- `./.venv/bin/python -m pytest tests/integration/test_task_workspaces_api.py tests/integration/test_migrations.py`
  - sandboxed run failed before test execution could start against Postgres: `3 errors in 0.21s`
- `./.venv/bin/python -m pytest tests/unit`
  - passed: `315 passed in 0.57s`
- `./.venv/bin/python -m pytest tests/integration`
  - passed outside the sandbox: `99 passed in 28.56s`

## unit and integration test results

- Unit suite:
  - green
  - covers config loading, migration statement order, store queries, workspace service behavior, rooted path safety, duplicate rejection, route registration, and endpoint error mapping
- Integration suite:
  - green
  - covers migration upgrade/downgrade expectations, workspace API provisioning, duplicate rejection, deterministic list/detail responses, and per-user isolation against Postgres

## one example workspace create response

```json
{
  "workspace": {
    "id": "11111111-1111-1111-1111-111111111111",
    "task_id": "22222222-2222-2222-2222-222222222222",
    "status": "active",
    "local_path": "/tmp/alicebot/task-workspaces/33333333-3333-3333-3333-333333333333/22222222-2222-2222-2222-222222222222",
    "created_at": "2026-03-13T10:00:00+00:00",
    "updated_at": "2026-03-13T10:00:00+00:00"
  }
}
```

## one example workspace detail response

```json
{
  "workspace": {
    "id": "11111111-1111-1111-1111-111111111111",
    "task_id": "22222222-2222-2222-2222-222222222222",
    "status": "active",
    "local_path": "/tmp/alicebot/task-workspaces/33333333-3333-3333-3333-333333333333/22222222-2222-2222-2222-222222222222",
    "created_at": "2026-03-13T10:00:00+00:00",
    "updated_at": "2026-03-13T10:00:00+00:00"
  }
}
```

## blockers/issues

- No implementation blocker remains.
- Verification note:
  - Postgres-backed integration tests required unsandboxed access to `localhost:5432`; the initial sandboxed focused integration run failed with connection-permission errors before being rerun successfully outside the sandbox.

## what remains intentionally deferred to later milestones

- Artifact inventory and artifact metadata tables
- Document ingestion
- Chunking, embeddings, or document retrieval tied to workspaces
- Gmail or Calendar connector scope
- Runner-style orchestration
- New proxy handlers or broader side-effect expansion
- Any remote storage abstraction beyond the local deterministic workspace boundary added here

## recommended next step

Build the next workspace-dependent milestone slice on top of this boundary without widening the seam: artifact or document work should consume `task_workspaces` records and the configured rooted local path instead of inventing a parallel storage contract.
