# Phase 9 Sprint 33 Control Tower Packet

## Sprint

`P9-S33: Public Core Packaging`

## Objective

Package the existing internal Alice substrate so an external technical user can install it locally, load sample data, and complete one recall flow and one resumption flow from canonical docs without founder intervention.

## Why This Sprint Matters

- It is the first packaging sprint that turns internal product truth into a public technical product.
- Every later Phase 9 sprint depends on a stable package boundary, startup path, and sample-data story.
- It reduces launch risk by forcing one documented install path to match real repo behavior.

## Required Planning Inputs

- [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md)
- [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md)
- [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md)
- [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md)
- [.ai/handoff/CURRENT_STATE.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/handoff/CURRENT_STATE.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)
- [phase9-product-spec.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/phase9-product-spec.md)
- [phase9-sprint-33-38-plan.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/phase9-sprint-33-38-plan.md)
- [phase9-public-core-boundary.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/phase9-public-core-boundary.md)

## Scope

### In Scope

- explicit public-safe package boundary for `alice-core`
- one canonical local startup flow
- sample-data fixture or seed path usable by external users
- install and smoke verification path for recall and resumption
- repo and docs reshaping needed to support the public-core story
- ADR capture for public boundary decisions blocking follow-on work

### Out Of Scope

- CLI command implementation
- MCP server implementation
- OpenClaw adapter implementation
- hosted deployment modes
- broad connector writes
- repo-wide restructure unrelated to public packaging

## Workstreams

### Workstream 1: Public Boundary and Packaging

Owner:
- platform/package owner

Primary outcome:
- public-facing package boundary is explicit enough that later CLI and MCP work can target stable seams

Likely files:
- [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md)
- [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md)
- [README.md](/Users/samirusani/Desktop/Codex/AliceBot/README.md)
- [pyproject.toml](/Users/samirusani/Desktop/Codex/AliceBot/pyproject.toml)
- [docker-compose.yml](/Users/samirusani/Desktop/Codex/AliceBot/docker-compose.yml)
- [LICENSE](/Users/samirusani/Desktop/Codex/AliceBot/LICENSE)
- [docs/phase9-public-core-boundary.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/phase9-public-core-boundary.md)

Tasks:
- define what is in `alice-core` versus still internal
- define required runtime assumptions for v0.1
- confirm one supported local startup path
- capture any blocking public packaging decision as an ADR or explicit deferred item

Acceptance checks:
- public boundary is documented without relying on internal tribal knowledge
- no canonical doc implies unsupported public surfaces are already shipped
- boundary is narrow enough that `P9-S34` and `P9-S35` have stable targets

### Workstream 2: Startup Path and Sample Data

Owner:
- backend/runtime owner

Primary outcome:
- external user can stand up the system from scratch and load usable sample data

Likely files:
- [.env.example](/Users/samirusani/Desktop/Codex/AliceBot/.env.example)
- [scripts/migrate.sh](/Users/samirusani/Desktop/Codex/AliceBot/scripts/migrate.sh)
- [scripts/api_dev.sh](/Users/samirusani/Desktop/Codex/AliceBot/scripts/api_dev.sh)
- [scripts/dev_up.sh](/Users/samirusani/Desktop/Codex/AliceBot/scripts/dev_up.sh)
- `fixtures/` or equivalent sample-data location
- relevant API bootstrap/seed helpers under `apps/api` or `scripts`

Tasks:
- ensure sample-data path is deterministic and documented
- ensure startup scripts and env defaults match docs
- verify recall and resumption can run against the sample dataset
- remove ambiguity between internal-only and public setup steps

Acceptance checks:
- clean-machine setup path is executable end to end
- sample dataset is available or loadable from a single documented flow
- one recall example and one resumption example work from the documented setup

### Workstream 3: Docs and External Onboarding

Owner:
- docs/integration owner

Primary outcome:
- repo onboarding works for an external technical user without prior Alice context

Likely files:
- [README.md](/Users/samirusani/Desktop/Codex/AliceBot/README.md)
- [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md)
- [.ai/handoff/CURRENT_STATE.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/handoff/CURRENT_STATE.md)
- new quickstart docs if introduced under `docs/quickstart/`

Tasks:
- keep README onboarding-focused
- ensure current state remains factual about shipped versus targeted surfaces
- make roadmap sequencing consistent with packaging-first execution
- add any missing quickstart examples needed to close the install gap

Acceptance checks:
- README supports install, basic verification, and repo orientation only
- CURRENT_STATE reflects post-Phase-8 shipped truth and pre-Phase-9 packaging gaps
- roadmap and sprint packet do not drift on current milestone or next move

### Workstream 4: Integration Review

Owner:
- sprint integrator

Primary outcome:
- sprint lands as one coherent package rather than disconnected doc and setup edits

Tasks:
- verify doc, runtime, and sample-data paths agree
- verify any new ADRs match the canonical docs
- verify no sprint work quietly expands scope into CLI, MCP, or OpenClaw delivery
- prepare final evidence notes for review

Acceptance checks:
- all changed docs point to the same Phase 9 contract
- no conflicting startup commands remain in canonical docs
- sprint review can validate scope directly from changed files

## Required Commands

Minimum verification expected before review:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/api_dev.sh
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
```

If a dedicated sample-data or smoke command is added this sprint, include it in the review evidence and README.

`P9-S33` sample-data command:

```bash
./scripts/load_sample_data.sh
```

## Required Acceptance Evidence

- exact startup path used during verification
- exact sample-data load path used during verification
- one successful recall example
- one successful resumption example
- note of any deferred public-boundary decision moved into ADRs

## Docs To Update

- [README.md](/Users/samirusani/Desktop/Codex/AliceBot/README.md)
- [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md)
- [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md)
- [.ai/handoff/CURRENT_STATE.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/handoff/CURRENT_STATE.md)
- any new quickstart or packaging docs introduced in-sprint
- ADRs for blocking packaging decisions

## Definition Of Done

Sprint 33 is done when:

- the repo has one canonical public-core startup path
- sample data is available for immediate technical evaluation
- recall and resumption can be demonstrated from public-facing docs
- the public package boundary is explicit enough that Sprint 34 can implement CLI work without reopening core packaging ambiguity
