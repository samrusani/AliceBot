# SPRINT_PACKET.md

## Sprint Title

Phase 9 Sprint 37 (P9-S37): Importers and Evaluation Harness

## Sprint Type

feature

## Sprint Reason

`P9-S33` shipped the public-safe `alice-core` boundary and startup path. `P9-S34` shipped the deterministic local CLI contract. `P9-S35` shipped the narrow MCP transport. `P9-S36` shipped the first concrete external adapter via OpenClaw. The next non-redundant seam is broadening importer coverage and generating reproducible evidence that imported memory improves recall, resumption, and correction-aware continuity quality.

## Planning Anchors

- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-public-core-boundary.md`
- `docs/phase9-bootstrap-notes.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`
- `docs/adr/ADR-004-openclaw-integration-boundary.md`
- `docs/adr/ADR-005-import-provenance-and-dedupe-strategy.md` if introduced
- `docs/adr/ADR-007-public-evaluation-harness-scope.md` if introduced

## Sprint Objective

Ship broader importer coverage plus a reproducible local evaluation harness so Alice can ingest at least three production-usable sources in total and generate baseline evidence for recall precision, resumption usefulness, correction effectiveness, and duplicate-memory posture.

## Git Instructions

- Branch Name: `codex/phase9-sprint-37-importers-eval-harness`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint Matters

- It moves Alice from a single-adapter proof to a credible public import story.
- It makes quality claims reproducible instead of anecdotal.
- It sets the evidence baseline that `P9-S38` launch docs and release claims must reflect.

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
- Required now (`P9-S37`):
  - broader importer coverage beyond OpenClaw
  - at least three production-usable importers in total across shipped Phase 9 surfaces
  - reproducible benchmark/evaluation harness
  - baseline report generation from local fixtures and documented commands
- Explicitly out of `P9-S37`:
  - launch narrative polish or release assets
  - public release tagging and distribution work
  - widening the MCP tool surface
  - hosted deployment or remote auth work
  - reopening OpenClaw adapter semantics except for truly shared importer fixes

## Design Truth

- Importers should map outside data into the same shipped Alice continuity model, not create source-specific behavior islands.
- Provenance and dedupe posture must stay explicit across every importer, not only OpenClaw.
- Evaluation should measure useful continuity outcomes, not generic benchmark theatre.
- `P9-S37` should leave `P9-S38` with evidence to publish, not more product ambiguity.

## Exact Surfaces In Scope

- at least two additional importer paths beyond OpenClaw, bringing shipped total importer coverage to at least three
- importer provenance and dedupe policy generalization
- reproducible fixtures for each newly shipped importer
- local evaluation harness and baseline report generation
- docs for importer usage and evaluation commands
- tests covering import success, dedupe posture, and evaluation script/report generation

## Exact Files In Scope

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `README.md`
- `ROADMAP.md`
- `ARCHITECTURE.md` if importer/eval architecture notes need syncing
- `RULES.md` if importer/eval discipline needs canonization
- `docs/phase9-sprint-33-38-plan.md`
- `docs/adr/ADR-005-import-provenance-and-dedupe-strategy.md` if introduced
- `docs/adr/ADR-007-public-evaluation-harness-scope.md` if introduced
- `apps/api/src/alicebot_api/openclaw_import.py` if shared importer abstractions are factored carefully
- `apps/api/src/alicebot_api/openclaw_adapter.py` if shared importer fixes are required
- `apps/api/src/alicebot_api/importers/` if introduced
- `apps/api/src/alicebot_api/markdown_import.py` if introduced
- `apps/api/src/alicebot_api/chatgpt_import.py` if introduced
- `apps/api/src/alicebot_api/claude_import.py` if introduced
- `apps/api/src/alicebot_api/csv_import.py` if introduced
- `apps/api/src/alicebot_api/importer_models.py` if introduced
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `apps/api/src/alicebot_api/continuity_recall.py` if eval parity fixes are required
- `apps/api/src/alicebot_api/continuity_resumption.py` if eval parity fixes are required
- `apps/api/src/alicebot_api/store.py`
- `apps/web/components/approval-detail.test.tsx` if required to keep the mandated web suite stable
- `apps/web/components/continuity-open-loops-panel.test.tsx` if required to keep the mandated web suite stable
- `apps/web/components/workflow-memory-writeback-form.tsx` if required to keep importer/eval-related submit state stable
- `scripts/load_markdown_sample_data.py` if introduced
- `scripts/load_markdown_sample_data.sh` if introduced
- `scripts/load_chatgpt_sample_data.py` if introduced
- `scripts/load_chatgpt_sample_data.sh` if introduced
- `scripts/load_claude_sample_data.py` if introduced
- `scripts/load_claude_sample_data.sh` if introduced
- `scripts/load_csv_sample_data.py` if introduced
- `scripts/load_csv_sample_data.sh` if introduced
- `scripts/run_phase9_eval.py` if introduced
- `scripts/run_phase9_eval.sh` if introduced
- `fixtures/importers/` if introduced
- `eval/` if introduced for reports/baselines/fixtures
- `tests/__init__.py` if introduced for package import stability
- `tests/unit/__init__.py` if introduced for package import stability
- `tests/integration/__init__.py` if introduced for package import stability
- `tests/unit/test_importers.py` if introduced
- `tests/unit/test_phase9_eval.py` if introduced
- `tests/integration/test_markdown_import.py` if introduced
- `tests/integration/test_chatgpt_import.py` if introduced
- `tests/integration/test_claude_import.py` if introduced
- `tests/integration/test_csv_import.py` if introduced
- `tests/integration/test_phase9_eval.py` if introduced
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## In Scope

- ship at least two additional importer paths beyond OpenClaw
- reach at least three production-usable importers total by end of sprint
- preserve explicit provenance and deterministic dedupe posture across importers
- generate a reproducible local evaluation/baseline report
- keep the mandated backend/web verification suites stable when importer/eval changes expose adjacent regressions
- measure at minimum:
  - recall precision
  - resumption usefulness
  - correction effectiveness
  - importer success and duplicate-memory posture
- document exact importer and evaluation commands

## Out Of Scope

- launch polish, screenshots, comparison pages, or public release tag work
- broad UI work
- MCP transport expansion
- generic plugin/SDK ecosystem work
- hosted ingestion services

## Required Deliverables

- at least three production-usable importers total across shipped Phase 9 work
- reproducible fixtures and loader paths for the newly added importers
- explicit importer provenance/dedupe policy if generalized beyond OpenClaw
- local evaluation harness command(s)
- sample baseline report generated from repo-local fixtures
- synced docs, reports, and any needed ADRs

## Acceptance Criteria

- at least three production-usable importers exist by the end of `P9-S37`
- newly added imported sources become queryable through Alice recall
- newly added imported sources contribute useful output to Alice resumption
- duplicate-memory posture is measurable and deterministic for every shipped importer
- a local evaluation script runs successfully and produces a baseline report from repo fixtures
- correction-aware behavior is represented in the baseline evidence, not just import-success metrics

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

If dedicated importer loaders or evaluation commands are introduced this sprint, they must be run and included in review evidence together with at least one generated baseline report path.

## Required Acceptance Evidence

- exact importer fixture paths and commands used during verification
- proof that at least three production-usable importers are working in total
- one successful recall example from at least one newly added importer
- one successful resumption example from at least one newly added importer
- one generated evaluation/baseline report path and summary
- measured duplicate-memory posture and correction-aware outcome evidence

## Implementation Constraints

- preserve shipped P5/P6/P7/P8/P9-S33/P9-S34/P9-S35/P9-S36 semantics
- keep provenance explicit and deterministic for every importer
- do not invent source-specific retrieval semantics
- prefer a narrow shared importer discipline over an over-abstracted framework
- ensure evaluation claims are reproducible from repo-local commands and fixtures

## Control Tower Task Cards

### Task 1: Importer Expansion

Owner: import/interop owner

Write scope:

- `apps/api/src/alicebot_api/importers/`
- `apps/api/src/alicebot_api/markdown_import.py`
- `apps/api/src/alicebot_api/chatgpt_import.py`
- `apps/api/src/alicebot_api/claude_import.py`
- `apps/api/src/alicebot_api/csv_import.py`
- `apps/api/src/alicebot_api/importer_models.py`
- `apps/api/src/alicebot_api/openclaw_import.py`

Responsibilities:

- add at least two additional production-usable importers beyond OpenClaw
- keep provenance and dedupe posture explicit and source-aware
- share only the abstractions that are truly common across importers
- avoid widening into launch-polish or generic platform work

### Task 2: Continuity and Evaluation Wiring

Owner: backend/runtime owner

Write scope:

- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `scripts/run_phase9_eval.py`
- `scripts/run_phase9_eval.sh`

Responsibilities:

- ensure imported data behaves consistently through shipped recall/resumption semantics
- implement the local evaluation harness and baseline report generation
- keep metrics narrow, reproducible, and tied to actual continuity outcomes
- fix only true shared importer/eval defects

### Task 3: Fixtures, Docs, and Policy

Owner: docs/integration owner

Write scope:

- `README.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`
- `RULES.md`
- `.ai/handoff/CURRENT_STATE.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/adr/ADR-005-import-provenance-and-dedupe-strategy.md`
- `docs/adr/ADR-007-public-evaluation-harness-scope.md`
- `fixtures/importers/`
- `eval/`

Responsibilities:

- document exact importer and evaluation paths
- keep provenance/dedupe rules explicit in canonical docs
- keep Phase 9 sequencing factual and non-redundant
- leave `P9-S38` with evidence-backed documentation inputs rather than open product questions

### Task 4: Verification and Evidence

Owner: sprint integrator

Write scope:

- `tests/unit/test_importers.py`
- `tests/unit/test_phase9_eval.py`
- `tests/__init__.py`
- `tests/unit/__init__.py`
- `tests/integration/__init__.py`
- `tests/integration/test_markdown_import.py`
- `tests/integration/test_chatgpt_import.py`
- `tests/integration/test_claude_import.py`
- `tests/integration/test_csv_import.py`
- `tests/integration/test_phase9_eval.py`
- `apps/web/components/approval-detail.test.tsx`
- `apps/web/components/continuity-open-loops-panel.test.tsx`
- `apps/web/components/workflow-memory-writeback-form.tsx`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- prove the newly added importers work against documented fixtures
- prove dedupe and provenance behavior are deterministic
- prove the evaluation harness runs and generates a baseline report
- land only the minimum adjacent verification fixes needed to keep required suites green
- keep scope hygiene explicit if support files are touched

## Definition Of Done

- `P9-S37` ships at least three production-usable importers in total
- local evaluation harness exists and generates a reproducible baseline report
- imported data from newly added sources behaves correctly through shipped Alice recall/resumption semantics
- docs, tests, build report, and review report are aligned
- no launch-polish or release-tag work leaks into the sprint
