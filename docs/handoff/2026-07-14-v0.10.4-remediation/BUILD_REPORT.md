# Alice v0.10.4 Fifth-Audit Builder Report

## Build identity and constraints

- Base/current HEAD during build:
  `d52e32114eb0b4ef63499e53be14b70dc0864487` on `main`.
- Package version intentionally remains `0.10.3` until release-engineer
  finalization.
- No commit, push, tag, GitHub Release, or PyPI publication was performed.
- `docs/release/v0.10.3-release-notes.md` and
  `docs/release/v0.10.3-checksums.txt` have no diff.
- Pre-existing untracked `coverage.json` and `uv.lock` were preserved.
- `CURRENT_STATE.md` and `.ai/handoff/CURRENT_STATE.md` are byte-identical.
- Post-freeze repair stayed bounded to reviewer-confirmed classes. Batch 2
  covered candidate supersession, cross-backend project identity, and the
  dedicated MCP review schema. Batch 3 covers only future `0083` upgrade
  precedence and asymmetric trace detail/event fallback. Batch 4 covers only
  scheduler-status OpenAPI truth, legacy source-scope repair parity, exact
  `0083` ASCII whitespace, and release-handoff evidence truth. Batch 5 covers
  only terminal project-update consistency, exact Python 3.12 raw-text parity
  in migration `0090`, isolated release artifact directories/cache truth, and
  endpoint-level scheduler OpenAPI evidence. Batch 6 corrects only the
  terminal-replay evidence model: locked terminal artifact plus exactly one
  append-only `project_update_review` revision and one actor-coupled event,
  with exact true-redaction skeleton support and no dependency on mutable
  current memory/project state. Batch 7 changed only handoff-carrier truth.
  Batch 8 closes two later review findings: it counts exactly one total
  artifact/candidate-coupled accepted/rejected event before any outcome,
  actor, action, target, payload, or redaction validation; and it applies the
  complete persisted-source envelope precedence across both stores,
  retrieval admission, shared source consumers, and HTTP artifact-trace
  authorization. Batch 8 was frozen and twice fingerprinted before its
  independent review returned changes required. Batch 9 was also frozen and
  twice fingerprinted before its review returned changes required. Batch 10
  was frozen and twice fingerprinted before its review returned exactly two
  findings. Batch 11 was frozen before review returned one finding. Batch 12
  was frozen and twice fingerprinted before review approved its production
  changes but returned the fake cross-leaf P2. Batch 13 was never frozen; it
  was an unfrozen fake-only candidate whose review returned one
  Unicode/collation P2. Batch 14 was frozen and twice fingerprinted before its
  review returned exactly three bounded P2s. Repair Batch 15 was the then-
  current correction, was independently approved, and was later superseded by
  the engineering-team embedding-CAS finding. Repair Batch 16 is the current
  bounded correction; Refreeze 17 changes only documentation-truth enforcement
  after its reviewer approved the production CAS semantics.

## Historical Refreeze 7 carrier status (superseded)

Refreeze 7 was a carrier-only truth correction in the untracked
handoff README, fix matrix, and engineer handoff. It changes no source, test,
tracked patch, package input, or web byte, so the complete Refreeze 6 matrix
and package evidence remained applicable to that historical tree without
rerunning those gates.
The Refreeze 6 pre-carrier bundle was
`966429239311313957baf616967a933f0e197f7f25f021332caf93c2066b5672`.
The Refreeze 7 carrier fingerprint below reproduced identically in two
independent readbacks at that time. Repair Batch 8 changes source, tests, and
documents; none of these Refreeze 6/7 hashes or gate results approves the
current tree.

## Historical Refreeze 7 carrier fingerprints

Refreeze 7 was based on branch `main` at exact base/current HEAD
`d52e32114eb0b4ef63499e53be14b70dc0864487`.

On the Refreeze 7 tree, the tracked patch was produced by:

```zsh
base='d52e32114eb0b4ef63499e53be14b70dc0864487'
tracked_patch="$(mktemp -t alice-v104-tracked-patch)"
git diff --binary "$base" -- > "$tracked_patch"
shasum -a 256 "$tracked_patch"
```

Its tracked-patch SHA-256 is unchanged from Refreeze 6:

```text
0527362a0876d8807488ba3db4818cac6a3da83b06eb8a544619036ca888d3d4
```

The historical remediation-bundle fingerprint is a content-addressed
manifest: it binds
the base identity, branch, tracked-patch digest, and the path plus SHA-256 of
each intentional untracked remediation file. The allowlist makes selection
deterministic and path-safe; quoted zsh arrays avoid whitespace expansion, and
the recipe uses macOS-provided `mktemp`, `shasum`, and `cut` rather than GNU-only
options.

The exact historical recipe is retained below for provenance. It must not be
run against the current Batch 8 tree with an expectation of the Refreeze 7
output; Batch 8 necessarily changes both the tracked patch and the handoff
carrier.

```zsh
set -euo pipefail

base='d52e32114eb0b4ef63499e53be14b70dc0864487'
branch='main'
tracked_patch="$(mktemp -t alice-v104-tracked-patch)"
manifest="$(mktemp -t alice-v104-bundle-manifest)"
trap 'rm -f "$tracked_patch" "$manifest"' EXIT

git diff --binary "$base" -- > "$tracked_patch"
tracked_sha="$(shasum -a 256 "$tracked_patch" | cut -d ' ' -f 1)"

intentional_untracked=(
  'apps/api/alembic/versions/20260714_0090_project_scope_identity.py'
  'apps/api/src/alicebot_api/vnext_artifact_review.py'
  'apps/api/src/alicebot_api/vnext_project_update_guard.py'
  'docs/handoff/2026-07-14-v0.10.4-remediation/ENGINEER_HANDOFF.md'
  'docs/handoff/2026-07-14-v0.10.4-remediation/FIX_MATRIX.md'
  'docs/handoff/2026-07-14-v0.10.4-remediation/README.md'
  'docs/handoff/2026-07-14-v0.10.4-remediation/SURFACE_INVENTORY.md'
  'docs/pypi-description.md'
  'tests/unit/test_20260714_0090_project_scope_identity.py'
  'tests/unit/test_hosted_channel_workspace_resolution.py'
)

{
  printf 'format\talice-v0.10.4-remediation-bundle-v1\n'
  printf 'base\t%s\n' "$base"
  printf 'branch\t%s\n' "$branch"
  printf 'tracked-patch\t%s\n' "$tracked_sha"
  for file_path in "${intentional_untracked[@]}"; do
    [[ -f "$file_path" ]]
    file_sha="$(shasum -a 256 "$file_path" | cut -d ' ' -f 1)"
    printf 'untracked\t%s\t%s\n' "$file_path" "$file_sha"
  done
} > "$manifest"

printf 'tracked patch: '
shasum -a 256 "$tracked_patch" | cut -d ' ' -f 1
printf 'bundle manifest: '
shasum -a 256 "$manifest" | cut -d ' ' -f 1
printf 'included untracked files: %s\n' "${#intentional_untracked[@]}"
```

Expected output:

```text
tracked patch: 0527362a0876d8807488ba3db4818cac6a3da83b06eb8a544619036ca888d3d4
bundle manifest: 8f98fd61424e08b41b5f429d42beab3b592d2b81e2b47610e68cc7a8b2c5f5ae
included untracked files: 10
```

Both fingerprints reproduced identically in two independent Refreeze 7
post-gate readbacks.

The ten included untracked files are exactly the ten entries in the array.
`coverage.json` and `uv.lock` are excluded because they were pre-existing,
user-owned untracked files. `REVIEW_REPORT.md` is excluded because it is future
reviewer output and was not part of the builder tree. This `BUILD_REPORT.md` is
also excluded because it carries the fingerprint; including it would create a
self-referential hash that changes when the expected hash is written into the
report. These exclusions are explicit through the fixed allowlist rather than
name filtering. The historical Batch 8 manifest and fingerprints are recorded
in its status section below.

## Builder Repair Batch 8 scope and current status

Repair Batch 8 replaces two claims that remained too broad after Refreeze 7:

1. Terminal replay now gathers every accepted/rejected decision event coupled
   through the locked artifact or candidate before it validates the expected
   outcome, actor, action, target, payload, or redaction skeleton. Exactly one
   total coupled decision event is allowed. A valid-looking event cannot hide
   a second rejection, a second acceptance with the wrong action, or a
   contradictory outcome. The fixed conflict/error and zero-mutation contract
   applies through all six generic/dedicated HTTP, MCP, and CLI adapters.
2. Persisted sources now use a source-specific envelope resolver instead of
   treating their outer metadata as a flat memory envelope. Precedence is root
   canonical; embedded `metadata_json` canonical; embedded `scope_json`
   canonical; nested `agentic_memory`/`agent_identity` canonical; root aliases;
   then embedded metadata/scope and nested-agentic aliases. Canonical presence
   is authoritative even for empty, null, or malformed values. The rule is
   shared by SQLite and PostgreSQL `search_sources` and parent-chunk searches,
   retrieval lexical/chunk/provenance/evidence/reference/currency/temporal
   admission, Brain, Projects, Connections, Contradictions, and HTTP
   artifact-trace authorization. Scheduler, HTTP, MCP, and CLI callers inherit
   those shared services.

The two fail-closed historical-envelope controls are:

- E0: stale root alias plus embedded `project_scope: []` is visible nowhere.
- E1: stale root alias plus embedded `project_scope: [real]` is visible only
  to project `real`, never to the stale alias.

Strings, finite mathematically integral numbers, and explicit boolean scalar
values retain identical project-identity behavior in Python, SQLite, and
PostgreSQL. Fractional and non-finite numbers, mappings, and null do not become
project identifiers.

### Historical Repair Batch 8 verification

- Static release gate: `make release-static` PASS before documentation, then
  PASS again on the updated documentation carrier. The post-doc run included
  control-document truth, `Release check: PASS (alice-memory 0.10.3)`, Ruff,
  and mypy across 146 source files.
- Full Python unit gate: 3,230 tests passed in 56.27 seconds; total coverage
  75.58%, `main.py` 52.64%, and the per-file `main.py` floor passed.
