# Alice v0.11.1 Phase 2 Build Report

## Verdict

Builder verification is green on the final uncommitted Phase 2 carrier. The
hard-freeze evidence covers the complete Python/static and coverage lanes,
LongMemEval and the provider-free negative control, complete legacy-on and
explicit flag-off role-separated PostgreSQL, SQLite, web/browser, dependency
advisory validation, reproducible packages, and an isolated code-health scan.

The independent reviewer marked the carrier **PRE-PACKAGE SAFE** before the r5
package/receipt run. Final reviewer approval and the reviewer-authored
`REVIEW_REPORT.md` were still pending when this builder report was finalized.
This report is therefore build evidence, not release approval. Exact-SHA CI,
real-provider semantic attestation, release identity, tag, GitHub Release, and
PyPI publication remain external release-engineer gates.

No stage, commit, push, tag, release-setting mutation, or publication was
performed. No cybersecurity audit was performed.

```text
base:      5f0a92d77d02b0699af3054fced7427929808aa8
base tree: 560bade5b9ad20c659f03f19693288558c706945
branch:    codex/v0111-phase2-debt-sweep
target:    alice-memory 0.11.1 / web 0.11.1
published: v0.11.0
```

The committed `HEAD` remains the base. All final local evidence binds the
complete uncommitted carrier rather than predicting a future release SHA.

## Scope readback

- Items 2.0 through 2.14 are dispositioned in `FIX_MATRIX.md`.
- Migrations `0091` and `0092` are additive forward migrations; migrations
  through `0090` are unchanged.
- Immutable v0.10.x/v0.11.0 release records and prior handoff directories are
  unchanged.
- Phase 3, roadmap features, hosted-offering work, and cybersecurity review
  were not started.
- `response_generation.py` is 610 lines versus 705 at base.
- The final raw selection has 148 tracked and 22 untracked paths, 170 selected
  paths total. Three selected paths are excluded, leaving 167 present carrier
  paths and zero deletions.
- The configured fourth exclusion, `REVIEW_REPORT.md`, was absent at builder
  freeze and therefore was not among the three selected exclusions.

## Response-hygiene measurement

GitHub CodeQL reported **242** open `py/stack-trace-exposure` alerts on current
`main`/the published base when queried on 2026-07-16. The uncommitted candidate
cannot update that server state. Local post-cut measurement identified **288**
surviving direct or delayed public callsites. Integration exposed eight more
dynamic 404 branches; the repaired source pins **296** calls through
`public_exception_response`, and the fail-on-old AST guard reports zero
old-pattern exception-to-`JSONResponse` violations.

Target-zero CodeQL is an external exact-commit CI gate, not a local claim. This
narrow response-hygiene measurement is not a cybersecurity audit.

## Python verification

### Final exact source/test lane

```text
unit tests:        3,547 passed
pytest duration:   106.17s
wall duration:     110.62s
overall coverage:  79.40092486353048% (37,119 / 45,062)
required floor:    50%
main.py coverage:  62.95914864400961% (3,342 / 5,110)
required floor:    45%
```

The complete unit lane includes HTTP/MCP/CLI error contracts, cross-store
search parity, bounded event lookup, reject/pending-candidate guards, Option A
shape/idempotence/anti-fabrication tests, migrations, scheduler/workflow shape,
response-generation trim, and release/control-document truth.

Final static evidence passed control-document truth, `release_check.py` for
0.11.1, Ruff, mypy, `compileall`, and `git diff --check`. After the last
documentation-truth correction, the focused control suite passed **79/79** and
the expanded release/control suite passed **231/231**. The latter includes the
focused control tests; the two counts are not additive to the complete unit
matrix.

### LongMemEval and offline evaluation

```text
LongMemEval tests:             127 passed
checked evidence replay:       PASS, 7 arms
focused vector/retrieval tests: 2 passed
SQLite offline evaluation:     6 suites / 78 cases, aggregate pass
offline retrieval posture:     fts_only
```

The intentionally provider-free release-gate invocation exited **1** with
aggregate `fail`, retrieval `pass_fts_only`, vector participation false, and
**0/48** vector queries participating. This is the expected negative control:
it proves the gate does not mislabel offline FTS evidence as semantic vector
attestation. Only release CI on the final SHA with the configured real
embedding provider can satisfy the vector/semantic gate.

## PostgreSQL, SQLite, and migration verification

Final role-separated PostgreSQL 16.13/pgvector 0.8.2 evidence:

```text
legacy-on complete integration: 399 passed, 1 intentional skip in 453.29s
explicit flag-off smoke:         1 passed in 1.89s
```

The flag-off process explicitly omitted `ALICE_LEGACY_SURFACES`,
`ALICE_MCP_LEGACY_TOOLS`, and `ALICE_AGENT_API_KEY`. The one legacy-on skip is
the default-surface test's intentional flag guard; that exact test passed in
the separate flag-off process.

