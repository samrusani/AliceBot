# SPRINT_PACKET.md

## Sprint Title

Phase 9 Sprint 34 (P9-S34): CLI and Continuity UX

## Sprint Type

feature

## Sprint Reason

`P9-S33` established the public-safe `alice-core` package boundary, one canonical local startup path, and deterministic sample data. The next non-redundant seam is a real local CLI so technical users can use Alice without the internal operator shell.

## Planning Anchors

- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-public-core-boundary.md`
- `docs/phase9-bootstrap-notes.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`

## Sprint Objective

Ship a deterministic local CLI for core continuity flows so an external technical user can run capture, recall, resume, open-loop review, correction, and status commands directly against the shipped `alice-core` runtime.

## Git Instructions

- Branch Name: `codex/phase9-sprint-34-cli-and-continuity-ux`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint Matters

- It is the first real user-facing runtime surface on top of the public core.
- It proves `alice-core` can be used directly by technical users before MCP arrives.
- It gives `P9-S35` a stable behavior contract to mirror instead of inventing a second UX path.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and qualification baseline.
  - Phase 5 continuity capture, recall, resumption, review, correction, and open-loop seams.
  - Phase 6 trust-calibrated memory-quality and retrieval posture.
  - Phase 7 chief-of-staff guidance layer.
  - Phase 8 operational chief-of-staff handoff, queue, routing, and outcome-learning seams.
  - `P9-S33` public-safe packaging, startup path, and sample-data baseline.
- Required now (`P9-S34`):
  - deterministic CLI entrypoint for local Alice usage
  - continuity command surface for capture/recall/resume/open loops/review/correction/status
  - terminal-friendly output with provenance-backed summaries
  - doc-matched CLI examples against the `P9-S33` local runtime path
- Explicitly out of `P9-S34`:
  - MCP server implementation
  - OpenClaw adapter implementation
  - importer expansion beyond the shipped sample-data path
  - hosted SaaS, remote auth, or unsafe autonomous execution
  - reworking `P9-S33` packaging/runtime contracts unless required for CLI correctness

## Design Truth

- Alice remains a local-first memory and continuity engine first.
- The CLI should reuse shipped core semantics, not fork or reinterpret them.
- CLI output should be deterministic, readable, and provenance-backed.
- The CLI is the reference human-operated interface for `P9-S35` MCP parity, not a one-off wrapper.

## Exact Surfaces In Scope

- one installable CLI entrypoint under the `alice-core` package
- local commands for capture, recall, resume, open loops, review queue/detail, correction, and status
- deterministic terminal formatting for summary and detail views
- provenance snippets and clear empty states in CLI output
- doc updates for CLI installation and usage against the shipped local runtime
- tests covering command routing, output contracts, and correction/resumption behavior

## Exact Files In Scope

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `README.md`
- `ROADMAP.md`
- `pyproject.toml`
- `apps/api/src/alicebot_api/__init__.py`
- `apps/api/src/alicebot_api/__main__.py` if introduced
- `apps/api/src/alicebot_api/cli.py` if introduced
- `apps/api/src/alicebot_api/cli_formatting.py` if introduced
- `apps/api/src/alicebot_api/config.py` if CLI config hooks are needed
- `apps/api/src/alicebot_api/continuity_capture.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/store.py`
- `scripts/load_sample_data.sh` if CLI smoke setup needs alignment
- `tests/unit/test_cli.py` if introduced
- `tests/integration/test_cli_integration.py` if introduced
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## In Scope

- add a packaged CLI entrypoint that works from the documented local install
- support command coverage for:
  - `capture`
  - `recall`
  - `resume`
  - `open-loops`
  - `review queue`
  - `review show`
  - `review apply`
  - `status`
- keep terminal output deterministic enough for stable review and MCP follow-on mapping
- show provenance/confidence/status where it materially affects trust
- document exact command examples using the `P9-S33` sample dataset

## Out Of Scope

- MCP transport or tool schemas
- OpenClaw or other external adapters
- broad repo packaging cleanup already handled in `P9-S33`
- broad TUI work or shell auto-completion polish
- any execution-autonomy expansion

## Required Deliverables

- packaged CLI entrypoint callable from a local install
- command coverage for core continuity flows
- deterministic text output for recall and resumption
- correction flow through CLI that updates later retrieval deterministically
- synced CLI docs and sprint reports

## Acceptance Criteria

- fresh local install can invoke the CLI from the documented path
- capture command writes a continuity event against real local data
- recall command returns deterministic ordered output with provenance snippets
- resume command returns recent decision, open loops, recent changes, and next action in terminal-friendly form
- open-loop and review commands expose correction-ready items without needing the internal web shell
- applying a correction via CLI changes later recall/resume behavior deterministically
- the CLI contract is narrow and stable enough for `P9-S35` MCP mirroring without reopening core UX semantics

## Required Commands

Minimum verification expected before review:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
./scripts/api_dev.sh
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python -m alicebot_api --help
./.venv/bin/python -m alicebot_api status
./.venv/bin/python -m alicebot_api recall --query local-first
./.venv/bin/python -m alicebot_api resume
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
```

