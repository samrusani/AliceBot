# Phase 5 Enterprise Track Fix Matrix

Phase 5 completion is **NO-GO pending the 5.4 owner gate and green
committed-SHA CI**. Stage A is the repository evidence described below; Stage B
history records the review boundary. **5.1.c OWNER DISPOSITION ACCEPTED** uses
the claim bar "automated security scanning under OpenAI Trusted Access on the
repository, plus internal adversarial review." No external auditor is required,
no third-party assessment occurred, and this carrier must never be described as
independently audited or security-certified. **5.4 OWNER GATE OPEN** still
requires the owner-run real-host deployment receipt.

| Area | Delivered change | Fail-on-old or execution proof | Status |
|---|---|---|---|
| Committed-SHA CI repair | Supersedes receipt `4cf7e08b...` / commit `e8d2018`; targets the six reported CI defects covering shallow-history truth, tagless shallow-lane delegation to the authoritative full-history ops drill, negative-path ordering, migration precondition/error precedence before the existing fixed-location `.venv` interpreter check, the example-file Gitleaks false positive, and browser capability timing; also targets aggregate CodeQL alerts #515-#522 as the seventh carrier defect, without suppressions | Reproduce the affected shallow jobs and authoritative full-history ops job; require Gitleaks and CodeQL on a fresh committed SHA; mint a fresh receipt and obtain independent control-tower re-review before integration | Old carrier not shippable; seven-defect repair uncommitted and not yet CI-certified |
| Merged base work | Preserved PR #310 reviewer/provenance binding, PR #311 scheduler DSN-in-environment behavior, and PR #312 dependency fix without rebuilding them | Base commit/tree and exact dirty-scope guard | Preserved |
| Browser clipper | Replaced visited-page reusable credentials with a 120-second, origin-bound, one-time capability; stores only SHA-256 digests; validates and consumes atomically on PostgreSQL and SQLite | Capability shape, origin canonicalization, expiry, replay, tamper, concurrency, migration, route, OpenAPI, redaction, and browser tests | Closed |
| Keyless boundary | Documented keyless as local-machine-owner trust and kept remote vNext behind agent keys plus an authenticated TLS proxy | Every-vNext-route auth sweep, keyless-after-key rejection, scope/escalation tests, production proxy-auth tests | Closed for Stage A |
| Security preparation | Added shipped-product threat model, auth/input/secrets/dependency evidence, retained Stage B review brief, and explicit proof gaps | Route/MCP/OpenAPI/error manifests, RLS/key isolation, secret/error tests, dependency audits | Stage A closed; 5.1.c owner disposition accepted at the stated claim bar |
| Ops evidence | Added physical SQLite backup/WAL restore, portable round trip, authentic v0.12 upgrade, PostgreSQL dump/destroy/restore, migrations 0093/0094, recall/signature, monitoring, and DR automation | Genuine `--backend all` run on PostgreSQL 16.13 with matching clients, no proof gaps and zero disposable DBs left; cleanup fails closed | Closed locally; committed-SHA CI open |
| Ops receipt truth | Bound receipts to source commit/tree plus a dirty-carrier snapshot, handled deletions/symlinks/races, retained multiple failure codes, propagated `PGSSLROOTCERT`, and rejects PostgreSQL client/server major drift | Adversarial temporary-repository and evidence-helper tests, exact mypy/Ruff, real PG16 run | Closed |
| Review dashboard | Added honest loading/error/unavailable states, bounded layouts, default navigation gating, same-origin HTTPS live auth, and the scripted review demo | 236 Vitest tests, two coverage lanes, 24 Playwright tests, keyed/keyless role-separated PostgreSQL demo | Closed |
| Demo truth | Uses an unbound `admin_agent` or zero-key local user, reads source trace by GET without mutation, and keeps raw keys out of curl argv | DB pre/post equality, doc/browser guards, runnable-doc secret-argv sentinel including attached and continued header forms | Closed |
| Deployment contract | Added loopback API/web, PostgreSQL verify-full, role-separated secrets, exact HTTPS origin, mTLS Caddy, HSTS/anti-framing headers, exact vNext-only public matcher, monitoring/backup/upgrade instructions | Adversarial validator, production-startup and migration fail-on-old tests, five input hashes, safe local receipt | Closed as configuration contract |
| Runtime admin credential | Removed the production API startup requirement, excludes `DATABASE_ADMIN_URL` from runtime environment, and requires one-shot injection for migration/recovery | Production startup without admin DSN; migration fails clearly without it; owner receipt requires absent env plus `session_user` and `current_user` equal `alicebot_app` | Closed |
| Real-host evidence | Owner receipt requires mTLS positive/negative/rotation probes, security headers, exact negative API perimeter probes, runtime role/env proof, backup/restore, auth, and monitoring timestamps | Must be executed on the deployed host; repository smoke reports `owner_real_host_deployment_receipt` | Owner gate open |

## Explicitly open, accepted, or out of scope

- **5.1.c OWNER DISPOSITION ACCEPTED:** Stage A evidence, automated security
  scanning under OpenAI Trusted Access on the repository, plus internal
  adversarial review meet the owner's chosen bar. This is not an independent
  audit, certification, or claim that every proof gap is closed.
- **5.4 OWNER GATE OPEN:** the owner-run real-host deployment receipt remains
  required; local configuration evidence cannot close it.
- **COMMITTED-SHA CI GATE OPEN:** the old receipt `4cf7e08b...` and commit
  `e8d2018` failed and are superseded. The seven-defect repair, including
  CodeQL #515-#522 without suppressions, needs a fresh receipt, independent
  re-review, and a green committed-SHA run. Because Gitleaks scans
  `c9d2424..HEAD`, the replacement must be one fresh commit directly on
  `c9d2424`, not a child of `e8d2018`; no historical scan allowlist may conceal
  the old placeholder.
- No real cloud VM, public DNS, public CA, firewall, certificate revocation,
  alert delivery, or scheduled backup was provisioned from this carrier.
- The process-wide settings cache and redaction-path pre-read remain documented
  internal hardening items.
- Importer symlink/TOCTOU hardening and a Python advisory-lock workflow remain
  future work.
- Legacy `/v0/memories/{id}` cannot serialize a vNext archived/redacted row;
  the Phase 5 demo uses the governed vNext path and does not conceal this
  pre-existing compatibility limitation.
- In the hardened remote topology, `/vnext` is the live authenticated browser
  console. Other server-rendered navigation pages remain demo/fixture until a
  future BFF or client-side authenticated refactor.