- Full role-separated PostgreSQL gate: 450 tests passed in 504.37 seconds.
- Combined independent focused unit readback: 818 tests passed.
- Persisted-source store/retrieval lane: 300 unit tests and 4 focused live
  PostgreSQL tests passed.
- Source-consumer lane: 448 unit tests covering seven regressions passed.
- Terminal-evidence lane: 125 unit tests and 4 focused live PostgreSQL tests
  passed; the complete touched PostgreSQL file passed all 7 tests.
- Combined focused live PostgreSQL readback: 11 tests passed.
- Model-free LongMemEval: 127 tests passed in 3.72 seconds; the complete
  command took 3.92 seconds. The seven-arm evidence checker passed against
  `per-question-results-2026-07-07.jsonl`, with identical repository status
  before and after the command.
- Web fingerprint before/after:
  `df3f667a4e06be6a998478a5a4b4ee0af4a2f27b4cbe7b516b7a80b85aa1e0d4`
  across 22 tracked inputs; lockfile unchanged and no tracked files edited.
- Fresh typecheck passed in 1.13 seconds; ESLint passed in 2.45 seconds with
  zero warnings. The standalone build passed in 9.62 seconds, compiled in
  1,073 milliseconds, and generated 19/19 pages without warnings.
- Full `make test-web` passed in 161.34 seconds: Vitest 71 files / 280 tests;
  core coverage 68 files / 267 tests at 89.56% statements/lines, 74.33%
  branches, and 89.96% functions; vNext coverage 3 files / 13 tests at 80.69%
  statements/lines, 66.84% branches, and 54.74% functions. Its embedded build
  compiled in 1,113 milliseconds and generated 19/19 pages.
- All bundle budgets passed: `/` 106,168/120,000 bytes, `/chat`
  124,526/140,000, `/continuity` 113,758/130,000, and `/vnext`
  137,329/155,000. Playwright passed 10/10 (8 core in 3.1 seconds, outage in
  4.4 seconds, partial outage in 4.3 seconds). The only diagnostic was the
  harmless `NO_COLOR`/`FORCE_COLOR` note.
- Canonical package run root:
  `/tmp/alice-refreeze8-package.dtigdk/{primary,reproducibility}`. Both fresh
  builds used `SOURCE_DATE_EPOCH=1783988183`, Python 3.12.11, `build 1.5.0`,
  isolated pinned `setuptools 80.9.0` and `wheel 0.45.1`; the builds completed
  in 123.36 and 123.30 seconds, and each sdist normalization took 0.39 seconds.
- Wheel and normalized sdist comparisons: byte-for-byte PASS. Wheel
  `alice_memory-0.10.3-py3-none-any.whl` is 1,213,622 bytes with SHA-256
  `72feafee3f423f283a454a0ded6f7ffd49848fef159e344da782076f7113932e`.
  Sdist `alice_memory-0.10.3.tar.gz` is 1,060,235 bytes with SHA-256
  `1b5f8bb48ccd82a1da494403fd813e7c7ad62b7c2b50b57cfd082fc40027d118`.
- Twine 6.2.0 passed in 0.28 seconds. `release_check.py --dist-dir` passed in
  0.18 seconds with exact output
  `Release check: PASS (alice-memory 0.10.3)`; no checksum artifact was written
  and the primary directory remained exactly wheel plus sdist.
- Installed wheel and sdist smokes passed in separate fresh virtualenv 20.39.1
  environments in 207.90 seconds. Both archives contain every Batch 8 critical
  production file and migration `0090`; the sdist contains the evergreen PyPI
  description and no remediation-handoff files.
- Repository `dist/` was untouched and unread. Before/after repository status,
  tracked-diff, and untracked-aggregate snapshots were identical. The package
  run observed 94 modified and 13 untracked paths at exact unchanged HEAD
  `d52e32114eb0b4ef63499e53be14b70dc0864487`.
- Final Repair Batch 8 repository freeze: base
  `d52e32114eb0b4ef63499e53be14b70dc0864487`, branch `main`, tracked-patch
  SHA-256
  `ceb87e4db1af8c104f4bbc290ec25d8f32e97d1fbd9f2c0b4ba364459845890b`,
  and canonical remediation-bundle SHA-256
  `00b4414067260b99fcf56b30ab533b48d1af32d62416bbf7e420544e044b2854`.
  The canonical bundle contains exactly 10 intentional untracked files under
  the fixed allowlist; this `BUILD_REPORT.md` remains self-excluded. Two
  independent fingerprint reconstructions matched exactly.
- Independent review of the exact final Batch 8 carrier subsequently returned
  changes required with eight bounded findings. Its twice-reproduced
  fingerprints and full-gate evidence are historical and do not approve the
  current tree.

## Historical Builder Repair Batch 9 scope and verification (superseded)

Repair Batch 9 closes only the eight findings returned by the independent
Batch 8 review:

1. Source capture validates envelope/classification identity across fast,
   hash, and atomic paths; SQLite/PostgreSQL update stale dedupe keys
   atomically, and collision/HTTP review fails without mutation.
2. Key-bound core MCP explanation authorizes memory chains, provenance,
   entity-backing memories, and continuity objects before expansion and uses a
   generic unavailable response on any mixed or missing evidence.
3. Terminal replay requires candidate-created evidence whose distinct target
   set is exactly the locked artifact, with exact ordinary/redacted forms.
4. Finite mathematically integral JSON numbers share canonical scope identity
   across Python, SQLite, PostgreSQL, and migration `0090`; fractional and
   non-finite numbers reject, while explicit boolean scalar identifiers remain.
5. Legacy MCP context-tree scope applies before limits across five resource
   groups (projects, memories, sources, open loops, and artifacts), uses
   persisted-source scope for sources, and reads a separate target-specific
   event group. The tool remains outside the core MCP surface and disabled on
   key-bound servers.
6. MCP open-loop/resume reads apply scope before bounded limits and fetch only
   admitted-target events.
7. The handoff carries completed protected-path metadata and an executable
   guard regression.
8. Control documents enforce the historical Batch 8 versus current Batch 9
   freeze/review boundary.

### Historical Repair Batch 9 verification

- Combined unit seam sweep: 906 passed.
- Combined role-separated PostgreSQL seam sweep: 18 passed.
- Focused migration `0090` sweep: 3 passed, 15 deselected.
- Ruff correctness lint passed; mypy passed across 137 API source files;
  `git diff --check` passed.
- Lane evidence: capture/store 287 unit plus 13 PostgreSQL; terminal 285 unit
  plus 7 live PostgreSQL; MCP 329 unit; context tree 7 unit.
- Full Python gate: 3,301 units passed in 57.77 seconds at 75.6699% coverage;
  `main.py` reached 52.6343% and its 45% floor passed. All 455 role-separated
  PostgreSQL integrations passed in 553.91 seconds; the full command took
  618.10 seconds.
- LongMemEval: 127 model-free tests passed in 4.11 seconds and the seven-arm
  checked-in evidence replay passed. Release-static passed control-document
  truth, `Release check: PASS (alice-memory 0.10.3)`, Ruff, and mypy across 146
  source files.
- Full web gate passed in about 3 minutes 3 seconds: 71 Vitest files / 280
  tests, core and vNext coverage gates, typecheck, zero-warning lint, 19 static
  page artifacts / 17 routes, all four budgets, and 10/10 Playwright cases.
  Its 202-input fingerprint remained
  `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`.
- Two fresh normalized package builds were byte-identical. Wheel SHA-256 is
  `fbcffb3f8a849e8482ae849baf84623d48f2ccd258838b6574a12109dee8fcd1`
  at 1,221,248 bytes; sdist SHA-256 is
  `42d1cdf111f7da2ca68f7dbc6b52d6cdc73ce595f71d5ac98eef1be4c0e1a34f`
  at 1,067,456 bytes. Twine, release-check without checksum output, byte parity
  for 11 critical files, and both isolated installed-artifact smokes passed.
  Repository `dist/` was not read or modified.
- Focused control/guard proof: 47 tests passed; control-document truth, the
  exact CURRENT_STATE mirror, and the representative `63397ab^...63397ab`
  protected-path event passed with exactly memory schema and continuity APIs.
- Final Repair Batch 9 repository freeze: base/current HEAD
  `d52e32114eb0b4ef63499e53be14b70dc0864487` on `main`; tracked-patch
  SHA-256
  `d43ffe5233fb22f122ff7106fc1770287c1e53a0a6f2c31b9844fe7a0ec010bf`;
  canonical remediation-bundle SHA-256
  `c34f5bd7d402f189edf531c7a00890ea7ae2a004101b0da5d8a909e050c44a08`.
  Two independent reconstructions matched exactly. The fixed bundle manifest
  contains 12 intentional untracked files: migration `0090`, the two shared
  review modules, the four included handoff carriers, the evergreen PyPI
  description, the source-review integration regression, and three unit-test
  files. This report is self-excluded; user-owned `coverage.json` and `uv.lock`
  and future reviewer output are excluded explicitly. Independent review of
  this exact carrier subsequently returned changes required on five bounded
  findings; no earlier result or hash approves the current tree.

## Historical Builder Repair Batch 10 scope and verification (superseded)

The Batch 9 review returned changes required with five bounded findings. Batch
10 closes only those findings:

1. Unresolved non-null supersession pointers in either direction fail before
   audit-envelope reads; key-bound core MCP returns one identifier-free
   unavailable response, while complete authorized chains pass.
2. Nested canonical `project_scope` under `agentic_memory` and
   `agent_identity` is presence-authoritative for generic memory, artifact, and
   open-loop admission, with scalar/array and Python/SQLite/PostgreSQL parity.
3. Resume status, type, canonical project, query, and time predicates execute
   in each store before row limits. Recent memory/open-loop events join to
   admitted targets and order by event time before event limits, so older
   targets with newer events survive foreign-row starvation.
4. Resume no longer relies on the incompatible explicit legacy project matcher
   after the canonical effective scope has been resolved.
5. Context-tree and freeze documentation now state five resource groups plus
   events, no entity group, the legacy/key-bound boundary, and Batch 9's
   historical frozen/fingerprinted then changes-required status.

