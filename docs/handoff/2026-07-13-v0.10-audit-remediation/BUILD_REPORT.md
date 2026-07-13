# Alice v0.10.0 Audit Remediation Build Report

> **Bounded repair pass 6 implemented and locally verified.** The fifth
> independent acceptance closed every pass-5 report, MCP, browser, HTTP, and
> web residual, then found that publication no longer required its independent
> repository-control declaration and that five boolean/integer/float
> substitutions survived semantic attestation copy checks. Pass 6 restores the
> release-specific control boundary and strict JSON type fidelity. The sixth
> independent acceptance is now **PASS with no P0, P1, or P2 finding**;
> `REVIEW_REPORT.md` is the authoritative verdict.

Review history remains explicit: each of the first five acceptance passes
returned REJECT with bounded residuals, and the sixth pass accepted the frozen
pass-6 tree. The final PASS closes code review only, not the external
publication procedure.

## Identity and scope

- Baseline: `68d6bf2f3e76425f5cbd13a73411a3231dffba02`
- Working branch: `codex/v0.10-audit-remediation`
- Published baseline: immutable `v0.9.4` at `e0561f3`
- Scope: correctness, reliability, performance, typing, web, backup,
  packaging, documentation, tests, and maintainability
- Explicit exclusion: cybersecurity audit
- External actions: none; no commit, push, merge, tag, release, or publication

## Builder architecture

The root agent is the control tower. A lead builder integrates specialist
lanes for embeddings/release, retrieval/performance, capture/contracts,
lifecycle/migrations, consolidation/rollups, web quality, backup/restore, and
documentation. An independent reviewer receives the completed shared tree and
owns `REVIEW_REPORT.md`; builder results are not self-approval. The final sixth
review has now supplied that independent acceptance.

## Implemented so far

### Backup and restore

- Import snapshots the selected JSONL from one stable file handle into a
  private owner-only file before validation.
- Validation decodes each JSONL envelope once into an owner-only, disk-backed
  FK-ordered spool; it does not retain the complete decoded graph in memory.
- Export ignores SQLite-reserved `sqlite_stat*` tables created by `ANALYZE`,
  while still rejecting unknown application tables and columns.
- The backup guide documents immutable input, single decoding, fail-closed
  future-schema behavior, and the existing quiesce-writer contract.

### Signed embeddings and release evidence

- One v2 writer contract now supplies a finite padded vector plus provider,
  model, canonical endpoint fingerprint, content digest, and signature version
  to CLI, SQLite onramp, eval, and scale callers.
- Endpoint identity normalizes scheme/host/default ports without folding
  case-sensitive path or query text; NaN/infinity fail before persistence.
- Failed backfills and any skipped release suite exit nonzero. Backfills select
  provider/model/endpoint/version mismatches and content-digest-stale vectors.
  Configured evals
  persist product-usable signed vectors and require positive vector candidates
  on every query.
- Installer, doctor, integration CI, and semantic gate require pgvector 0.8+.
- A dedicated protected-environment workflow produces a credential-free,
  exact-SHA semantic report/attestation. Publish resolves the successful run,
  downloads the SHA-named artifact, and validates report digest, complete suite
  execution, Postgres backend, vector participation, quality targets, and SHA.
- Publication also requires a separate structured repository-control
  attestation. Its closed credentialless JSON binds the exact repository,
  release SHA/tag, canonical UTC freshness/expiry, and affirmative readback of
  every documented environment, branch, tag, release, trusted-publishing,
  credential, and exact-SHA control. The semantic artifact cannot satisfy this
  gate and the control declaration cannot satisfy the semantic gate.
