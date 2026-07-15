# Alice v0.11.0 Phase 1 Build Report

## Verdict

Builder verification is green on the repaired, frozen, uncommitted Phase 1
tree. The first independent review returned twelve bounded Phase 1 findings;
all twelve are repaired below. Re-review of that repair receipt found one
canonical reference-fixture contract blocker, which is also closed below.
Phase 1 sign-off then ratified D1, accepted D2 with its flag-off smoke deferred
to Phase 2, and required the bounded D3 dead-S3 correction recorded here. This
report records implementation evidence only. Fresh independent review of the
final superseding receipt is pending; no release approval, commit, tag, push,
semantic attestation, or publication is claimed.

Base and branch:

```text
base:      8520f29d3812aa95a75d192fdaf897e5d099a29a
base tree: 7ef7984e7d396b740ecb719a411e6bd44ffe7289
branch: codex/v011-phase1-periphery-cut
target: alice-memory 0.11.0 / web 0.11.0
```

The committed `HEAD` remains the base because delivery is intentionally
uncommitted. The frozen receipt below binds the complete working-tree carrier,
not only the committed tree.

## Scope readback

- Base-relative tracked patch: 276 files, 4,183 insertions, 61,558 deletions.
- Complete receipt carrier: 312 paths after exact exclusions; 184 present and
  128 deleted.
- `main.py`: 17,082 lines at base to 12,802 lines in the candidate, a reduction
  of 4,280 lines.
- Web deletion carrier: 51 tracked files and 14,018 lines removed.
- Immutable migrations and v0.10.x release/handoff records: no changed paths.
- User-owned `coverage.json` and `uv.lock`: present, preserved, and excluded
  from evidence.

## Phase 1 sign-off closure

- **D1 ratified:** the default-on Telegram surface remains the bounded,
  allowlisted, caller-supplied raw-update ingestion endpoint already verified
  by the Phase 1 matrices. No implementation changed.
- **D2 accepted:** the complete v0.11.0 integration posture remains flag-on.
  The required flag-off default-surface integration smoke job is explicitly a
  Phase 2 CI deliverable and no workflow or Phase 2 code was added here.
- **D3 closed:** `Settings.from_env()` and `scripts/validate_env.sh` no longer
  reject core-only production configuration when S3 credentials are absent or
  at their dormant defaults. Authentication, overridden application/admin
  database URLs, and CORS deployment gates remain intact. The health payload
  retains `object_storage.status` but no longer echoes `s3_endpoint_url`.
- **Riders closed:** the five confirmed-empty removed route directories under
  `apps/web/app` are absent. Public upgrade docs state that the exact legacy
  flag is import/start-time and requires process restart, and that providers
  tied to hosted-era workspace identities must be re-registered under the
  deterministic local workspace.

The D3/rider code-and-test delta is limited to `config.py`, `main.py`,
`validate_env.sh`, two unit configuration/validator files, the unit and
integration health files, the two public upgrade documents, and this handoff
package. There is no database/store/migration or web-content delta. Removing
empty directories changes no Git carrier bytes.

## Exact surface inventories

### HTTP and OpenAPI

The isolated-process surface gate passed all default false-like/non-exact
values plus exact flag-on:

| Posture | Mounted/OpenAPI operations | Legacy operations | Permanently removed mounted |
|---|---:|---:|---:|
| default and every non-exact value | 182 | 0 | 0 |
| `ALICE_LEGACY_SURFACES=1` | 231 | 49 | 0 |

The permanent-removal inventory contains 63 operations. Physical OpenAPI
cleanup removed 137 dead contract entries. Registry closure, concrete success
schemas, runtime payload validation, and phantom-key rejection passed.
Same-process environment mutation cannot expand an already-mounted app. A
clean default process also leaves `alicebot_api.proxy_execution` unloaded;
flag-on mounts approval execution while preserving lazy loading until handler
invocation.

### MCP

The focused exact-inventory tests passed seven parametrized cases:

| Posture | Listed tools |
|---|---:|
| default | 11 |
| MCP legacy only | 73 |
| HTTP legacy only | 11 |
| both flags | 76 |
| agent-key-bound, regardless of flags | 11 |

## First-review repair closure

The superseded receipt was not reused. The builder reopened only the twelve
review findings, then froze these closures:

1. Web Telegram configuration is on-demand allowlist-only; secret-ref,
   polling, interval, and empty-update sync controls are absent.
2. Ubuntu packaging no longer advertises a bot token, Telegram secret, or
   webhook-secret header.
3. All fourteen deleted Python modules have parameterized import-spec and
   package-file absence proof; model-pack public-name/prefix guards and a
   same-process non-expansion proof were added.
4. The reference handoff fixture uses neutral `briefing_strategy` vocabulary
   and exact model-pack-free annotations; Python/TypeScript demo outputs match.