### Historical Repair Batch 10 verification

- Dangling-chain service/MCP focus: 11 passed.
- Nested canonical scope focus across shared Python resolution, SQLite, and
  PostgreSQL SQL-shape tests: 38 passed.
- Resume fail-on-old SQLite focus: 5 passed, including more-than-limit foreign
  status/window/event starvation, canonical-only decision scope, old memory
  and old loop targets with newer in-window events, and unscoped compatibility.
- Live role-separated PostgreSQL nested-scope/resume parity: 2 passed, 5
  deselected, against fresh migrated databases with 120 newer foreign events.
- Frozen owned lane: 705 units and all 7 focused role-separated PostgreSQL
  cases passed; Ruff lint/format, mypy on the five production files, and
  `git diff --check` were green.
- Combined 17-file owned/adapter/shared-consumer seam: 1,171 passed in 6.35
  seconds; `git diff --check` passed.
- Release-static passed in 2.03 seconds: control-document truth, release-check
  for `alice-memory 0.10.3`, Ruff, and mypy across 146 source files were green.
- LongMemEval passed 127 tests in 4.23 seconds; its complete target finished in
  4.50 seconds and the checked-in seven-arm evidence replay passed.
- The unchanged web carrier is exactly 202 tracked paths under `apps/web`. Its
  reproducible manifest digest command is:

  ```zsh
  git ls-files -z -- apps/web \
    | xargs -0 shasum -a 256 \
    | LC_ALL=C sort \
    | shasum -a 256
  ```

  `git ls-files -z` emits NUL-delimited paths. `shasum` converts each path to
  one newline-terminated `<sha256><two spaces><path>` record; bytewise `C`
  sorting defines the manifest order; the last `shasum` hashes those exact
  records. The command reproduced the R9 digest
  `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`.
  Included `apps/web/pnpm-lock.yaml` remained
  `f684d9f418db5b6b52964cdafdf27ab326aa68b777c5fc1a7b90dc4f7a4206d9`,
  so the complete R9 web matrix carries without a Playwright rerun.
- The first full-unit preflight exposed one obsolete test expectation that
  still treated a blank nested canonical scope as absent. The production
  behavior was correct; the test was replaced with a fail-on-old proof that
  the blank nested scope remains authoritative/unscoped and a stale-alias
  recapture is distinct. Its focused subset passed 17 tests and its complete
  file passed 30 before the clean full rerun.
- Final full Python gate: 3,325 units passed in 59.13 seconds. Exact overall
  coverage was 75.71076442580033% (40,486/51,521); `main.py` was
  52.63426457456308% (3,775/6,899), and its explicit 45% floor passed. All 457
  role-separated PostgreSQL integrations passed in 537.60 seconds with zero
  failures.
- Two fresh current-tree package builds were byte-identical after normalized
  sdist timestamps. Wheel `alice_memory-0.10.3-py3-none-any.whl` is 1,223,739
  bytes with SHA-256
  `a19c049c4610f7c0553df76611f9b572a19937133427f35739358500b3cf6154`;
  normalized sdist `alice_memory-0.10.3.tar.gz` is 1,069,941 bytes with SHA-256
  `d0a17ab83f06c805ff8de6311b0d5e8319524cb3015f29fe14ba0ec056c88f48`.
  Builds took 2.888/4.711 seconds and normalization 0.355/0.295 seconds. Twine
  passed in 0.152 seconds, release-check in 0.058 seconds, and isolated
  wheel/sdist smokes in 27.907 seconds. Six critical R10 production files were
  byte-identical across workspace, wheel, and sdist; the sdist includes the
  evergreen PyPI description and excludes this handoff. Repository `dist/`
  was neither read nor modified.

### Final Repair Batch 10 carrier fingerprints

The final carrier remains based on branch `main` at unchanged HEAD
`d52e32114eb0b4ef63499e53be14b70dc0864487`. The base-relative binary tracked
patch was reconstructed twice with:

```zsh
git diff --binary d52e32114eb0b4ef63499e53be14b70dc0864487 -- \
  | shasum -a 256
```

Both runs produced tracked-patch SHA-256:

```text
e155e9cd9ee024c21ea965946fc3ab0cbeae7c1602849cd6bd9b0254bd5de973
```

The canonical `alice-v0.10.4-remediation-bundle-v1` manifest binds that
tracked digest plus these 12 intentional untracked files in the listed order:

```text
apps/api/alembic/versions/20260714_0090_project_scope_identity.py
apps/api/src/alicebot_api/vnext_artifact_review.py
apps/api/src/alicebot_api/vnext_project_update_guard.py
docs/handoff/2026-07-14-v0.10.4-remediation/ENGINEER_HANDOFF.md
docs/handoff/2026-07-14-v0.10.4-remediation/FIX_MATRIX.md
docs/handoff/2026-07-14-v0.10.4-remediation/README.md
docs/handoff/2026-07-14-v0.10.4-remediation/SURFACE_INVENTORY.md
docs/pypi-description.md
tests/integration/test_source_review_identity_api.py
tests/unit/test_20260714_0090_project_scope_identity.py
tests/unit/test_hosted_channel_workspace_resolution.py
tests/unit/test_vnext_context_tree.py
```

Each manifest record is `untracked<TAB>path<TAB>sha256`, preceded by
`format`, `base`, `branch`, and `tracked-patch` tab-delimited records. Two
independent reconstructions were byte-identical and produced bundle SHA-256:

```text
dff2dd08b0cd00b94dffc4e3f4e9ec0376536f6831c95de8fce1d2f4527fff70
```

This `BUILD_REPORT.md` is self-excluded to avoid a recursive digest. Future
`REVIEW_REPORT.md` output is reviewer-owned and excluded. Pre-existing
user-owned `coverage.json` and `uv.lock` remain explicitly outside the fixed
allowlist. Independent review of the exact Batch 10 carrier subsequently
returned changes required on exactly two bounded findings: persisted-source
PostgreSQL/migration nested-key presence and `alice_resume` open-loop query
semantics. No Batch 10 review, gate, package hash, or fingerprint approves the
current tree.

## Historical Builder Repair Batch 11 scope and verification (superseded)

Batch 11 closes only the two findings returned by independent review of the
twice-fingerprinted Batch 10 carrier:

1. The persisted-source PostgreSQL resolver and migration `0090` now choose
   the nested canonical tier whenever either `agentic_memory` or
   `agent_identity` contains a `project_scope` key. Selection no longer
   depends on finding a nonempty normalized leaf, so present blank, null,
   malformed, or fractional values resolve to an empty identity instead of
   falling through to stale aliases. Valid scalar/array values, both nested
   containers, source/parent-chunk predicates, and migration dedupe identity
   retain Python/SQLite merge and normalization parity.
2. `alice_resume.query` now reaches `list_open_loops` and
   `list_open_loop_events` in both stores before their limits. Loop title,
   description, root/nested next-action metadata, and relevant event payload
   text participate. Scoped and unscoped calls exclude newer mismatching noise
   from `open_loops`, `next_action`, and `recent_changes`; queryless behavior
   remains unchanged.

### Historical Repair Batch 11 verification

- Persisted-source/migration focus: 7 passed. This includes Python/SQLite/SQL
  shape, one live role-separated PostgreSQL source+parent-chunk case, and one
  fresh `0089`→`0090` migration dedupe readback.
- Resume query focus: 3 passed. SQLite end-to-end, PostgreSQL SQL-shape, and
  live role-separated PostgreSQL scoped/unscoped coverage exercised exactly
  60 newer in-scope/time-valid mismatches, an older matching loop, a
  payload-only matching event, all three brief arms, and queryless behavior.
- Owned/shared unit seam: 595 passed.
- Role-separated PostgreSQL scope/source/resume seam: 9 passed.
- Migration `0090` subset: 4 passed.
- Ruff check and format, mypy on `vnext_store.py`, `sqlite_store.py`, and
  `mcp_tools.py`, and `git diff --check` passed.
- Full Python gate: 3,327 units passed in 56.35 seconds. Branch-inclusive
  coverage was 49,482/65,345 = 75.7242329176%; line coverage was
  40,508/51,541 and branch coverage was 8,974/13,804. `main.py` was
  4,126/7,839 = 52.6342645746% branch-inclusive, above its 45% floor, with
  3,775/6,899 lines and 351/940 branches covered. All 460 role-separated
  PostgreSQL integrations passed in 506.44 seconds. Pytest phases totaled
  562.79 seconds; end-to-end `make test-python` took 575 seconds.
- Release-static passed in 2.28 seconds: control-document truth verified 14
  documents, release-check reported `PASS (alice-memory 0.10.3)`, Ruff passed,
  and mypy passed across 146 source files.
- LongMemEval passed 127 tests in 3.91 seconds and its complete target took
  4.20 seconds. The seven-arm checked-in evidence replay passed against
  `per-question-results-2026-07-07.jsonl`.
- The unchanged web carrier reproduced exactly over 202 tracked inputs with:

  ```zsh
  git ls-files -z -- apps/web \
    | xargs -0 shasum -a 256 \
    | LC_ALL=C sort \
    | shasum -a 256
  ```

  The digest was
  `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`;
  `apps/web/pnpm-lock.yaml` remained
  `f684d9f418db5b6b52964cdafdf27ab326aa68b777c5fc1a7b90dc4f7a4206d9`.
  The R9/R10 71-file/280-test coverage, type, lint, build, budget, and 10-case
  browser matrix therefore carries unchanged; Playwright was not rerun.
- Two fresh `/tmp` builds using `SOURCE_DATE_EPOCH=1783988183`, Python 3.12.11,
  build 1.5.0, isolated setuptools 80.9.0, and wheel 0.45.1 were byte-identical.
  Wheel `alice_memory-0.10.3-py3-none-any.whl` is 1,224,332 bytes with SHA-256
  `212b18ef464d433ec37ee9c672914c00c46f39d0541be89e8eee560c504de1df`.
  Normalized sdist `alice_memory-0.10.3.tar.gz` is 1,070,505 bytes with SHA-256
  `041942b87d09327f321d037fa44b44bfe8e36174d3ab28d33371151b23e19852`.
  Builds took 2.94/3.02 seconds and normalization 0.39/0.38 seconds.