- The report now derives canonical suite order/titles, all 78 ordered case
  identities, exact query/target linkage, acceptance targets/checks, known
  corpus digests, and the complete nested contract directly from the six
  production corpus generators. Suite/case metrics and evidence, retrieval
  subsets/latencies/seeding, graph ranks, and control objects are recursively
  closed and typed; numeric values must be finite and non-boolean. Rank-derived
  case metrics and suite/subset aggregates reconcile with evidence. Executed/
  skipped and pass/fail counts, pass rate, six-suite Postgres backend evidence,
  and aggregate status are derived from actual cases. The canonical
  `sha256:<hex>` digest binds every semantic report field except wall-clock time
  and itself; the attestation's separate bare hash binds report bytes. Report/
  seeding signatures must match, and credential-bearing keys and values are
  rejected without echoing them. A no-provider run fails for missing configured
  semantic evidence without a spurious digest mismatch. Attestation-to-report
  copies use recursive type-sensitive equality; the positive integer vector
  count, exactly-true participation flag, and finite 0..1 float paraphrase
  recall also have independent shape validators.

### Documentation truth

- Active control docs now say v0.9.4 attempted, but did not prove closure of,
  the audit remediation.
- They no longer claim v0.9.4 passed a configured semantic-vector release gate.
- The active sprint packet describes the v0.10.0 remediation boundary.
- Release, vNext, Ubuntu, and integration guides point to the current published
  baseline and the unpublished v0.10.0 candidate.
- README links are absolute repository URLs so installed PyPI metadata does
  not route them under the PyPI project path.

### Python type contracts

- The first builder's `--follow-imports=skip` result was rejected after normal
  mypy exposed 262 errors in seven files. Shared psycopg row contracts and HTTP
  payload conversions were repaired; normal cross-module mypy now reports zero
  errors over 133 production/release-tool files in both Makefile and CI.
- The repair uses concrete TypedDict/Literal/protocol contracts, JSON boundary
  narrowing, optional-field handling, and private psycopg row adapters. No
  blanket `Any`, ignore, exclusion, disabled error code, or configuration
  weakening was added.

### Lifecycle and migration correctness

- Supersession traversal rejects repeated, malformed, depth-exhausted, and
  dangling chains instead of attaching to an unverifiable graph.
- The per-user graph advisory lock is acquired before candidate/member row
  locks across HTTP, MCP, CLI, and direct confirm/undo/correct/forget/
  accept/expire/unexpire/transition paths.
- Successors must be valid lifecycle heads; unexpire responses match stored
  state; expired confirmations append durable revision/event evidence; review
  accept/edit/promote actions close nested confirmation as `confirmed` with a
  timestamp, while reject closes it as `rejected` with its terminal timestamp,
  across both MCP and generic HTTP routes.
- Published migration 0084 is restored byte-for-byte. New idempotent migration
  0086, after 0085, repairs every stale pointer in duplicate groups larger
  than two for databases already stamped at the released 0084 state.

### Retrieval and graph performance

- Bundled stores apply project/people/time constraints before `LIMIT` for
  memories, source chunks, source titles, provenance sources, graph results,
  and open loops. Legacy adapters deduplicate, detect non-progress/exhaustion,
  and fail closed at 16,384 rows instead of doubling forever.
- Query vectors are computed once per request and reused across deepening.
- Entity edges, memories, provenance links, and sources have bulk read paths;
  optional capability detection preserves older adapters.
- A rank-4,002 row is recovered, 251 entity edges use two bulk reads, and 40
  provenance targets use two bulk reads. Live PostgreSQL tests also prove a
  matching row behind 4,001 decoys survives combined people/time predicates
  and all 251 person edges resolve.

### Capture and public contracts

- Candidate and source dedupe are exact on text, live status, project scope,
  domain, and sensitivity; identical text/project recaptured with a new
  classification preserves the new source and candidate on both stores.
  Stable public content hashes and exact raw-text SHA-256 values
  are separate from the internal scoped dedupe key, with legacy compatibility.
- Migration 0085 and both bundled stores atomically claim a live source
  identity. Real two-connection SQLite and PostgreSQL regressions return one
  source ID and exactly one creator.
