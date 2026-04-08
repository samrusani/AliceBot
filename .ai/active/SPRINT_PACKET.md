# SPRINT_PACKET.md

## Sprint Title

Phase 9 Sprint 38 (P9-S38): Docs, Launch Assets, and Public Release

## Sprint Type

feature

## Sprint Reason

`P9-S33` through `P9-S37` shipped the public core, CLI, MCP transport, OpenClaw adapter, broader importer coverage, and reproducible evaluation evidence. The next non-redundant seam is turning that shipped product and evidence into launch-quality public documentation and release assets without reopening core product semantics.

## Planning Anchors

- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-public-core-boundary.md`
- `docs/phase9-bootstrap-notes.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`
- `docs/adr/ADR-004-openclaw-integration-boundary.md`
- `docs/adr/ADR-005-import-provenance-and-dedupe-strategy.md`
- `docs/adr/ADR-007-public-evaluation-harness-scope.md`

## Sprint Objective

Ship the launch-ready documentation, quickstart flow, integration docs, release checklist, and first public release assets for Alice v0.1, all grounded in the already-shipped local runtime, importer paths, and evaluation evidence.

## Git Instructions

- Branch Name: `codex/phase9-sprint-38-launch-and-release`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint Matters

- It converts the shipped technical wedge into something an external user can actually adopt.
- It is the public-facing proof that Phase 9 is complete.
- It should make zero new product promises that are not already supported by shipped code and evidence.

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
  - `P9-S36` OpenClaw adapter/import boundary with deterministic provenance and dedupe posture.
  - `P9-S37` broader importer coverage and reproducible local evaluation harness baseline.
- Required now (`P9-S38`):
  - launch-quality public docs and quickstart
  - integration and architecture docs aligned to shipped behavior
  - release checklist/runbook and first public versioning assets
  - claims and examples grounded only in shipped code and committed evidence
- Explicitly out of `P9-S38`:
  - new importer implementation
  - MCP tool-surface expansion
  - new adapters or runtime features
  - hosted deployment work
  - reopening product semantics to support aspirational launch copy

## Design Truth

- Docs are product surface in this sprint.
- Every public claim must be anchored to a shipped command path, fixture, or committed evidence artifact.
- Launch polish must not invent scope; it should compress and clarify what already exists.
- The release should feel credible, reproducible, and narrow, not broad and hand-wavy.

## Exact Surfaces In Scope

- public-facing README polish
- quickstart and integration documentation
- architecture overview and launch-facing repo docs
- release checklist, runbook, and version-tag prep
- launch assets that are documentation-native and evidence-backed
- public comparisons/positioning only if constrained to shipped wedge truth

## Exact Files In Scope

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `README.md`
- `PRODUCT_BRIEF.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `RULES.md` if release-doc discipline needs explicit hardening
- `CHANGELOG.md` if introduced
- `CONTRIBUTING.md` if introduced
- `SECURITY.md` if introduced
- `LICENSE` if finalized in this sprint
- `docs/phase9-sprint-33-38-plan.md`
- `docs/quickstart/` if introduced
- `docs/integrations/` if introduced
- `docs/examples/` if introduced
- `docs/runbooks/` if introduced
- `docs/release/` if introduced
- `docs/archive/` only if needed to archive superseded planning/runbook material cleanly
- `eval/baselines/phase9_s37_baseline.json` if referenced/curated in launch docs
- `eval/reports/phase9_eval_latest.json` if referenced/curated in launch docs
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## In Scope

- publish a clean external quickstart from install to first useful result
- document shipped importer paths, MCP setup, and evaluation command paths
- document architecture and product wedge in launch-ready language
- add contribution/security/release docs if needed for a credible public repo
- prepare first public release/versioning assets and checklist

## Out Of Scope

- new product implementation beyond doc-fix or release-fix necessities
- new benchmarks or importer paths beyond `P9-S37`
- screenshots/demo media generation that requires new UI work
- hosted SaaS or remote auth packaging
- broad marketing site or launch campaign work

## Required Deliverables

- polished public README
- public quickstart flow
- integration docs for CLI, MCP, and shipped importers
- architecture/repo docs aligned to shipped Phase 9 state
- release checklist and runbook
- first public version tag plan/assets
- synced docs, reports, and any release metadata needed

## Acceptance Criteria

- an external technical tester can follow the docs from local install to first useful result without handholding
- public docs accurately describe the shipped importer, CLI, MCP, and evaluation surfaces
- release checklist/runbook is complete enough to cut the first public version without reopening product ambiguity
- no public-facing claims exceed what is supported by shipped commands, tests, and baseline evidence

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
./scripts/run_phase9_eval.sh --report-path eval/reports/phase9_eval_latest.json
```

If release-tag preparation commands or doc-link verification commands are introduced this sprint, they must be run and included in review evidence.

## Required Acceptance Evidence

- exact quickstart path used during verification
- proof that shipped importer/MCP/eval doc paths were followed as written
- final release checklist/runbook path
- note of any intentionally deferred public-release items that remain outside Phase 9

## Implementation Constraints

- preserve shipped P5/P6/P7/P8/P9-S33/P9-S34/P9-S35/P9-S36/P9-S37 semantics
- do not add launch copy that outruns shipped functionality
- prefer doc clarity and reproducibility over breadth
- keep release artifacts local-first and technically concrete
- avoid reopening old planning drift unless necessary for launch truth

## Control Tower Task Cards

### Task 1: Public Docs

Owner: docs/product owner

Write scope:

- `README.md`
- `PRODUCT_BRIEF.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `docs/quickstart/`
- `docs/integrations/`
- `docs/examples/`

Responsibilities:

- produce launch-ready docs for the shipped wedge
- keep wording anchored to shipped commands and evidence
- compress complexity without hiding constraints

### Task 2: Release Readiness

Owner: release/control owner

Write scope:

- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `LICENSE`
- `docs/runbooks/`
- `docs/release/`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- add the release checklist and runbook
- prepare version/release metadata
- ensure repo-level public-readiness docs exist where needed

### Task 3: Canonical Truth Sync

Owner: control-tower integrator

Write scope:

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `docs/phase9-sprint-33-38-plan.md`
- `RULES.md`

Responsibilities:

- keep the final Phase 9 story internally consistent
- ensure no redundant feature scope leaks into the launch sprint
- leave the repo in a clean post-Phase-9 handoff state

## Definition Of Done

- `P9-S38` produces launch-ready docs and release assets grounded in shipped product truth
- quickstart, integration docs, and release checklist are complete and review-safe
- Phase 9 can be treated as complete without another implementation sprint