- Twine 6.2.0 passed in 0.25 seconds. Release-check without checksum output
  passed in 0.18 seconds with exact output
  `Release check: PASS (alice-memory 0.10.3)`. Isolated wheel and sdist smokes
  passed in 13.53 and 14.89 seconds. The six carried R10 production files plus
  migration `0090` were byte-identical across workspace, wheel, and sdist;
  the evergreen description matched and the handoff was absent. Repository
  `dist/` was unused. Pre/post package-task status and tracked-diff hashes
  matched exactly. One initial sandboxed build could not resolve PyPI and
  produced no artifacts; the approved network rerun supplied all evidence
  above.
- Control-document truth and its 43-test unit file passed; CURRENT_STATE
  mirrors matched exactly; `git diff --check` passed.

Independent review of the exact Batch 11 carrier subsequently approved the
persisted-source closure and every other bounded area, but returned changes
required on one P2: event payload matching admitted serialized JSON key names.
No Batch 11 review, gate, package hash, or fingerprint approves the current
tree.

### Final Repair Batch 11 carrier fingerprints

The final carrier remains based on branch `main` at unchanged HEAD
`d52e32114eb0b4ef63499e53be14b70dc0864487`. Two independent
reconstructions of the base-relative binary tracked patch produced SHA-256:

```text
e98c197f4e3d868c6e43650d79038154a797cdfd79d8ebdf565da540b2f5608e
```

The canonical `alice-v0.10.4-remediation-bundle-v1` manifest binds that
tracked digest plus these 12 intentional untracked files in this exact order:

```text
apps/api/alembic/versions/20260714_0090_project_scope_identity.py
apps/api/src/alicebot_api/vnext_artifact_review.py
apps/api/src/alicebot_api/vnext_project_update_guard.py
docs/handoff/2026-07-14-v0.10.4-remediation/ENGINEER_HANDOFF.md
docs/handoff/2026-07-14-v0.10.4-remediation/FIX_MATRIX.md
docs/handoff/2026-07-14-v0.10.4-remediation/README.md
docs/handoff/2026-07-14-v0.10.4-remediation/SURFACE_INVENTORY.md
docs/pypi-description.md
tests/integration/test_source_review_identity_api.py
tests/unit/test_20260714_0090_project_scope_identity.py
tests/unit/test_hosted_channel_workspace_resolution.py
tests/unit/test_vnext_context_tree.py
```

Each manifest record is `untracked<TAB>path<TAB>sha256`, preceded by the
tab-delimited `format`, `base`, `branch`, and `tracked-patch` records. Both
independent manifests were byte-identical and produced bundle SHA-256:

```text
b560f4c2045592928184411a838a14cfd7a8b52062c429118b7bc773cc1e1d09
```

This `BUILD_REPORT.md` is self-excluded to avoid a recursive digest. Future
reviewer-owned `REVIEW_REPORT.md`, pre-existing user-owned `coverage.json` and
`uv.lock`, and every file outside the fixed allowlist remain excluded. No
commit, tag, push, release, version bump, or publication was performed.

## Historical Builder Repair Batch 12 scope and verification (review rejected)

Batch 12 closes only the one P2 returned by independent review of the
twice-fingerprinted Batch 11 carrier. `list_open_loop_events` now matches event
payloads through recursive string leaf values only: SQLite uses `json_tree`
rows with type `text`, while PostgreSQL uses recursive `jsonb_path_query`
results whose JSON type is string. Keys, numbers, booleans, nulls, and
serialization punctuation cannot match. Existing loop title, description,
next-action, status, time, scope, ordering, scoped/unscoped, queryless, and
optional-default behavior is unchanged.

### Historical Repair Batch 12 verification

- Focused real SQLite MCP regression: 1 passed, 254 deselected in 0.45 seconds.
- Focused PostgreSQL SQL-shape regression: 1 passed, 80 deselected in 0.24
  seconds.
- Focused live role-separated PostgreSQL regression: 1 passed, 8 deselected in
  1.35 seconds.
- The regressions cover scoped and unscoped calls, nested-object and array
  string leaves, a key-only negative payload
  `{"text":"completely unrelated value"}` queried with `text`, and 62 newer
  mismatch rows before the older matches.
- Owned unit files: 442 passed in 1.37 seconds. The complete role-separated
  PostgreSQL scope/source/resume integration file passed all 9 cases in 11.43
  seconds.
- Ruff check/format, mypy on both store files, `git diff --check`, and the
  pre-documentation release-static gate passed.
- One initial live test attempt failed before reaching production query logic
  because the newly increased fixture generated minute 60. Hour/minute
  rollover corrected the fixture; every reported focused and full-file result
  above is from the clean rerun.

- Full Python gate: 3,327 units passed in 57.47 seconds. Branch-inclusive
  coverage was 49,482/65,345 = 75.72423291759125%; `main.py` was
  4,126/7,839 = 52.63426457456308%, above its 45% floor. All 460
  role-separated PostgreSQL integrations passed in 537.56 seconds with zero
  failures/errors. Pytest phases totaled 595.03 seconds; end-to-end `make`
  took approximately 596 seconds.
- Final release-static passed in 0.74 seconds: control truth verified 14
  documents, release-check reported `PASS (alice-memory 0.10.3)`, Ruff passed,
  and mypy passed across 146 source files. The control test file passed 43
  tests in 0.28 seconds; CURRENT_STATE mirrors matched; diff-check passed.
- LongMemEval passed 127 tests in 4.07 seconds and its complete target took
  4.38 seconds. Seven-arm evidence replay passed against
  `per-question-results-2026-07-07.jsonl`.
- The literal 202-input web digest recipe reproduced
  `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`;
  the pnpm lock remained
  `f684d9f418db5b6b52964cdafdf27ab326aa68b777c5fc1a7b90dc4f7a4206d9`.
  The prior 71-file/280-test coverage, type, lint, build, budget, and 10-case
  browser matrix carries unchanged; Playwright was not rerun.
- Two fresh `/tmp` builds using `SOURCE_DATE_EPOCH=1783988183`, Python 3.12.11,
  build 1.5.0, isolated setuptools 80.9.0, and wheel 0.45.1 were byte-identical.
  Wheel `alice_memory-0.10.3-py3-none-any.whl` is 1,224,406 bytes with SHA-256
  `fe751b56adc5d5457c304dc53932b0323fdd17ac96bbcd8a747d5e081bdd7973`.
  Normalized sdist `alice_memory-0.10.3.tar.gz` is 1,070,564 bytes with SHA-256
  `23c6720ecbdc1bcb0fe898b13f5f41a4a4040e22d99900362f53cb90ea4ae495`.
  Builds took 3.28/3.13 seconds; normalization took 0.39 seconds each.
- Twine 6.2.0 passed in 0.31 seconds. Release-check without checksum output
  passed in 0.18 seconds with exact output
  `Release check: PASS (alice-memory 0.10.3)`. Isolated wheel/sdist smokes
  passed in 14.10/15.32 seconds. All seven carried files matched byte-for-byte
  across workspace, wheel, and sdist; evergreen description and handoff
  exclusion passed. Repository `dist/` was unused. Stable package-task status
  SHA was `b4ae00b93a3583d787080bd958b846923ba27ba8f545a6bae4062e7002364c8b`;
  tracked-diff SHA remained
  `a50c31b79df777528bf5ce1b257f85a36ac12f1eba9bba931b7832f15765faa9`.
- One initial read-only source-copy attempt collided with deletion of transient
  coverage shards from the concurrent full suite and was abandoned before any
  build or artifact. The successful source copies excluded coverage shards;
  no package gate failed and the repository was untouched.

Final fingerprints are recorded below. Independent review approved the exact
production SQLite/PostgreSQL recursive string-leaf behavior but returned
changes required because the MCP fake could combine strings from separate JSON
leaves before matching. Batch 12 is frozen historical evidence, not approval
for the current tree.

### Final Repair Batch 12 carrier fingerprints

The final carrier remains based on branch `main` at unchanged HEAD
`d52e32114eb0b4ef63499e53be14b70dc0864487`. Two independent
reconstructions of the base-relative binary tracked patch produced SHA-256:

```text
f4d85855da96b00380f4666a6e24bfc97308e4f95af7babc858c47d4b1e9aa7f
```

The canonical `alice-v0.10.4-remediation-bundle-v1` manifest binds that
tracked digest plus the same 12 intentional untracked paths listed in the
Batch 11 receipt, in the same order. Each record is
`untracked<TAB>path<TAB>sha256`, preceded by the tab-delimited `format`,
`base`, `branch`, and `tracked-patch` records. Both independent manifests were
byte-identical and produced bundle SHA-256:

```text
097b768925e3009ff0be68fbbd8ac2ce7a7df719bdead421ab860c10d0a3c5b0
```

This `BUILD_REPORT.md` remains self-excluded. Future reviewer-owned
`REVIEW_REPORT.md`, pre-existing user-owned `coverage.json` and `uv.lock`, and
every path outside the fixed allowlist remain excluded. No commit, tag, push,
release, version bump, or publication was performed.

## Historical Builder Repair Batch 13 status (never frozen)

Batch 13 was never frozen. It was an unfrozen pre-finalization candidate that
corrected only the MCP fake's cross-leaf payload matching: a query had to occur
inside one recursive string leaf rather than across text concatenated from
multiple leaves. Two focused regressions, the complete 256-test MCP unit file,
and the full 3,328-unit suite passed. Exact production-file hashes matched the
frozen Batch 12 files, so Batch 12's 460-case role-separated PostgreSQL result
was carried without a PostgreSQL rerun.

Independent review then returned one P2: the fake used Python Unicode folding,
while SQLite and PostgreSQL relied on backend `lower`/collation behavior. That
did not define deterministic cross-backend behavior for non-ASCII queries.
Batch 13 had no final static gate, package build, tracked-patch fingerprint,
bundle fingerprint, or independent approval. Its focused and unit results are
historical diagnostics only.

