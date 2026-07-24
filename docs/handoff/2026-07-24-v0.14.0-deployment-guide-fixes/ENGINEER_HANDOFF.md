# v0.14.0 Deployment Guide Fixes Engineer Handoff

## Start here

- **Code carrier:** independent review **GO**.
- **Release:** **NO-GO** until committed-SHA CI is green.
- **Owner evidence:** the 2026-07-24 real-host receipt is accepted at 29 of 29.
  The local configuration smoke still names
  `owner_real_host_deployment_receipt` because it cannot prove external host
  state; do not reopen 5.4 from that expected static result.
- **Version state:** `pyproject.toml` and `apps/web/package.json` both remain
  `0.13.1`. Release engineering owns the later `0.14.0` version cut.

Base commit: `b383f6e69896717dfb60b887747e304c33f70d5b`.

Base tree: `faec22103b6bdee8650513f0c4c6aa28b7e5b912`.

Receipt format:
`alice-v0.14.0-deployment-guide-fixes-explicit-carrier-v1`.

## Review order

1. Reconstruct the explicit receipt from the sorted path manifest in
   `BUILD_REPORT.md`.
2. Review the Phase 5 guard transition. It must reconstruct the old carrier at
   its own commit and freeze only the old handoff afterward. A later source or
   handoff carrier must not fail the old guard.
3. Review `scripts/seed_local_user.py`, installer invocation, manual guide, and
   exact forced-RLS empty-user acceptance. Confirm the bootstrap API still
   rejects an identity that has not been provisioned.
4. Review all four operational roles. Confirm admin is
   `NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`, backup is
   `NOSUPERUSER BYPASSRLS` with read access, and lifecycle alone holds
   `CREATEDB` for disposable drills.
5. Inspect the dump and restore command vectors, extension ownership
   precondition, archive comment check, ACL reconstruction, cleanup, and
   stderr sanitization.
6. Compare every persistent `/etc/alicebot` path across the guide, cloud
   examples, smoke validator, and tests.
7. Review the control-document tests against pending and published release
   states.
8. Read the reviewer-authored `REVIEW_REPORT.md`, then require all committed-SHA
   workflows on the actual PR head.

## Required local gates

At minimum, reproduce the focused carrier matrix:

```bash
./.venv/bin/python -m pytest \
  tests/unit/test_20260721_0093_artifact_quality_rating_reviewer_unique.py \
  tests/unit/test_control_doc_truth.py \
  tests/unit/test_least_privilege_deployment_workflow.py \
  tests/unit/test_phase5_enterprise_handoff_truth.py \
  tests/unit/test_phase5_ops_evidence.py \
  tests/unit/test_seed_local_user.py \
  tests/unit/test_single_tenant_deployment.py \
  tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py \
  tests/unit/test_vnext_release_polish.py \
  -q -p no:cacheprovider
./.venv/bin/python scripts/check_control_doc_truth.py
./.venv/bin/python scripts/run_single_tenant_deployment_smoke.py
./.venv/bin/ruff check \
  scripts/seed_local_user.py \
  scripts/run_phase5_ops_evidence.py \
  scripts/run_single_tenant_deployment_smoke.py \
  tests/unit/test_v0140_deployment_guide_fixes_handoff_truth.py
bash -n scripts/install-ubuntu.sh
git diff --check
git check-ignore -v apps/web/.env.production.local
git ls-files -i -c --exclude-standard
```

The exact PostgreSQL acceptance also requires PostgreSQL 16 client tools,
pgvector, the full Git history, and the operational-role URLs used by
`.github/workflows/ops-evidence.yml`. Run that workflow on the committed SHA
instead of substituting mocks.

## Receipt and commit protocol

The receipt hashes the explicit bytewise-sorted path list with each entry's
mode, kind, and content or link-target hash, relative to the recorded base
commit and tree. It excludes exactly this package's `BUILD_REPORT.md` and
reviewer-owned `REVIEW_REPORT.md`.

The release engineer must:

1. Confirm the worktree contains only the receipt-listed paths and the two
   report exclusions.
2. Reproduce the carrier digest and review both report byte hashes.
3. Commit the exact carrier and both reports without rebasing or rewriting the
   Phase 5 lineage.
4. Add these trailers with values computed from the final bytes:

```text
Alice-Carrier-Receipt-SHA256: <carrier digest>
Alice-Build-Report-SHA256: <sha256 of BUILD_REPORT.md>
Alice-Review-Report-SHA256: <sha256 of REVIEW_REPORT.md>
```

The truth guard locates the carrier by receipt trailer, proves its direct
parent and content, and freezes this handoff directory. It does not predict the
future PR merge, release, or tag SHA. Later reviewed source edits are allowed;
edits to this integrated handoff are not.

## Compatibility Impact

No public API signature, route, operation ID, or continuity contract changes.
The only protected memory-schema edit is unpublished migration `0093`. Its
already-stamped database end state is unchanged because the old body
successfully applied the unique constraint and the trailing `FORCE ROW LEVEL
SECURITY` is idempotent. Operators gain an explicit identity-seed step,
separate backup and lifecycle credentials, and persistent `/etc/alicebot`
paths. Existing pre-fix backup automation and units must be updated before use.

## Validation

Local focused suites, control-document truth, static deployment smoke, an
isolated PostgreSQL 16 plus pgvector run, and independent review are green. The
live database proof
used a non-superuser admin, started with no user, migrated through `0094`,
completed physical destroy and restore, matched recall and the current
embedding signature, preserved the expected row counts, and left no disposable
database. Committed-SHA CI remains open.

## Rollback

Before publication, discard this uncommitted carrier and return to base
`b383f6e69896717dfb60b887747e304c33f70d5b`. After integration, revert the
carrier as one reviewed unit. Do not partially revert only the docs, role
setup, dump flags, seed helper, validators, or tests because those parts form
one deployment contract. A rollback must not delete operator backup archives
or persistent `/etc/alicebot` configuration.

## Operator Action

Re-render deployment files from the corrected examples. Provision the core
user with `scripts/seed_local_user.py` after migrations and before workspace
bootstrap. Create and protect separate admin, application, backup, and
lifecycle credentials. Move scheduled-unit environment and CA files to the
documented persistent `/etc/alicebot` paths. Run one fresh physical backup and
destroy/restore drill, inspect scrubbed stderr if it fails, and verify cleanup
before trusting the schedule.

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
  - Rollback: Revert this carrier before publication. No data or schema rollback
    is required on an already-stamped database.
  - Operator Action: None on migrated hosts.
- [x] Continuity APIs
  - No continuity API contract changed.

The release claim must remain: automated security scanning and internal
adversarial review, findings triaged and fixed. Do not claim an independent
audit, third-party audit, penetration test, or certification.
