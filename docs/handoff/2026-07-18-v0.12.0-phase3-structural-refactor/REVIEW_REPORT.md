# Alice v0.12.0 Phase 3 Independent Review Report

**Structure only. Zero behavior change.**

## Verdict

**GO for release-engineer verification.** I found no remaining P0, P1, P2,
or P3 issue in the frozen Phase 3 carrier.

This is approval of the uncommitted structural carrier for the next protected
release-engineering steps. It is not approval to publish the candidate-version
artifacts, and it does not claim that exact-SHA CI, real-provider semantic
attestation, CodeQL, tagging, GitHub Release creation, or PyPI publication has
already happened.

No production or included control byte was changed by the final reviewer. This
report is the reviewer-owned exact receipt exclusion. I did not stage, commit,
push, tag, publish, mutate repository settings, invoke `uv`, or perform a
cybersecurity audit.

```text
base:            f342d45dabe127acca6231f29830ff11d98a340e
base tree:       1d84e26597aecfcd9ad894c6d0b86fbe9a66dfd6
branch:          codex/v0120-phase3-structural-refactor
target release:  v0.12.0
package version: 0.11.1
web version:     0.11.1
builder report:  sha256:484f175082d37264b4dfdf6c8d32251f43efc277949fa1527570d9f3f02efa31
```

The two governed versions intentionally remain at the published v0.11.1
baseline. The release engineer owns the single coordinated bump to 0.12.0
after committing and merging the reviewed carrier.

## Independent code review

I reviewed the final worktree against the published v0.11.1 base, not only the
builder narrative. The review covered the moved HTTP, store, contract, MCP, and
CLI surfaces; the migrated truth gates; packaging; active documentation; and
the complete final matrix readback.

Normalized AST comparison found the moved definitions semantically identical
to the base except for the mechanical wiring required by relocation:

- `main.py` plus `routers/` preserved the handler bodies; the one router-context
  adaptation is pinned by the route and OpenAPI guards.
- PostgreSQL store definitions matched the base; SQLite retained the paired
  shape with shared helper carriers. SQL-shape tests pin generated SQL text.
- The legacy-store and contract definitions matched their base definitions;
  only facade binding helpers were added.
- MCP definitions and dispatch ordering matched the base, including alias
  identity, late-bound test seams, exception ordering, and runtime gates.
- CLI definitions matched the base apart from the two required `__file__`
  depth compensations. Parser order, defaults, logger identity, annotations,
  monkeypatch forwarding, and the historical no-op module execution are
  explicitly guarded.

Runtime and structural readback confirmed:

- OpenAPI has 182 default operations and 231 gated operations, delta 49, with
  unique operation IDs and exact registered contracts.
- Response hygiene still accounts for exactly 296 public exception responses
  across the router manifest.
- MCP remains 11 core / 65 legacy / 76 total with agent-key suppression and
  legacy flags unchanged.
- CLI exports and all three console entrypoints remain stable.
- PostgreSQL and SQLite seams correspond file-for-file where parity is
  required, while the public store facades remain stable.
- No production Python file exceeds 4,000 lines. The largest is
  `vnext_retrieval.py` at 3,803 lines; the principal final facades are
  1,140 / 1,692 / 3,595 / 564 / 80 / 1,964 / 1,563 lines for `main.py`,
  `store.py`, `vnext_store.py`, `mcp_tools.py`, `cli`, `contracts.py`, and
  `sqlite_store.py` respectively.
- Immutable v0.10.x and v0.11.x release records are unchanged. Phase 4 and the
  security review remain out of scope.

## Final verification evidence

The final frozen-byte matrix is green:

```text
Python unit:                3,804 passed, 0 skipped
package coverage:           80.37778972842162% (floor 50%)
router aggregate coverage:  3,604 / 5,373 = 67.07612134747814% (floor 45%)
release-static:             PASS
Ruff / mypy / compileall:   PASS
focused docs/control:       100 passed
split/parity review batch:  218 passed independently
store/SQL parity guards:    763 passed
PostgreSQL legacy-on:       399 passed, 1 expected skip
PostgreSQL flag-off smoke:  1 passed with executed-test enforcement
LongMemEval:                127 passed
evidence replay:            7 arms checked
focused vector/quality:     2 passed
web unit:                   217 passed (202 core + 15 vNext)
web coverage:               89.55% core / 80.62% vNext
web type/lint/build/budget: PASS
browser matrix:             17 + 1 + 1 + 1 passed
```

