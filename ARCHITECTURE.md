# Architecture

## Current Implemented Slice

AliceBot now implements the accepted repo slice through Sprint 6V.

- `apps/api` is the core shipped surface. It provides continuity storage and review over `users`, `threads`, `sessions`, and append-only `events`; deterministic context compilation; governed memory admission and review; embeddings and semantic retrieval; entities and entity edges; policy, tool, approval, and execution governance; the no-tools assistant-response seam at `POST /v0/responses`; explicit task and task-step lifecycle reads and mutations; rooted local task workspaces and artifact ingestion; artifact chunk retrieval and embeddings; and narrow read-only Gmail and Calendar seams with external-secret-backed credentials plus selected-item ingestion into the artifact pipeline.
- `apps/web` is a shipped operator shell over those backend seams, not a scaffold-only placeholder. The current routes are `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/entities`, and `/traces`. The shell can read live backend seams when configured and otherwise falls back to explicit fixture states instead of pretending the backend is connected.
- `/chat` now carries both shipped operator modes: governed request composition and assistant-response mode. It uses visible thread selection instead of a raw typed thread id, supports compact thread creation through the continuity API, renders a selected-thread transcript from immutable continuity events, and keeps supporting session and operational review, thread-linked governed workflow review, ordered task-step timeline review, and bounded explain-why trace review in the right rail.
- `/gmail` and `/calendar` are shipped bounded connector workspaces over existing backend seams: visible account list review, selected-account detail, explicit account connection, and explicit single-item ingestion into one chosen task workspace, with live/fixture/unavailable states kept explicit.
- `/artifacts`, `/memories`, and `/entities` are now shipped bounded review workspaces that expose existing artifact, memory, and entity read seams with explicit live/fixture/unavailable modes.
- `workers` remains scaffold-only. No background runner, automatic multi-step progression, or asynchronous job system is implemented.

The repo is intentionally still narrow. Document ingestion remains local and deterministic. The only live execution handler is the no-external-I/O `proxy.echo` path. Gmail and Calendar remain read-only and selected-item-only. Rich parsing, mailbox sync, attachments, broader Calendar capabilities, broader proxying, and runner-style orchestration are still planned later.

## Implemented Now

### Runtime

- `docker-compose.yml` starts local Postgres with `pgvector`, Redis, and MinIO.
- `scripts/dev_up.sh`, `scripts/migrate.sh`, and `scripts/api_dev.sh` provide the local startup path.
- `apps/api` exposes FastAPI endpoints for:
  - continuity and response generation: `/healthz`, `POST /v0/threads`, `GET /v0/threads`, `GET /v0/threads/{thread_id}`, `GET /v0/threads/{thread_id}/sessions`, `GET /v0/threads/{thread_id}/events`, `POST /v0/context/compile`, `POST /v0/responses`
  - memory, embeddings, and graph seams
  - policy, tool, approval, execution-budget, and proxy execution governance
  - task, task-step, task-workspace, task-artifact, artifact-chunk, and trace review reads and mutations
  - narrow Gmail account connect/read plus selected-message ingestion
  - narrow Calendar account connect/read plus selected-event ingestion
- `apps/web` exposes the current operator shell:
  - `/`: bounded home view over the shipped shell surfaces
  - `/chat`: assistant mode, governed request mode, thread selection, thread creation, transcript-first continuity review, thread-linked governed workflow and task-step timeline review, bounded explain-why embedding, and bounded supporting operational review
  - `/approvals`: approval inbox and execution review
  - `/tasks`: task summary and ordered task-step review
  - `/artifacts`: artifact list and selected detail, linked workspace summary, and ordered chunk review
  - `/gmail`: connected-account review, selected-account detail, explicit connect, and selected-message ingestion into one chosen task workspace
  - `/calendar`: connected-account review, selected-account detail, explicit connect, and selected-event ingestion into one chosen task workspace
  - `/memories`: memory summary and queue posture, selected detail, revision review, and label review
  - `/entities`: entity list and selected detail with related edge review
  - `/traces`: trace summary, detail, and ordered event review
- `tests` cover both the backend seams and the web shell. Durable repo evidence includes integration coverage for continuity and responses plus Vitest coverage for `/chat`, thread selection, bounded continuity review, and assistant-response submission.

### Data And Safety Boundaries

- Postgres is the system of record.
- Row-level security is enforced on user-owned continuity, trace, memory, governance, task, workspace, artifact, Gmail, and Calendar tables.
- `events`, `trace_events`, and `memory_revisions` are append-only by contract.
- Task-step lineage and execution linkage stay explicit through `parent_step_id`, `source_approval_id`, `source_execution_id`, and `tool_executions.task_step_id`.
- Task workspaces are rooted local directories under `TASK_WORKSPACE_ROOT`.
- Task artifacts are explicit rooted local-file registrations only; compile and retrieval read persisted chunk rows, not raw files.
- Gmail and Calendar credential material stay off normal metadata tables and flow through dedicated secret-manager seams.

