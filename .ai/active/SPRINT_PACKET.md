# SPRINT_PACKET.md

## Sprint Title

Phase 9 Sprint 35 (P9-S35): MCP Server

## Sprint Type

feature

## Sprint Reason

`P9-S33` established the public-safe `alice-core` package boundary and startup path. `P9-S34` established the deterministic local CLI contract. The next non-redundant seam is exposing that same continuity contract through a narrow MCP server so external assistants can use Alice without reopening core behavior.

## Planning Anchors

- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-public-core-boundary.md`
- `docs/phase9-bootstrap-notes.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`

## Sprint Objective

Ship a small deterministic MCP server for Alice continuity flows so one external MCP-capable client can call capture, recall, resume, open-loop, review, correction, and context-pack tools against the shipped local `alice-core` runtime.

## Git Instructions

- Branch Name: `codex/phase9-sprint-35-mcp-server`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint Matters

- It is the first real interop transport for external assistants.
- It should inherit the already-shipped `P9-S34` CLI semantics instead of inventing a second behavior model.
- It turns Alice from a local tool into a reusable memory layer for external agent clients.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and qualification baseline.
  - Phase 5 continuity capture, recall, resumption, review, correction, and open-loop seams.
  - Phase 6 trust-calibrated memory-quality and retrieval posture.
  - Phase 7 chief-of-staff guidance layer.
  - Phase 8 operational chief-of-staff handoff, queue, routing, and outcome-learning seams.
  - `P9-S33` public-safe packaging, startup path, and sample-data baseline.
  - `P9-S34` deterministic local CLI contract for continuity workflows.
- Required now (`P9-S35`):
  - narrow MCP transport for the shipped continuity contract
  - deterministic tool schemas and serialization
  - one local client interoperability proof
  - parity tests between MCP outputs and shipped CLI/core behavior where relevant
- Explicitly out of `P9-S35`:
  - OpenClaw adapter implementation
  - importer expansion
  - hosted auth or remote deployment systems
  - widening the tool surface beyond the ADR-defined initial wedge
  - reopening `P9-S33` packaging or `P9-S34` CLI semantics unless transport parity exposes a real defect

## Design Truth

- MCP is a transport layer over the shipped Alice continuity contract, not a new product surface with different semantics.
- Tool outputs must stay deterministic, provenance-backed, and narrowly scoped.
- External clients should get the same essential behavior as the local CLI for the same dataset and scope.
- The first MCP release should privilege stability and auditability over breadth.

## Exact Surfaces In Scope

- local MCP server entrypoint and runtime wiring
- deterministic tool schemas for the initial ADR-backed tool set
- transport wrappers for shipped continuity flows
- context-pack output where it can be defined directly from shipped continuity seams
- local auth/config model for MCP use on the documented startup path
- docs and examples for one compatible MCP client
- parity and transport tests for the scoped tool set

## Exact Files In Scope

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `README.md`
- `ROADMAP.md`
- `pyproject.toml`
- `apps/api/src/alicebot_api/__init__.py`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/mcp_server.py` if introduced
- `apps/api/src/alicebot_api/mcp_tools.py` if introduced
- `apps/api/src/alicebot_api/mcp_models.py` if introduced
- `apps/api/src/alicebot_api/cli.py` if parity-alignment fixes are required
- `apps/api/src/alicebot_api/cli_formatting.py` if parity-alignment fixes are required
- `apps/api/src/alicebot_api/continuity_capture.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/chief_of_staff.py` if `alice_context_pack` is implemented through existing brief assembly
- `tests/unit/test_mcp.py` if introduced
- `tests/integration/test_mcp_server.py` if introduced
- `tests/integration/test_mcp_cli_parity.py` if introduced
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## In Scope

- support an initial MCP tool set aligned to ADR-003:
  - `alice_capture`
  - `alice_recall`
  - `alice_resume`
  - `alice_open_loops`
  - `alice_recent_decisions`
  - `alice_recent_changes`
  - `alice_memory_review`
  - `alice_memory_correct`
  - `alice_context_pack`