- Agent-output scope plus agent/run attribution propagate to durable rows;
  SQLite upgrades repair historical attribution.
- HTTP enums fail as 422. Every nested MCP object/array schema is closed and
  enforced recursively for unions/null, scalar and container types, enums,
  UUID/date-time/full-date formats, bounds, patterns, item schemas, and
  cardinality. Full dates require real calendar dates; unsupported advertised
  formats fail closed.
  Core and legacy correction confidence/replacement-confidence fields now
  explicitly enforce finite numeric 0..1 bounds before handlers; invalid
  inputs leave memory, revision, provenance, and handler state unchanged.
  Provenance source/chunk ownership, role, confidence, and quote type validate
  atomically before mutation. Documented `alice_recall` thread/task/project/
  person/since/until scopes are restored end-to-end.

### Consolidation and rollups

- Authoritative membership counts are separate from bounded display input;
  cards disclose truncation and model summaries refuse full-group claims.
- Complete-link/all-pairs cohesion replaces bridge-prone single linkage.
- Float32 blockwise similarity and silhouette work replace dense matrices;
  the 2,000-row cap uses a roughly 1 MB temporary block rather than a 16 MB
  dense similarity matrix.
- Exact embedding presence precedes provider calls; consolidation embeddings
  are cached and reused by semantic rollups.

### Web correctness and release gates

- Assistant and governed-request drafts are keyed to the selected thread and
  reset on navigation. Independent reads execute concurrently. Fixture-backed
  outage displays are read-only; existing-object mutations require successful
  live list/detail provenance and can never submit fixture IDs to live APIs.
- Chat, continuity, and vNext now provide route loading boundaries. Landmark,
  heading, skip-link, `aria-current`, and related accessibility defects were
  corrected and are checked with axe in a real browser.
- Full TypeScript moved from 69 errors to zero. CI now runs typecheck, core and
  stable per-file-threshold vNext coverage shards, production build, gzip
  bundle budgets, and Playwright navigation/a11y/configured-outage gates.
- Clean local setup now exposes idempotent `make setup-browser`, which installs
  Playwright-managed Chromium without the Linux-only `--with-deps` package
  step. `test-web` declares that prerequisite. Clean Debian/Ubuntu operators
  can explicitly select guarded `make setup-browser-linux`; Linux CI shares
  that package script, and the target refuses to run on macOS.
- The 4,590-line vNext workspace was reduced by 27.2% to a 3,342-line
  orchestrator, with a 1,281-line model module and 65-line overview module
  extracted as the first responsibility split.
- The stable vNext shard now executes capture, review acceptance, artifact,
  scheduler, connector, and charter handlers. The orchestrator records 63.93%
  lines/statements, 42.85% branches, and 14.42% functions under a nonzero 10%
  per-file function floor. A live queue target remains correction-capable when
  only detail/history fails; fixture-derived IDs remain read-only.

### Release engineering and package truth

- Release-note/checksum state is exactly one strict JSON declaration on line 2
  immediately after the exact title. Fenced, duplicate, misplaced, malformed,
  and inconsistent declarations are rejected.
- Exact-SHA required checks are parsed from current workflow job display names,
  preventing script/workflow name drift from blocking or bypassing publication.
- Active release, vNext, Ubuntu, integration, architecture, product, roadmap,
  sprint, and handoff documents now agree on the immutable v0.9.4 baseline and
  unpublished v0.10.0 remediation candidate.
- An isolated pass-5 package build produced both 0.10.0 wheel and sdist outside
  the worktree. Twine, release metadata, and fresh installed-artifact smokes
  pass for both formats. The wheel was 1,110,095 bytes with local SHA-256
  `ace3010422593cb9d06f5ba0aa3ad2205b83ac39f79df017b7a5897d3c4e4c42`;
  the sdist was 971,376 bytes with local SHA-256
  `0726b2d728f5deb2bcbc717d2517f7a115a3b4a0bedc3e5c1a1ffcc7fe85a37b`.
  These hashes identify only this dirty-tree verification build, not a release:
  the final workflow must checksum and attest the exact artifacts built from
  the reviewed clean candidate SHA. Tests and `docs/handoff/` are not sdist
  members.
