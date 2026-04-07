# SPRINT_PACKET.md

## Sprint Title

Phase 9 Sprint 33 (P9-S33): Public Core Packaging

## Sprint Type

feature

## Sprint Reason

Phase 8 is complete. The next non-redundant seam is converting the internal Alice system into a public-safe, installable core with one documented local startup path, explicit package boundaries, and sample data that proves recall and resumption from public docs.

## Planning Anchors

- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-public-core-boundary.md`
- `docs/phase9-bootstrap-notes.md`
- `docs/phase9-sprint-33-control-tower-packet.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`

## Sprint Objective

Package the existing Alice substrate so an external technical user can install it locally, load sample data, and complete one recall flow and one resumption flow from canonical docs without internal project context.

## Git Instructions

- Branch Name: `codex/phase9-sprint-33-public-core-packaging`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint Matters

- It is the first real public-product step of Phase 9.
- It creates the stable package/runtime boundary that `P9-S34` CLI and `P9-S35` MCP depend on.
- It forces docs, scripts, config, and sample data to match one real install path instead of internal assumptions.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and qualification baseline.
  - Phase 5 continuity capture, recall, resumption, review, correction, and open-loop seams.
  - Phase 6 trust-calibrated memory-quality and retrieval posture.
  - Phase 7 chief-of-staff guidance layer.
  - Phase 8 operational chief-of-staff handoff, queue, routing, and outcome-learning seams.
- Required now (`P9-S33`):
  - explicit public-safe `alice-core` package boundary
  - one canonical local startup path
  - sample-data path for external technical evaluation
  - public-facing repo/docs reshaping for install + first recall/resume proof
- Explicitly out of `P9-S33`:
  - CLI command implementation
  - MCP server implementation
  - OpenClaw adapter implementation
  - broad importer work beyond sample-data support
  - hosted SaaS, channel work, or unsafe autonomous execution

## Design Truth

- Alice remains a memory and continuity layer first, not a broad autonomous agent platform.
- Public packaging must preserve shipped P5/P6/P7/P8 semantics instead of reimplementing them.
- One documented local startup path is the source of truth for public v0.1.
- Public docs are product surface in this phase and must match real runtime behavior.

## Exact Surfaces In Scope

- public-safe package boundary definition for `alice-core`
- canonical local startup and install path
- sample-data fixture/seed path for recall and resumption verification
- repo and docs reshaping for external technical onboarding
- ADR capture for any blocking packaging/runtime/license decisions
- required gate-alignment test updates needed to satisfy the sprint's required verification commands

## Exact Files In Scope

- `README.md`
- `PRODUCT_BRIEF.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `RULES.md`
- `.ai/handoff/CURRENT_STATE.md`
- `.ai/active/SPRINT_PACKET.md`
- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-public-core-boundary.md`
- `docs/phase9-bootstrap-notes.md`
- `docs/phase9-sprint-33-control-tower-packet.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`
- `.env.example`
- `docker-compose.yml`
- `pyproject.toml`
- `scripts/dev_up.sh`
- `scripts/migrate.sh`
- `scripts/api_dev.sh`
- `apps/web/components/memory-summary.test.tsx`
- `tests/integration/test_explicit_preferences_api.py`
- `tests/unit/test_approval_store.py`
- `tests/unit/test_compiler.py`
- `tests/unit/test_entity_store.py`
- `tests/unit/test_events.py`
- `tests/unit/test_store.py`
- `tests/unit/test_task_run_store.py`
- `tests/unit/test_tool_execution_store.py`
- `tests/unit/test_trace_store.py`
- `fixtures/` or equivalent sample-data location
- `LICENSE` if finalized in this sprint
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## In Scope

- Define what is public in `alice-core` versus deferred/internal.
- Confirm one supported local runtime baseline and startup flow.
- Ensure env defaults, scripts, and docs all point to the same install path.
- Provide sample data that an external technical user can load or use immediately.
- Prove one recall query and one resumption brief from the documented public setup.
- Capture blocking public-boundary/runtime/tool-surface decisions in ADRs or explicit deferred notes.

## Out Of Scope

- CLI command implementation or terminal UX polish
- MCP server code or tool execution
- OpenClaw adapter implementation
- broad repo-wide restructuring unrelated to public packaging
- broad importer set
- hosted deployment modes

## Required Deliverables

- explicit `alice-core` public boundary
- one canonical local startup path
- sample-data story usable by external users
- external-facing README/repo map reshaped for public onboarding
- ADR-backed decisions for package boundary/runtime/tool-surface blockers
- synced sprint reports

## Acceptance Criteria

- a fresh local install works from the documented startup path
- sample data can be loaded or is available for immediate local use
- one recall query works end to end from the documented setup
- one resumption brief works end to end from the documented setup
- public-safe boundaries are written clearly enough that `P9-S34` CLI and `P9-S35` MCP can build on them without reopening packaging ambiguity

## Required Commands

Minimum verification expected before review:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/api_dev.sh
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
```

