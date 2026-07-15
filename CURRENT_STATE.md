# Current State

## Snapshot

- `v0.11.0` is the latest published release. It is available from PyPI and
  GitHub; exact artifact digests are in
  `docs/release/v0.11.0-checksums.txt`.
- `v0.11.0` shipped the Phase 1 periphery cut, removing product
  periphery so the default runtime matches Alice's two priorities: a small
  agent interface and high-quality, explainable retrieval/memory.
- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. It is not a repeated estimate or a measurement of this candidate.
- Alice remains public-alpha, pre-1.0, local-first, single-user, and self-hosted.

## What `v0.11.0` Shipped

- Keeps the eleven-tool core MCP surface, core HTTP/CLI memory workflows,
  per-agent keys, continuity, provenance, retrieval, traces, entities,
  artifacts, provider-backed embeddings, and the local review console.
- Removes Telegram channels, hosted administration/design-partner controls,
  hosted identity/session/device management, chief-of-staff/chat/model-pack
  features, and the public `/v0/responses` chat surface from the current product
  surface. Internal response-generation/jobs remain behind retained
  `/v1/runtime/invoke` for durable provider idempotency.
- Leaves task, approval, execution, Gmail, and Calendar compatibility surfaces
  unmounted by default. Keyless local operators may temporarily mount the
  surviving compatibility surface with `ALICE_LEGACY_SURFACES=1`; it is
  deprecated for removal before `1.0`.
- Removes legacy MCP tools whose backing surfaces no longer exist. Retained
  long-tail memory tools require `ALICE_MCP_LEGACY_TOOLS=1`; only the three task-
  brief tools additionally require `ALICE_LEGACY_SURFACES=1`. Key-bound MCP
  exposes the eleven-tool core only.
- Retains all existing database migrations as immutable schema history; removed
  surfaces leave their historical tables inert instead of destructively
  rewriting old migrations.
- Reconciles architecture, product, roadmap, OpenAPI, test, and documentation
  truth with the post-cut runtime. Detailed v0.10.4 repair chronology now lives
  in `docs/handoff/history/v0.10.4-repair-batches.md`.

## Verification Posture

- Phase 1 is complete only when default and compatibility-enabled route/tool
  inventories, both persistence modes, the full Python/web/release matrix, and
  independent review all pass on one frozen tree.
- OpenAPI remains fail-closed: every mounted operation needs an explicit
  contract, every contract must map to a mounted operation, and phantom keys are
  rejected.
- OCR and transcription execution remain out of scope. Connectors accept text
  payloads extracted by external tools.

## Release Boundary

`v0.11.0` is tagged, published, and immutable. Its authoritative records are:

- `docs/release/v0.11.0-release-notes.md`
- `docs/release/v0.11.0-checksums.txt`

`v0.10.4` is the prior published release; its records remain at
`docs/release/v0.10.4-release-notes.md` and `docs/release/v0.10.4-checksums.txt`.

Historically, the candidate remained unpublished until exact-SHA gates, independent
review, artifact reproducibility, PyPI publication, and GitHub finalization all
succeed through the transactional release workflow.

## Product Boundaries

- No hosted service, multi-tenant control plane, or SLA.
- No managed OAuth consent/account-linking or automatic account polling.
- No Telegram or other channel transport in the current runtime.
- No public bundled chat/response product, chief-of-staff product, or model
  packs. Internal response jobs support retained provider invocation only.
- No silent capture from arbitrary conversations.
- No OCR or transcription execution; Alice only ingests extracted text.
- Durable agent writes remain policy-checked, provenance-linked, and reviewable.
