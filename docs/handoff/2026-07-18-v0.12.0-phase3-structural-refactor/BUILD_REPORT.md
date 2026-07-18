# Alice v0.12.0 Phase 3 Build Report

**Structure only. Zero behavior change.**

## Verdict

Builder implementation and the production-byte matrix are green on the final
uncommitted Phase 3 code carrier. Included documentation/control bytes are
frozen, and the twice-reproduced carrier receipt plus final evaluation lane are
recorded below. The final frozen-byte Python, PostgreSQL, web, evaluation, and
two-root package readbacks are all green.

Independent increment reviewers returned GO with no remaining P0-P3 finding.
The final reviewer-owned verdict belongs in `REVIEW_REPORT.md`; this builder
report is evidence, not release approval.

No stage, commit, push, tag, publication, repository-setting mutation, or
cybersecurity audit was performed.

```text
base:            f342d45dabe127acca6231f29830ff11d98a340e
base tree:       1d84e26597aecfcd9ad894c6d0b86fbe9a66dfd6
branch:          codex/v0120-phase3-structural-refactor
target release:  v0.12.0
source versions: 0.11.1 (intentional release-engineer hold)
published:       v0.11.1
```

## Final documentation/control lane

The final included tree collects exactly 3,804 unit tests. The definitive
frozen-byte Python and static lane reported:

```text
unit tests:         3,804 passed, 0 skipped
duration:           152.62s
covered lines:      39,037 / 46,840
covered branches:   8,791 / 12,664
package coverage:   80.37778972842162%
required floor:     50%
router aggregate:   3,604 / 5,373 = 67.07612134747814%
router floor:       45%
release-static:     PASS
control truth:      PASS
release_check:      PASS at governed version 0.11.1
Ruff:               PASS
mypy:               PASS across 224 source files
compileall:          PASS
tracked whitespace: PASS
untracked paths:    122 checked, 0 whitespace diagnostics
```

After the final included-byte freeze, the focused documentation/control/
protected-path suite passed 100 tests. Control-document truth, the exact
CURRENT_STATE mirror, tracked and untracked whitespace checks, and protected
hash readback passed. The whitespace normalization's complete split/parity
selection passed 89 tests and exact-file Ruff.

## Production-byte matrix

The final frozen carrier passed:

- 3,804 unit tests with 80.3777897% package coverage, and router aggregate
  3,604/5,373 = 67.0761% above the 45% floor;
- 763 focused store, SQL-shape, and parity guards in 13.37s;
- 399 role-separated PostgreSQL integration tests with one expected skip in
  447.79s, plus one executed flag-off smoke in 3.99s with
  `--require-executed-tests`;
- 127 LongMemEval tests, seven checked evidence-replay arms, and two focused
  vector/retrieval tests;
- 217 web unit tests, 202 core cases at 89.55%, 15 vNext cases at 80.62%,
  typecheck, lint, build, bundle budgets, and browser 17+1+1+1;
- release-static, exact OpenAPI/response/contract/MCP/CLI/store manifests, and
  independent review per increment;
- reproducible two-root package builds and exact installed-artifact smokes.

The explicit flag-off PostgreSQL smoke ran with `ALICE_LEGACY_SURFACES`,
`ALICE_MCP_LEGACY_TOOLS`, and `ALICE_AGENT_API_KEY` all absent. Protected hashes
and tracked carrier digests remained unchanged across the lane; only this
receipt-excluded builder report changed concurrently.

The final frozen-byte web rerun is also green:

```text
unit tests:            217 passed (202 core + 15 vNext)
core coverage:         89.55% statements, 75.43% branches,
                       89.34% functions, 89.55% lines
vNext coverage:        80.62% statements, 67.21% branches,
                       54.74% functions, 80.62% lines
typecheck/lint/build:  PASS
bundle budgets:        106,168 / 120,000 bytes
                       113,461 / 130,000 bytes
                       137,018 / 155,000 bytes
browser matrix:        17 + 1 + 1 + 1 passed
```

The first concurrently loaded vNext coverage attempt had one environmental
timeout and is superseded by the exact clean vNext rerun. Separately, the
browser matrix passed after the required local port-bind escalation.

## Superseded CLI-code-freeze package evidence

At the earlier CLI code freeze, two clean package builds were byte-identical and passed `twine`,
`release_check.py`, checksum generation, exact wheel and sdist install smokes,
four entrypoints, CLI carrier checks, MCP 11/65/76 checks, and SQLite smoke:

```text
wheel: alice_memory-0.11.1-py3-none-any.whl
bytes: 1,239,873
sha256: 6245bd2e6e098c5afdda340aabf4655f19a9be335c8b705f3ad943c7cb728527

sdist: alice_memory-0.11.1.tar.gz
bytes: 1,045,569
sha256: af7c2d5d34660357e9be5d03ec5ab9480cbc95de399fad170b1d0942aedad442

SHA256SUMS sha256:
10a1126e517d95d549d1b261daf4a0b1d153474131e5683b64002388bc879f83
```

These hashes are superseded because final documentation changes a source-
distribution input. They are not reproducible from the final carrier and are
retained only as CLI-code-freeze evidence. They are not v0.12.0 release
artifacts and must not be published. Authoritative final-carrier package
evidence is recorded separately below.

