# Active Sprint Packet

<!-- alice-sprint-scope: phase-2-only -->

## Objective

Alice v0.11.1 Phase 2 debt sweep.

Close the bounded post-periphery-cut correctness, test-infrastructure, cleanup,
and release-process debt on the published v0.11.0 base. Items 2.0 through 2.14
are the complete carrier scope.

## Carrier

- Branch: `codex/v0111-phase2-debt-sweep`
- Base commit: `5f0a92d77d02b0699af3054fced7427929808aa8`
- Target version: `0.11.1`
- Latest published release: `v0.11.0`
- State at package-input freeze: uncommitted implementation candidate. The
  bounded local builder matrix was green while final packages, a superseding
  receipt, and independent review were still pending. Exact-SHA external gates
  remain pending.

## Item disposition

- **2.0 — implemented:** required flag-off real-PostgreSQL default-surface
  bootstrap/capture/recall/resume/context-pack/review smoke.
- **2.1 — implemented:** stable public error codes/static messages across the
  surviving surface; local source repair is separate from post-push CodeQL
  alert closure.
- **2.2 — implemented:** `list_memories(query=...)` and
  `list_resume_memory_events(query=...)` use the open-loop ASCII case-
  insensitive literal filtering contract across PostgreSQL, SQLite, and fakes;
  generic `search_memories`/`alice_recall` retrieval is unchanged.
- **2.3 — implemented:** target-filtered, indexed terminal project-update event
  replay with stable order and deduplication.
- **2.4 — implemented:** reject fails before mutation when the mandatory memory
  key is absent.
- **2.5 — implemented:** generic HTTP, MCP, and CLI memory mutations cannot
  strand a pending project-update candidate.
- **2.6 — owner-selected design implemented:** coupled true redaction converges
  artifacts, rating free text, provenance quotes, memories, revisions, and
  events on content-free skeletons without rolling back applied project state;
  numeric ratings retain structural audit value. Source and source-chunk
  evidence remains unchanged because it may be shared across memories.
- **2.7 — implemented:** explicit CPython whitespace normalization and defensive
  source-domain vocabulary alignment.
- **2.8 — implemented:** strict fake-store filters/deleted parity, coverage
  floor, release-body mypy coverage, workflow shape, and readme-pointer truth.
- **2.9 — implemented:** response-generation code trimmed to retained provider
  runtime consumers.
- **2.10 — already satisfied:** Phase 1 removed the five empty web directories.
- **2.11 — already satisfied:** import-time legacy flag and provider
  re-registration notes shipped with Phase 1.
- **2.12 — obsolete after re-measurement:** the entrypoint rate limiter no
  longer exists on the post-cut surface.
- **2.13 — decision recorded:** keep the fail-closed bulk-advisory wrapper while
  Node 20 and pnpm 10 remain pinned.
- **2.14 — evaluated:** accepted action/pytest pins are in the carrier;
  incompatible major dependency candidates remain deferred to dedicated
  compatibility work. External pull-request closure waits for a committed green
  SHA.

## Boundaries

- Phase 3 has not begun and is outside this carrier.
- No roadmap features, hosted-offering work, security review, publication,
  tagging, pushing, or repository-setting mutation.
- Existing migrations through `0090` and all v0.10.x/v0.11.0 release records
  remain immutable.
- Text extraction happens outside Alice.
  Alice does not perform OCR or transcription.

## Exit condition

At package-input freeze, the remaining exit condition was to reproduce one
exact uncommitted tree twice, record the full required matrix and receipts,
obtain an independent review with no blocker, and hand the carrier to the
release engineer for verification. Final outcomes belong in the Phase 2
`BUILD_REPORT.md` and reviewer-authored `REVIEW_REPORT.md`.

Stop after the Phase 2 handoff; do not begin Phase 3.
