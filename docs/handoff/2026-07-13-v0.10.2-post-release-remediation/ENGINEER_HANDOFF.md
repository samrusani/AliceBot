# Post-v0.10.2 Main-Engineer Handoff

## Decision state

The control-tower builders have implemented the post-v0.10.2 non-security
audit corrections and the first independent review's requested changes. The
complete local release matrix is green on the resulting code-frozen dirty
tree. The independent reviewer has returned **APPROVE** in
`REVIEW_REPORT.md`. This is a local code-review verdict, not a release
authorization.

The remaining configured semantic and repository-control checks must run
against the clean candidate's exact SHA before publication.

## Review order

1. Read `FIX_MATRIX.md` and reproduce any item whose contract is unclear.
2. Review migrations 0087 through 0089 before application code. In particular,
   confirm concurrent index behavior, scheduler leases/fences, response-job
   RLS, provider revision/fingerprint compatibility, and graph-edge workflow
   idempotency.
3. Review `response_jobs.py` with both response endpoints. `Idempotency-Key` is
   now required per logical invocation: missing is 428, a reused key with a
   different request is 409, an active job is 202, terminal results replay,
   and an expired uncertain provider outcome fails closed without reinvoking.
4. Review scheduler claim, heartbeat, finalize, and reaper paths together. No
   model/provider work should hold a database connection. Verify that staged
   domain writes publish only after the live fence is locked and in the same
   transaction as finalization; provider failure or fence loss must publish
   none of those writes.
5. Review project/artifact transition tables and Postgres race tests together;
   do not replace locked reads or status CAS with check-then-update logic.
6. Review release workflow recovery modes and exact asset/body validation.
   Stable GitHub state may be created only after PyPI bytes verify. Body
   extraction must remain exact JSON-string decoding rather than `--jq` text
   redirection.
7. Review the current docs as unreleased remediation. Do not rewrite immutable
   v0.10.2 notes or checksums to include these changes.
8. Review the OpenAPI inventory as a fail-closed contract: 294 live operations,
   49 typed exact contracts, and 245 literal per-operation contracts. Do not
   restore a domain-wide fallback or close helper-backed schemas without
   evidence for their complete envelope.
9. Review migration 0087's invalid-index retry and migration 0088's previous-
   binary update path against the new PostgreSQL regressions before approving a
   rolling deployment.
10. Review connection and contradiction logical replay with migration 0089.
    Volatile run/trace identifiers must not change workflow identity, and
    concurrent retries must publish one artifact and one logical edge set.
11. Review explicit-empty project scope and SQLite reindex boundaries. A
    present `project_scope: []` must suppress every legacy fallback, and each
    reindex batch must close its read connection before provider work.

## Required clean-candidate procedure

1. Inspect the entire dirty tree and separate any unrelated user work before
   staging. The builders intentionally did not create a commit.
2. Create an intentional candidate commit on the remediation branch and record
   its exact SHA.
3. Rerun, on that clean SHA:

   ```bash
   make release-static
   make test-python
   make test-longmemeval
   make test-web
   ```

4. Build wheel and sdist twice with the same `SOURCE_DATE_EPOCH`, normalize the
   sdists, byte-compare both formats, run Twine, and smoke both installed
   artifacts. Use empty output directories so stale artifacts cannot enter a
   wildcard, and ensure migrations 0087, 0088, and 0089 are packaged.
5. Run the repository-control readback documented in `RELEASING.md`. Apply the
   generated `MainProtect` payload only after reviewing its preservation of
   bypass actors, conditions, and non-status settings.
6. Set a fresh closed `ALICE_RELEASE_CONTROLS_ATTESTATION` for the exact
   repository/SHA/tag.
7. Dispatch the protected semantic release gate for the exact candidate SHA
   with PostgreSQL 16, pgvector 0.8+, and the intended configured embedding
   provider. All vector queries must return signed candidates.
8. Select a new version. Do not reuse or mutate `v0.10.2`.
9. Run the transactional publish workflow. If interrupted, use only the
   documented exact-byte `finalize-existing-draft` or
   `resume-pypi-and-finalize` path that matches observed PyPI/GitHub state.

## Operational notes

- Downstream callers of `/v0/responses` and `/v1/runtime/invoke` must propagate
  one stable idempotency key across retries. First-party web, readiness,
  runtime scripts, integration helpers, and guides are updated. The web client
  also polls legitimate HTTP 202 response jobs rather than reading terminal-
  only fields.
- SQLite remains supported for local memory workflows, but durable scheduler
  execution intentionally requires PostgreSQL and now fails with a clear
  boundary error.
- Migration 0088 backfills existing provider fingerprints, supplies a valid
  token for omitted legacy inserts, and fences raw configuration updates. Do
  not remove this compatibility behavior while keeping the NOT NULL/CAS
  contract.
- Terminal `/v1/runtime/invoke` outcomes replay before provider/model-pack
  reads, DNS, secret resolution, or adapter selection. This ordering is part of
  the durable idempotency contract, not an optimization.
- Source trace responses are intentionally bounded to 500 rows per collection
  and expose truncation/completeness metadata. Consumers must not assume a
  truncated trace is exhaustive.
- Provider configuration changes use revision/fingerprint CAS, validate
  endpoint addresses before commit, require credentials compatible with Azure
  auth-mode changes, retire replaced secrets only after reference checks, and
  fence capability reads to the exact current configuration.
- Memory review, consolidation, project review, CLI/MCP workflows, and SQLite
  reindex all perform provider embedding outside database transactions; vector
  persistence remains a separate best-effort step.
- Temporary package hashes in `BUILD_REPORT.md` are verification receipts, not
  release hashes.

## Stop conditions

Stop publication if the tree is dirty, a required check is absent or stale,
the semantic artifact is for another SHA, any vector query has zero signed
candidates, repository controls differ from the attestation, PyPI contains an
unexpected subset of files, GitHub draft assets/body differ by one byte, or the
independent review has an unresolved P0/P1/P2 finding.
