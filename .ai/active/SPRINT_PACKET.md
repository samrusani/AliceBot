# SPRINT_PACKET.md

## Sprint Title

Phase 9 Sprint 36 (P9-S36): OpenClaw Adapter

## Sprint Type

feature

## Sprint Reason

`P9-S33` shipped the public-safe `alice-core` boundary and startup path. `P9-S34` shipped the deterministic local CLI contract. `P9-S35` shipped the narrow MCP transport. The next non-redundant seam is proving Alice is agent-agnostic by wiring one concrete external adapter against the already-shipped CLI/MCP continuity contract.

## Planning Anchors

- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-public-core-boundary.md`
- `docs/phase9-bootstrap-notes.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`
- `docs/adr/ADR-004-openclaw-integration-boundary.md` if introduced

## Sprint Objective

Ship the first OpenClaw adapter path so a sample or real OpenClaw workspace can be imported into Alice, queried through Alice recall/resumption, and optionally consumed through the shipped MCP wedge without changing Alice continuity semantics.

## Git Instructions

- Branch Name: `codex/phase9-sprint-36-openclaw-adapter`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint Matters

- It is the first proof that Alice works as an interoperable memory layer, not just a standalone local tool.
- It validates the Phase 9 thesis using one real external agent stack instead of abstract compatibility claims.
- It sets the adapter/import boundary ahead of broader importer work in `P9-S37`.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and qualification baseline.
  - Phase 5 continuity capture, recall, resumption, review, correction, and open-loop seams.
  - Phase 6 trust-calibrated memory-quality and retrieval posture.
  - Phase 7 chief-of-staff guidance layer.
  - Phase 8 operational chief-of-staff handoff, queue, routing, and outcome-learning seams.
  - `P9-S33` public-safe packaging, startup path, and sample-data baseline.
  - `P9-S34` deterministic local CLI contract for continuity workflows.
  - `P9-S35` deterministic MCP transport for the shipped continuity contract.
- Required now (`P9-S36`):
  - OpenClaw adapter/import boundary
  - file-based import path for OpenClaw workspace or durable memory data
  - imported provenance tagging and dedupe stance
  - recall/resumption proof on imported OpenClaw material
  - optional MCP augmentation proof using imported data through the shipped tool surface
- Explicitly out of `P9-S36`:
  - broad importer set beyond the OpenClaw adapter path
  - widening the MCP tool surface
  - hosted deployment or remote auth work
  - launch assets / public release polish
  - reopening CLI or MCP semantics unless adapter integration exposes a real parity defect

## Design Truth

- OpenClaw integration should prove Alice can augment an external agent stack without becoming a generic platform wrapper.
- The adapter should map external state into shipped Alice continuity objects with explicit provenance, not bypass Alice’s trust and correction model.
- Imported material should remain queryable through the same recall/resumption semantics as native Alice data.
- The adapter boundary should stay narrow enough that later importer work can generalize from it.

## Exact Surfaces In Scope

- OpenClaw import/adapter module(s)
- file-based input contract for OpenClaw workspace or durable memory export
- import mapping into shipped Alice continuity objects
- provenance tagging and dedupe behavior for imported material
- one documented local demo path for import -> recall/resume
- optional MCP augmentation proof against imported data
- tests and fixtures for the adapter path

## Exact Files In Scope

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `ARCHITECTURE.md`
- `README.md`
- `ROADMAP.md`
- `RULES.md`
- `docs/phase9-sprint-33-38-plan.md`
- `pyproject.toml` if adapter packaging entrypoints are introduced
- `apps/api/src/alicebot_api/openclaw_adapter.py` if introduced
- `apps/api/src/alicebot_api/openclaw_models.py` if introduced
- `apps/api/src/alicebot_api/openclaw_import.py` if introduced
- `apps/api/src/alicebot_api/mcp_tools.py` if parity-alignment is required
- `apps/api/src/alicebot_api/continuity_capture.py` if adapter ingestion reuses capture helpers
- `apps/api/src/alicebot_api/continuity_recall.py` if import parity fixes are required
- `apps/api/src/alicebot_api/continuity_resumption.py` if import parity fixes are required
- `apps/api/src/alicebot_api/store.py`
- `scripts/load_openclaw_sample_data.py` if introduced
- `scripts/load_openclaw_sample_data.sh` if introduced
- `fixtures/openclaw/` if introduced
- `docs/adr/ADR-004-openclaw-integration-boundary.md` if introduced
- `.ai/archive/planning/2026-04-07-phase9-bootstrap/` if bootstrap planning state is archived for traceability
- `docs/archive/planning/2026-04-07-phase9-bootstrap/` if canonical planning docs are archived for traceability
- `tests/unit/test_openclaw_adapter.py` if introduced
- `tests/integration/test_openclaw_import.py` if introduced
- `tests/integration/test_openclaw_mcp_integration.py` if introduced
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## In Scope

- define the first-class OpenClaw adapter boundary
- import a sample or real OpenClaw workspace / durable memory export into Alice
- preserve source provenance on imported material
- make imported memory visible through Alice recall and resumption
- document exact local import and demo steps
- keep MCP augmentation proof limited to using the already-shipped tool surface on imported data

## Out Of Scope

- generic importer framework for all sources
- ChatGPT/Claude/markdown/CSV importer bundle
- MCP tool-surface expansion
- hosted adapter services
- broad repo packaging changes
- public launch polish and release assets

## Required Deliverables

- runnable OpenClaw adapter/import path
- sample or documented real OpenClaw fixture path
- provenance-preserving import mapping
- recall/resumption proof against imported data
- optional MCP proof against imported data if used to validate augmentation mode
- synced docs, reports, and any new ADR boundary needed for the adapter

## Acceptance Criteria

- a sample or real OpenClaw workspace can be imported through the documented path
- imported material becomes queryable via Alice recall
- imported material contributes useful output to Alice resumption briefs
- imported provenance is explicit enough to distinguish adapter-ingested material from native Alice capture
- if MCP augmentation is exercised, one shipped MCP tool path works successfully against imported data without widening the tool contract

## Required Commands

Minimum verification expected before review:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
./scripts/api_dev.sh
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
```