The complete integration matrix covers `0091`/`0092` upgrade,
downgrade/re-upgrade, role grants, RLS, indexed event linkage, exact redaction
classification and triggers, accepted/edit/rejected coupled graphs,
anti-fabrication controls, terminal replay, provider/runtime behavior, and the
retained legacy-on compatibility surface. SQLite memory/revision/event/
provenance parity is included in the final unit and evaluation lanes; SQLite
truthfully has no generated-artifact or quality-rating repository.

## Web verification

Environment: Node 20.20.0, pnpm 10.23.0, Playwright 1.55.1.

```text
web unit tests:  217/217 passed
core coverage:   202/202; 89.55% statements, 75.43% branches,
                 89.34% functions, 89.55% lines
vNext coverage:  15/15; 80.62% statements, 67.21% branches,
                 54.74% functions, 80.62% lines
typecheck:       PASS
lint:            PASS, zero warnings
build:           PASS
browser tests:   20/20 passed
```

Bundle budgets passed:

```text
/page:      106,168 / 120,000 bytes
continuity: 113,461 / 130,000 bytes
vnext:      137,018 / 155,000 bytes
```

The browser matrix contains 17 default/core cases, one exact-legacy case, one
outage case, and one partial-outage case.

## Dependency-advisory verification

The response validator passed **5/5** focused cases, including fail-closed
malformed-success responses. A fresh isolated frozen pnpm install resolved the
declared direct `semver@7.8.0` audit-tool dependency and passed the validator.
The live bulk-advisory endpoint then passed both scopes:

```text
production: 55 packages, 0 advisories, 0 high-or-higher, exit 0
complete:   525 packages, 0 advisories, 0 high-or-higher, exit 0
endpoint:   healthy
```

The final pnpm lockfile SHA-256 is
`c4cd48f582508459ca4927539bd5ae7c6976aa99a12201f588bf6a81669d86a3`.
This is a dependency-advisory release check, not a cybersecurity audit.

## Reproducible package verification

The authoritative r5 package root is:

```text
/private/tmp/alice-p2-package-final-r5.bOrBkB
```

The r5 root candidate bind was unchanged before, during, and after packaging:

```text
records: 1,122
bytes:   135,541
sha256:  94eb3e397c211020485ca73a97aee6d4a1b265aa789aed23695815bcfb947ec2
```

The fourteen final documentation/control bindings were also byte-identical
before and after packaging. Their binding manifest has 14 records, 1,495
bytes, and SHA-256
`b53a149df968abd4c85f565ae925fc343e6e063ecb8088eaf6d03dc3ea89d5a5`:

```text
.ai/active/SPRINT_PACKET.md
.ai/handoff/CURRENT_STATE.md
CHANGELOG.md
CURRENT_STATE.md
README.md
ROADMAP.md
docs/handoff/2026-07-16-v0.11.1-phase2-debt-sweep/ENGINEER_HANDOFF.md
docs/handoff/2026-07-16-v0.11.1-phase2-debt-sweep/FIX_MATRIX.md
docs/handoff/2026-07-16-v0.11.1-phase2-debt-sweep/README.md
docs/handoff/2026-07-16-v0.11.1-phase2-debt-sweep/SURFACE_INVENTORY.md
docs/integrations/cli.md
docs/memory-operations-protocol.md
docs/release/v0.11.1-release-notes.md
tests/unit/test_control_doc_truth.py
```

The package-input manifest was reproduced independently for both builds:

```text
files:   233
bytes:   30,056
sha256:  1a6b030e68185ab4d05184731dda97087eb8a6c3fe8e19afbc3c9fb15c21597c
```

Two fresh build roots used `SOURCE_DATE_EPOCH=1784149436`. The wheel and
normalized sdist compared byte-identical across `dist-a` and `dist-b`:

```text
wheel:   alice_memory-0.11.1-py3-none-any.whl
bytes:   1,142,257
sha256:  92124d23e95d0c8a56d16946115db6b577db64a026066ff6d08c61b619948a97

sdist:   alice_memory-0.11.1.tar.gz
bytes:   995,229
sha256:  b128660dae91bbf8ac94afc1b99340c19c401bd2d4f1c8c14695219682e9a59c

SHA256SUMS bytes:   196
SHA256SUMS sha256:  6efdeb95cf208cd8abddf563a0348b38e6db5270800d6a66407faaf73a3f1525
```

Twine, `release_check.py --dist-dir`, checksum generation, cross-build
comparison, and isolated wheel/sdist installed-artifact smokes passed. The
isolated resolver selected Redis 8.0.1 and `pip check` passed. Archive readback
confirmed version 0.11.1 and migrations `0091` and `0092` in both artifacts.
No top-level reusable `dist/` or user-owned artifact directory was used.

All r2, r3, and r4 package roots and receipts are superseded and invalid as
final evidence, even where an artifact happened to be byte-equal. Every unit
or package result produced before the definitive r5 source/doc bind is likewise
non-authoritative. Only the values and r5 paths in this report are final.

