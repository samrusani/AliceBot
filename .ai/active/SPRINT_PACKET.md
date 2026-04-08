# Sprint Packet

## Status

- No active build sprint is open.
- Context Compaction 01 is complete and archived under `docs/archive/planning/2026-04-08-context-compaction/` and `.ai/archive/planning/2026-04-08-context-compaction/`.
- Phase 10 planning docs are not defined yet.

## Why This File Exists

- Control Tower expects `.ai/active/SPRINT_PACKET.md` to exist even when the repo is between planning cycles.
- Keep this file as an idle-state pointer, not as a fake active sprint.

## Current Approval Branch

- Branch purpose: one-off context compaction and archival cleanup before Phase 10 planning, not a new product sprint.
- Branch name: `codex/refactor-context-compaction-01`
- Base branch: `main`
- PR strategy: create-or-update
- Merge policy: squash-merge only after `REVIEW_REPORT.md` is `PASS` and Control Tower issues explicit merge approval.

## Branch Scope

- compact live operating docs so active project memory reflects only current, durable Phase 9 truth
- preserve superseded planning/control material in archive instead of deleting it
- keep shipped Phase 9 release/quickstart/integration artifacts live and canonical
- limit non-doc code changes to validation tooling/tests required for the new archive and idle-state control truth

## Next Activation Criteria

- Run the Phase 9 release checklist and runbook on a clean environment.
- Add canonical Phase 10 planning docs.
- Replace this placeholder only when a new approved sprint is activated.
