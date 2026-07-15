# Roadmap

## Baseline (Not Roadmap Work)

- `v0.10.3`: latest published release. It carries the fourth-audit remediation
  on top of the v0.10.2 semantic-vector, capture-deduplication, lifecycle,
  scoped-retrieval, pgvector 0.8+, typing, web-quality, installed-artifact, and
  structured-attestation baseline. It is tagged and immutable on GitHub and
  published on PyPI; exact artifact digests are in
  `docs/release/v0.10.3-checksums.txt`.
- `v0.9.4`: prior published release. It remains available as historical
  evidence but is superseded by v0.10.3.
- `v0.9.3`, `v0.10.0`, and `v0.10.1`: withdrawn or failed-publication versions;
  none has a PyPI distribution. Do not recommend them for installation.
- `v0.9.1`: prior release associated with the historical LongMemEval_s
  **79.4% (397/500)** single run. The run is dated 2026-07-07 and must not be
  presented as a repeated result or current-version benchmark.
- `v0.9.0`: Memory Operations Protocol, Context API v2, temporal graph memory,
  entity resolution, expanded export/import, and the published scale envelope.
- `v0.8.0`: typed and staleness-aware retrieval, agentic writes, key-bound
  scopes, consolidation, memory-quality evals, and the LongMemEval harness.
- `v0.7.0`: zero-infrastructure SQLite on-ramp published as `alice-memory`.
- `v0.6.0`: hybrid FTS/vector retrieval, consolidated MCP surface, per-agent
  API keys, and live-store evals.

## Current Remediation

`v0.10.4` is the current release-hardening candidate. It fixes the
fifth-audit correctness, workspace-selection, project-update lifecycle,
SQLite-scope, API-contract, provider, documentation, and release-truth defects
forward from the immutable v0.10.3 release.

Repair Batch 9 validated capture identity and atomic dedupe-key
maintenance; key-bound core MCP explanation policy; exact terminal
candidate-created evidence for the locked artifact; finite integral numeric
scope parity; the project-scoped legacy context tree's five resource groups
plus events; and bounded, target-specific open-loop/resume reads. It also
supplies the protected-path Upgrade Overview and makes the Repair Batch 8/9
evidence boundary executable through control-document tests.

Repair Batch 9 builder gates were green: 3,301 Python units, the coverage floors,
455 role-separated PostgreSQL integrations, 127 model-free LongMemEval tests
plus evidence replay, the full web matrix, release-static, reproducible fresh
packages, and isolated installed-artifact smokes all passed. Focused seam,
migration, control-truth, and protected-path checks passed as well. Its final
fingerprints were reproduced twice, but independent review later returned
changes required on five bounded findings. Repair Batch 8's complete gates and
twice-reproduced fingerprints are also historical because its review returned
changes required.

Repair Batch 10 made dangling supersession
pointers fail before explanation expansion; nested canonical resource scope is
authoritative across Python, SQLite, and PostgreSQL; resume status, project,
time, and query predicates run before limits; recent memory/open-loop events
are joined to admitted targets before event limits; and context-tree/freeze
documentation is truthful. Its 3,325-unit/457-PostgreSQL full gate, 1,171-test
integrated seam, release-static, 127-test LongMemEval/evidence run, unchanged
202-input web carrier, reproducible package pair, and installed-artifact smokes
are green. Final tracked-patch and bundle fingerprints were reproduced twice,
but independent review then returned changes required on two bounded findings.
That evidence is historical and does not approve the current tree.

Repair Batch 11 corrected persisted-source PostgreSQL predicates and migration
`0090` to select nested canonical scope by key presence,
matching Python and SQLite even when the present value is blank, null,
malformed, or fractional. Resume query predicates now cover open-loop rows and
event payload/text joins before limits for scoped and unscoped calls. Its
3,327-unit/460-PostgreSQL full gate, 595-test owned/shared seam,
release-static, 127-test LongMemEval/evidence run, unchanged 202-input web
carrier, reproducible package pair, archive parity, and installed-artifact
smokes are green. Final tracked-patch and bundle fingerprints were reproduced
twice. Independent review approved that persisted-source closure and every
other bounded area, but returned changes required on one P2 because serialized
event JSON could match key names.

Repair Batch 12 corrected resume event payload
queries now recurse over string leaf values only in SQLite and PostgreSQL;
keys, non-string values, and serialization structure cannot match. Nested and
array strings, scoped/unscoped behavior, row-field matching, pre-limit scope/
status/time predicates, and event ordering are preserved. Its 442-unit owned
seam and complete 9-case role-separated PostgreSQL file are green. Its final
3,327-unit/460-PostgreSQL gate, release-static, 127-test LongMemEval/evidence
run, unchanged 202-input web carrier, reproducible package pair, archive
parity, and installed-artifact smokes passed. Final fingerprints reproduced
twice. Independent review approved production closure and every other bounded
area, but returned changes required on one P2 in the MCP unit fake.