- A fresh isolated pass-6 build produced a 1,110,095-byte wheel with SHA-256
  `77e494f17643e94c76a12f2cda9df97a21092d0603fc9928154f6999cff16fb5`
  and a 971,417-byte sdist with SHA-256
  `bfb9a23313ee2286a3de4cff2718b8f86b848bd76581c26ddeea76517c164775`.
  Twine, repository release validation, and installed-artifact smokes passed
  for both. Wheel METADATA and sdist PKG-INFO each contain 28 Markdown targets
  and zero relative targets. These remain local dirty-tree evidence, not
  publishable release artifacts.

## Verification evidence

| Command | Result |
|---|---|
| `./.venv/bin/python -m pytest tests/unit/test_sqlite_onramp.py -q` | 112 passed; 50k-record spool peak 43,259 bytes |
| Lifecycle/migration/lock-order focused unit slice | 120 passed |
| Real PostgreSQL released-0084 upgrade + lifecycle/candidate/member races | 11 passed; published 0084 byte comparison clean |
| Scoped lifecycle Ruff + compile check | passed |
| Retrieval/store/SQLite/stability/grounding/reranker focused suite | 361 passed |
| Live PostgreSQL rank-4,002, 251-edge, and 420-decoy source/title/open-loop regressions | 3 passed |
| Capture/SQLite contract focused suite | 135 passed |
| Real PostgreSQL capture dedupe/reclassification | 2 passed |
| MCP nested-schema/provenance/scoped-recall units | 94 passed |
| Real PostgreSQL MCP parity/server/provenance/all-scope suites | 10 passed |
| Full sequential PostgreSQL integration suite (CI order) after repair pass 3 | 418 passed in 997.89 seconds; zero failures |
| Previously failing shared MCP/onramp assertions after integration | 3 passed |
| Consolidation/rollup/store/MCP/scheduler focused suite | 213 passed |
| README relative-link scan | zero relative Markdown links |
| `./.venv/bin/python scripts/check_control_doc_truth.py` | passed |
| Embedding/eval/release focused pytest batches | 274 passed; final boundary slice 147 passed |
| Repair-pass-5 full release/eval files | 113 passed; producer-owned real 78-case report validates, writes an attestation, and validates the artifact; canonical/nested/type drift, numeric-bool equivalence, fabricated evidence, and provider-free false-digest paths reject |
| Repair-pass-5 fresh-digest malformed semantic matrix | 21 passed; fourth-review nested mutations plus bool/NaN/infinity and aggregate/rank drift reject |
| Repair-pass-6 semantic report/attestation files | 131 passed; all five fifth-review bool/int/float substitutions reject; 102/102 recursive copied-field/node type drifts reject; positive six-suite/78-case report -> attest -> validate roundtrip passes |
| Repair-pass-6 repository-control/workflow/control-doc/GitHub-check slice | 88 passed; missing/malformed/stale/future/expired, wrong repository/SHA/tag, duplicate/unknown/missing keys, every false/non-bool control, gate substitution, and executable-doc contract drift reject |
| Independent pass-6 repository-control mutation sweep | 155 mutations rejected, zero accepted and zero crashes |
| Release lane Ruff, release-tool mypy, installer `bash -n`, workflow YAML parse | passed |
| `python scripts/release_check.py` | passed for development version 0.10.0 |
| Normal cross-module mypy, production + release tools | success, 0 errors in 133 files; no `--follow-imports=skip` |
| Package Ruff after typing cleanup | passed |
| SQLite scale smoke (`--scales 100 --iterations 2`, results under `/tmp`) | passed; 100 seeded at 262/s; recall p50 38.151 ms / p95 41.169 ms; all eight operations within budget |
| Full Python unit suite with coverage after repair pass 3 | 2,497 passed in 101.24 seconds; 69.47% total coverage (50% gate) |
| LongMemEval suite | 127 passed in 14.94 seconds |
| `scripts/check_longmemeval_evidence.py` | PASS; 7 arms, baseline evidence found |
| Full web unit suite after repair pass 3 | 66 files, 252 passed |
| Core web coverage suite after repair pass 3 | 63 files, 239 passed; 83.16% lines/statements, 72.08% branches, 85.68% functions |
| Repair-pass-3 MCP schema units / PostgreSQL parity+rollback | 130 units + 8 PG parity/server tests passed; invalid calls leave memory/revisions/provenance unchanged |
| Repair-pass-5 MCP schema/date/confidence | 184 MCP units; 58 focused date/confidence cases; 8 durable file-backed SQLite bool/NaN/+Inf/-Inf edit/replacement rollbacks; 1 PostgreSQL atomic edit/replacement rollback passed; valid dates and 0/1 boundaries accepted; scoped Ruff/mypy/diff green |
| Repair-pass-3 HTTP review lifecycle | 41 full vNext-main units + 5 ASGI/PostgreSQL action/row-to-graph tests passed |
| Stable vNext coverage shard | 4 behavioral tests; orchestrator 63.93% lines/statements, 42.85% branches, 14.42% functions; hard 60/40/10/60 per-file thresholds pass |
| Web typecheck / lint / production build | passed; 0 type errors; 19 pages built |
| Playwright navigation, axe, configured-live full/partial outage | 8/8 passed; fixture IDs remain blocked and live-queue/detail-503 correction posts only the live ID |
| Clean-machine browser bootstrap | `make setup-browser` passed; Linux-only target rejected macOS as designed; 9 static release-polish tests, 19-route production build, and full 8/8 Chromium tests passed |
| Gzip bundle budgets | passed: `/` 106,168/120,000; chat 124,178/140,000; continuity 113,696/130,000; vNext 137,266/155,000 bytes |
| `make release-static` | passed; control docs, release metadata, Ruff, and mypy over 133 files |
| Repaired-tree wheel + sdist / Twine / both artifact smokes | passed for `alice-memory 0.10.0`; 27 Markdown targets in each packaged README surface, zero relative |
| Repair-pass-5 isolated package revalidation | `uv build` produced wheel+sdist outside the worktree; Twine, repository `--dist-dir` release check, and fresh-install smokes for both artifacts passed; wheel METADATA and sdist PKG-INFO each contain 27 Markdown targets and zero relative links |
| Repair-pass-5 final integration | `make release-static`, control-doc truth, release metadata, Ruff, mypy over 133 files, workflow YAML/web-package JSON parse, and `git diff --check` passed; browser lane unchanged and not rerun |
| Repair-pass-6 final static integration | `make release-static`, control-doc truth, release metadata, Ruff, mypy over 134 files, publish-workflow YAML parse, and `git diff --check` passed |
| Repair-pass-6 isolated package revalidation | wheel+sdist build, Twine, repository `--dist-dir` release check, and installed-artifact smokes passed; 28 Markdown targets per metadata surface and zero relative links; exact local hashes recorded above |
| Sixth independent acceptance | **PASS**, no P0/P1/P2; 219 affected tests, 157 adversarial control claims rejected with only two valid boundary claims accepted, 18 workflow assertions, semantic drift matrices, release-static, YAML, and diff checks independently verified; see `REVIEW_REPORT.md` |
| No-provider `eval run --suite all --release-gate` | correctly failed closed, exit 1; 6/6 suites executed, 78 cases, 65 pass/13 fail, signature null |
| Desloppify pass-5 full-profile scan | overall/strict 34.3; objective/verified 85.6; code 83.7, file 80.6, duplication 99.5, test 73.6, security 95.9 reduced-confidence mechanical inventory |