5. Dead response/entrypoint rate-limiter classes, globals, settings, env,
   scripts, fixture, and tests are removed; `_request_client_identifier`
   remains.
6. Twelve unused channel/Telegram store row TypedDicts are removed with an AST
   absence guard; migrations are untouched.
7. Rendered web copy states caller/operator-supplied data and externally
   extracted text; live-poll, webhook, Alice-OCR/transcription, and retry-
   execution claims fail tests.
8. Recursive web inventory pins exactly seven core plus four gated pages and
   four middleware matchers; a synthetic extra page fails closed.
9. The active sprint packet is governed at 120 lines / 8,192 bytes with
   mutation guards against stale repair-ledger, Phase-2-active, and extraction-
   execution claims.
10. `proxy_execution` is imported only when the gated execute handler runs;
    default and flag-on-before-invocation processes keep it unloaded.
11. Positive generic request fixtures now use mounted retained routes;
    retired-route literals remain only in negative inventories.
12. Operational-looking Phase 2/3 closeout runbooks are retired and replaced
    by one explicitly non-operational archive history with path/reference
    guards.

## Final re-review blocker closure

Receipt `2ba2492c37d8eddc8765cecbe78995e5bc346f34cac95e780861a0fdf989a3dc`
is superseded and must not be approved. Re-review showed that the canonical
reference fixture still exposed an incomplete `next_suggested_action`, an
incomplete `trust_posture`, and optional scope keys populated with invalid
`null` values.

The bounded correction:

- makes `next_suggested_action` exactly match all six required
  `ContinuityBriefSuggestedActionRecord` fields and removes `rationale`;
- makes `trust_posture` exactly match all ten required
  `ContinuityBriefTrustPostureRecord` fields;
- omits absent `NotRequired[str]` scope keys instead of serializing them as
  `null`; and
- replaces selected-key fixture checks with generic recursive validation of
  the entire current `ContinuityBriefResponse` TypedDict graph, including
  required/optional keys, extra keys, lists, dictionaries, unions, literals,
  and value types. Systematic mutations prove every required key and every
  extra key fail in every populated nested record.

Affected verification is green:

```text
reference unit/integration tests: 8 passed in 0.81s
Python/TypeScript reference outputs: identical, status pass
Ruff: pass
Mypy (recursive contract test): pass
control-document truth: pass
git diff --check: pass
```

No production, PostgreSQL, web, migration, or release-control implementation
changed, so the already-green full PostgreSQL and web matrices were not rerun.

## Phase 1 sign-off correction verification

Focused config, environment-validator, unit health, and complete integration
health verification passed **32 tests in 1.25 seconds**. The fail-on-old
production proofs cover both absent S3 keys and explicitly supplied dormant
defaults in `Settings` and a production `.env`. A separate isolated
`get_settings()` production boot smoke also passed with only local identity,
role-separated database URLs, and a concrete CORS origin configured. `bash -n
scripts/validate_env.sh` passed.

The health tests keep a non-default S3 endpoint in their `Settings` fixture and
explicitly assert that `endpoint_url` is absent in both healthy and degraded
responses. Archive readback later repeated the same absence proof against the
wheel and sdist.

## Python verification

### Final unit and coverage gate

```text
3365 passed in 93.22s
overall coverage: 78.94478269261137%
required overall floor: 50%
main.py line coverage: 62.41610738255034% (3305 / 5099 statements)
required main.py floor: 45%
```

Commands:

```bash
./.venv/bin/python -m pytest tests/unit -q \
  --cov=alicebot_api --cov-report=term \
  --cov-report=json:/tmp/alicebot-phase1-python-coverage.json \
  --cov-fail-under=50
./.venv/bin/python scripts/check_python_coverage.py \
  --coverage-json /tmp/alicebot-phase1-python-coverage.json \
  --path apps/api/src/alicebot_api/main.py --min-percent 45
```

Both coverage floors passed without threshold changes.

### Final frozen-tree PostgreSQL integration gate

```text
381 passed in 411.39s (0:06:51)
```

The post-review receipt run started only after every delegated repair lane
reported frozen. It used `ALICE_LEGACY_SURFACES=1`, PostgreSQL 16, pgvector at
least 0.8, and separate `alicebot_admin`/`alicebot_app` roles. Integration
fixtures created isolated databases and migrated from the immutable chain to
head `20260714_0090`.

A prior moving-tree preflight also passed 381 tests but is deliberately not
used as final evidence.

Focused live results included:

- local bootstrap plus PostgreSQL Telegram raw-source parity: 3 passed;
- retained `/v1` local-identity reconciliation: 10 passed;
- provider/runtime plus OpenClaw MCP carrier: 23 passed; and
- full frozen integration: 381 passed.

The D3 reseal did not touch database, store, migration, connector, provider, or
other PostgreSQL behavior, so the full role-separated database matrix was not
repeated. The complete current `tests/integration/test_healthcheck.py` file was
rerun as part of the 30-test focused gate, including the live API-script smoke.

