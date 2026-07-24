# v0.14.0 Deployment Guide Fixes v4 Independent Review Report

## Verdict

- **Code carrier (frozen): GO.** The reviewed 28-path v4 carrier closes the five
  deployment-guide defects, the integrated Phase 5 guard deadlock, and the
  candidate-versus-published control-document conflict. It closes the v2 return
  corrections, removes the undeclared PyYAML dependency, and makes the
  base-tree proof respect a verified shallow checkout without weakening
  full-history enforcement.
- **Release: NO-GO until amended committed-SHA CI is green.** The current v4
  successor is an unstaged amendment over committed v3 SHA `87e1a10`. The new
  receipt cannot select the guard's integrated branch until release engineering
  amends that commit with the v4 bytes and report-hash trailers.
- **Open review findings:** none at P0, P1, P2, or P3.
- **Owner real-host evidence:** accepted on 2026-07-24 with 29 of 29 checks
  passing. The static deployment smoke intentionally retains
  `owner_real_host_deployment_receipt` as a configuration-only proof gap. That
  expected result does not reopen the owner gate.
- **Version state:** Python and web versions remain `0.13.1`. This carrier does
  not perform the separate `0.14.0` version cut, tag, publication, or external
  readback.

The supported security claim remains: automated security scanning and internal
adversarial review, findings triaged and fixed. This review grants no broader
assurance or certification.

## Carrier and receipt review

I independently reproduced the frozen v4 carrier identity:

- base commit:
  `b383f6e69896717dfb60b887747e304c33f70d5b`;
- base tree:
  `faec22103b6bdee8650513f0c4c6aa28b7e5b912`;
- receipt format:
  `alice-v0.14.0-deployment-guide-fixes-explicit-carrier-v1`;
- manifest: 28 unique, bytewise-sorted paths;
- serialized receipt: 5,068 bytes;
- carrier receipt SHA-256:
  `81e7b479f760fa3fcc1c3a32f3539f98019e6e992ac6815097b4cd0eec1f28a8`;
- builder report SHA-256:
  `8072a5e555cbfc1431d8571c8d19ad396d193687b467b1b700e744cfeb90090b`.

The receipt binds the base, base tree, file mode, entry kind, and content or
link-target hash for every listed path. Its only exclusions are the
builder-owned `BUILD_REPORT.md` and this reviewer-owned `REVIEW_REPORT.md`.
Those two reports are bound separately by the required commit-message hashes.

The successor guard preserves the historical Phase 5 receipt, lineage,
protected-path proof, and handoff bytes at their own carrier commit. It no
longer freezes every historical source and documentation byte forever. The new
guard independently binds this carrier and freezes this handoff after
integration while allowing later reviewed source changes.

## V2 return-review closure

I reviewed the exact v2 delta against the returned five-item correction list.
The migration change is documentation-only: its SQL body is byte-identical to
the preceding carrier. The other four requested edits are narrowly confined to
the protected-path attestation, seed-step symptom, full `--no-comments` scope,
and disaster-recovery paragraph break.

The migration rationale is consistent with the code and repository history.
Migration `0069` forced RLS on `artifact_quality_ratings`; migration `0093`
temporarily applies `NO FORCE` before its global dedupe and constraint build,
then restores `FORCE`. Alembic wraps that sequence in one PostgreSQL
transaction. No tag contains `0093`, and the latest published release remains
v0.13.1. For a database that already applied the old `0093` body, successful
creation of the global unique constraint proves that duplicate non-null
reviewer keys did not remain, while the final FORCE posture is unchanged.

During this refresh I found the same stale protected-path denial in the
engineer, builder, and preceding reviewer declarations. The
receipt-listed engineer declaration and excluded builder report were corrected
before the v2 freeze. This reviewer-owned report now records the same truthful
protected-path disposition.

## V3 committed-SHA CI closure

Committed v2 SHA `9979f58` imported `yaml` from
`tests/unit/test_least_privilege_deployment_workflow.py`. PyYAML is not declared
in `pyproject.toml`, while the affected CI jobs install exactly `.[dev]`.
Blocking imports of `yaml` reproduces the old module's collection failure with
`ModuleNotFoundError`.

The v3 receipt changes exactly that one test file. It now uses indentation-aware
raw-workflow helpers built from the standard library and imports only `pytest`,
which is declared in the `dev` extra. It does not use `importorskip` or a
dependency fallback. With `yaml` imports forcibly blocked, the v3 module still
loads all six tests.