The first pass-3 full-unit run exposed two stale expectations that still sent
now-invalid MCP enum values and expected the old downstream handler/SQLite
errors. Production behavior was correct: recursive schema validation rejected
both before mutation. The fixtures were updated to assert that stronger public
boundary, the exact pair passed, and the complete rerun produced the 2,497-test
green result above.

## Final gate state

The repair-pass-3 full-tree gate remains the broad baseline: 2,497 units with
coverage, 418 sequential PostgreSQL integrations, LongMemEval/evidence, scale,
all web gates, Ruff/mypy, package/Twine/installed-artifact checks, control-doc
truth, release-static, and the post-change Desloppify inventory. Pass 4 changed
semantic release evidence, MCP confidence schemas/tests, and browser setup plus
their documentation; those exact release/eval, MCP, package, browser, static,
and documentation gates were rerun. The fourth reviewer independently accepted
the browser lane, then required the pass-5 semantic nested contract, MCP full-
date enforcement, and durable special-value confidence regressions. Their
release/eval, MCP, package, static, documentation, and diff gates were rerun;
browser code was unaffected and its tests were not repeated in pass 5. J1 and
J2 are closed locally. The fifth reviewer accepted those pass-5 lanes and
required only the pass-6 control-attestation and semantic-copy repairs. Pass 6
reruns those affected release, workflow, documentation, package, static, and
diff surfaces; it does not claim a fresh broad-tree run. Builder evidence is
not self-approval. The sixth reviewer independently accepted this frozen tree
with no P0, P1, or P2 finding; `REVIEW_REPORT.md` supersedes the former pending
state.

