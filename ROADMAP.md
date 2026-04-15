# Roadmap

## Baseline Context (Not Roadmap Work)
- Phase 9: shipped
- Phase 10: shipped
- Phase 11: shipped
- Bridge `B1`-`B4`: shipped
- Bridge Phase (`B1`-`B4`): shipped
- Phase 12: shipped
- `v0.3.2`: released

These remain baseline truth and are not future milestones.

## Active Planning Status
- Phase 13 is active.
- `P13-S1` One-Call Continuity is shipped.
- `P13-S2` Alice Lite is the active execution sprint.
- `P13-S3` Memory Hygiene + Conversation Health follows after Alice Lite.

## Phase 13 Planned Milestones

### P13-S1: One-Call Continuity
- ship `POST /v1/continuity/brief`
- ship matching CLI `alice brief`
- ship matching MCP `alice_brief`
- return one continuity bundle containing summary, recent changes, open loops, conflicts, next action, provenance, and trust posture
- make this the default integration surface for external agents

Status: shipped

### P13-S2: Alice Lite
- add one-command local startup
- add smaller-footprint deployment profile
- tighten quickstart and first-result path
- keep semantics aligned with the full Alice baseline

Status: active

### P13-S3: Memory Hygiene + Conversation Health
- surface duplicates, stale facts, unresolved contradictions, and review queue pressure
- surface recent threads, stale threads, risky threads, and thread health
- improve operational visibility without adding new substrate work

Status: queued

## Sequencing Rules
- Phase 13 is an adoption layer on top of the shipped Phase 12 baseline.
- Prioritize one-call continuity first, then Alice Lite, then hygiene and conversation health.
- Do not add new substrate work unless it is required to support those deliverables.
- Judge every Phase 13 change against three questions:
  - does this reduce integration complexity?
  - does this improve first-run experience?
  - does this make memory quality more visible?
- Do not widen Phase 13 into retrieval research, graph-database migration, new channels, new provider/runtime work, marketplace work, or enterprise/admin expansion.

## Beyond Phase 13
- No post-Phase-13 feature plan is currently defined.
- The next step after Phase 13 is to decide the next release boundary and the next phase.