If a dedicated OpenClaw import command or adapter loader is introduced this sprint, it must be run and included in review evidence together with at least one recall and one resumption proof against imported data.

## Required Acceptance Evidence

- exact OpenClaw input fixture or workspace path used during verification
- exact import command/path used during verification
- one successful recall example against imported data
- one successful resumption example against imported data
- note of import provenance and dedupe posture actually observed
- if used, one successful shipped MCP tool call against imported data

## Implementation Constraints

- preserve shipped P5/P6/P7/P8/P9-S33/P9-S34/P9-S35 semantics
- do not bypass Alice continuity objects or correction semantics for imported data
- keep the adapter narrow and specific to OpenClaw in this sprint
- keep provenance explicit and deterministic
- prefer an auditable import path over a “magic sync” abstraction

## Control Tower Task Cards

### Task 1: Adapter Boundary and Models

Owner: interop/adapter owner

Write scope:

- `apps/api/src/alicebot_api/openclaw_adapter.py`
- `apps/api/src/alicebot_api/openclaw_models.py`
- `apps/api/src/alicebot_api/openclaw_import.py`
- `docs/adr/ADR-004-openclaw-integration-boundary.md`

Responsibilities:

- define the OpenClaw import boundary
- define supported file/input shapes for the first adapter pass
- keep provenance and dedupe rules explicit
- avoid drifting into generic importer-framework work

### Task 2: Continuity Mapping and Storage

Owner: backend/runtime owner

Write scope:

- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/continuity_capture.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/mcp_tools.py`

Responsibilities:

- map imported OpenClaw material into shipped Alice continuity semantics
- preserve deterministic retrieval/resumption behavior
- expose imported provenance through recall/resumption/MCP where relevant
- fix only true parity gaps exposed by the adapter

### Task 3: Fixtures, Demo Path, and Docs

Owner: docs/integration owner

Write scope:

- `ARCHITECTURE.md`
- `README.md`
- `ROADMAP.md`
- `RULES.md`
- `.ai/handoff/CURRENT_STATE.md`
- `docs/phase9-sprint-33-38-plan.md`
- `fixtures/openclaw/`
- `scripts/load_openclaw_sample_data.py`
- `scripts/load_openclaw_sample_data.sh`

Responsibilities:

- provide one reproducible local OpenClaw demo path
- document exact import steps and expected outcomes
- keep startup/sample-data guidance from `P9-S33` unchanged
- keep architecture/rules/planning docs aligned with the shipped adapter boundary and importer posture
- make the next seam toward broader importers/eval explicit

### Task 4: Verification and Interop Proof

Owner: sprint integrator

Write scope:

- `tests/unit/test_openclaw_adapter.py`
- `tests/integration/test_openclaw_import.py`
- `tests/integration/test_openclaw_mcp_integration.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- prove import works against the documented fixture/workspace shape
- prove recall/resumption work against imported data
- prove any MCP augmentation path stays within the shipped tool contract
- keep scope hygiene explicit if supporting files are touched

## Definition Of Done

- `P9-S36` OpenClaw adapter/import path exists and is runnable from the documented local install
- imported OpenClaw data is queryable through shipped Alice recall/resumption semantics
- provenance and dedupe posture are explicit and reviewable
- docs, tests, build report, and review report are aligned
- no broad importer-bundle or launch-polish work leaks into the sprint