The replacement keeps assertions scoped to the unique `ops-evidence` job and
named steps. It retains exact environment mappings, action pins, checkout
keys, root-credential confinement, role capabilities and probes, command
flags, lifecycle URL, and ordered upload paths. Duplicate blocks and mapping
keys fail closed. Its in-file mutation test proves that duplicate steps,
duplicate keys, and a valid-looking pin in a comment or another step cannot
satisfy the contract.

I additionally changed four workflow values in memory without editing the
carrier: an admin RLS capability, a root credential in an unprivileged step,
the executed-test requirement, and an upload path. Each corresponding semantic
test failed. The raw parser is therefore not relying on vacuous global
substring matches.

## V4 shallow-checkout CI closure

Committed v3 SHA `87e1a10` unconditionally resolved the recorded base tree
inside `test_deployment_fixes_base_version_and_protected_scope`. A depth-one
checkout contains the carrier commit but not base `b383f6e`, so the old
`git rev-parse BASE^{tree}` call exited `128` before the guard could apply its
existing verified-shallow policy.

The v4 receipt changes exactly one assertion in
`tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py`. Only the
base-tree lookup is now guarded by `_base_history_available()`. If the base is
missing, that helper still requires Git to report a shallow repository; a
missing base in a non-shallow checkout remains a hard failure. When history is
available, the exact recorded base tree remains mandatory.

Every following assertion remains unconditional: bytewise carrier-path
ordering; exclusion of both version sources, release documents, security
documents, and foreign handoffs; live Python/web version coherence; and the
shallow-safe HEAD-equals-base version pin. Receipt, report-trailer, claim,
integrated ancestry, exact-path, content-hash, and handoff-immutability checks
retain their existing mode-specific enforcement.

I forced `_base_history_available()` to return false in memory and ran the
complete protected-scope test under a Git-call spy. It passed, and the only Git
call was `rev-parse HEAD`. This proves that the base-object lookup alone is
skipped while the file and version assertions still execute.

## Independent review findings

### Identity bootstrap

The implementation uses option (a) from the brief. The manual guide and Ubuntu
installer now invoke the same `scripts/seed_local_user.py` helper. It requires
the migration DSN, validates the configured UUID, sets transaction-local
`app.current_user_id`, and performs the user upsert on that same transaction.
It does not fall back to the runtime DSN or change the bootstrap API's
unknown-user behavior.

The live fail-on-old test starts without the configured core user, confirms
that the supplied admin owns the forced-RLS `users` table, proves an unscoped
insert fails, runs the documented seed helper, and then completes workspace
bootstrap twice to prove idempotency.

### Backup and restore authority

The four operational identities now have distinct, checked responsibilities:

- `alicebot_admin` is a non-superuser without `CREATEDB`, `CREATEROLE`, or
  `BYPASSRLS`;
- `alicebot_app` is the non-superuser runtime identity;
- `alicebot_backup` is a non-superuser with `BYPASSRLS` and read-only object
  grants so forced-RLS tables can be dumped completely;
- `alicebot_drill` alone has `CREATEDB` for randomly named disposable
  databases and remains without superuser, role-creation, or RLS-bypass
  authority.

The documentation plainly describes both the backup role's data-reading power
and the lifecycle role's cluster-wide database-creation risk.

New dumps use `--no-comments`, and restore also uses `--no-comments` so older
archives do not replay extension comments through a non-owner. Compatible
`pgcrypto` and `vector` extensions are inherited from `template1`, where the
setup identity owns them.

The first complete live reviewer drill exposed one additional restore defect:
the archive's `ACL - SCHEMA public` entry could not be replayed by
`alicebot_admin` against a target schema owned by `alicebot_drill`. The final
repair now:

1. requires exactly one matching public-schema ACL entry and fails closed when
   it is absent or ambiguous;
2. removes only that entry through a private mode-`0600` restore list;
3. reconstructs explicit target-side public-schema grants for admin, app, and
   backup through the lifecycle identity;
4. retains table, sequence, and non-public-schema object ACL entries;
5. verifies direct app and backup schema grants plus restored object access;
6. forbids the broader `--no-acl` shortcut.

The corrected drill then passed independently. Its actual archive contained
zero comment entries, exactly one public-schema ACL, one application-schema
ACL, and 105 table ACLs. The filtered list removed only the public-schema ACL
and retained the other 106 ACL lines byte-for-byte.

### Diagnostics and cleanup

Subprocess failures emit bounded, credential-scrubbed diagnostics only to
stderr. Diagnostics, database URLs, credentials, fixture text, and local paths
remain outside the sanitized JSON evidence.

Database cleanup is attempted after both success and failure. Both live
review runs confirmed that no `alice_phase5_ops_*` database remained.

### Deployment and control-document truth

