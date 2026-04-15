# Roadmap

## Baseline Context (Not Roadmap Work)
- Phase 9: shipped
- Phase 10: shipped
- Phase 11: shipped
- Bridge `B1`-`B4`: shipped
- Bridge Phase (`B1`-`B4`): shipped
- Phase 12: shipped
- Phase 13: shipped
- `v0.4.0`: released

These remain baseline truth and are not future milestones.

## Current Planning Status
- Phase 13 is shipped.
- No post-Phase-13 execution sprint is active yet.
- The next roadmap step is to define the next phase on top of the `v0.4.0` baseline.

## Completed Phase 13 Sequence

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

Status: shipped

### P13-S3: Memory Hygiene + Conversation Health
- surface duplicates, stale facts, unresolved contradictions, and review queue pressure
- surface recent threads, stale threads, risky threads, and thread health
- improve operational visibility without adding new substrate work

Status: shipped

## Next Roadmap Gate
- Define the next phase explicitly before reactivating `.ai/active/SPRINT_PACKET.md` for new build work.
- Preserve the shipped one-call continuity, Alice Lite, and hygiene/thread-health surfaces as baseline behavior.

## Beyond Phase 13
- No post-Phase-13 feature plan is currently defined.
- The next step after Phase 13 is to define the next phase, not to reopen Phase 13 work.
