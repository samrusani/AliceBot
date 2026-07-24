# v0.14.0 Deployment Guide Fix Matrix

The code carrier has independent review **GO**. Release remains **NO-GO**
pending committed-SHA CI. The owner real-host receipt was
accepted on 2026-07-24 with 29 of 29 checks passing; the static smoke's
`owner_real_host_deployment_receipt` proof gap is intrinsic and is not an open
owner gate.

| Brief item | Delivered change | Fail-on-old or execution proof | Status |
|---|---|---|---|
| Work item 0: integrated carrier guard | Phase 5 source bytes are proved at the historical receipt-trailed carrier commit, while only its handoff directory remains immutable afterward. Successor source, docs, and handoff carriers are allowed. | Historical parent, receipt, changed-path, report-trailer, protected-path, future-source-edit, and handoff-drift tests | Closed locally |
| Defect 1: empty-user bootstrap | Chose option (a): one parameterized seed helper shared by installer and manual guide. The helper sets transaction-local RLS identity and upserts the user before workspace bootstrap. | Exact PostgreSQL acceptance starts with no user, proves FORCE RLS and an unscoped insert failure, then seeds and bootstraps under an owning admin with `NOSUPERUSER` and `NOBYPASSRLS`; repeat calls prove idempotency | Closed locally |
| Defect 2: Next.js local environment | Root ignore policy covers `apps/web/.env*.local`, preserves the tracked example, and unignores previously tracked paths hidden by broad patterns. Deployment hashing recognizes the rendered production-local file. | `git check-ignore`, tracked-example check, zero tracked ignored files, deployment contract tests, and smoke | Closed locally |
| Defect 3: backup role | Dedicated `alicebot_backup` is non-superuser, holds `BYPASSRLS`, and receives read-only grants. `alicebot_drill` separately holds `CREATEDB` for disposable targets; the docs disclose the privilege tradeoff. | Workflow asserts exact role bits and the isolated PostgreSQL drill dumps forced-RLS tables with the backup role | Closed locally; committed-SHA CI required |
| Defect 4: restore and diagnostics | Dumps and restores use `--no-comments`; archive contents are checked. Restore setup reconstructs required database and schema grants. Scrubbed bounded diagnostics go only to stderr. | Unit subprocess tests plus real PostgreSQL 16 destroy/restore with root-owned commented extensions; sanitized JSON remains free of diagnostics and credentials | Closed locally; committed-SHA CI required |
| Defect 5: reboot-safe paths | Runtime environment, backup environment, and CA paths move from `/run/secrets/alicebot` to persistent `/etc/alicebot` locations across docs, examples, tests, and validators. | Exact-string fail-on-old guards, 64 deployment tests, and passing static deployment smoke | Closed locally |
| Work item 6: control-doc truth | Roadmap latest-published truth is derived from the validated structured release record, not a pending governed version. | Pending `0.14.0`, simulated publication, and wrong-roadmap-version tests; 82 tests and control-doc script pass | Closed locally |
| Cross-cutting least privilege | Full-history ops CI creates separate root, admin, app, backup, and lifecycle roles. Admin is neither superuser nor `BYPASSRLS`; root is confined to setup. | Workflow contract tests, migrations through `0094`, empty-user integration, and both-backend ops evidence | Closed locally; committed-SHA CI required |
| Receipt and release truth | New explicit carrier receipt binds mode, kind, and content hash to the merge base and tree. Old handoffs, release records, security evidence, and version sources are excluded. | Live receipt reconstruction, historical carrier reconstruction, exact changed-path set, direct-parent ancestry, report hash trailers, and immutable handoff test | Independent review GO; integration pending |

## Protected paths

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
  - No continuity route, request, response, operation ID, or public contract is
    changed by this carrier. Identity provisioning remains an explicit
    pre-bootstrap operator step.

## Claim boundary

The supported wording is: automated security scanning and internal adversarial
review, findings triaged and fixed. Do not claim an independent or third-party
audit, a penetration test, or security certification.