- `apps/web/.env.production.local` is ignored, while the tracked example
  remains visible and no tracked repository file is ignored.
- Runtime, recovery environment, PostgreSQL CA, and client CA paths now use
  persistent `/etc/alicebot` locations across the guide, examples, validators,
  tests, and service units.
- The deployment guide distinguishes the exact automated lifecycle role from
  a manual same-host peer-superuser procedure.
- The roadmap's latest-published statement now follows a validated structured
  publication record rather than a pending governed-version bump.
- No version source, release record, or `docs/security` evidence file changed.

## Validation

The full-suite and isolated-database results below are preserved evidence from
the preceding carrier. That evidence remains applicable because the returned
v2 delta changes four documentation/control prose regions and one migration
module docstring, with no SQL or runtime-code edit. Independent v2 refresh
verification added:

- exact live receipt reconstruction: 5,068 bytes and
  `54a1375bf095c6f02b2e819c6f4b529c873b1ee41d86cbce6533e86d726c8e0e`;
- focused migration, deployment, and ops suite: 120 passed;
- control-document suite: 82 passed;
- final handoff guard: 8 passed and 1 expected pre-integration skip;
- Ruff and `git diff --check`: passed.

Independent v3 refresh verification added:

- committed-v2 fail-on-old reproduction: exit 1 with
  `ModuleNotFoundError: No module named yaml`;
- dependency declaration: `pytest>=8.3,<10.0` is present in the installed
  `dev` extra; PyYAML remains intentionally undeclared;
- dependency-free target: 6 passed, including the in-file mutation guard;
- forced no-YAML collection: all 6 v3 tests loaded without a skip;
- independent semantic mutation probes: 4 of 4 rejected;
- exact live receipt reconstruction: 5,068 bytes and
  `ca82376dbe63ba6824bb879a57512779a52a6772288426a19df53c9e4f78f773`;
- frozen build report:
  `ae19c0baa830ad075b7ab89efb4a50686096aa74e1e434f0267332a614d8dc2c`;
- Ruff, Ruff formatting, and `git diff --check`: passed.

The broad local contract run produced 79 passed and 2 documented skips, plus
the expected new-receipt topology failure. That failure is not waived or called
green: HEAD is still committed v2 SHA `9979f58`, while the v3 receipt is only
in the dirty amendment. The guard accepts either an uncommitted carrier directly
on base or a receipt-trailed integrated carrier. Release engineering must amend
`9979f58` in place with the new trailers before the integrated branch and
committed-SHA CI become authoritative.

The control tower separately proved the exact candidate in the guard's
intended live-base mode without changing this worktree. It created a disposable
checkout at recorded base `b383f6e`, applied the complete v3 patch, and blocked
`yaml` imports. The handoff and workflow focus passed 14 tests with 1 expected
pre-integration skip. The complete unit suite then passed 4,101 tests with 3
skips in 66.22 seconds. This isolates the current dirty-HEAD failure to the
pre-amend receipt topology: the candidate itself is green in live-base mode,
and only the amendment plus committed-SHA CI remain.

Independent v4 refresh verification added:

- committed-v3 shallow fail-on-old: 1 failed, 7 passed, and 1 skipped because
  the unguarded base-tree lookup exited `128`;
- fixed depth-one checkout with `yaml` blocked: 8 passed and 1 documented
  full-history skip;
- full-history guard: 9 passed, with the exact base tree, integrated ancestry,
  receipt, report, and immutability assertions active;
- full unit suite with `yaml` blocked: 4,102 passed and 2 skipped in 66.02
  seconds;
- independent false-history spy: the protected-scope test passed and issued
  only shallow-safe `rev-parse HEAD`;
- exact live receipt reconstruction: 5,068 bytes and
  `81e7b479f760fa3fcc1c3a32f3539f98019e6e992ac6815097b4cd0eec1f28a8`;
- frozen build report:
  `8072a5e555cbfc1431d8571c8d19ad396d193687b467b1b700e744cfeb90090b`;
- Ruff, Ruff formatting, and `git diff --check`: passed.

The current dirty worktree is not an integrated v4 carrier. Once this excluded
review report advances to the new receipt, the live receipt test is expected to
reject committed v3 HEAD `87e1a10` until release engineering amends it with the
v4 bytes and new receipt, build-report, and review-report trailers. The
depth-one and full-history disposable proofs above establish the candidate's
intended branches; they do not replace amended committed-SHA CI.

Preceding-carrier independent verification included:

