# Roadmap

## Baseline Context (Not Roadmap Work)
- Phase 9: shipped
- Phase 10: shipped
- Phase 11: shipped
- Bridge `B1`-`B4`: shipped
- Bridge Phase (`B1`-`B4`): shipped
- `v0.2.0`: released

These remain baseline truth and are not future milestones.

## Active Planning Status
- Phase 12 Sprint 1 (`P12-S1`) is shipped.
- Phase 12 Sprint 2 (`P12-S2`) is shipped.
- Phase 12 Sprint 3 (`P12-S3`) is the active execution sprint.
- `P12-S3` is the contradiction-and-trust sprint for the Phase 12 quality stack.

## Phase 12 Milestones

### P12-S1: Hybrid Retrieval + Reranking
- add hybrid retrieval pipeline
- add reranking and retrieval traces
- expose debug visibility through API, CLI, and MCP

### P12-S2: Automated Memory Operations
- add explicit memory operation candidates and commit engine
- define auto-apply vs review thresholds

### P12-S3: Contradiction Detection + Trust Calibration
- add contradiction cases and resolution flow
- add trust-signal computation and retrieval penalties

### P12-S4: Public Eval Harness
- ship public fixture suites and local eval runner
- commit baseline reports and eval docs

### P12-S5: Task-Adaptive Briefing
- add brief compiler and brief modes
- integrate provider/model-pack briefing strategy

## Release Sequencing
- `v0.3.0`: retrieval and memory quality (`P12-S1` through `P12-S3`)
- `v0.3.1`: public evaluation (`P12-S4`)
- `v0.3.2`: task-adaptive briefing (`P12-S5`)

## Sequencing Rules
- Keep shipped baseline out of roadmap sections.
- Do not widen Phase 12 into graph migration, marketplace, enterprise/compliance, or new channel work.
- Use eval evidence to justify public quality claims before updating release docs.
- Treat later releases as separate contracts; do not collapse all Phase 12 work into one oversized sprint.

## Beyond Phase 12
- No post-Phase-12 feature plan is defined in the source packet.
- Additional work after `v0.3.2` requires a new planning pass.
