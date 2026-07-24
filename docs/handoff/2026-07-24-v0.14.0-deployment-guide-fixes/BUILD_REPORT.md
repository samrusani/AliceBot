# v0.14.0 Deployment Guide Fixes v4 Build Report

## Builder verdict

The reviewed v3 carrier is committed at
`87e1a1013816606ef58cbea426db09d295d6748e`, directly on the recorded base.
Committed-SHA CI exposed one narrow carrier defect: a handoff-truth test
unconditionally resolved the recorded base tree in a depth-one checkout even
though the guard's history helper had already recognized the missing base as
an allowed, verified shallow boundary.

At the v4 builder freeze, the carrier was an uncommitted amendment over that
commit. Its only receipt-listed delta was the guarded base-tree lookup in
`tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py`; this excluded
build report was the only other live change. Focused v4 validation was locally
green. The reviewer-owned v4 refresh and amended committed-SHA CI were
pending, so release status was **NO-GO**. At that freeze,
`REVIEW_REPORT.md` still recorded the reviewed v3 carrier and was not the v4
verdict.

The owner real-host deployment receipt was accepted on 2026-07-24 with 29 of
29 checks passing. The static configuration smoke still reports
`owner_real_host_deployment_receipt` as an intrinsic proof boundary; that
result does not reopen the accepted owner gate.

```text
base commit:       b383f6e69896717dfb60b887747e304c33f70d5b
base tree:         faec22103b6bdee8650513f0c4c6aa28b7e5b912
branch:            codex/v0140-deployment-guide-fixes
committed v2:      9979f58f876479c2759f01fdd75219aca393f4e6
v2 receipt:        54a1375bf095c6f02b2e819c6f4b529c873b1ee41d86cbce6533e86d726c8e0e
committed v3:      87e1a1013816606ef58cbea426db09d295d6748e
v3 receipt:        ca82376dbe63ba6824bb879a57512779a52a6772288426a19df53c9e4f78f773
builder-freeze v4: uncommitted amendment over committed v3
target release:    v0.14.0
source versions:   0.13.1
freeze state:      v3 committed; v4 amendment, tag, and publish not performed
```

## Delivery summary

- Identity provisioning follows option (a): one RLS-aware seed helper is used
  by both the installer and manual guide before the unchanged bootstrap API.
- A dedicated `alicebot_backup` role combines non-superuser posture,
  `BYPASSRLS`, and read-only grants. A separate lifecycle role owns disposable
  database creation.
- Dumps and restores omit comments; archive checks, ACL reconstruction,
  extension prerequisites, bounded scrubbed stderr, and cleanup are covered.
- Deployment configuration and CA material move to persistent
  `/etc/alicebot` paths.
- Next.js `.env*.local` files are ignored without hiding the tracked example or
  any tracked repository file.
- The published-roadmap assertion follows structured publication truth, so a
  pending `0.14.0` candidate does not require a false publication statement.
- The historical Phase 5 carrier remains ancestry and content bound while
  successor source, documentation, and handoff carriers are permitted.

## V2 returned corrections

The v2 carrier makes exactly the five corrections requested in the return
note:

1. `FIX_MATRIX.md` now truthfully identifies migration `0093` as a protected
   memory-schema path and records compatibility, validation, rollback, and
   operator-action disposition.
2. Migration `0093` now has a module docstring explaining its transactional
   `NO FORCE` and `FORCE` bracket and why the pre-publication in-place repair is
   safe.
3. The deployment guide states that skipping the local-user seed causes
   workspace bootstrap to return `404 not_found` until the row exists.
4. The backup guide states that `--no-comments` omits all object comments, not
   only extension comments.
5. The disaster-recovery runbook restores the missing paragraph break before
   the `CREATEDB` caveat.

During the v2 review refresh, the same stale memory-schema attestation was
found in `ENGINEER_HANDOFF.md`. Its receipt-listed protected-path declaration
was synchronized with the corrected `FIX_MATRIX.md` before this freeze. This
handoff truth repair does not change production behavior.

## V3 committed-SHA CI correction

The committed v2 test module imported `yaml`, but PyYAML is not declared in
`pyproject.toml`. Both affected CI jobs install only `.[dev]`, so clean
collection failed with `ModuleNotFoundError: No module named 'yaml'`. The
collection error interrupted the unit job and the ops-evidence job before
their tests could run.

Adding PyYAML is not valid inside this carrier because `pyproject.toml` is
deliberately outside the 28-path receipt manifest. The v3 amendment instead
parses the workflow as raw text with dependency-free block, scalar, mapping,
and direct-key helpers. The assertions remain scoped to exact job and step
boundaries, role SQL, environment keys, action pins, and evidence paths.
Fail-on-old cases reject duplicate steps, duplicate mapping keys, and action
pins hidden in comments or another step. The test does not skip when PyYAML is
absent.