## Historical Builder Repair Batch 14 scope and verification (review rejected)

Repair Batch 14 was the frozen predecessor. It replaced backend and
fake Unicode folding with one **ASCII case-insensitive literal substring**
contract across SQLite, PostgreSQL, and the MCP fake. The same comparator must
govern both open-loop row fields (title, description, root `next_action`, and
nested `agentic_memory.next_action`) and every recursive event-payload string
leaf. ASCII `A-Z` folds to `a-z`; every non-ASCII code point remains exact,
with no Unicode normalization, locale dependency, or cross-leaf concatenation.
SQL wildcard characters `%`, `_`, and backslash are ordinary literal query
characters, not pattern operators. Existing query trimming/blank behavior,
scope/status/time predicates before limits, event-time ordering, scoped and
unscoped calls, optional defaults, and queryless results remain unchanged.

### Historical Repair Batch 14 verification

- Implementation and production/fake parity readback passed. Four focused
  SQLite, PostgreSQL SQL-shape, fake, wildcard, non-ASCII, and cross-backend
  units passed. The complete MCP/store seam passed 338 units in 1.01 seconds.
- Focused role-separated PostgreSQL verification passed 2 cases in 3.81
  seconds; the complete affected PostgreSQL file passed 10 cases in 15.09
  seconds. The initial live PostgreSQL attempt failed 2 cases before executing
  SQL because psycopg requires literal `%` characters in the query text to be
  escaped as `%%`; the corrected, clean reruns produced the passing results
  above.
- The full Python unit gate passed 3,329 tests in 58.09 seconds. Branch-inclusive
  coverage was 49,494/65,357, or 75.72869011735544%. `main.py` coverage was
  4,126/7,839, or 52.63426457456308%, above its 45% floor.
- The complete role-separated PostgreSQL gate passed 461 tests in 539.11
  seconds. Total real time for the full unit plus PostgreSQL gate was 603.33
  seconds.
- Ruff, format-check, `py_compile`, and diff checks passed. Release-static
  passed in 2.95 seconds, including 14 control documents, `release_check`,
  Ruff, and mypy over 146 files. The control suite passed 43 tests in 0.25
  seconds, and mirror/diff readback was green.
- LongMemEval passed 127 tests in 4.09 seconds against a 4.76-second target,
  and evidence replay passed. The baseline SHA-256 remained
  `027db2960a761d44bb3b20e9ed04a5f434a16d88a3ff9cf65b43a64a3b96589f`.
- The unchanged web carrier was read back without rerunning the historical web
  suite. Its 202-input digest remained
  `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`,
  the `apps/web` diff digest remained
  `df3f667a4e06be6a998478a5a4b4ee0af4a2f27b4cbe7b516b7a80b85aa1e0d4`,
  and `apps/web/pnpm-lock.yaml` remained
  `f684d9f418db5b6b52964cdafdf27ab326aa68b777c5fc1a7b90dc4f7a4206d9`.
  The carried evidence is 71 files/280 tests plus coverage, types, lint, build,
  four budgets, and 10 browser cases; it is explicitly not a Batch 14 rerun.
- Two fresh package builds completed in 3.18 and 3.09 seconds. Normalization
  completed in 0.39 seconds for each build, and the normalized archives were
  byte-identical. The wheel was 1,224,846 bytes with SHA-256
  `3fb15c21ca6aefce80f7be87d56bca853c6252c51d9145a2b7f7e7216aa6cf1f`;
  the sdist was 1,070,994 bytes with SHA-256
  `cf348680005eca2c9dcdc37a1f9307b7a043648557760aa8eb63f38bef30080b`.
  Twine passed in 0.40 seconds, release-check passed in 0.28 seconds, isolated
  wheel and sdist smokes passed in 13.82 and 15.48 seconds, seven-file archive
  parity passed, the evergreen PyPI description was present, and exclusions
  passed. Expected sandbox-DNS preflights produced no artifacts; approved
  reruns passed. The repository `dist/` directory was untouched.

The final source/test readback for this Batch 14 correction is:

```text
6c22b273730cb61b21ca036e241303a3c9940cc1ee8fc29758f0095b818da1c4  apps/api/src/alicebot_api/sqlite_store.py
229c9a38520f649867d8f2c6a4936ba94939eaf912d3d96ce9ca1b9bba669a87  apps/api/src/alicebot_api/vnext_store.py
624891943aa858a0eae4cbd1a9502bcc70fa5b46d6d0ed14d9bd1ea105d3b3d1  tests/unit/test_mcp.py
0da822f3dcee560e56be2b479b9a8801e10e1a6d9cd0a1b9e803361dab917b7f  tests/unit/test_vnext_store.py
bcd5eddf3c976329cb438154746ac833e3efd7f4af876dd345d77d75c643668a  tests/integration/test_project_scope_precedence_postgres.py
```

Repository readback preserved immutable
`docs/release/v0.10.3-release-notes.md` at SHA-256
`463a6b0d4a54b23a577126ce17202736f0aeeebcb2a5ee314416ed5283415938`
and `docs/release/v0.10.3-checksums.txt` at SHA-256
`57e4cc30bbbb9c7438b54954fecb4fdd88f15d0f2874e62ea66faa45612a6387`.
Pre-existing user-owned `coverage.json` remained
`57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711`
and `uv.lock` remained
`65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52`.
`REVIEW_REPORT.md` was absent from the builder carrier and remained outside the
fingerprint allowlist.

- Final tracked-patch and remediation-bundle fingerprints: **PASS**. Two
  independent reconstructions matched exactly; the receipt is below.
- Independent review of the exact fingerprinted Batch 14 carrier: **CHANGES
  REQUIRED** on exactly three bounded P2s: non-string metadata `next_action`
  row parity, overbroad alpha-documentation scope, and missing `created_at` in
  the fake open-loop ordering.

### Final Repair Batch 14 carrier fingerprints

The frozen builder carrier remains based on branch `main` at unchanged HEAD
`d52e32114eb0b4ef63499e53be14b70dc0864487`. Two independent
reconstructions of the base-relative binary tracked patch produced SHA-256:

```text
0fc353e4c37f153e3ba283959bf4564e5021bfd43d3813ad4cf800c3cad99290
```

The canonical `alice-v0.10.4-remediation-bundle-v1` manifest binds that
tracked digest plus the same fixed 12 intentional untracked paths listed in
the Batch 11/12 receipt, in the same order. Each record is
`untracked<TAB>path<TAB>sha256`, preceded by the tab-delimited `format`,
`base`, `branch`, and `tracked-patch` records. The manifest is 1,721 bytes.
Both independent reconstructions were byte-identical and produced bundle
SHA-256:

```text
638e9e0ada3c4698a79fd120cbdabfda9eb28c1451aebde282db088f8e2a23bd
```

This `BUILD_REPORT.md` remains self-excluded to avoid a recursive digest.
Future reviewer-owned `REVIEW_REPORT.md`, pre-existing user-owned
`coverage.json` and `uv.lock`, and every path outside the fixed allowlist were
also excluded explicitly. The Batch 14 carrier was frozen, but independent
review rejected it on exactly the three bounded P2s below. Its gate, package,
source/test-hash, and fingerprint evidence is historical and does not approve
the current tree.

## Historical Builder Repair Batch 15 scope and status

Repair Batch 15 was the then-current bounded correction. It was limited to the three
P2s returned by review of the exact twice-fingerprinted Batch 14 carrier:

1. SQLite, PostgreSQL, and `FakeVNextMCPStore` must treat root
   `metadata_json.next_action` and nested
   `metadata_json.agentic_memory.next_action` as row-match candidates only
   when the value itself is a string. Objects, arrays, numbers, booleans, and
   null must not be stringified or admitted through those fields. Title and
   description matching is unchanged.
2. Alpha documentation must state that the **ASCII case-insensitive literal
   substring** rule, exact non-ASCII behavior, and literal `%`, `_`, and
   backslash behavior apply only to open-loop row fields and loop-event
   recursive string leaves. They do not define decision-memory or
   next-action-memory search behavior.
3. `FakeVNextMCPStore.list_open_loops` must mirror production ordering exactly:
   `opened_at DESC`, then `created_at DESC`, then `id DESC`.

Recursive individual string-leaf matching for loop-event payloads is
unchanged. Blank/queryless behavior, scope/status/time predicates before
limits, event ordering, scoped/unscoped calls, optional defaults, and every
surface outside these three corrections remain unchanged.

### Historical Repair Batch 15 verification

- Implementation and readback passed for string-only root/nested metadata
  `next_action` row candidates across SQLite, PostgreSQL, and the fake; exact
  fake ordering; unchanged per-string-leaf event matching; and the narrowed
  alpha-documentation contract.
- Five focused units passed with 334 deselected in 0.41 seconds. The complete
  owned MCP/store seam passed 339 tests in 0.53 seconds. The first focused
  fixture run passed 4 and failed 1 because the blank-query case expected 23
  rows while the established default limit is 20; setting that fixture's
  explicit limit to 50 corrected the test without changing production
  behavior, and the clean focused rerun passed.
- Focused live role-separated PostgreSQL verification passed 1 case with 9
  deselected in 1.25 seconds; the complete affected PostgreSQL file passed 10
  cases in 11.54 seconds. The first live attempt was blocked by the sandbox;
  the approved rerun passed.
- Ruff, format-check, `py_compile`, and diff checks passed.
- The full Python unit gate passed 3,331 tests in 62.90 seconds. Combined
  branch-aware coverage was 49,494/65,361, or 75.7241%; statement coverage was
  40,520/51,557, or 78.5926%; and branch coverage was 8,974/13,804, or
  65.0101%. `main.py` statement coverage was 3,775/6,899, or 54.7181%, above
  its 45% floor; branch-aware `main.py` coverage was 4,126/7,839, or 52.6343%.
- The control suite passed 44 tests in 0.26 seconds. The complete
  role-separated PostgreSQL gate passed 461 tests in 465.73 seconds. The full
  Python plus PostgreSQL matrix therefore passed 3,792 tests in 528.63 seconds.
