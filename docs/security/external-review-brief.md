# Phase 5.1.c Independent Review Brief

## Ownership And Status

Phase 5.1.c is **owner-owned**. The Alice builder/reviewer team has prepared the
environment, threat model, and evidence, but must not appoint itself as the
independent reviewer or mark this item complete.

Current status: **external reviewer engagement and exact-review-commit receipt
not recorded**. Phase 5 is not security-reviewed merely because Stage A tests
pass. The owner commissions the reviewer, receives the report privately, and
records the disposition of every finding.

## Review Target

The reviewer should receive:

- the exact immutable release-candidate commit and package/container hashes;
- the supported local-first and keyed single-tenant deployment profiles;
- [the threat model](threat-model.md) and [Stage A ledger](stage-a-evidence.md);
- the historical scan artifacts for commit
  `2c372417e1d07d072265d2efdfbdace04f8bfcbb`, explicitly labeled partial and
  historical;
- instructions to run PostgreSQL and SQLite postures, default and gated HTTP
  surfaces, the 11-tool core MCP server, browser clipper, scheduler, importers,
  providers, exports, and redaction; and
- the private reporting path described in the repository root `SECURITY.md`.

Do not ask the reviewer to infer the target from `main`, a branch name, or an
unpublished version string. Their report must name the commit and deployment
configuration they actually assessed.

## Priority Questions

1. Does the keyless-local assumption remain contained to loopback/owner trust,
   and does keyed mode close every vNext HTTP and core MCP path?
2. Can a key or payload escalate actor, permission profile, project scope,
   sensitivity, review authority, or PostgreSQL user context?
3. Can a visited page reuse, transfer, race, or leak a browser-clipper
   capability, or cause a capture after capability rejection?
4. Can hostile SQL/JSON/FTS input change query structure or bypass user/project/
   lifecycle filters?
5. Can hostile imported files escape roots, substitute content after evidence
   capture, exhaust a worker, or create provenance that does not match parsed
   bytes?
6. Can agent keys, provider/connector credentials, database URLs, or sensitive
   user content reach public errors, logs, events, traces, process arguments,
   archives, or package artifacts?
7. Are provider URL/redirect/DNS and response-size controls adequate for the
   documented deployment, and what residual availability risks are acceptable?
8. Do PostgreSQL RLS, SQLite filesystem isolation, true redaction, backup/export,
   and legacy gating match the documentation under adversarial use?

The reviewer should explicitly revisit the deferred directory-import
symlink/TOCTOU issue, Python dependency-audit gap, settings cache footgun,
redaction RAM lifetime, and the historical scan's unresolved availability and
provider-network hypotheses.

## Expected Deliverables

- Executive verdict scoped to the exact commit and deployment assumptions.
- Findings with severity, confidence, source-to-sink proof, reproduction, impact,
  and a falsifiable remediation test.
- Reviewed-surface and unreviewed-surface inventories.
- Clear disposition of Stage A known gaps and historical scan hypotheses.
- Separate code-security and deployment/operational recommendations.
- A retest receipt for each fixed High/Critical and any other release blocker.

Any High or Critical finding opens a Phase 5 fix-and-retest window. Medium/Low
items require an explicit owner disposition; silence is not acceptance.

## Stand-up Path

A reviewer should be able to reach a working local environment in under one
hour by following:

1. [`docs/alpha/headless-ubuntu-install.md`](../alpha/headless-ubuntu-install.md)
   for role-separated PostgreSQL, or the
   [alpha quickstart](../alpha/quickstart.md) for the SQLite on-ramp;
2. `make setup`, migrations where applicable, and `alicebot vnext doctor
   --fix-safe --ci`;
3. the focused commands in [the Stage A ledger](stage-a-evidence.md); and
4. the repository's full release matrix for the exact carrier.

If those instructions fail on a clean supported host, record the failure as an
environment/reproducibility gap before beginning substantive review.

## Completion Receipt

The owner records completion only after the repository has a non-secret receipt
containing the reviewer/organization identity, exact commit, dates, surfaces,
methods, report location, severity rollup, open blockers, remediation commits,
and retest status. Do not commit exploit details or live secrets to the public
repository; use a private GitHub security advisory for active vulnerabilities.
