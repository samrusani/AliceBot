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

- no published MCP server surface exists yet
- importer and adapter story is not yet public-ready
- OSS license finalization is still open

## Current Milestone

Phase 9: Alice Public Core and Agent Interop

## Latest State Summary

`P9-S33` and `P9-S34` are now shipped baselines:

- package boundary is documented around `alice-core`
- canonical local startup path is documented and script-backed
- deterministic sample fixture exists at `fixtures/public_sample_data/continuity_v1.json`
- sample load path exists at `./scripts/load_sample_data.sh`
- packaged CLI entrypoint exists at `python -m alicebot_api` (optional console script `alicebot`)
- continuity command coverage exists for capture, recall, resume, open-loops, review queue/show/apply, and status
- correction flow through CLI now deterministically changes later recall/resume outputs

The next active seam is `P9-S35`:

- mirror the shipped CLI continuity contract via MCP tool transport
- keep parity strict with existing deterministic CLI semantics
- avoid reopening continuity behavior in transport work

## Critical Constraints

- Preserve shipped P5/P6/P7/P8 semantics.
- Keep public interop deterministic and provenance-backed.
- Do not expand into unsafe autonomy or broad connector write actions during Phase 9.
- Keep the public v0.1 install path local-first and straightforward.

## Immediate Next Move

Execute `P9-S35` on top of the `P9-S33`/`P9-S34` boundary:

- map MCP tools directly to the shipped CLI behavior contract
- preserve deterministic output semantics for parity tests
- keep startup/sample-data path unchanged while MCP is introduced

## Legacy Compatibility Markers

Repository lineage remains continuous through Phase 3 Sprint 9.

Active Sprint focus is Phase 4 Sprint 14.

Gate ownership is canonicalized to Phase 4 runner script names.