## Core Flows Implemented Now

### Continuity And Chat

1. `POST /v0/threads` creates one visible thread.
2. `GET /v0/threads`, `GET /v0/threads/{thread_id}`, `GET /v0/threads/{thread_id}/sessions`, and `GET /v0/threads/{thread_id}/events` expose bounded continuity review over persisted records.
3. `POST /v0/responses` compiles context deterministically, persists the submitted user message plus the assistant reply as immutable events, and returns linked compile and response trace metadata.
4. `/chat` consumes those shipped seams directly. Selected-thread identity stays explicit across assistant and governed-request modes, immutable thread events drive the primary transcript surface, and non-conversation continuity stays in bounded supporting review instead of polluting the main conversation record.

### Governance, Tasks, And Explainability

1. `POST /v0/approvals/requests` creates one task and one initial task step for each governed request.
2. Approval resolution and approved execution reuse explicit task-step linkage instead of inferring from first-step-only assumptions.
3. `GET /v0/approvals`, `GET /v0/tasks`, `GET /v0/tasks/{task_id}/steps`, `GET /v0/tool-executions`, `GET /v0/traces`, and related detail reads expose durable review state through the web shell, including thread-linked workflow review and ordered task-step timeline review in `/chat`.
4. The shipped explainability surface is calm and bounded: `/chat` embeds selected-thread explain-why review over linked trace targets, with summary first, detail second, and ordered trace events last.

### Workspaces, Artifacts, Gmail, And Calendar

1. Tasks can provision one rooted local workspace and register local artifacts under that boundary.
2. Artifact ingestion supports the narrow current set only: plain text, markdown, narrow local PDF text extraction, narrow DOCX text extraction from `word/document.xml`, and narrow RFC822 email extraction.
3. Artifact retrieval works over persisted chunk rows and persisted chunk embeddings, including deterministic lexical retrieval, direct semantic retrieval, and the current lexical-first hybrid compile merge.
4. Gmail remains narrow: one read-only account seam, secret-free account reads, external-secret-backed primary credentials, refresh-token renewal and rotation handling, and one selected-message ingestion path that lands in the existing RFC822 artifact workflow.
5. Calendar remains narrow: one read-only account seam, secret-free account reads, external-secret-backed credentials, and one selected-event ingestion path that lands in the existing text artifact/chunk workflow.

## Testing Coverage Implemented Now

- Backend continuity and response seams are covered in `tests/integration/test_continuity_api.py`, `tests/integration/test_continuity_store.py`, `tests/integration/test_responses_api.py`, and related unit coverage under `tests/unit`.
- Web continuity and `/chat` operator review adoption are covered in `apps/web/app/chat/page.test.tsx`, `apps/web/components/thread-list.test.tsx`, `apps/web/components/thread-summary.test.tsx`, `apps/web/components/thread-event-list.test.tsx`, `apps/web/components/thread-create.test.tsx`, `apps/web/components/response-composer.test.tsx`, `apps/web/components/thread-workflow-panel.test.tsx`, `apps/web/components/task-step-list.test.tsx`, `apps/web/components/response-history.test.tsx`, and `apps/web/components/thread-trace-panel.test.tsx`.
- Review workspaces are covered at route level in `apps/web/app/artifacts/page.test.tsx`, `apps/web/app/memories/page.test.tsx`, and `apps/web/app/entities/page.test.tsx`, with matching component and API-client coverage under `apps/web`.
- Connector workspaces are covered through `apps/web/lib/api.test.ts`, `apps/web/components/gmail-account-list.test.tsx`, `apps/web/components/calendar-account-list.test.tsx`, and `apps/web/components/calendar-event-ingest-form.test.tsx`.
- The shell also has route and API-client coverage for approvals, tasks, traces, and shared API utilities under `apps/web`.

## Planned Later

The following remain planned later and must not be described as implemented:

- runner-style orchestration and automatic multi-step progression
- auth beyond the current database user-context model
- richer document parsing, OCR, image extraction, or layout reconstruction
- Gmail search, mailbox sync, attachment ingestion, write-capable Gmail actions, and broader Calendar capabilities such as event listing/search, recurrence expansion, sync, and write actions
- broader proxy execution breadth or real-world side effects beyond `proxy.echo`
- retrieval reranking or weighted fusion beyond the current lexical-first hybrid compile merge

Future planning should start from the shipped API-plus-web-shell baseline above, not from older Gmail-era or scaffold-era descriptions.