- Release-static passed in 1.31 seconds, including 14 control documents,
  `release_check`, Ruff, and mypy over 146 files. Mirror and diff readback was
  green.
- LongMemEval passed 127 tests in 4.26 seconds against a 4.67-second target,
  and evidence replay passed. The evidence contained 892 rows and the baseline
  SHA-256 remained
  `027db2960a761d44bb3b20e9ed04a5f434a16d88a3ff9cf65b43a64a3b96589f`.
- The unchanged web carrier was read back without rerunning the historical web
  suite. Its 202-input digest remained
  `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`,
  the `apps/web` diff digest remained
  `df3f667a4e06be6a998478a5a4b4ee0af4a2f27b4cbe7b516b7a80b85aa1e0d4`,
  and `apps/web/pnpm-lock.yaml` remained
  `f684d9f418db5b6b52964cdafdf27ab326aa68b777c5fc1a7b90dc4f7a4206d9`.
  The carried evidence is 71 files/280 tests plus coverage, types, lint, build,
  budgets, and 10 browser cases; it is explicitly not a Batch 15 rerun.
- Two fresh package builds completed in 3.68 and 3.12 seconds. Normalization
  completed in 0.40 seconds for each build, and the normalized archives were
  byte-identical. The wheel was 1,224,931 bytes with SHA-256
  `8fd31e9cb289da7b85389201eecfa1160f5e8ca2afd6abca6dc18eb7e838b407`;
  the sdist was 1,071,126 bytes with SHA-256
  `263666ccc16faced4a54f270edefc17359c8dad128414220342ecd776f28f2a6`.
  Twine passed in 0.29 seconds, release-check passed in 0.17 seconds, isolated
  wheel and sdist smokes passed in 15.03 and 15.66 seconds, seven-file archive
  parity passed, the evergreen PyPI description was present, and exclusions
  passed. The repository `dist/` directory was untouched.

The final source/test readback for this Batch 15 correction is:

```text
7ad4d2b22c2bc0a83022bde38848b173c86e9d2467d2c620604a53b9282fe68f  apps/api/src/alicebot_api/sqlite_store.py
4dd38a7074aaf88c36c479deffb41ee463cc295e45126644ed99234899833cea  apps/api/src/alicebot_api/vnext_store.py
e0fa31e8b9f70a8f4a2f505ade3bc719f4119236cbcdcca9a46228a5c478ef04  tests/unit/test_mcp.py
daee041b9ab9bf3143ddf544d8d98bf0bb596467e664532ab4dda75ae0233630  tests/unit/test_vnext_store.py
673cccb455250664fa8e291cf66fe7f74032fb6621cc918340915457c068d959  tests/integration/test_project_scope_precedence_postgres.py
a5dd10311f90dd154717dec112bd5942566acb37430c23d4d2502fe7ff75908c  tests/unit/test_control_doc_truth.py
```

Repository readback preserved immutable
`docs/release/v0.10.3-release-notes.md` at SHA-256
`463a6b0d4a54b23a577126ce17202736f0aeeebcb2a5ee314416ed5283415938`
and `docs/release/v0.10.3-checksums.txt` at SHA-256
`57e4cc30bbbb9c7438b54954fecb4fdd88f15d0f2874e62ea66faa45612a6387`.
Pre-existing user-owned `coverage.json` remained
`57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711`
and `uv.lock` remained
`65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52`.
`REVIEW_REPORT.md` remains absent, as required before independent Batch 15
review.

- Final tracked-patch and remediation-bundle fingerprints: **PASS**. Two
  independent reconstructions matched exactly; the receipt is below.
- Independent review of the exact frozen Batch 15 carrier: **APPROVED
  historically, then superseded by the Batch 16 engineering finding**.

### Final Repair Batch 15 carrier fingerprints

The frozen builder carrier remains based on branch `main` at unchanged HEAD
`d52e32114eb0b4ef63499e53be14b70dc0864487`. Two independent
reconstructions of the 1,005,065-byte base-relative binary tracked patch were
byte-identical and produced SHA-256:

```text
ec26dab041a3ca49094ac16ec423d054f7fd2ae5db59330c4e22c61727dd9718
```

The canonical `alice-v0.10.4-remediation-bundle-v1` manifest binds that
tracked digest plus the fixed 12 intentional untracked paths, in this order:

```text
apps/api/alembic/versions/20260714_0090_project_scope_identity.py
apps/api/src/alicebot_api/vnext_artifact_review.py
apps/api/src/alicebot_api/vnext_project_update_guard.py
docs/handoff/2026-07-14-v0.10.4-remediation/ENGINEER_HANDOFF.md
docs/handoff/2026-07-14-v0.10.4-remediation/FIX_MATRIX.md
docs/handoff/2026-07-14-v0.10.4-remediation/README.md
docs/handoff/2026-07-14-v0.10.4-remediation/SURFACE_INVENTORY.md
docs/pypi-description.md
tests/integration/test_source_review_identity_api.py
tests/unit/test_20260714_0090_project_scope_identity.py
tests/unit/test_hosted_channel_workspace_resolution.py
tests/unit/test_vnext_context_tree.py
```

Each manifest record is `untracked<TAB>path<TAB>sha256`, preceded by the
tab-delimited `format`, `base`, `branch`, and `tracked-patch` records. The
manifest is 1,721 bytes and 16 lines. Both independent reconstructions were
byte-identical and produced bundle SHA-256:

```text
7bc73afa88094d75ee2ad6b62566e5a77acdc26a844dcb4207072d3bd0304c08
```

This `BUILD_REPORT.md` remains self-excluded to avoid a recursive digest.
Future reviewer-owned `REVIEW_REPORT.md`, pre-existing user-owned
`coverage.json` and `uv.lock`, and every path outside the fixed allowlist are
also excluded explicitly. Batch 15 was builder-frozen on these fingerprints
and subsequently approved. The Batch 16 engineering finding supersedes that
approval, so neither Batch 14 nor Batch 15 evidence approves the current tree.

## Builder Repair Batch 16 scope and current status

Repair Batch 16 is the current bounded correction for the engineering-team
whitespace finding discovered after independent approval of Batch 15. The
approved Batch 15 carrier still mirrored Python `str.strip()` with PostgreSQL's
locale-dependent POSIX `[[:space:]]`, which deterministically omitted
U+001C–U+001F and could disagree for NBSP-class whitespace. Batch 15 evidence
and `REVIEW_REPORT.md` are historical and do not approve changed Batch 16
bytes; the builder did not edit or delete the reviewer-owned report.

The production change is limited to
`apps/api/src/alicebot_api/vnext_store.py`. A private runtime constant repeats
migration `0090`'s exact CPython 3.12 29-codepoint table, and one helper emits
`btrim(expression, chr(...) || ...)`. The embedding content digest still
trims title/canonical/summary in that order, omits blanks, keeps the first
occurrence of duplicate normalized values, joins with LF, and hashes UTF-8
with SHA-256. Runtime code does not import migration code.

Fail-on-old unit coverage proves that the signed vector-search freshness
filter, signed embedding update CAS, and missing-embedding selection each
contain all 29 codepoints—including `chr(28)` through `chr(31)`, `chr(133)`,
and `chr(160)`—and no POSIX trim. The live role-separated PostgreSQL regression
uses NBSP, U+001C, and mixed blank/deduplicated fields and proves successful
CAS, no re-embed loop, and signed vector participation.

### Current Repair Batch 16 verification

- Focused SQL-shape/CAS units: 4 passed, 78 deselected.
- Complete affected unit file: 82 passed.
- Focused live role-separated PostgreSQL: 3 passed, 1 deselected in 3.85
  seconds after an initial sandbox-blocked attempt made no database
  connection.
- Complete affected PostgreSQL file: 4 passed in 5.26 seconds.
- Authoritative post-wording full unit gate: 3,332 passed in 66.89 seconds.
  Branch-inclusive coverage was
  49,498/65,365 (75.7255%); statement coverage was 40,524/51,561 (78.5943%).
  `main.py` statement coverage was 3,775/6,899 (54.7181%, above its 45%
  floor), and branch-inclusive coverage was 4,126/7,839 (52.6343%).
- Ruff format/check and `git diff --check`: PASS for the implementation and
  affected tests.
- Complete role-separated PostgreSQL gate: 463 passed in 508.29 seconds with
  zero failures/errors. The initial sandboxed connection denial was a non-
  verdict; the approved role-separated run supplied this result.
- Release-static: PASS in 2.9 seconds, including 14 control documents,
  release-check for `alice-memory 0.10.3`, Ruff, and mypy over 146 files.
  The control suite passed 44 tests; format, `py_compile`, mirror, and diff
  checks passed.
- LongMemEval: 127 passed in 4.33 seconds; seven-arm evidence replay passed.
  The 892-row baseline remained SHA-256
  `027db2960a761d44bb3b20e9ed04a5f434a16d88a3ff9cf65b43a64a3b96589f`.
- Exact unchanged-web readback: 202-input digest
  `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`,
  base-relative diff digest
  `df3f667a4e06be6a998478a5a4b4ee0af4a2f27b4cbe7b516b7a80b85aa1e0d4`,
  and lock digest
  `f684d9f418db5b6b52964cdafdf27ab326aa68b777c5fc1a7b90dc4f7a4206d9`.
  The prior 71-file/280-test coverage/type/lint/build/budget and 10-browser-
  case matrix carries unchanged; it was not rerun.
- Fresh package gate under `/tmp/alice-batch16-package.28kLWH`: builds passed
  in 2.96/3.11 seconds and sdist normalization in 0.39/0.38 seconds. Both
  artifacts reproduced byte-for-byte. Wheel
  `alice_memory-0.10.3-py3-none-any.whl` was 1,225,285 bytes with SHA-256
  `ae441138a6d7530a063532fd75f9c4d8a9fd10f886d7e8c799e6648d9511e596`;
  normalized sdist `alice_memory-0.10.3.tar.gz` was 1,071,493 bytes with
  SHA-256
  `4a02646d89ae3d556dc5273db9c21c2a5afb63572e3ab1b08bd2b7b377fae0b9`.
  Twine passed in 0.36 seconds; release-check passed in 0.18 seconds and left
  exactly two artifacts/no checksum. Wheel/sdist installed smokes passed in
  13.69/14.55 seconds. Seven current critical files matched across workspace,
  wheel, and sdist. The wheel/sdist contained 241/263 entries, zero tests or
  handoff files, and exact evergreen-description metadata. Repository `dist/`
  was untouched. An initial sandbox-DNS preflight produced no artifacts; the
  approved pinned-dependency run supplied the accepted evidence.
