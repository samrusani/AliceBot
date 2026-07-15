# Alice v0.10.4 Fifth-Audit Remediation — Independent Batch 15 Review

## Verdict

**APPROVED — no actionable P1, P2, or P3 finding remains in the Batch 15
closure scope.**

The exact builder-frozen Batch 15 carrier closes all three findings returned
by the independent Batch 14 review: non-string open-loop `next_action` row
parity, overbroad MCP documentation, and the fake store's missing
`created_at` ordering tie-breaker. The implementation, fail-on-old tests,
public documentation, cumulative handoff, and retained final-tree evidence
agree.

This is approval of the local remediation carrier, not authorization to
publish it directly. The tree is still uncommitted, the package version remains
`0.10.3`, and clean-SHA release, semantic, repository-control, tag, artifact,
and publication gates remain mandatory. Cybersecurity review was explicitly
outside this engagement.

## Reviewed identity and frozen carrier

- Branch: `main`
- Base/current `HEAD`: `d52e32114eb0b4ef63499e53be14b70dc0864487`
- Base-relative binary tracked patch: 1,005,065 bytes, SHA-256
  `ec26dab041a3ca49094ac16ec423d054f7fd2ae5db59330c4e22c61727dd9718`
- Canonical fixed-12 `alice-v0.10.4-remediation-bundle-v1` manifest:
  1,721 bytes / 16 lines, SHA-256
  `7bc73afa88094d75ee2ad6b62566e5a77acdc26a844dcb4207072d3bd0304c08`
- Self-excluded builder report SHA-256:
  `d77165cac3e8c4d9986b8d8f98ddd141055d995902435006918434329047c177`
- Pre-review expanded status: 101 modified, 15 untracked, 0 deleted,
  0 staged; status-manifest SHA-256
  `94196e4abdcc778aefde99c138b490d7d5971aae7cc275be78f93683758f464b`

The fixed manifest excludes this reviewer-owned report, the self-referential
builder report, and the pre-existing user-owned `coverage.json` and `uv.lock`.
The reviewer changed no production code, tests, existing documentation, Git
state, or user-owned file.

## Findings

### P1

None.

### P2

None.

### P3

None.

## Batch 14 finding closure

### 1. String-only open-loop row metadata — closed

SQLite and PostgreSQL now admit root `metadata_json.next_action` and nested
`metadata_json.agentic_memory.next_action` as row-match candidates only when
the selected JSON value is a string:

- SQLite guards each path with `json_type(...)= 'text'` before applying the
  ASCII-folded literal substring predicate.
- PostgreSQL guards each path with `jsonb_typeof(...)= 'string'` before
  extracting its text.
- `FakeVNextMCPStore` applies the same scalar-string requirement to both
  direct open-loop reads and the row portion of loop-event reads.

Integers, objects, arrays, booleans, nulls, and their keys therefore cannot
match through the two row metadata fields. Title and description remain
ordinary string fields.

Loop-event payload behavior remains deliberately different from row metadata:
each recursive JSON string leaf is independently eligible. Nested object and
array strings match, but keys, non-string values, JSON serialization, and text
split across separate leaves do not. The same ASCII-only case folding, exact
non-ASCII behavior, and literal `%`, `_`, and backslash handling remains in
SQLite, PostgreSQL, and the fake. Scoped and unscoped calls, blank queries,
status/time/scope admission before limits, scalar positives, and queryless
behavior were preserved.

### 2. MCP documentation scope — closed

`docs/alpha/mcp-tools.md` now states explicitly that:

- row `next_action` metadata participates only when its JSON value is a
  string;
- event matching is per recursive string leaf; and
- the ASCII-case-insensitive literal substring, exact non-ASCII, and literal
  SQL-wildcard-character contract applies only to open-loop row fields and
  loop-event string leaves.

The document separately states that decision/next-action memory search retains
its memory-store matching contract. It no longer promises the open-loop
comparison rule for memory search.

The new control-document regression requires all four distinguishing phrases.
The historical Batch 14 wording satisfies none of those assertions, so the
test is fail-on-old rather than a generic documentation-presence check.

### 3. Open-loop ordering parity — closed

`FakeVNextMCPStore.list_open_loops` now sorts before applying the limit by:

1. `opened_at DESC`;
2. `created_at DESC`; and
3. `id DESC`.

This matches both production stores. The equal-`opened_at` regression proves
that a newer `created_at` wins before identifier ordering and that `limit=1`
is applied only after the complete order. Independent direct SQLite and
rollback-only PostgreSQL probes returned the expected newer row, followed by
the identifier tie-break. Loop-event ordering remains
`occurred_at DESC, id DESC` in all three implementations.

## Independent focused verification

