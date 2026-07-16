# Alice v0.11.1 Phase 2 Independent Review Report

## Verdict

**APPROVED** for Phase 2 handoff to the release engineer.

The exact frozen, uncommitted carrier below closes the bounded Phase 2 debt
sweep without starting Phase 3. The implementation, fail-on-old coverage,
cross-store behavior, documentation truth, package evidence, and handoff
controls were reviewed independently. No remaining code, test, documentation,
package, or handoff blocker was found.

This approves the carrier for release-engineer verification. It does not
authorize a commit, merge, tag, GitHub Release, PyPI upload, repository-setting
mutation, or claim that the external exact-SHA gates have passed.

No cybersecurity audit was performed, as requested. The response-hygiene
CodeQL count and dependency-advisory runs are narrow release measurements, not
a security assessment.

## Reviewed carrier

```text
format:                    alice-v0.11.1-phase2-carrier-v1
base:                      5f0a92d77d02b0699af3054fced7427929808aa8
base tree:                 560bade5b9ad20c659f03f19693288558c706945
branch:                    codex/v0111-phase2-debt-sweep
tracked paths:             148
untracked before review:   22
selected before review:    170
selected exclusions:       3
included/present paths:    167
deleted paths:             0
content bytes:             7,378,573
manifest bytes:            25,366
sha256:                    ed36cd71c8986ecda0b7b7f43bd2e9bdb9e4de35980de327dd7fd576f5a2c296
```

The manifest was reconstructed independently in Python and Ruby by the package
and receipt lanes. I then reconstructed it independently from the live working
tree and obtained the same 167 entries, byte count, manifest length, and SHA-256.

The configured exclusions are exactly `coverage.json`, `uv.lock`,
`BUILD_REPORT.md`, and this reviewer-owned `REVIEW_REPORT.md`. Before this
report existed, three exclusions were selected. Adding this report makes the
working-tree selection 171 paths with 23 untracked paths and four selected
exclusions, while preserving the same 167-entry carrier receipt and digest.
Any later edit outside those four exclusions invalidates this approval.

The authoritative builder report is `BUILD_REPORT.md`, SHA-256
`79f3883978e403a875f83a723e3a290bae9ef193dc455b6b2b359001a7c772fe`.
The r5 carrier bind is
`94eb3e397c211020485ca73a97aee6d4a1b265aa789aed23695815bcfb947ec2`;
the fourteen-file documentation/control bind is
`b53a149df968abd4c85f565ae925fc343e6e063ecb8088eaf6d03dc3ea89d5a5`;
and the 233-file package-input bind is
`1a6b030e68185ab4d05184731dda97087eb8a6c3fe8e19afbc3c9fb15c21597c`.

All r2, r3, and r4 receipts and mixed-tree runs are superseded and invalid as
final evidence. In particular, r4 receipt
`4150240ea82ae0ab31e11895b61c76373c16e9005e78ad8fbed87eea65422ee9`
predates the final 3,547-test documentation-truth correction.

## Scope and correctness review

The review reconciled every brief item, 2.0 through 2.14, against production
callers, both stores where applicable, public adapters, tests, workflows, and
the final documentation:

- The default-surface, role-separated PostgreSQL smoke is a distinct required
  check and proves the 182-operation HTTP and eleven-tool MCP default surface
  through bootstrap, capture, review, recall, resume, and context-pack with all
  legacy/agent-key mount flags absent.
- HTTP, MCP, CLI, and onramp exception-backed failures use stable public
  contracts. Migrated provider, response, scheduler, evaluation, doctor, and
  connector diagnostics are static and keep specifics private. The intentional
  legacy-on proxy-execution business-result text is explicitly disclosed rather
  than misrepresented as part of that migrated diagnostic contract.
- The affected `list_memories(query=...)` and
  `list_resume_memory_events(query=...)` legs now share the open-loop ASCII
  literal-substring contract across PostgreSQL, SQLite, and fakes. Generic
  `search_memories` and `alice_recall` FTS/websearch retrieval remain separate.
- Terminal project-update replay uses one target-filtered store lookup with
  indexed linkage and stable full-row `UNION` set semantics. Reject validates
  its mandatory memory key before mutation, and generic HTTP/MCP/CLI lifecycle
  paths cannot strand a pending project-update candidate.
- The owner-selected Option A redaction path is atomic, replay-safe, and guarded
  against fabricated or partial marker states. Governed text and JSON content,
  digests, embeddings, fact keys, revisions, event payloads, quoted provenance,
  artifact content, and quality prose are scrubbed to their exact marker/null
  shapes. The docs now disclose the retained non-content classification,
  lifecycle, linkage, rating, and categorical-verbosity fields; source/source-
  chunk evidence; and already-applied project state. SQLite truthfully reports
  zero artifact/rating counts because it has no such repositories.
- Migration `0091` aligns CPython 3.12 whitespace and defensive vocabulary
  edges while adding bounded event linkage. Migration `0092` installs the
  coupled-redaction guards and role grants. Existing migrations through `0090`
  and immutable v0.10.x/v0.11.0 release records remain unchanged.
- Fake-store filter honesty, the coverage feature floor, mypy coverage,
  manual-only publish trigger, scheduler `--once` forwarding, evergreen readme
  pointer, and report-unignore behavior have fail-on-old tests.
- The response-generation trim preserves the retained provider-runtime path.
  The five empty web directories and upgrade riders were already closed in
  Phase 1. The removed entrypoint limiter leaves no Alice Redis client or reader,
  making the old shared-Redis flake obsolete.