- Final guards and twice-reproduced carrier fingerprints: **PASS**; receipt
  below.
- Independent review of the exact frozen Batch 16 carrier: **CHANGES
  REQUIRED** on one documentation-truth P3; production CAS semantics approved.

The fixed 12-file intentional-untracked bundle allowlist remains unchanged.
`REVIEW_REPORT.md`, this self-referential builder report, and pre-existing
user-owned `coverage.json` and `uv.lock` remain excluded from the bundle.

### Final Repair Batch 16 carrier fingerprints

The frozen builder carrier remains on branch `main` at unchanged HEAD/base
`d52e32114eb0b4ef63499e53be14b70dc0864487`. Two independent reconstructions
of the base-relative binary tracked patch were byte-identical and produced
SHA-256:

```text
73dbc5eb530d7e59a13587ddf489d3795dd4da7f0f5e1d635bd5b5d0c18e71f3
```

The canonical `alice-v0.10.4-remediation-bundle-v1` manifest binds that digest
to the same fixed 12 intentional untracked paths used by Batch 15, in this
order:

```text
apps/api/alembic/versions/20260714_0090_project_scope_identity.py
apps/api/src/alicebot_api/vnext_artifact_review.py
apps/api/src/alicebot_api/vnext_project_update_guard.py
docs/handoff/2026-07-14-v0.10.4-remediation/ENGINEER_HANDOFF.md
docs/handoff/2026-07-14-v0.10.4-remediation/FIX_MATRIX.md
docs/handoff/2026-07-14-v0.10.4-remediation/README.md
docs/handoff/2026-07-14-v0.10.4-remediation/SURFACE_INVENTORY.md
docs/pypi-description.md
tests/integration/test_source_review_identity_api.py
tests/unit/test_20260714_0090_project_scope_identity.py
tests/unit/test_hosted_channel_workspace_resolution.py
tests/unit/test_vnext_context_tree.py
```

Each record is `untracked<TAB>path<TAB>sha256`, preceded by tab-delimited
`format`, `base`, `branch`, and `tracked-patch` records. Both independent
reconstructions were byte-identical. The manifest is 1,721 bytes / 16 lines
and produced SHA-256:

```text
15719258db03248147c02d4ae8cf2c1c06d1282eb3d1ddd051e59d2050c79f5e
```

The final Batch 16 source/test readback is:

```text
2613f024ebf8bf1a1d6c461a8b4b59d8ab66cdc2bc171c2ed6f1336bdb030fa7  apps/api/src/alicebot_api/vnext_store.py
9b7e372022a2569a908e7c4fd2fde05282f66128818b3589bde4ebc128f9ca61  tests/unit/test_vnext_store.py
f600a283c3cc6e7a5f460b092fca3c7fa930753a4614bbda3ce4733e5800f8e7  tests/integration/test_vnext_embedding_backfill_postgres.py
55643f1c80a5525a06d73a135d603ae3e9e573a24eef616e1fd5ecd4ad067dc4  scripts/check_control_doc_truth.py
a5dd10311f90dd154717dec112bd5942566acb37430c23d4d2502fe7ff75908c  tests/unit/test_control_doc_truth.py
```

The seven-file workspace/wheel/sdist parity set was byte-identical at these
workspace SHA-256 values:

```text
2613f024ebf8bf1a1d6c461a8b4b59d8ab66cdc2bc171c2ed6f1336bdb030fa7  apps/api/src/alicebot_api/vnext_store.py
20cf0442f9593ce20b6fe6d9b2ba85d7f321fd88c29861b80db34017b0d8a299  apps/api/src/alicebot_api/vnext_embeddings.py
0bcecace04d9d3540aeec171a9ac6e1522fe8370bf93040fe52c18b840d490cb  apps/api/src/alicebot_api/vnext_project_scope.py
7ad4d2b22c2bc0a83022bde38848b173c86e9d2467d2c620604a53b9282fe68f  apps/api/src/alicebot_api/sqlite_store.py
941d14effeb252e2e3e92c641885c10a9cacefb030a64f77b9693e0b72dcbabc  apps/api/src/alicebot_api/vnext_retrieval.py
46e767095999b646322750bd018b36c68cebf3c6e7bea6e8fadef7044ab5eb16  apps/api/src/alicebot_api/mcp_tools.py
9050f5e809ddcb36dfabc492f0e0022437c977f94a8ee343bf7e6956a11a0f4a  apps/api/alembic/versions/20260714_0090_project_scope_identity.py
```

Expanded status is 101 modified, 16 untracked, 0 deleted, and 0 staged paths;
the 117-line status manifest SHA-256 is
`6ae8331d205f5e186e85f74d5ec8df59bdae88600c510c524313be1b4a4c9eed`.
Immutable v0.10.3 release notes/checksums remain
`463a6b0d4a54b23a577126ce17202736f0aeeebcb2a5ee314416ed5283415938`
and
`57e4cc30bbbb9c7438b54954fecb4fdd88f15d0f2874e62ea66faa45612a6387`.
User-owned `coverage.json`/`uv.lock` remain
`57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711`
and
`65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52`.
Reviewer-owned historical `REVIEW_REPORT.md` remains byte-identical at
`b2f495174504d77e1d574d821ef45ea08e6c3721fc71be923559cce75173578e`.
CURRENT_STATE mirrors match exactly, the package version remains `0.10.3`,
and no commit, tag, push, publication, or security work was performed.

This `BUILD_REPORT.md` is self-excluded to avoid a recursive digest. The
reviewer report and user-owned files are excluded explicitly. Batch 16 was
builder-frozen on the fingerprints above. Its reviewer approved the production
CAS semantics and returned changes required on one documentation-truth P3;
Refreeze 17 supersedes only the affected truth carriers and control guard.

## Historical Builder Repair Batch 6 scope (superseded)

Repair Batch 6 replaces only the Refreeze 5 terminal-replay proof. A terminal
retry now derives the original coupled outcome from the already-locked
project-update artifact, exactly one append-only `project_update_review`
revision, and exactly one actor-coupled decision event. Current memory contents
and lifecycle fields, current memory-row existence, and current project state
are deliberately not evidence because supported lifecycle operations,
retention, and later project updates can change them legitimately.

The ordinary proof still checks exact artifact/revision/event linkage and
action semantics. Authorized true redaction is accepted only through the exact
content-free revision/event skeleton retained by the store, including the
cleared accepted-event integrity hash. Partial redaction markers or fabricated
decision evidence fail closed. Generic and dedicated HTTP, MCP, and CLI tests
retain the fixed 409/error and zero-mutation contract for forced terminal
side-door states. Live PostgreSQL tests exercise accepted and rejected
redaction/replay; SQLite tests prove that its redaction path preserves the same
revision/event skeleton without claiming a project-service surface SQLite does
not have.

## Historical Refreeze 6 builder verification (superseded)

The results below belong only to Refreeze 6. Refreeze 5 values are retained
only where explicitly labeled as superseded historical context. Repair Batch
8 changes the tree, so the Refreeze 6 web, package, test, and fingerprint
evidence below is historical rather than current approval evidence.

### Static release gate

Command: `make release-static`

- Fresh Builder Repair Batch 6 run: PASS.
- Control-document truth: PASS.
- `Release check: PASS (alice-memory 0.10.3)`.
- Ruff across API, scripts, tests, and LongMemEval: PASS.
- Mypy across 146 first-party/release-tool source files: PASS.

### Python unit and coverage gate

Fresh Builder Repair Batch 6 command, using the local PostgreSQL 16 + pgvector
container and explicit role-separated credentials:

```zsh
DATABASE_ADMIN_URL=postgresql://alicebot_admin:alicebot_admin@127.0.0.1:15433/alicebot \
DATABASE_URL=postgresql://alicebot_app:alicebot_app@127.0.0.1:15433/alicebot \
make test-python
```

- 3,197 unit tests passed in 116.21 seconds.
- Total coverage: 75.55% (required 50%).
- `apps/api/src/alicebot_api/main.py`: 52.64% (required 45%).
- Per-file coverage checker: PASS.
- Live role-separated PostgreSQL: **447 tests passed in 885.36 seconds
  (14:45)**.

The complete command was launched with approved local-container access from
the start. Only this final fully green role-separated run is accepted evidence
for Refreeze 6.

### Focused lane evidence

- Repair Batch 6 terminal replay: 557 combined service, generic/dedicated
  HTTP, MCP, CLI, and SQLite tests passed in 6.15 seconds. Coverage includes
  the locked-artifact plus exactly-one revision/event proof, supported
  correction/undo/forget evolution, a genuine later project update,
  exact/partial redaction handling, forced terminal side-door failures with
  the fixed 409/error and zero mutation, and valid accepted/rejected controls.
  The focused role-separated PostgreSQL accept/reject true-redaction replay
  added two more passing cases in 4.94 seconds and proved zero mutation after
  replay. Ruff, focused mypy, and diff-check passed.

- Project lifecycle: 310 focused HTTP/MCP/CLI/service tests passed; Ruff,
  Python compile, and diff-check passed.
- Scope/identity/store: 509 focused unit/adapter/store tests passed; 5 focused
  live PostgreSQL tests passed; Ruff and mypy passed.
- OpenAPI: 82 `test_main` tests passed; 294 operations covered by 49 exact,
  243 closed registry, and two intentional polymorphic contracts; Ruff and
  focused mypy passed.
- Hosted/web: 7 focused Python tests, 4 live PostgreSQL Phase 10 tests, and 30
  focused web tests passed; ESLint, typecheck, Ruff, and diff-check passed.