If the CLI is exposed through a console script instead of `python -m alicebot_api`, both invocation forms should be documented and at least one must be included in review evidence.

## Required Acceptance Evidence

- exact CLI install/invocation path used during verification
- one successful capture example
- one successful recall example
- one successful resumption example
- one successful review/correction example that changes a later retrieval result
- note of any deferred CLI ergonomics intentionally left for later phases

## Implementation Constraints

- preserve shipped P5/P6/P7/P8/P9-S33 semantics
- do not require the internal web shell for the scoped flows
- keep CLI output deterministic and reviewable
- prefer stdlib CLI plumbing over new heavyweight dependencies unless clearly necessary
- do not widen the public surface beyond what `P9-S35` should inherit

## Control Tower Task Cards

### Task 1: CLI Entry and Packaging

Owner: platform/package owner

Write scope:

- `pyproject.toml`
- `apps/api/src/alicebot_api/__init__.py`
- `apps/api/src/alicebot_api/__main__.py`
- `apps/api/src/alicebot_api/cli.py`
- `apps/api/src/alicebot_api/cli_formatting.py`

Responsibilities:

- define the packaged CLI entrypoint
- keep invocation local-install friendly
- keep command tree narrow and deterministic
- ensure output contracts are stable enough for follow-on MCP mapping

### Task 2: Continuity Command Wiring

Owner: backend/runtime owner

Write scope:

- `apps/api/src/alicebot_api/continuity_capture.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/config.py`

Responsibilities:

- wire core continuity functions into CLI-safe calls
- preserve deterministic ordering and validation behavior
- expose provenance/trust signals where needed
- ensure correction flows update later recall and resumption behavior

### Task 3: Docs and Examples

Owner: docs/integration owner

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`

Responsibilities:

- document exact CLI invocation path
- add example commands against the shipped sample data
- keep docs aligned with the `P9-S33` startup path instead of reopening packaging guidance
- make the next seam toward MCP explicit

### Task 4: Verification and Reports

Owner: sprint integrator

Write scope:

- `tests/unit/test_cli.py`
- `tests/integration/test_cli_integration.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- prove command coverage against the shipped local runtime
- keep CLI output assertions stable and narrow
- document exact acceptance evidence and any deferred ergonomics
- keep scope hygiene explicit if any supporting files are touched

## Definition Of Done

- `P9-S34` CLI entrypoint exists and is callable from a documented local install
- core continuity flows are usable from the terminal without the internal shell
- command output is deterministic enough for review and future MCP parity
- docs, tests, build report, and review report are aligned
- no `P9-S35` MCP work or `P9-S36` adapter work leaks into the sprint
