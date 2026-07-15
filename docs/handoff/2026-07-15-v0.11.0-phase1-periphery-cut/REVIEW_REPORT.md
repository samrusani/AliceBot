# Alice v0.11.0 Phase 1 Independent Review Report

## Verdict

**APPROVED** for Phase 1 handoff to the release engineer.

The exact frozen, uncommitted carrier below closes the required D3 correction
and its three riders without opening Phase 2. No remaining code, test,
documentation, package, or handoff blocker was found. This is approval of the
Phase 1 carrier for release-engineer verification; it is not approval to tag,
publish, begin Phase 2, or claim completion of the external release gates.

No cybersecurity audit was performed, as requested.

## Superseding reviewed carrier

```text
format:         alice-v0.11.0-phase1-carrier-v1
base:           8520f29d3812aa95a75d192fdaf897e5d099a29a
base tree:      7ef7984e7d396b740ecb719a411e6bd44ffe7289
branch:         codex/v011-phase1-periphery-cut
paths:          312
present:        184
deleted:        128
manifest bytes: 37044
sha256:         3a9b9775c7001fd029251c634ea9a9a3dade83aa2e1ede9622c25778d891e958
```

This approval supersedes the prior 311-path receipt
`4b5970460fbb6a1bbe15061827e085554f7a9ff92e488f44e49f84ca504904a8`.
The new manifest was reconstructed independently in Python and Ruby before
review and again immediately before this report. Every reconstruction produced
the exact counts, byte length, and digest above.

The manifest excludes only `coverage.json`, `uv.lock`, `BUILD_REPORT.md`, and
this reviewer-owned report under the documented protocol. Updating this report
therefore does not alter the reviewed carrier receipt.

## Scope reconciliation

An independent record-by-record comparison with the prior approved manifest
found exactly thirteen included-path changes and no others:

- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/main.py`
- `scripts/validate_env.sh`
- `tests/unit/test_config.py`
- `tests/unit/test_main.py`
- `tests/unit/test_vnext_release_polish.py`
- `tests/integration/test_healthcheck.py`
- `docs/release/v0.11.0-release-notes.md`
- `docs/integrations/phase14-provider-configuration.md`
- `README.md`, `FIX_MATRIX.md`, `ENGINEER_HANDOFF.md`, and
  `SURFACE_INVENTORY.md` in this handoff directory.

`BUILD_REPORT.md` changed only under its explicit self-exclusion. This report
is reviewer-owned and excluded. Removing the five already-empty web route
directories changed no Git carrier bytes. No web content, workflow, database,
store, migration, Telegram implementation, or Phase 2 implementation changed
after the prior approved receipt.

## Sign-off disposition

- **D1 ratified:** the default-on, allowlisted, ingest-only Telegram raw-update
  surface is unchanged. The thirteen-path delta contains no Telegram runtime or
  test implementation.
- **D2 accepted:** v0.11.0 retains the flag-on full integration posture. The
  flag-off default-surface integration smoke remains a required Phase 2 CI
  deliverable and is absent from this carrier. The integration workflow still
  invokes the suite only with `ALICE_LEGACY_SURFACES=1`.
- **D3 closed:** production `Settings` and the adjacent environment validator
  no longer require dead S3 credentials. Dormant settings remain accepted;
  local identity, overridden application/admin database URLs, and non-wildcard
  CORS gates remain enforced. Health payloads retain
  `object_storage.status` and do not expose `endpoint_url`.
- **Riders closed:** `apps/web/app/admin`, `chat`, `chief-of-staff`,
  `onboarding`, and `settings` are absent. Upgrade docs state that
  `ALICE_LEGACY_SURFACES` is read at process import/start and requires restart,
  and that hosted-era provider rows are orphaned from the deterministic local
  workspace and require bootstrap plus provider re-registration.

## Independent verification

Fresh reviewer checks on the superseding carrier passed:

- D3 configuration, environment-validator, unit-health, and complete
  integration-health/API-script smoke: **31 passed**, followed by the route
  registration proof: **1 passed**;
- isolated production `get_settings()` boot in separate clean processes with
  S3 variables absent and with both explicit dormant defaults: pass;
- negative production probes for missing identity, default application DB,
  default administrator DB, and wildcard CORS: all rejected with the expected
  errors;
- `bash -n scripts/validate_env.sh`: pass;
- runtime healthy/degraded payloads, the live `/healthz` script smoke, the
  health `TypedDict`, and generated OpenAPI: no `endpoint_url`; status retained;
- `make release-static`: control-document truth, release identity, Ruff, and
  mypy all pass;
- `git diff --check`: pass;
- the five named route directories: absent; no other empty web-app directory
  remained;
- immutable Alembic migrations and v0.10.2/v0.10.3/v0.10.4 release and handoff
  records: no base-relative changes;
- no staged files; committed `HEAD` and branch still match the receipt; and
- preserved user-owned files:
  - `coverage.json` SHA-256
    `57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711`;
  - `uv.lock` SHA-256
    `65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52`.

The builder's current-tree full-unit result (**3,365 passed**, overall coverage
**78.94478269261137%**, `main.py` **62.41610738255034%**) was reviewed together
with the unchanged prior PostgreSQL (**381 passed**), web (**217 unit tests**
plus coverage/static/browser lanes), and LongMemEval (**127 passed**) evidence.
The bounded D3 reseal did not touch their database, web, or retrieval behavior;
the focused current-tree checks above cover every changed production path.

## Package verification

Both isolated package build directories remain byte-identical and bind the
current `config.py` and `main.py` bytes exactly:

```text
wheel bytes:  1116689
wheel sha256: bd4e3cee376ece9458ec9b13f1467fa66be2820fdd8be13580e157324ce38be0
sdist bytes:  971675
sdist sha256: fe742710277f9867e58a40a0324c6052029c90ccfd6d00c6222446ed094f2eb5
```

Fresh reviewer checks confirmed Twine validity, `release_check.py --dist-dir`
with byte-identical comparison, and exact archive readback. Wheel and sdist
omit both dead S3 production errors and the health endpoint echo, contain the
three required new production modules, omit removed modules, and preserve
immutable migration history. Independent installed-artifact smokes passed for
both the wheel and sdist, including entry points, version identity, migrations,
eleven-tool MCP inventory, and a real SQLite commit/recall flow.

## Handoff truth and remaining gates

The pending-review statements in the builder-authored README and build report
record their freeze-time state; this superseding reviewer-owned report closes
that pending gate. The carrier remains intentionally uncommitted and unstaged.

The release engineer must still commit and merge through the protected flow,
run required CI and the real-provider semantic retrieval attestation on the
resulting final SHA, rebuild and verify final artifacts/checksums against that
SHA, and only then tag, create the GitHub Release, and publish to PyPI. Code and
Phase 1 carrier readiness are therefore approved; release and publication
readiness remain external until those exact-SHA gates are green.

Phase 2 remains stopped until v0.11.0 is tagged and published.