- Provider/base-path: 23 Python unit tests, 24 provider integration tests, and
  56 web API tests passed; Ruff, mypy, typecheck, ESLint, and diff-check passed.
- Release/control docs: combined control/release/migration unit group passed
  151 tests; active mirror and control-doc checker passed.
- Human HTTP review attribution follow-up: 5 focused review tests passed;
  Ruff and diff-check passed.
- Repair Batch 2 project lifecycle: 45 project-service tests and 326 combined
  lifecycle/CLI/MCP tests passed. All five durable supersession marker forms
  fail on accept/edit/reject without mutation, and central dispatch propagates
  the guard. Ruff, focused mypy, and diff-check passed.
- Repair Batch 2 identity/store/key policy: 241 core helper/key/SQLite/schema/
  SQL-shape/migration tests and 654 affected routing/workflow/adapter tests
  passed; 4 live PostgreSQL parity tests passed. Ruff, mypy across 12 affected
  source files, closure greps, and diff-check passed.
- Repair Batch 2 dedicated MCP schema: 6 focused tests and the complete
  204-test MCP unit file passed. The normal MCP schema-validation path proved
  agent identity/profile/scope/run/trace persistence. Ruff, mypy, a structural
  schema assertion, and diff-check passed.
- Repair Batch 3 migration precedence: 4 focused `0083` unit tests passed; 2
  focused live PostgreSQL migration tests passed, including the exact
  `0082`→head chain. Present empty/null/malformed/nonempty canonical values
  remained authoritative, stale nested scope stayed filter-invisible, and an
  absent canonical key retained legacy singleton backfill. Ruff, format,
  focused mypy, and diff-check passed.
- Repair Batch 3 trace fallback: 16 focused trace/page/component tests passed.
  Both asymmetric failures retain the successful leg with truthful source
  labels, and the same-wave concurrency regression remains. Typecheck, ESLint,
  and diff-check passed.
- Repair Batch 4 scheduler OpenAPI: the complete 83-test `test_main.py` file
  and 37 scheduler service/runtime regressions passed. The fail-on-old sample
  builds the real 13-field merged scheduler/daemon payload and validates it
  against the generated required, closed schema. The 294-operation closure,
  authoritative-source, runtime, and phantom-key invariants remained green;
  Ruff, mypy, format, and diff-check passed.
- Repair Batch 4 project scope/migrations: 46 focused unit tests and 6 live
  PostgreSQL tests passed. SQLite and migration `0090` cover every supported
  resolver tier, full-envelope `scope_json`, actual duplicate recapture, and
  present-canonical precedence; a live `0082`→head test preserves U+2003
  byte-exactly through corrected `0083`. Ruff, mypy, format, and diff-check
  passed.
- Repair Batch 4 release truth: 170 focused release/control/recovery tests
  passed. Direct runbook/tooling readback verified the finalization order,
  transactional workflow ownership, post-publication checksum receipt, exact
  `release_check.py` output, and the absence of a dedicated marker assertion
  for the `0087`/`0089` operator prose.
- Repair Batch 5 terminal consistency: 82 focused project-update cases passed;
  all 402 tests in the four touched service/HTTP/MCP/CLI modules passed.
  Forced accepted/rejected legacy states and eleven independent durable-leg
  corruptions fail with the fixed repair instruction without mutation, while
  consistent accepted/rejected retries remain idempotent through both generic
  and dedicated adapters. Ruff, mypy, format-range checks, and diff-check
  passed.
- Repair Batch 5 migration `0090` raw-text parity: 3 focused unit tests and 3
  live PostgreSQL `0089`→head tests passed. Explicit CPython 3.12 whitespace
  normalization produced the runtime digests for NBSP, NEL, and EM SPACE; an
  actual recapture returned the three original sources without duplicates.
  Ruff, mypy, formatting, and diff-check passed.
- Repair Batch 5 scheduler OpenAPI: the complete 83-test `test_main.py` file
  and 37 scheduler tests passed. The fail-on-old regression invokes
  `get_vnext_scheduler_status`, parses its serialized response, and validates
  the exact 13 fields against the generated required, closed schema, including
  phantom-key rejection. Ruff, mypy, formatting, and diff-check passed.
- Repair Batch 5 release operability: all 40 control-document tests and the
  direct control-document checker passed. The regression locks both fresh-dir
  matrices, explicit `DIST_DIR`/`REPRO_DIST_DIR`, their emptiness checks, no
  parallel target, no separate artifact target, user-directory preservation,
  and the truthful ignored-cache evidence boundary.

### LongMemEval

Command: `make test-longmemeval`

- 127 tests passed in 7.94 seconds in the fresh Builder Repair Batch 6 run;
  the complete command took 8.57 seconds.
- Evidence checker: PASS, seven arms, checked-in
  `per-question-results-2026-07-07.jsonl` baseline.

### Web gate

Repair Batch 6 changed no web source or test bytes. The base-relative binary
web patch remains exactly
`df3f667a4e06be6a998478a5a4b4ee0af4a2f27b4cbe7b516b7a80b85aa1e0d4`,
the Refreeze 3 fingerprint. It reproduced before and after the fresh Batch 6
checks. TypeScript typecheck passed in 3.26 seconds and ESLint passed in 7.50
seconds with zero warnings. The complete Refreeze 3 `make test-web` evidence
therefore remains applicable to this byte-identical web patch:

- Full Vitest: 71 files / 280 tests passed.
- Core coverage shard: 68 files / 267 tests passed; 89.56%
  statements/lines, 74.33% branches, 89.96% functions.
- vNext coverage shard: 3 files / 13 tests passed; 80.69%
  statements/lines, 66.84% branches, 54.74% functions.
- TypeScript typecheck and ESLint with zero warnings: PASS.
- Next.js 15.5.20 production build: PASS; 19/19 static pages generated,
  compiled in 1,394 milliseconds.
- All four bundle budgets passed: `/` had 13,832 bytes headroom, `/chat`
  15,474, `/continuity` 16,242, and `/vnext` 17,671.
- Playwright: 8 core in 3.1 seconds + 1 outage in 4.4 seconds + 1
  partial-outage in 4.3 seconds = 10/10 passed.

That Refreeze 3 run required approved execution outside the sandbox for
Playwright's user cache and localhost test servers. A redundant full rerun was
not performed for Batch 6 because the web patch bytes are unchanged; the
fresh typecheck/lint and repeated exact binary fingerprint are the Refreeze 6
invariance evidence.

### Reproducible package gate

The Refreeze 6 packaged-input tree was built twice into brand-new
empty, explicitly selected `/tmp` primary and reproducibility directories with
`SOURCE_DATE_EPOCH=1783988183`; both sdists were normalized. Repository
`dist/` was not read, modified, deleted, or reused.

- Wheel and sdist comparisons: byte-for-byte PASS.
- Refreeze 6 wheel `alice_memory-0.10.3-py3-none-any.whl`: SHA-256
  `1994bd808a618f670dea7f7bcb50f3f034ee032afa0b78c4a355da5bd7e60670`
  (1,211,496 bytes).
- Refreeze 6 sdist `alice_memory-0.10.3.tar.gz`: SHA-256
  `1137b5a3b99f7023aa5bc0da7a165a953864fd2ea5b60a6fc7746ed2b81a9e8f`
  (1,058,025 bytes).
- Twine checks: PASS.
- `release_check.py --dist-dir` without checksum writes: PASS with exact
  output `Release check: PASS (alice-memory 0.10.3)`; neither build directory
  gained a checksum artifact.
- Installed wheel and sdist smoke in separate fresh isolated environments:
  PASS, including public CLI help/version entry points, metadata/API identity,
  package isolation, Alembic and eval resources, MCP tool catalogs, SQLite
  commit, and recall.

These hashes verify the dirty, version-unfinalized Refreeze 6 remediation tree.
They are not v0.10.4 release checksums and must not be published or copied into
immutable release records.

Both builds used Python 3.12.11, `build 1.5.0`, pinned `setuptools 80.9.0`
and `wheel 0.45.1`; sdist normalization passed twice. The artifacts contain
migration `0090`, both new review-guard modules, the terminal-consistency
service changes, and the evergreen PyPI description. The sdist contains no
remediation-handoff files. Post-build snapshot readback found no packaged-input
drift. The immutable v0.10.3 release files remained unchanged, and the
pre-existing untracked `coverage.json` and `uv.lock` were preserved.

### External semantic gate

The provider-backed semantic release attestation is intentionally deferred to
the exact clean release SHA. An attestation for this dirty uncommitted tree
would not be a valid release artifact.

## Historical Refreeze 7 repository checks (superseded)

The Refreeze 7 carrier freeze repeated every readback below on its then-current
source/package tree. These counts and hashes are provenance for that
historical carrier, not the pending Batch 8 freeze:

- `git diff --check`;
- unchanged base HEAD and branch readback;
- immutable v0.10.3 release-file no-diff readback;
- active handoff package completeness;
- exact manifest: 90 tracked modified paths and 13 untracked paths, of which
  ten are fingerprinted remediation files, `BUILD_REPORT.md` is the
  self-reference carrier, and `coverage.json`/`uv.lock` are preserved
  user-owned inputs;
- pre-existing ignored `dist/` artifacts were neither read, overwritten, nor
  deleted; all accepted package bytes were produced in brand-new empty
  temporary directories passed explicitly as `DIST_DIR` and
  `REPRO_DIST_DIR`. Ignored dependency, test, coverage, semantic-evidence,
  browser, and build caches may have been refreshed by verification commands,
  but they are excluded from the tracked/untracked manifest and remediation
  fingerprints, and their presence or timestamps are not used as evidence;
- preserved `coverage.json` SHA-256
  `57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711`
  and `uv.lock` SHA-256
  `65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52`;
- explicit external-only release items in `ENGINEER_HANDOFF.md`.

Refreeze 6 included a fresh focused/full verification record for the Batch 6
terminal evidence model, immutable v0.10.3 release-file readback, preservation
of user-owned `coverage.json` and `uv.lock`, and two matching post-gate
fingerprint reconstructions. Batch 8 requires its own final repository
readback and fingerprints; its current gates are recorded above.