Four publication gates remain intentionally outside builder authority:

1. commit the accepted dirty tree and establish one clean candidate SHA;
2. pass the complete required CI/check set on that exact SHA;
3. perform fresh external control readback and provide the structured
   `ALICE_RELEASE_CONTROLS_ATTESTATION` for the repository, clean release SHA,
   and stable tag; and
4. produce and inspect a configured exact-SHA semantic report/attestation from
   the protected `semantic-release` environment for that same SHA.

The Desloppify full-profile scan used isolated state under `/tmp`. Scores were:
overall 34.3, objective 85.6, strict 34.3, and verified 85.6. Mechanical
dimensions were code quality 83.7, file health 80.6, duplication 99.5,
test health 73.6, and security 95.9 (a reduced-confidence mechanical signal;
Bandit was unavailable and no cybersecurity audit was performed). The 20
unassessed subjective placeholders were each 0: abstraction fit, AI-generated
debt, API coherence, auth consistency, contracts, convention drift,
cross-module architecture, dependency health, design coherence, error
consistency, high/mid/low elegance, stale migration, initialization coupling,
logic clarity, naming quality, structure navigation, test strategy, and type
safety. These placeholders must not be presented as negative judgments or as
an independently reviewed code-quality verdict.

The fresh isolated scan recorded 1,256 in-scope open findings across 613 files
(about 303K lines). Bandit was unavailable and `jscpd`'s boilerplate pass
errored; the standard duplication detector still completed. These scanner
caveats do not change the release-test verdict and are not a cybersecurity
assessment.

## Honest limitations

The configured semantic release gate needs the protected `semantic-release`
environment and operator-supplied provider configuration. The branch fails
closed in their absence; a local deterministic provider validates plumbing but
cannot be represented as public release evidence. The workflow has not been
dispatched for the eventual exact clean candidate SHA, so this report is not
release approval.

The repository-control gate is an operator readback declaration, not
authenticated live GitHub-settings introspection. Pass 6 improves the baseline
permanent `v1` flag by binding a closed credentialless claim to the exact
repository/SHA/tag and a maximum 24-hour validity window. The operator must
still perform the documented readback truthfully and replace or remove the
variable whenever control state changes.