- final Python unit suite: 4,100 passed, 3 skipped in 96.93 seconds;
- combined focused carrier suite: 244 passed, 1 documented skip;
- final ops unit focus: 53 passed;
- final handoff guard: 8 passed, 1 documented pre-integration skip;
- control-document tests: 82 passed, with the control-document checker green;
- deployment contract tests and static smoke green;
- Ruff, Ruff formatting, YAML parsing, Bash syntax, receipt reconstruction,
  ignore-policy checks, and `git diff --check` green.

The first full-unit pass caught a stale router-split sentinel because the new
bootstrap acceptance test patched settings directly. The final receipt input
uses the existing `configure_local_api(settings=...)` helper instead. This is a
test-only mechanical refactor: the exact router-split test now passes 5 of 5,
and the final full unit suite is green.

Two isolated PostgreSQL executions exercised the final four-role design. The
independent reviewer execution used PostgreSQL 16.14, pgvector 0.8.5, and
matching PostgreSQL 16.14 dump and restore clients from the pinned workflow
image. It proved:

- exact admin, app, backup, lifecycle, and setup-role authority bits;
- root-owned, commented `pgcrypto` and `vector` extensions before the drill;
- migration through `20260721_0094` as the non-superuser admin;
- empty-user seed and workspace bootstrap under forced RLS;
- 71 passed and 1 documented skip in the workflow contract set;
- successful `v0.12.0` baseline upgrade through migration `0094`;
- preserved counts of 1 user, 1 memory, 2 events, 1 artifact, and 1 rating;
- migration `0093` newest-survivor and uniqueness enforcement;
- matched recall and a current embedding signature;
- accepted `pg_restore --use-list --no-owner --no-comments`;
- direct restored app and backup privileges;
- destroy and restore on a disposable database;
- a mode-`0600` sanitized report with no sensitive-content matches;
- zero remaining drill databases and successful container cleanup.

The control-tower all-backend run also exited zero with overall status
`passed`, no proof gaps, and green SQLite, portable export, PostgreSQL, recall,
embedding, health, and monitoring checks.

## Compatibility Impact

No public API signature, route, operation ID, or continuity contract changes.
The bootstrap endpoint keeps its prior behavior. The only protected
memory-schema path edited by this carrier is unpublished migration `0093`;
its final schema and RLS posture are unchanged for databases that already
applied the preceding body.

Operator procedure changes are intentional: seed the configured core user
after migrations, use separate admin, app, backup, and lifecycle credentials,
filter the one public-schema ACL during restore, and use persistent
`/etc/alicebot` configuration paths.

## Rollback

Before the v4 amendment, discard the unstaged v4 guard and report refresh to
return to committed v3 SHA `87e1a10`. After the v4 amendment, revert the carrier
as one reviewed unit. Do not partially revert only the guide, seed helper, role
setup, dump or restore flags, ACL filter, validators, or tests because they form
one executable deployment contract.

A rollback must not delete operator backup archives or persistent
`/etc/alicebot` configuration.

## Operator Action

Release engineering should:

1. reproduce the final carrier, build-report, and review-report hashes;
2. amend committed v3 SHA `87e1a10` in place with the exact v4 bytes and the
   three required receipt trailers, keeping the rewritten carrier directly on
   base `b383f6e`;
3. run the handoff guard and full pull-request workflow matrix on that exact
   amended commit;
4. require the deployment and ops evidence jobs to remain green under the
   exact four-role PostgreSQL posture;
5. only then perform the separate `0.14.0` version cut, merge, tag,
   publication, and external readback.

Deployment operators must re-render the corrected examples, move scheduled
configuration to `/etc/alicebot`, provision the core user before workspace
bootstrap, rotate and protect the four database credentials, and complete one
fresh backup and restore drill before trusting the schedule.

## Protected-path declaration

- [x] Memory schema
  - This carrier edits
    `apps/api/alembic/versions/20260721_0093_artifact_quality_rating_reviewer_unique.py`
    in place so `NO FORCE` and `FORCE` bracket its dedupe and unique-constraint
    work.
  - Compatibility Impact: No published release contains `0093`. Databases
    already stamped at `0093` retain the same end state because the old body's
    unique constraint succeeded and the trailing `FORCE ROW LEVEL SECURITY` is
    idempotent.
  - Validation: Tests pin the bracket order. The transaction keeps the
    `NO FORCE` window invisible to concurrent sessions and rolls the full
    migration back on failure.
  - Rollback: Revert this carrier before publication. Already-stamped databases
    require no data or schema rollback because their end state is unchanged.
  - Operator Action: None on migrated hosts.
- [x] Continuity APIs
  - No continuity route, request, response, operation ID, or public contract
    changed.

Amended committed-SHA CI is the only remaining release gate owned by this
carrier. The code and documentation reviewed here are ready for the
release-engineer amendment.
