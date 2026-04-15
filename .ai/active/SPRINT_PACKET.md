# Sprint Packet

## Sprint Title
Phase 12 Closeout and `v0.3.2` Release Update

## Activation Note
- This packet is active.
- `v0.2.0` is the latest published tag.
- `v0.3.2` is the current release target for the completed Phase 12 boundary.
- Phase 12 implementation scope is complete through `P12-S1` to `P12-S5`.

## Sprint Type
closeout

## Sprint Reason
Phase 12 implementation is complete. The remaining work is not another product sprint. It is closeout:
- summarize the completed phase clearly
- align canonical docs to Phase 12 completion
- update release docs from the old `v0.2.0` boundary to the new `v0.3.2` target
- prepare the repo for either a `v0.3.2` tag or next-phase planning

## Git Instructions
- Branch Name: `codex/phase12-closeout-v0-3-2`
- Base Branch: `main`
- PR Strategy: one docs/control branch, one PR
- Merge Policy: squash merge after review `PASS` and explicit approval

## Baseline To Preserve
- shipped Phase 9 through Phase 11 baseline
- shipped Bridge `B1` through `B4`
- shipped Phase 12 `P12-S1` through `P12-S5`
- current published tag remains `v0.2.0` until a new tag is cut

## Exact Goal
Close Phase 12 cleanly and move the documented release boundary to `v0.3.2` without falsely claiming that the `v0.3.2` tag has already been cut.

## In Scope
- Phase 12 closeout packet
- Phase 12 closeout summary
- current-state and roadmap alignment for completed Phase 12
- `v0.3.2` release checklist, tag plan, and runbook
- README and public-doc release-boundary updates
- changelog update for completed Phase 12

## Out Of Scope
- new product or runtime features
- reopening any Phase 12 implementation sprint
- tagging or publishing `v0.3.2` without explicit approval
- defining the next phase in detail

## Proposed Files And Modules
- `README.md`
- `CHANGELOG.md`
- `PRODUCT_BRIEF.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `RULES.md`
- `CURRENT_STATE.md`
- `.ai/handoff/CURRENT_STATE.md`
- `.ai/active/SPRINT_PACKET.md`
- `docs/runbooks/phase12-closeout-packet.md`
- `docs/phase12-closeout-summary.md`
- `docs/release/v0.3.2-release-checklist.md`
- `docs/release/v0.3.2-tag-plan.md`
- `docs/runbooks/v0.3.2-public-release-runbook.md`
- public docs that still hard-code the old `v0.2.0` release boundary
- `scripts/check_control_doc_truth.py`

## Planned Deliverables
- Phase 12 closeout packet
- Phase 12 closeout summary
- `v0.3.2` release-target docs
- canonical doc alignment to completed Phase 12
- updated release-boundary references in public docs

## Acceptance Criteria
- Phase 12 is described as complete in canonical docs
- The documented release target is `v0.3.2`
- the docs do not falsely claim that `v0.3.2` is already tagged or published
- closeout docs summarize what shipped in `P12-S1` through `P12-S5`
- control-doc truth passes after the closeout update

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`

## Control Tower Decisions Needed
- whether to tag and publish `v0.3.2` immediately after closeout
- whether to run a dedicated release-readiness pass before the `v0.3.2` tag
- what the next planned phase is after Phase 12

## Exit Condition
This closeout packet is complete when Phase 12 is summarized cleanly, canonical docs reflect completed Phase 12 truth, and the documented release target is updated to `v0.3.2` without claiming a tag that has not yet been cut.