| Check | Result |
| --- | --- |
| Five Batch 15 closure units | **5 passed** |
| Complete owned MCP/store seam | **339 passed** |
| Complete affected PostgreSQL file | **10 passed** |
| Focused live role-separated PostgreSQL semantic case | **PASS** |
| Direct SQLite equal-`opened_at` order probe | **PASS**: newer `created_at`, then `id` |
| Rollback-only PostgreSQL equal-`opened_at` order probe | **PASS**: newer `created_at`, then `id` |
| MCP documentation fail-on-old control | **1 passed** |
| Complete control-document test file | **44 passed** |
| Control-document truth checker | **PASS**, 14 documents |
| `git diff --check` | **PASS** |

The focused tests exercise root and nested string positives; integer, object,
and array row negatives; nested and array event-leaf positives; key,
non-string, and cross-leaf negatives; scoped and unscoped reads; blank/queryless
compatibility; and predicates and ordering before limits. SQL-shape assertions
also require the JSON type guards to precede text matching in both row and
event queries.

## Recorded final-tree evidence validation

The full 8+ minute Python/PostgreSQL matrix was not rerun during this closure
review. Its evidence was accepted only after independently binding it to the
exact frozen carrier and corroborating the affected surfaces proportionally:

- test collection reproduces exactly 3,331 unit tests and 461 integration
  tests, matching the recorded 3,792-test matrix;
- the retained final Batch 15 coverage receipt reproduces 40,520/51,557
  covered statements, 8,974/13,804 covered branches, and combined
  branch-aware coverage of 49,494/65,361 (75.7241%);
- `main.py` reproduces 3,775/6,899 covered statements (54.7181%) and
  4,126/7,839 branch-aware elements (52.6343%), above the 45% floor;
- release-static, Ruff, formatting, compilation, release-check, and mypy over
  146 files are recorded green and were corroborated by the static/control
  lane;
- LongMemEval is recorded at 127 passing tests plus seven-arm evidence replay;
  its 892-row baseline remains SHA-256
  `027db2960a761d44bb3b20e9ed04a5f434a16d88a3ff9cf65b43a64a3b96589f`;
- the unchanged 202-input web carrier remains
  `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`,
  with base-relative web diff
  `df3f667a4e06be6a998478a5a4b4ee0af4a2f27b4cbe7b516b7a80b85aa1e0d4`
  and lockfile
  `f684d9f418db5b6b52964cdafdf27ab326aa68b777c5fc1a7b90dc4f7a4206d9`;
  the prior web suite is explicitly carried, not represented as rerun; and
- the retained primary and reproducibility package builds are byte-identical.
  The 1,224,931-byte wheel is
  `8fd31e9cb289da7b85389201eecfa1160f5e8ca2afd6abca6dc18eb7e838b407`;
  the 1,071,126-byte normalized sdist is
  `263666ccc16faced4a54f270edefc17359c8dad128414220342ecd776f28f2a6`.
  Twine, distribution release-check, seven-file workspace/archive parity,
  archive exclusions, and isolated wheel/sdist smokes are green.

These package files are dirty-tree verification artifacts for version
`0.10.3`; they are not the future publishable v0.10.4 bytes.

## Preservation readback

- `CURRENT_STATE.md` and `.ai/handoff/CURRENT_STATE.md` are byte-identical at
  SHA-256
  `85caec77fedea80a9281c366c613a42ebf578e6bc1027409503649b7b8aed225`.
- Pre-existing `coverage.json` remains
  `57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711`.
- Pre-existing `uv.lock` remains
  `65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52`.
- Immutable v0.10.3 release notes remain
  `463a6b0d4a54b23a577126ce17202736f0aeeebcb2a5ee314416ed5283415938`.
- Immutable v0.10.3 checksums remain
  `57e4cc30bbbb9c7438b54954fecb4fdd88f15d0f2874e62ea66faa45612a6387`.
- Repository `dist/` was not used for or modified by the Batch 15 package
  verification.

## Residual limitations and release-engineer gates

- The deterministic ASCII/literal comparator is intentionally scoped to
  open-loop row fields and loop-event string leaves. Memory search retains its
  existing store-specific comparison behavior; this review does not broaden
  that contract.
- The exact accepted carrier is still an uncommitted dirty working tree on a
  v0.10.3 base. It is not itself a release identity.
- No version finalization, clean candidate commit, protected tag, GitHub
  Release, PyPI publication, or post-publication receipt was performed.
- The release engineer must establish one clean candidate SHA, finalize the
  v0.10.4 version and release documents, and rerun the prescribed exact-SHA
  static, role-separated PostgreSQL/pgvector, LongMemEval, web, reproducible
  package, installed-artifact, and release-finalization checks.
- The production-compatible semantic-vector gate must run for that same SHA
  with the configured provider and PostgreSQL/pgvector environment. Required
  repository-control attestations and external GitHub/PyPI readbacks must also
  be current for that exact release identity.
- Cybersecurity assessment remained out of scope.

Subject to those external and exact-SHA gates, the Batch 15 remediation is
approved for main-engineer release finalization.
