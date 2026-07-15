# Alice v0.10.4 Fifth-Audit Remediation Handoff

This directory is the control-tower handoff for the uncommitted v0.10.4
remediation built from `main` at
`d52e32114eb0b4ef63499e53be14b70dc0864487`.

The tree is intentionally uncommitted. No version source was bumped, no tag or
release was created, and the immutable v0.10.3 release notes and checksums were
not edited. The release engineer owns commit selection, version finalization,
the clean-SHA semantic gate, publication, and the post-publication truth flip.

## Package contents

- `SURFACE_INVENTORY.md` — the pre-edit enumeration of HTTP, MCP, CLI,
  scheduler, web, PostgreSQL, and SQLite surfaces.
- `FIX_MATRIX.md` — finding-by-finding disposition, implementation boundary,
  and fail-on-old coverage.
- `BUILD_REPORT.md` — builder verification commands and evidence.
- `ENGINEER_HANDOFF.md` — review order, residual limitation, and release steps.
- `REVIEW_REPORT.md` — reviewer-owned historical Batch 15 approval. The
  builder does not edit or delete it, and it does not approve Batch 16.

## Builder state

Repair Batch 16 is the current bounded correction. It closes the engineering-
team whitespace finding in the memory-embedding compare-and-swap digest. The
PostgreSQL SQL mirror previously used locale-dependent POSIX `[[:space:]]`,
which deterministically omitted U+001C–U+001F and could disagree with Python
for NBSP-class whitespace. It now uses the same explicit CPython 3.12
29-codepoint `chr()`-enumerated `btrim` table already installed by migration
`0090`, without importing migration code at runtime or changing any other
embedding-text semantics.

The fail-on-old SQL-shape regression proves that all three consumers—signed
vector freshness, signed embedding-update CAS, and missing-embedding
selection—contain all 29 codepoints and no POSIX trim. Live role-separated
PostgreSQL verifies NBSP, U+001C, and mixed blank/deduplicated fields through
CAS acceptance, no re-embed loop, and signed vector participation. The full
gate passed 3,332 units with coverage floors, 463 role-separated PostgreSQL
integrations, release-static/control, 127 LongMemEval tests plus evidence
replay, unchanged-web readback, and two byte-identical package builds with
Twine, release-check, seven-file archive parity, and installed wheel/sdist
smokes. The final tracked patch and fixed 12-file remediation bundle each
reproduced twice and are recorded in the self-excluded builder report. Batch
16 review approved the production CAS semantics and returned changes required
on one documentation-truth P3. Refreeze 17 changes only the stale Batch 15/
current-review wording plus its fail-on-old control guard. Independent review
of the exact Refreeze 17 carrier remains required, so it is not release-
approved.

Batch 15 is historical, independently approved, and superseded. Its open-loop
row parity, alpha documentation, fake ordering, full gates, package receipts,
and reviewer report remain valid historical evidence, but its approved carrier
still contained the embedding-CAS whitespace mismatch and cannot approve the
current tree.

Batch 14 is historical, frozen, and review-rejected. Its 4 focused units, 338
complete MCP/store units, 3,329 full units with required coverage floors, 461
role-separated PostgreSQL integrations, release-static/control checks,
LongMemEval plus evidence replay, unchanged-web readback, reproducible package
pair and isolated smokes all passed. Its tracked-patch SHA-256
`0fc353e4c37f153e3ba283959bf4564e5021bfd43d3813ad4cf800c3cad99290`
and fixed 12-file bundle SHA-256
`638e9e0ada3c4698a79fd120cbdabfda9eb28c1451aebde282db088f8e2a23bd`
each reproduced twice. Independent review then returned exactly the three
bounded P2s above, so that evidence does not approve Batch 15.

Batch 13 was never frozen. It was an unfrozen pre-finalization candidate that
fixed the fake store's cross-leaf matching only. Two focused regressions, the
256-test MCP file, and 3,328 full units passed. Exact production-file hashes
were unchanged from the frozen Batch 12 carrier, so its 460-case PostgreSQL
result was carried without rerun. Independent review then returned one
Unicode/collation P2. No Batch 13 static, package, fingerprint, or release
approval claim exists.

Batch 12 is historical, frozen, and review-rejected. Its production SQLite and
PostgreSQL recursive string-leaf implementation was approved, but the fake
store could still combine text from different JSON leaves before matching.
The frozen Batch 12 gates, packages, and twice-reproduced fingerprints remain
historical evidence only and do not approve Batch 15.

Batch 11's full 3,327-unit/460-PostgreSQL gate, release-static, LongMemEval,
web, package, and twice-reproduced fingerprints were green. Its subsequent
independent review approved persisted-source closure and every other bounded
area, but returned changes required on the single event-payload P2. Batch 11
evidence is historical and does not approve the current tree.

Batch 10's full gate passed 3,325 units with coverage floors and 457
role-separated PostgreSQL integrations. Its 1,171-test integrated seam,
release-static, 127 LongMemEval tests plus evidence replay, unchanged 202-input
web carrier, two byte-identical package builds, Twine/release-check/archive
parity, isolated wheel/sdist smokes, and twice-reproduced fingerprints also
passed. Its subsequent independent review returned changes required on exactly
two bounded findings, so Batch 10 evidence is historical and does not approve
the current tree; the same is true of Batches 8 and 9. Clean-SHA semantic
attestation, version finalization, commit selection, and publication remain
external release-engineer gates after Batch 15 review.