## Code-health scan

Independent isolated `desloppify 0.9.3` scans of the exact candidate produced
two honest readings because basename-only test-to-source mapping is
nondeterministic. The result is therefore a range, not a favorable point
estimate:

```text
overall:             34.3-34.4
objective/verified:  85.8-85.9
strict:              34.2
code quality:        83.1 (82.9 strict)
file health:         81.1 (80.8 strict)
duplication:         99.6
test health:         73.7-74.6 (73.7 strict)
open findings:       1,308-1,309
```

All 20 subjective dimensions were unassessed and therefore scored as zero,
which dominates the low overall/strict presentation. Bandit was unavailable,
jscpd exited with errors, and the scan was Python-only. No root `.desloppify`
state was created or mutated. This is a bounded code-health measurement, not a
cybersecurity audit or security score.

## Environment incident and protected artifacts

An early builder setup attempt accidentally invoked `uv`, temporarily changing
the local environment carrier. The tracked candidate was restored. All final
Python release evidence used direct `./.venv/bin/python` and
`./.venv/bin/pytest` execution.

Protected user-owned files remain byte-exact and excluded from release
evidence:

```text
uv.lock sha256:
65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52

coverage.json sha256:
57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711
```

## Frozen r5 carrier receipt

The canonical format is `alice-v0.11.1-phase2-carrier-v1`. Selection is the
byte-sorted, de-duplicated raw-path union of:

```text
git diff --name-only -z 5f0a92d77d02b0699af3054fced7427929808aa8 --
git ls-files --others --exclude-standard -z --
```

The NUL-delimited manifest records `format`, `base`, and `branch`, then each
present path's four-digit mode, kind, and raw-content/link-target SHA-256; a
deletion would record the six-digit base mode from `git ls-tree -z`.

Configured exclusions are exactly:

```text
coverage.json
uv.lock
docs/handoff/2026-07-16-v0.11.1-phase2-debt-sweep/BUILD_REPORT.md
docs/handoff/2026-07-16-v0.11.1-phase2-debt-sweep/REVIEW_REPORT.md
```

Because the reviewer-owned report did not yet exist, three configured
exclusions were selected. Independent Python and Ruby reconstructions produced
identical bytes:

```text
format:                    alice-v0.11.1-phase2-carrier-v1
base:                      5f0a92d77d02b0699af3054fced7427929808aa8
branch:                    codex/v0111-phase2-debt-sweep
tracked paths:             148
untracked paths:           22
selected paths:            170
selected exclusions:       3
included/present paths:    167
deleted paths:             0
content bytes:             7,378,573
manifest bytes:            25,366
sha256:                    ed36cd71c8986ecda0b7b7f43bd2e9bdb9e4de35980de327dd7fd576f5a2c296
Python reconstruction:     exact match
Ruby reconstruction:       exact match
```

Evidence manifests:

```text
/private/tmp/alice-v0111-phase2-final-receipt-r5-python.bin
/private/tmp/alice-v0111-phase2-final-receipt-r5-ruby.bin
```

The following earlier receipts are explicitly superseded and invalid:

```text
d97c59955eca404a8fd3a4f094aee3cdf109251df14c8ad4367fbaf44aba7b5f
ea755d8c50e4075f3864dc7c2f82a443a3a3a13fc1d1c2dea2651d6b36cec89f
4150240ea82ae0ab31e11895b61c76373c16e9005e78ad8fbed87eea65422ee9
```

The first predates the bounded report-unignore control, the second predates
later correctness fixes, and the third is the invalidated r4 doc-count freeze.
No r2/r3/r4 receipt or mixed-run result may be used as release evidence.

`BUILD_REPORT.md` and the future reviewer-authored `REVIEW_REPORT.md` are exact
receipt exclusions, so finalizing either report does not change the r5 carrier
manifest. Any later edit outside the four configured exclusions invalidates
this receipt and requires package/receipt reproduction plus fresh review.

## Independent review

**PENDING FINAL APPROVAL:** the independent reviewer had marked the included
carrier PRE-PACKAGE SAFE before r5 packaging. The reviewer must now validate the
r5 bind, package evidence, and receipt, then author `REVIEW_REPORT.md`. The
builder neither creates nor pre-authorizes that file.

## Remaining external gates

- Commit and merge through the protected flow; no release SHA exists yet.
- Run every required check, including the separately named default-surface
  PostgreSQL check, on that exact SHA and verify check-suite provenance.
- Apply and read back the prepared MainProtect required-check update.
- Obtain exact-SHA CodeQL response-hygiene evidence.
- Run semantic retrieval attestation with the configured real embedding
  provider; offline `fts_only` evidence is insufficient.
- Verify version, tag ancestry, release identity, final artifact checksums, and
  release-finalization controls on the committed SHA.
- Create the GitHub Release and publish to PyPI only from the approved SHA, then
  read back both external states.
- Close or supersede stale Dependabot PRs only after merged carrier truth
  exists.