- The fail-closed npm bulk-advisory wrapper remains the documented Node 20/pnpm
  10 path. The bounded pytest, redis-py, checkout, and CodeQL updates are in the
  carrier; incompatible major toolchain changes and GitHub PR closure remain
  separate release-engineer work.

Phase 3, roadmap features, hosted-offering work, publication, and security
review were not opened by this carrier.

## Independent verification

The final evidence reviewed and reproduced includes:

- **3,547 unit tests passed**; total coverage
  **79.40092486353048%** (37,119/45,062) and `main.py` coverage
  **62.95914864400961%** (3,342/5,110), above the 50% and 45% floors;
- control-document truth, release identity for 0.11.1, Ruff, mypy across 137
  source files, `compileall`, tracked diff hygiene, and all-untracked diff
  hygiene passed;
- the final focused control suite passed **79/79**, and the expanded
  release/control suite passed **231/231**;
- role-separated PostgreSQL 16.13/pgvector 0.8.2 passed **399** legacy-on
  integration tests with one intentional default-surface skip, while the
  separate flag-off smoke passed **1/1**;
- LongMemEval passed **127** tests, evidence replay passed all seven arms,
  focused vector contracts passed **2/2**, and all six provider-free SQLite
  evaluation suites passed all **78** cases in honest `fts_only` mode;
- the provider-free semantic gate correctly failed with 0/48 vector queries,
  proving that offline FTS evidence is not mislabeled as real vector
  attestation;
- web verification passed **217/217** unit tests, **20/20** browser tests,
  coverage floors, typecheck, lint, production build, and bundle budgets;
- the advisory response validator passed **5/5**, and live production/full
  bulk-advisory checks reported zero high-or-higher advisories for 55/525
  packages; and
- the isolated code-health scan was reported honestly as a range: overall
  34.3-34.4, objective 85.8-85.9, code quality 83.1 (82.9 strict), file health
  81.1 (80.8 strict), duplication 99.6, and test health 73.7-74.6. Its low
  overall presentation is dominated by unassessed subjective dimensions; the
  basename-only test mapping is nondeterministic.

The final control/doc count correction changed no production, migration,
integration, workflow, dependency, or package-input bytes. The prior
PostgreSQL, web, and focused migration evidence therefore remains applicable to
the final carrier. The full Python/static lane was rerun on the final bytes.

## Package verification

The authoritative evidence root is
`/private/tmp/alice-p2-package-final-r5.bOrBkB`. Two fresh isolated builds used
the same 233-file package-input bind. The wheel and normalized sdist compared
byte-identical across both builds:

```text
wheel bytes:       1,142,257
wheel sha256:      92124d23e95d0c8a56d16946115db6b577db64a026066ff6d08c61b619948a97
sdist bytes:       995,229
sdist sha256:      b128660dae91bbf8ac94afc1b99340c19c401bd2d4f1c8c14695219682e9a59c
SHA256SUMS bytes:  196
SHA256SUMS sha256: 6efdeb95cf208cd8abddf563a0348b38e6db5270800d6a66407faaf73a3f1525
```

Twine, `release_check.py --dist-dir`, checksum comparison/readback, and both
installed wheel/sdist smokes passed. Independent archive inspection confirmed
version 0.11.1, `redis>=5.0,<9.0`, migrations `0091` and `0092`, all four public
entrypoints, and installed Alembic head `20260716_0092`. A fresh resolver chose
Redis 8.0.1 and `pip check` passed.

## Protected state and residual debt

The Git index is empty. Nothing was committed, pushed, tagged, published, or
staged. Protected hashes remain:

```text
uv.lock:
65239f714c5a0fbccb1555f2270f08dc465671d2ddd71055ffb38582c23b8e52

coverage.json:
57ff783feb003358b0195b6b03538827a8efe73bfa9d79652b807e0ec501d711

apps/web/pnpm-lock.yaml:
c4cd48f582508459ca4927539bd5ae7c6976aa99a12201f588bf6a81669d86a3

migration 0092:
55424bba49bc61cf1107888d4a265d6bf3fac86a2c209b415243001aed75b232
```

Two unchanged private helpers remain confirmed repository-local dead code:
`main.py::_runtime_provider_config_or_none` (18 lines) and
`mcp_tools.py::_build_recall_query` (11 lines). They predate this carrier and
are nonblocking follow-up for the separately scoped structural split.

The health scan also lacked Bandit, saw jscpd fail, and left 20 subjective
dimensions unassessed. Those limitations prevent treating its overall number
as a security or holistic quality score; they do not invalidate the verified
release lanes above.

## Remaining release-engineer gates

The carrier is approved for handoff, but publication is not yet approved. The
release engineer must still:

1. commit and merge through the protected flow and identify the exact final SHA;
2. run and read back every required check on that SHA, including the separately
   named default-surface PostgreSQL job;
3. apply and verify the prepared MainProtect required-check update;
4. obtain target-zero CodeQL response-hygiene evidence on the committed SHA;
5. run the semantic release gate with the configured real embedding provider;
6. verify release identity, version, tag ancestry, final artifact checksums,
   and release-finalization controls against that exact SHA;
7. create the GitHub Release and publish to PyPI only after those gates pass,
   then read back both external states; and
8. close or supersede stale Dependabot PRs only after the merged carrier makes
   their disposition true.

Stop at this handoff. Phase 3 starts only under its own brief after v0.11.1 is
tagged and published.