The single receipt-listed v3 delta is
`tests/unit/test_least_privilege_deployment_workflow.py`, with SHA-256:

```text
e1a0f57fcfc3520cf19aafa4a67d04d08c0c151c1f0ef5211077ad0508e00281
```

The pull-request body correction and dependency-advisory update in PR #322 are
separate from this carrier and are not included in the v3 receipt.

## V4 shallow-checkout CI correction

The committed v3 handoff test called
`git rev-parse b383f6e69896717dfb60b887747e304c33f70d5b^{tree}`
unconditionally. A normal depth-one CI checkout contains the committed carrier
but not its recorded base, so that command exits `128` before the guard can use
its designed shallow-checkout behavior.

The v4 amendment applies `_base_history_available()` to that single base-tree
lookup. When the base exists, its exact tree must still equal
`faec22103b6bdee8650513f0c4c6aa28b7e5b912`. When it does not exist, the
helper still requires Git to report a verified shallow repository. Every other
manifest, protected-scope, version, receipt, claim-boundary, ancestry,
content-hash, and report assertion remains unconditional in its applicable
mode.

The single receipt-listed v4 delta is
`tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py`, with SHA-256:

```text
863c4ba35aa8bde34bbe9ba82d221623119d7fe77300e3016dcc9081dfdf9f6b
```

## Validation matrix

The full-suite and isolated-database rows below are preserved evidence from the
preceding carrier. The v2 delta is limited to four documentation/control
corrections and one migration module docstring; its post-correction focused
evidence is recorded separately and does not substitute for committed-SHA CI.

| Lane | Result | Boundary |
|---|---|---|
| Full Python unit suite | 4,100 passed, 3 skipped in 96.93s | The first run exposed one stale router-split sentinel after the new integration test added direct settings patches. A mechanical test-only refactor routed the settings through the existing helper; the exact sentinel and final full suite are green. |
| Combined focused carrier suite before handoff freeze | 152 passed, 1 skipped | One concurrent-edit snapshot failure was rerun after freeze and resolved |
| Control-document truth | 82 passed; `scripts/check_control_doc_truth.py` passed | Covers pending candidate, simulated publication, and wrong roadmap release |
| Deployment contract | 64 passed; static deployment smoke passed | Smoke intentionally retains only its external owner-receipt proof gap |
| Empty-user bootstrap | Exact live acceptance passed | Admin owns the forced-RLS table and is neither superuser nor `BYPASSRLS`; an unscoped insert fails first |
| Workflow and historical guard | 62 passed, 1 skipped | Skip is the documented mode-specific history boundary |
| Ops and migration focus | 56 passed | Includes stderr sanitization, archive comments, role posture, cleanup, and migration 0093 transaction handling |
| Isolated PostgreSQL 16 plus pgvector | Migrations exit 0 through `20260721_0094`; exact empty-user bootstrap passed; `--backend all` exited 0 with `status: passed` and no proof gaps | Full physical destroy/restore proved under four-role separation |
| Isolated evidence readback | Recall matched; embedding signature current; users 1, memories 1, event log 2, artifacts 1, ratings 1; no disposable database remained | Root credentials were confined to cluster setup |
| Independent pinned PostgreSQL 16.14 and pgvector 0.8.5 run | 71 contract tests passed, 1 skipped; migration, bootstrap, smoke, and full PostgreSQL drill passed | TOC filtering removed exactly one public-schema ACL while retaining 1 application-schema and 105 table ACLs; direct app and backup privilege probes passed; sanitized mode-0600 report was clean; no database or container remained |
| Preceding-carrier handoff truth and static checks | 26 passed, 2 documented skips; new guard alone 8 passed, 1 skipped; Ruff and `git diff --check` passed; production-local env ignored; zero tracked ignored files | The return review requested the five v2 corrections; its verdict does not certify the v2 bytes |
| V2 focused correction suite | Builder run: 120 passed in 6.45s; final freezer repeat: 120 passed in 7.38s | Migration `0093`, deployment contract, and Phase 5 ops evidence tests; no skips |
| V2 control-document focus | Builder run: 82 passed in 0.53s; final freezer repeat: 82 passed in 0.46s | Pending-candidate and structured publication truth; no skips |
| V2 static correction checks | Ruff passed on migration `0093` and its unit test; `git diff --check` passed | Reviewer-owned v2 refresh granted GO; committed-SHA CI then exposed the v3 collection defect |
| Final v2 handoff truth | 8 passed, 1 skipped in 0.16s | The only skip is the explicit pre-integration boundary: the uncommitted carrier uses its authoritative live-receipt branch |
| V3 fail-on-old reproduction | Committed v2 module exited 1 with `ModuleNotFoundError: No module named 'yaml'` under a forced-YAML blocker | Reproduces the clean-CI collection failure without changing declared dependencies |
| V3 dependency-free target | Builder blocker run: 6 passed in 0.04s; final freezer repeat: 6 passed in 0.06s | Same forced-YAML blocker; no skip or PyYAML fallback |
| V3 combined focus | Root run: 68 passed in 5.27s; final freezer repeat: 68 passed in 5.17s | Least-privilege workflow, Phase 5 ops, and handoff truth |
| V3 adversarial mutations | 5 temporary workflow mutations were rejected | Supplemental non-receipt harness covered shadow steps, duplicate keys, comment-hidden pins, and malformed boundaries |
| V3 static checks | Ruff check passed; Ruff format check reported 1 file already formatted; `git diff --check` passed | At builder freeze, only the workflow-contract test and this excluded report differed from committed v2 |
| V4 fail-on-old shallow checkout | 1 failed, 7 passed, 1 skipped | Depth-one checkout lacked the recorded base; the unguarded base-tree lookup failed exactly as committed-SHA CI did |
| V4 fixed shallow checkout with YAML blocked | 8 passed, 1 documented skip in 0.53s | Missing base was accepted only after Git proved the checkout shallow; all executable shallow-mode assertions passed |
| V4 full-history guard | 9 passed in 0.68s | Recorded base and exact tree remained mandatory, with all integrated ancestry, receipt, report, and immutability assertions active |
| V4 full unit suite with YAML blocked | 4,102 passed, 2 skipped in 66.02s | Full-history checkout; the integrated v3 report branch was authoritative before the excluded v4 report freeze |
| V4 static checks | Ruff check passed; Ruff format check passed; `git diff --check` passed | At builder freeze, only the handoff-truth test and this excluded report differed from committed v3 |