### Static and release checks

`make release-static` passed on the repaired tree:

```text
Control-doc truth check: PASS (17 governed documents)
Release check: PASS (alice-memory 0.11.0)
Ruff: All checks passed
Mypy: no issues in 135 source files
```

`git diff --check` passed on the complete tree. Deleted-module import sweeps
and removed public-contract sweeps were empty outside explicit fail-on-old and
historical/migration records.

### LongMemEval evidence carrier

```text
127 passed in 4.04s
evidence replay: PASS
arms: 7
baseline: per-question-results-2026-07-07.jsonl
```

This verifies the checked-in evidence and deterministic test carrier. It does
not claim a new provider-backed benchmark run or semantic release attestation.

## Web verification

The delegated web repair builder froze the final web content carrier before
the receipt was reconstructed; no later edit changed a web file. The sign-off
rider only removed five empty directories left behind by the already-recorded
page deletions.

- unit tests: 217 passed;
- core coverage: 202 passed, 89.55% statements / 75.43% branches;
- vNext coverage: 15 passed, 80.62% statements / 67.21% branches;
- typecheck, zero-warning lint, production build, and bundle budgets: passed;
- Playwright: 17 retained default cases, one exact-legacy case, one outage
  case, and one partial-outage case passed.

The neutral validation-matrix web subset independently passed 12 files / 100
tests.

## Reproducible package verification

Two isolated builds used `SOURCE_DATE_EPOCH=1784115100`. The first sandboxed
attempt could not resolve PyPI; the authorized network retry installed the
pinned `setuptools==80.9.0` and `wheel==0.45.1` build backends and completed.
After deterministic sdist normalization, both build directories were
byte-identical.

```text
wheel  alice_memory-0.11.0-py3-none-any.whl
bytes  1116689
sha256 bd4e3cee376ece9458ec9b13f1467fa66be2820fdd8be13580e157324ce38be0

sdist  alice_memory-0.11.0.tar.gz
bytes  971675
sha256 fe742710277f9867e58a40a0324c6052029c90ccfd6d00c6222446ed094f2eb5
```

Twine passed both artifacts. `release_check.py --dist-dir` passed for
`alice-memory 0.11.0`. Isolated installed-artifact smokes passed for the wheel
and sdist. Archive readback confirmed the three new production modules
(`connector_payloads.py`, `local_workspace.py`, and `surface_flags.py`) are
present and deleted modules are absent; historical model-pack migration files
remain intentionally packaged as immutable schema history.

The D3 correction changes packaged `config.py` and `main.py`, so the previous
artifact hashes are superseded. Fresh archive readback proved both artifacts
omit the dead production S3 override errors and the health endpoint echo while
retaining the expected production modules and immutable migration history.

## Frozen carrier receipt

The canonical receipt format is
`alice-v0.11.0-phase1-carrier-v1`. Two independent reconstructions produced
the same result:

```text
base:           8520f29d3812aa95a75d192fdaf897e5d099a29a
paths:          312
present:        184
deleted:        128
manifest bytes: 37044
sha256:         3a9b9775c7001fd029251c634ea9a9a3dade83aa2e1ede9622c25778d891e958
```

Selection is the raw-path union of:

```text
git diff --name-only -z <base> --
git ls-files --others --exclude-standard -z --
```

Paths are deduplicated and sorted by filesystem bytes. The manifest is entirely
NUL-delimited. Its header fields, in order, are `format`, `base`, and `branch`.
Each sorted path then records:

- present file: `path`, `state=present`, four-digit octal `mode`, `kind`
  (`file` or `symlink`), and SHA-256 of raw content (or the raw symlink target);
- deletion: `path`, `state=deleted`, and the six-digit base mode read from
  `git ls-tree -z <base> -- <path>`.

Every label and value is a separate NUL-terminated field. The SHA-256 above is
over those exact manifest bytes.

Exactly four paths are excluded:

```text
coverage.json
uv.lock
docs/handoff/2026-07-15-v0.11.0-phase1-periphery-cut/BUILD_REPORT.md
docs/handoff/2026-07-15-v0.11.0-phase1-periphery-cut/REVIEW_REPORT.md
```

The two user-owned files are not candidate evidence. `BUILD_REPORT.md` is
self-referential, and `REVIEW_REPORT.md` is future reviewer output. No other
path or filename class is excluded.

Any change outside these four paths invalidates this receipt and all review
claims tied to it.

## Remaining external gates

- Independent review of the exact receipt above and reviewer-authored
  `REVIEW_REPORT.md`.
- Release-engineer commit/merge through the protected flow.
- Full CI and semantic retrieval attestation on the resulting final SHA with a
  real configured embedding provider.
- Reproducible release artifacts, final checksums, tag verification, GitHub
  Release, and PyPI publication on that same approved SHA.

Phase 2 remains explicitly stopped.