## Final-carrier package verification

Two independent clean roots reproduced the final frozen carrier with
`SOURCE_DATE_EPOCH=1784214379` and produced byte-identical artifacts:

```text
wheel: alice_memory-0.11.1-py3-none-any.whl
bytes: 1,239,866
sha256: f610189c3f53e39750f932774aef98d668e525d2d29844f748f38d96aaa7421d

sdist: alice_memory-0.11.1.tar.gz
bytes: 1,045,629
sha256: a7197baec83af440bbbf8e07b9109a504b8c270002e591fb38f32e3b49c42188

SHA256SUMS bytes: 196
SHA256SUMS sha256:
42cb09d40a1f5d86b9da3621ff9b3afbfd2ab2db474c23125c9a22fdfbd7a2ba
```

Cross-root artifact comparison, `twine`, and `release_check.py` passed in both
roots. Exact wheel and sdist install smokes passed, including four entrypoint
help checks, three version checks, API/CLI/parser/runner/MCP provenance,
migrations and fixture inclusion, MCP 11-tool posture, SQLite commit-plus-
recall, and explicit CLI no-op behavior (`0/0/0`). Archive inventories contain
18 CLI and 19 MCP package files. Initial sandboxed dependency-fetch attempts
were superseded by the authoritative escalated runs.

## Final evaluation lane

The frozen carrier passed:

```text
LongMemEval:              127 passed in 4.78s
checked evidence replay: PASS, 7 arms
focused vector/quality:  2 passed in 0.16s
SQLite offline battery:  6 suites / 78 cases, aggregate pass
retrieval posture:       fts_only
paraphrase target:       measured, not enforced without a provider
```

The provider-free SQLite battery reported 65 passed and 13 failed cases,
pass-rate 0.8333333333333334. All six suites passed because the 13 failures are
the expected FTS-only paraphrase misses and the semantic target is deliberately
not enforced without a configured embedding provider. This is plumbing and
negative-control evidence, not semantic release attestation.

```text
report: /private/tmp/alice-p3-final-sqlite-eval.json
report digest: sha256:9cd9b1f0521c53009328d08b88b644ec87db91cab2875935a01a5e6b82bdd612
file sha256: 4df30bc9f110a305520de727aae2162d50ee3c7e3cbcb8bf0314f23c54fa8835
```

## Protected artifacts

```text
uv.lock sha256:
65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52

coverage.json sha256:
57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711

apps/web/pnpm-lock.yaml sha256:
c4cd48f582508459ca4927539bd5ae7c6976aa99a12201f588bf6a81669d86a3
```

All final Python commands use direct `./.venv/bin/python` and
`./.venv/bin/pytest`; `uv` is not invoked.

## Frozen carrier receipt

The canonical format is `alice-v0.12.0-phase3-structural-carrier-v1`.
Selection is the byte-sorted, de-duplicated raw-path union of the tracked diff
from base and untracked paths. The NUL-delimited manifest records format, base,
and branch, then each present path's four-digit mode, kind, and raw-content or
link-target SHA-256. A deletion records the six-digit base mode.

Configured exclusions are exactly:

```text
coverage.json
uv.lock
docs/handoff/2026-07-18-v0.12.0-phase3-structural-refactor/BUILD_REPORT.md
docs/handoff/2026-07-18-v0.12.0-phase3-structural-refactor/REVIEW_REPORT.md
```

The reviewer-authored `REVIEW_REPORT.md` did not exist at builder receipt
freeze, so three of the four configured exclusions were selected. Independent
Python and Ruby implementations produced byte-identical manifests:

```text
format:                    alice-v0.12.0-phase3-structural-carrier-v1
base:                      f342d45dabe127acca6231f29830ff11d98a340e
base tree:                 1d84e26597aecfcd9ad894c6d0b86fbe9a66dfd6
branch:                    codex/v0120-phase3-structural-refactor
tracked paths:             108
untracked paths:           122
selected paths:            230
selected exclusions:       3
included paths:            227
present paths:             226
deleted paths:             1
content bytes:             5,887,819
manifest bytes:            35,464
sha256:                    fbee28353b24bc62f49bef52323af7c16b1366e52d9b4b6cc6786b0321a8ea96
Python reconstruction:     exact match
Ruby reconstruction:       exact match
```

Evidence manifests:

```text
/private/tmp/alice-v0120-phase3-final-receipt-python.bin
/private/tmp/alice-v0120-phase3-final-receipt-ruby.bin
```

`BUILD_REPORT.md` and the reviewer-authored `REVIEW_REPORT.md` are exact
receipt exclusions, so finalizing either report does not change the carrier
manifest. Any edit outside the four configured exclusions invalidates this
receipt and requires a complete new bind plus fresh review.

## Deferred and external work

- The independent final verdict is owned only by `REVIEW_REPORT.md`.
- The pre-existing MCP alias wording in `docs/alpha/mcp-tools.md`, filed for a
  later documentation-behavior correction.
- Commit/merge and full exact-SHA required checks, real-provider semantic
  attestation, and CodeQL readback.
- Release-engineer version cut to 0.12.0, fresh package reproduction,
  checksums, tag, GitHub Release, PyPI publication, and external readback.
- Phase 4 and security review.