The final freezer repeated the focused v2 validation with these exact commands:

```text
./.venv/bin/python -m pytest tests/unit/test_20260721_0093_artifact_quality_rating_reviewer_unique.py tests/unit/test_single_tenant_deployment.py tests/unit/test_phase5_ops_evidence.py -q -p no:cacheprovider
./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q -p no:cacheprovider
./.venv/bin/python -m ruff check apps/api/alembic/versions/20260721_0093_artifact_quality_rating_reviewer_unique.py tests/unit/test_20260721_0093_artifact_quality_rating_reviewer_unique.py
git diff --check
./.venv/bin/python -m pytest tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py -q -rs -p no:cacheprovider
```

Every command exited `0`. The pytest results are recorded in the matrix above;
Ruff reported `All checks passed!`, and `git diff --check` emitted no output.

The final freezer repeated the durable v3 checks with these exact commands:

```text
PYTHONPATH=/tmp/alicebot-v3-block-yaml ./.venv/bin/python -m pytest tests/unit/test_least_privilege_deployment_workflow.py -q -p no:cacheprovider
./.venv/bin/python -m pytest tests/unit/test_least_privilege_deployment_workflow.py tests/unit/test_phase5_ops_evidence.py tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py -q -rs -p no:cacheprovider
./.venv/bin/python -m ruff format --check tests/unit/test_least_privilege_deployment_workflow.py
./.venv/bin/python -m ruff check tests/unit/test_least_privilege_deployment_workflow.py
git diff --check
```

Every command exited `0`. The blocker directory and the five-mutation harness
were temporary verification fixtures outside the repository and are not
receipt inputs. At the v3 builder freeze, the combined handoff execution ran
while the committed v2 report still selected the integrated v2 guard branch.
The release engineer subsequently amended the carrier and its report-hash
trailers at `87e1a1013816606ef58cbea426db09d295d6748e`; committed-SHA CI on
that v3 carrier then exposed the v4 shallow-checkout defect.

The v4 shallow checkout was constructed and verified with this command shape:

```text
ALICEBOT_SOURCE="$(pwd)"
git clone --depth 1 --branch codex/v0140-deployment-guide-fixes "file://${ALICEBOT_SOURCE}" /tmp/alicebot-v4-shallow-old
git -C /tmp/alicebot-v4-shallow-old rev-list --count HEAD
git -C /tmp/alicebot-v4-shallow-old rev-parse --is-shallow-repository
git -C /tmp/alicebot-v4-shallow-old cat-file -e b383f6e69896717dfb60b887747e304c33f70d5b^{commit}
```

The first two probes returned `1` and `true`; the base `cat-file` probe exited
`128`. The committed v3 fail-on-old and patched v4 runs then used:

```text
cd /tmp/alicebot-v4-shallow-old
PYTHONPATH=/tmp/alicebot-v3-block-yaml "${ALICEBOT_SOURCE}/.venv/bin/python" -m pytest tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py -q -rs -p no:cacheprovider
```

The temporary `yaml.py` shadow module raises `ModuleNotFoundError`; it is a
non-receipt fixture. Full-history validation used:

```text
PYTHONPATH=/tmp/alicebot-v3-block-yaml ./.venv/bin/python -m pytest tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py -q -rs -p no:cacheprovider
PYTHONPATH=/tmp/alicebot-v3-block-yaml ./.venv/bin/python -m pytest tests/unit -q -p no:cacheprovider
./.venv/bin/python -m ruff check tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py
./.venv/bin/python -m ruff format --check tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py
git diff --check
```

All commands produced the results recorded above. At builder freeze, the v4
receipt existed only in the working tree over committed v3. The release
engineer must amend the carrier commit and its receipt, build-report, and
review-report trailers before the integrated v4 guard and committed-SHA CI can
be authoritative.

The isolated database proof used root only to provision roles, install
extensions, and inspect cleanup. The operational admin was non-superuser and
did not hold `BYPASSRLS`. The backup role was non-superuser with
`BYPASSRLS`. The lifecycle role alone held `CREATEDB`.

## Protected paths and claim boundary

- [x] Memory schema
  - This carrier edits
    `apps/api/alembic/versions/20260721_0093_artifact_quality_rating_reviewer_unique.py`
    in place so `NO FORCE` and `FORCE` bracket its dedupe and unique-constraint
    work.
  - Compatibility Impact: No published release contains `0093`. The end state
    is identical for databases already stamped at `0093`: the old body's
    successful unique-constraint application proves no duplicate reviewer rows
    remained, and the trailing `FORCE ROW LEVEL SECURITY` is idempotent.
  - Validation: Migration-shape tests pin the bracket order. The `NO FORCE`
    window is transaction-internal and is never visible to concurrent sessions.
  - Rollback: Revert this carrier before publication. No data or schema rollback
    is required for an already-stamped database because its end state is
    unchanged.
  - Operator Action: None on migrated hosts.
- [x] Continuity APIs
  - No continuity API contract changed.

The supported release wording is: automated security scanning and internal
adversarial review, findings triaged and fixed. This report does not claim an
independent audit, third-party audit, penetration test, or security
certification.

## Explicit v4 carrier receipt

Receipt format:
`alice-v0.14.0-deployment-guide-fixes-explicit-carrier-v1`.

Receipt-listed paths (28, bytewise sorted):

```text
.github/workflows/ops-evidence.yml
.gitignore
apps/api/alembic/versions/20260721_0093_artifact_quality_rating_reviewer_unique.py
docs/alpha/backup-and-restore.md
docs/deployment/single-tenant-self-hosted.md
docs/handoff/2026-07-24-v0.14.0-deployment-guide-fixes/ENGINEER_HANDOFF.md
docs/handoff/2026-07-24-v0.14.0-deployment-guide-fixes/FIX_MATRIX.md
docs/handoff/2026-07-24-v0.14.0-deployment-guide-fixes/README.md
docs/runbooks/disaster-recovery.md
packaging/cloud/Caddyfile.example
packaging/cloud/single-tenant.env.example
scripts/_phase5_ops_seed.py
scripts/check_control_doc_truth.py
scripts/install-ubuntu.sh
scripts/run_phase5_ops_evidence.py
scripts/run_single_tenant_deployment_smoke.py
scripts/seed_local_user.py
tests/integration/conftest.py
tests/integration/test_local_workspace_bootstrap_api.py
tests/unit/test_20260721_0093_artifact_quality_rating_reviewer_unique.py
tests/unit/test_control_doc_truth.py
tests/unit/test_least_privilege_deployment_workflow.py
tests/unit/test_phase5_enterprise_handoff_truth.py
tests/unit/test_phase5_ops_evidence.py
tests/unit/test_seed_local_user.py
tests/unit/test_single_tenant_deployment.py
tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py
tests/unit/test_vnext_release_polish.py
```

The receipt serializes the format, base commit, base tree, and each path's
mode, kind, and SHA-256 of file content or symlink target using
length-prefixed fields.

serialized receipt bytes: 5,068

carrier receipt sha256:
`81e7b479f760fa3fcc1c3a32f3539f98019e6e992ac6815097b4cd0eec1f28a8`

The canonical live builder reconstructed this v4 receipt twice from the final
receipt-listed bytes. Both runs serialized 5,068 bytes and produced the exact
digest above.

Receipt-loop exclusions are exactly:

```text
docs/handoff/2026-07-24-v0.14.0-deployment-guide-fixes/BUILD_REPORT.md
docs/handoff/2026-07-24-v0.14.0-deployment-guide-fixes/REVIEW_REPORT.md
```

`BUILD_REPORT.md` is builder-owned. `REVIEW_REPORT.md` is reviewer-owned. Both
are bound independently by commit-message content hashes after review. Any
pre-commit edit to a receipt-listed path invalidates this digest. After
integration, the truth guard freezes the handoff bytes while allowing later
reviewed source changes.