Repair Batch 13 was an unfrozen test-only candidate. The fake stopped
concatenating recursive string leaves; focused fake/real-SQLite parity, all
256 MCP units, and the full 3,328-unit coverage gate passed. Exact production
hashes allowed the R12 460-case PostgreSQL result to carry without a rerun.
Before final documentation, packages, or fingerprints were bound, independent
review found non-ASCII query-folding differences across SQLite, PostgreSQL,
and Python. Batch 13 was never frozen and does not approve the current tree.

Repair Batch 14 was a frozen bounded correction. Open-loop row fields and
event string leaves now share ASCII case-insensitive literal substring
semantics across SQLite, PostgreSQL, and the MCP fake. Non-ASCII code points
are exact and are not normalized; `%`, `_`, and `\\` are literal characters,
not SQL wildcards. Blank-query, per-leaf, scoped/unscoped, pre-limit, and event
ordering behavior remains intact. Its 3,329-unit/461-PostgreSQL full gate,
release-static, 127-test LongMemEval/evidence run, exact unchanged 202-input
web carrier, reproducible package pair, archive parity, and installed-artifact
smokes passed. The tracked-patch and fixed 12-file bundle fingerprints
reproduced twice and are recorded in the self-excluded builder report;
independent review then returned changes required on three bounded P2s: SQL/
fake non-string `next_action` row parity, overbroad MCP documentation, and the
fake's missing `created_at` ordering tie-breaker. Batch 14 evidence is
historical and does not approve the current tree.

Repair Batch 15 was a bounded correction. Root and nested open-loop
`next_action` metadata participates in row query matching only when its JSON
value is a string; recursive loop-event string-leaf behavior is unchanged.
The deterministic ASCII/literal contract is explicitly limited to open-loop
row fields and loop-event leaves, and the fake now uses the production
`opened_at DESC, created_at DESC, id DESC` order before limits. Its final-tree
3,331-unit/461-PostgreSQL gate, release-static, 127-test LongMemEval/evidence
run, exact unchanged 202-input web carrier, reproducible package pair, archive
parity, and installed-artifact smokes passed. The final tracked-patch and fixed
12-file remediation-bundle fingerprints were reproduced twice and are recorded
in the self-excluded builder report. Independent review approved that exact
carrier, but a later engineering-team readback found a locale-dependent POSIX
whitespace mirror in the embedding CAS. Batch 15 approval is historical and
does not approve the current tree.

Repair Batch 16 is the current bounded correction. The PostgreSQL embedding
CAS now uses migration `0090`'s explicit CPython 3.12 29-codepoint `chr()`
table for title/canonical/summary trimming instead of `[[:space:]]`, while
preserving blank omission, first-occurrence deduplication, LF joining, and
SHA-256. Unit SQL-shape proof binds all three consumers—signed vector
freshness, update CAS, and missing-embedding selection—and live role-separated
PostgreSQL covers NBSP, U+001C, mixed blanks, no re-embed loop, and vector
participation. The full gate passed 3,332 units with coverage floors, 463
role-separated PostgreSQL integrations, release-static/control, 127
LongMemEval tests plus evidence replay, unchanged-web readback, and two
byte-identical package builds with Twine, release-check, archive parity, and
isolated smokes. Final carrier fingerprints reproduced twice and are recorded
in the self-excluded builder report. Batch 16 review approved the production
CAS semantics and returned changes required on one documentation-truth P3.
Refreeze 17 changes only that stale Batch 15/current-review wording and its
fail-on-old control guard; independent review of the Refreeze 17 carrier
remains required.

The next release gate must prove one exact clean SHA through role-separated
Postgres/pgvector integration, all model-free LongMemEval tests and checked-in
dataset-manifest consistency, production-compatible semantic-vector evidence,
Python 3.12–3.14 functional coverage, web units/types/coverage/browser checks,
reproducible installed artifacts, and independent review. PyPI must receive the
verified bytes before the stable immutable GitHub Release is created.

## Next

After the remediation release is independently approved:

1. **Multi-session synthesis** — still the weakest historical LongMemEval
   category. Measure and improve aggregation-aware retrieval without tuning
   repeatedly on one development slice.
2. **Dogfood daily** — use real agent workflows with an embedding endpoint;
   measure correction quality, review burden, project-scope usability, and
   end-to-end latency.
3. **Reference integrations** — deepen examples for popular agent frameworks
   on the eleven-tool core surface.
4. **SQLite vector search at scale** — improve the documented 20–30k embedding
   comfort zone and publish recall deltas alongside latency improvements.
5. **Hosted offering exploration** — only after the local authorization, RLS,
   backup, and operations model has stronger production evidence.

## Explicit Non-Goals For Now

- Hosted-service or SLA commitments.
- Managed OAuth consent/account-linking and automatic connector polling.
- A consumer knowledge-management product.
- OCR or transcription execution beyond ingesting text extracted elsewhere.