If a dedicated seed-data or public smoke command is introduced this sprint, it must also be run and included in review evidence.

## Required Acceptance Evidence

- exact startup path used during verification
- exact sample-data load path used during verification
- one successful recall example
- one successful resumption example
- note of any deferred public-boundary/runtime/license decision moved into ADRs

## Implementation Constraints

- preserve shipped P5/P6/P7/P8 semantics
- do not introduce unsafe autonomous execution
- keep one documented startup flow as the only canonical public path
- prefer packaging clarity over premature repo-wide restructuring
- keep public-boundary decisions explicit and narrow

## Control Tower Task Cards

### Task 1: Public Boundary and Packaging

Owner: platform/package owner

Write scope:

- `ARCHITECTURE.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `pyproject.toml`
- `docker-compose.yml`
- `LICENSE`
- `docs/phase9-public-core-boundary.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`

Responsibilities:

- define what is in `alice-core` versus deferred/internal
- define public runtime assumptions for v0.1
- confirm one supported local startup path
- capture blocking decisions as ADRs or explicit deferred items

### Task 2: Startup Path and Sample Data

Owner: backend/runtime owner

Write scope:

- `.env.example`
- `scripts/migrate.sh`
- `scripts/api_dev.sh`
- `scripts/dev_up.sh`
- `fixtures/` or equivalent sample-data location
- relevant bootstrap/seed helpers under `apps/api` or `scripts`

Responsibilities:

- ensure sample-data path is deterministic and documented
- ensure startup scripts and env defaults match docs
- verify recall and resumption against the sample dataset
- remove ambiguity between internal-only and public setup steps

### Task 3: Docs and External Onboarding

Owner: docs/integration owner

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-bootstrap-notes.md`
- any new quickstart docs introduced under `docs/`

Responsibilities:

- keep README onboarding-focused
- keep current state factual about shipped versus targeted surfaces
- keep roadmap sequencing consistent with packaging-first execution
- add any missing quickstart examples needed to close the install gap

### Task 4: Integration Review

Owner: sprint integrator

Write scope:

- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify doc, runtime, and sample-data paths agree
- verify ADRs match canonical docs
- verify no hidden expansion into CLI, MCP, or OpenClaw delivery
- prepare final evidence notes for review

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact startup path used during verification
- exact sample-data path used during verification
- exact recall and resumption proof steps
- exact commands run and outcomes
- any deferred public-boundary/runtime/license decisions

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed `P9-S33` scoped
- startup path is singular, real, and doc-matched
- sample-data story is usable by an external technical user
- recall and resumption proof is real from public docs
- no hidden CLI/MCP/OpenClaw implementation scope entered the sprint

## Definition Of Done

This sprint is done when Alice has a public-core packaging boundary, one clean local boot flow, sample-data support, and canonical docs that an external technical user can follow without internal project context.