- define deterministic request/response shapes for those tools
- make one local MCP client call recall and resume successfully
- prove correction via MCP changes later retrieval behavior deterministically
- document exact local MCP startup/use path without changing the canonical `P9-S33` runtime flow

## Out Of Scope

- OpenClaw or other adapters
- broad tool-surface expansion beyond the ADR
- hosted or remote auth systems
- general-purpose agent execution tools
- broad repo restructuring
- replacing CLI as the reference behavior contract

## Required Deliverables

- packaged or runnable local MCP server entrypoint
- deterministic initial tool schemas and handlers
- one compatibility example for a real MCP client
- parity evidence showing MCP reflects shipped Alice continuity behavior
- synced docs and sprint reports

## Acceptance Criteria

- one MCP-capable client can call `alice_recall` successfully against the local runtime
- one MCP-capable client can call `alice_resume` successfully against the local runtime
- correction through `alice_memory_correct` changes a later retrieval/result deterministically
- MCP outputs remain narrow, deterministic, and provenance-backed
- the MCP tool contract is stable enough that `P9-S36` and `P9-S37` can build on it without reopening transport semantics

## Required Commands

Minimum verification expected before review:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
./scripts/api_dev.sh
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python -m alicebot_api --help
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
```

If a dedicated MCP server entrypoint or local MCP smoke command is introduced this sprint, it must be run and included in review evidence alongside one real client interoperability proof.

## Required Acceptance Evidence

- exact MCP startup path used during verification
- exact client/config used for interoperability proof
- one successful `alice_recall` tool call
- one successful `alice_resume` tool call
- one successful correction flow showing later retrieval changed deterministically
- note of any intentionally deferred MCP ergonomics or auth concerns

## Implementation Constraints

- preserve shipped P5/P6/P7/P8/P9-S33/P9-S34 semantics
- keep the MCP surface narrow and ADR-aligned
- keep transport payloads deterministic and easily diffable
- do not introduce unsafe autonomous side effects
- prefer parity with shipped CLI/core behavior over transport cleverness

## Control Tower Task Cards

### Task 1: MCP Entry and Schemas

Owner: platform/interop owner

Write scope:

- `pyproject.toml`
- `apps/api/src/alicebot_api/__init__.py`
- `apps/api/src/alicebot_api/mcp_server.py`
- `apps/api/src/alicebot_api/mcp_tools.py`
- `apps/api/src/alicebot_api/mcp_models.py`

Responsibilities:

- define the runnable MCP server entrypoint
- keep the tool surface narrow and stable
- keep schema names and payloads deterministic
- avoid leaking internal-only helper seams

### Task 2: Continuity Transport Wiring

Owner: backend/runtime owner

Write scope:

- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/continuity_capture.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/chief_of_staff.py`

Responsibilities:

- map tool calls directly onto shipped continuity behavior
- expose provenance/trust signals consistently
- keep context-pack behavior grounded in shipped brief assembly
- fix only true parity gaps exposed during transport integration

### Task 3: Docs and Interop Example

Owner: docs/integration owner

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`

Responsibilities:

- document exact MCP startup path
- document one compatible local client example
- keep startup/sample-data instructions unchanged from `P9-S33`
- make the next seam toward adapters/importers explicit

### Task 4: Verification and Parity

Owner: sprint integrator

Write scope:

- `tests/unit/test_mcp.py`
- `tests/integration/test_mcp_server.py`
- `tests/integration/test_mcp_cli_parity.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- prove recall/resume work through a real MCP client path
- prove correction changes later retrieval deterministically
- keep parity evidence explicit against shipped CLI/core behavior
- keep scope hygiene explicit if support files are touched

## Definition Of Done

- `P9-S35` MCP server exists and is runnable from the documented local install
- the initial ADR-backed tool surface is implemented and deterministic
- one real client interoperability proof exists for recall and resume
- docs, tests, build report, and review report are aligned
- no adapter or importer work leaks into the sprint
