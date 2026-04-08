# Current State

## What Exists Today

- Phase 4 release-control and MVP qualification/sign-off seams are complete and trusted baseline.
- Phase 5 continuity capture, recall, resumption, review, correction, and open-loop seams are shipped baseline.
- Phase 6 memory trust-calibration, review prioritization, retrieval evaluation, and trust dashboard seams are shipped baseline.
- Phase 7 chief-of-staff prioritization, follow-through, preparation, and weekly review seams are shipped baseline.
- Phase 8 operational chief-of-staff handoff, queue, routing, and outcome-learning seams are shipped baseline.
- The current product surface is a local-first, trust-calibrated continuity and chief-of-staff system with bounded operator UI, governed workflows, and a shipped local continuity CLI.

## Stable / Trusted Areas

- deterministic continuity and resumption behavior
- correction-aware memory behavior
- open-loop review and brief generation
- chief-of-staff recommendation and handoff substrate
- release-control and evidence infrastructure
- approval-bounded operational posture

## Incomplete / At-Risk Areas

- importer coverage is now broader but still file-import scoped (OpenClaw + Markdown + ChatGPT)
- evaluation harness is local and fixture-backed; hosted/remote benchmarking is still intentionally out of scope
- OSS license finalization is still open

## Current Milestone

Phase 9: Alice Public Core and Agent Interop

## Latest State Summary

`P9-S33`, `P9-S34`, `P9-S35`, `P9-S36`, and `P9-S37` are now shipped baselines:

- package boundary is documented around `alice-core`
- canonical local startup path is documented and script-backed
- deterministic sample fixture exists at `fixtures/public_sample_data/continuity_v1.json`
- sample load path exists at `./scripts/load_sample_data.sh`
- packaged CLI entrypoint exists at `python -m alicebot_api` (optional console script `alicebot`)
- continuity command coverage exists for capture, recall, resume, open-loops, review queue/show/apply, and status
- correction flow through CLI now deterministically changes later recall/resume outputs
- local MCP server entrypoint exists at `python -m alicebot_api.mcp_server` (optional console script `alicebot-mcp`)
- ADR-003 MCP tools are wired to shipped continuity seams:
  - `alice_capture`
  - `alice_recall`
  - `alice_resume`
  - `alice_open_loops`
  - `alice_recent_decisions`
  - `alice_recent_changes`
  - `alice_memory_review`
  - `alice_memory_correct`
  - `alice_context_pack`
- MCP interoperability proof is now covered by integration tests for:
  - successful `alice_recall` and `alice_resume` calls
  - correction via `alice_memory_correct` changing subsequent retrieval deterministically
  - structured parity against shipped CLI/core behavior
- OpenClaw adapter/import path exists for file-based workspace/export input:
  - adapter modules: `openclaw_adapter.py`, `openclaw_models.py`, `openclaw_import.py`
  - loader scripts: `./scripts/load_openclaw_sample_data.sh` and `load_openclaw_sample_data.py`
  - deterministic fixture path: `fixtures/openclaw/workspace_v1.json`
  - deterministic dedupe posture: workspace+payload fingerprint (repeat import returns noop duplicates)
  - imported provenance is explicit via `source_kind=openclaw_import` and OpenClaw source metadata
- OpenClaw interop proof is covered by tests for:
  - import -> recall/resumption behavior on imported scope
  - shipped MCP `alice_recall`/`alice_resume` usage over imported data without MCP surface expansion
- ADR-004 defines the accepted OpenClaw integration boundary and scope constraints.
- Additional importer paths now exist and are shipped:
  - markdown importer: `markdown_import.py` plus `./scripts/load_markdown_sample_data.sh`
  - ChatGPT importer: `chatgpt_import.py` plus `./scripts/load_chatgpt_sample_data.sh`
- Shared importer provenance/dedupe persistence now uses one deterministic policy seam:
  - `apps/api/src/alicebot_api/importers/common.py`
  - importer-typed provenance fields with source-specific dedupe keys
- Local Phase 9 evaluation harness is now shipped:
  - command: `./scripts/run_phase9_eval.sh`
  - generated report path: `eval/reports/phase9_eval_latest.json`
  - committed baseline report path: `eval/baselines/phase9_s37_baseline.json`
- ADR-005 and ADR-007 now define the accepted importer provenance/dedupe and evaluation-harness boundaries.

## Critical Constraints

- Preserve shipped P5/P6/P7/P8 semantics.
- Keep public interop deterministic and provenance-backed.
- Do not expand into unsafe autonomy or broad connector write actions during Phase 9.
- Keep the public v0.1 install path local-first and straightforward.

## Immediate Next Move

Execute `P9-S38` on top of the shipped `P9-S37` boundary:

- convert shipped `P9-S37` evidence and commands into launch-quality public docs
- keep claims anchored to reproducible local importer/evaluation evidence
- preserve startup/sample-data/runtime determinism and avoid MCP contract expansion unless parity defects are found

## Legacy Compatibility Markers

Repository lineage remains continuous through Phase 3 Sprint 9.

Active Sprint focus is Phase 4 Sprint 14.

Gate ownership is canonicalized to Phase 4 runner script names.