The provider-free SQLite evaluation executed all six suites and 78 cases. It
reported aggregate pass with 65 case passes and 13 expected FTS-only
paraphrase misses. That is valid offline plumbing and negative-control
evidence, not a substitute for the real-provider semantic release gate.

Control-document truth, the exact `CURRENT_STATE.md` mirror, tracked and
untracked whitespace checks, protected-path guards, governed-version readback,
and an empty Git index all passed at final review.

## Reproducible package evidence

I independently built the frozen carrier from two byte-identical clean roots
using `SOURCE_DATE_EPOCH=1784214379`. After sdist normalization, both wheels and
both sdists matched byte-for-byte:

```text
wheel:  alice_memory-0.11.1-py3-none-any.whl
bytes:  1,239,866
sha256: f610189c3f53e39750f932774aef98d668e525d2d29844f748f38d96aaa7421d

sdist:  alice_memory-0.11.1.tar.gz
bytes:  1,045,629
sha256: a7197baec83af440bbbf8e07b9109a504b8c270002e591fb38f32e3b49c42188

SHA256SUMS bytes:  196
SHA256SUMS sha256: 42cb09d40a1f5d86b9da3621ff9b3afbfd2ab2db474c23125c9a22fdfbd7a2ba
```

`twine` and `release_check.py` passed for both roots. Exact wheel and sdist
install smokes passed the four help entrypoints, three version entrypoints,
installed API/CLI/parser/runner/MCP provenance, migration and fixture
inclusion, 11-tool MCP posture, SQLite commit-plus-recall flow, and explicit
`python -m alicebot_api.cli` no-op behavior with exit/stdout/stderr `0/0/0`.
Both archives contain all 18 CLI and 19 MCP carrier modules.

These are candidate-version verification artifacts at 0.11.1. They must not be
published as v0.12.0; the release engineer must rebuild and reverify after the
coordinated version cut.

## Carrier receipt

I independently implemented the documented NUL-delimited receipt in Python
and Ruby and compared both outputs to both builder manifests. All four files
were byte-identical before this report was authored:

```text
format:              alice-v0.12.0-phase3-structural-carrier-v1
tracked paths:       108
untracked paths:     122
selected paths:      230
selected exclusions: 3
included paths:      227
present paths:       226
deleted paths:       1
content bytes:       5,887,819
manifest bytes:      35,464
sha256:              fbee28353b24bc62f49bef52323af7c16b1366e52d9b4b6cc6786b0321a8ea96
```

After this reviewer-owned exact exclusion was created, the worktree gained one
untracked selected path and one selected exclusion; the included path set,
content count, manifest bytes, and receipt SHA remained identical. This proves
the reviewer report does not create a receipt loop.

Protected artifacts remain byte-identical to their recorded values:

```text
uv.lock:
65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52

coverage.json:
57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711

apps/web/pnpm-lock.yaml:
c4cd48f582508459ca4927539bd5ae7c6976aa99a12201f588bf6a81669d86a3
```

Any change outside the four exact receipt exclusions invalidates this verdict
and requires a fresh matrix bind and independent review.

## Superseded environment attempts

The evidence set does not hide environmental attempts that were not accepted
as proof:

- An initially concurrent vNext coverage run timed out; the exact clean rerun
  passed and is the authoritative result.
- Browser port binding was denied by the sandbox; the approved escalated rerun
  passed the complete browser matrix.
- Initial isolated package builds could not resolve pinned build dependencies
  under sandboxed DNS. The approved escalated builds succeeded in two clean
  roots and produced byte-identical artifacts.
- An initial source-copy attempt encountered a concurrently changing generated
  web coverage file. New clean roots excluded generated coverage/build output,
  compared byte-for-byte before build, and produced the authoritative package
  evidence above.

## Release-engineer gates and deferred work

Before publication, the release engineer must:

1. Verify this report and receipt, then commit and merge through the protected
   flow.
2. Run the full required matrix on the exact release SHA.
3. Complete the real-provider semantic/vector attestation and CodeQL readback.
4. Bump both governed version sources once from 0.11.1 to 0.12.0 and finalize
   the pending changelog/release notes.
5. Rebuild v0.12.0 wheel and sdist twice, compare, install-smoke, checksum, and
   validate those exact release artifacts.
6. Tag only the approved SHA, create the GitHub Release, publish to PyPI, and
   read back ancestry, assets, checksums, provenance, and package metadata.

The pre-existing MCP alias wording in `docs/alpha/mcp-tools.md` remains filed
for a later documentation-behavior correction. Phase 4 and the security review
remain separate future phases.
