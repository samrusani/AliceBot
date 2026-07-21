# Phase 5 Enterprise Track Fix Matrix

Phase 5 completion is **NO-GO pending owner-only gates**. Stage A is the
repository evidence described below; it does not replace Stage B. **5.1.c OWNER
GATE OPEN** requires the owner-appointed external review, and **5.4 OWNER GATE
OPEN** requires the owner-run real-host deployment receipt.

| Area | Delivered change | Fail-on-old or execution proof | Status |
|---|---|---|---|
| Merged base work | Preserved PR #310 reviewer/provenance binding, PR #311 scheduler DSN-in-environment behavior, and PR #312 dependency fix without rebuilding them | Base commit/tree and exact dirty-scope guard | Preserved |
| Browser clipper | Replaced visited-page reusable credentials with a 120-second, origin-bound, one-time capability; stores only SHA-256 digests; validates and consumes atomically on PostgreSQL and SQLite | Capability shape, origin canonicalization, expiry, replay, tamper, concurrency, migration, route, OpenAPI, redaction, and browser tests | Closed |
| Keyless boundary | Documented keyless as local-machine-owner trust and kept remote vNext behind agent keys plus an authenticated TLS proxy | Every-vNext-route auth sweep, keyless-after-key rejection, scope/escalation tests, production proxy-auth tests | Closed for Stage A |
| Security preparation | Added shipped-product threat model, auth/input/secrets/dependency evidence, external-review brief, and explicit proof gaps | Route/MCP/OpenAPI/error manifests, RLS/key isolation, secret/error tests, dependency audits | Stage A closed; 5.1.c open |
| Ops evidence | Added physical SQLite backup/WAL restore, portable round trip, authentic v0.12 upgrade, PostgreSQL dump/destroy/restore, migrations 0093/0094, recall/signature, monitoring, and DR automation | Genuine `--backend all` run on PostgreSQL 16.13 with matching clients, no proof gaps and zero disposable DBs left; cleanup fails closed | Closed locally; committed-SHA CI open |
| Ops receipt truth | Bound receipts to source commit/tree plus a dirty-carrier snapshot, handled deletions/symlinks/races, retained multiple failure codes, propagated `PGSSLROOTCERT`, and rejects PostgreSQL client/server major drift | Adversarial temporary-repository and evidence-helper tests, exact mypy/Ruff, real PG16 run | Closed |
| Review dashboard | Added honest loading/error/unavailable states, bounded layouts, default navigation gating, same-origin HTTPS live auth, and the scripted review demo | 236 Vitest tests, two coverage lanes, 24 Playwright tests, keyed/keyless role-separated PostgreSQL demo | Closed |
| Demo truth | Uses an unbound `admin_agent` or zero-key local user, reads source trace by GET without mutation, and keeps raw keys out of curl argv | DB pre/post equality, doc/browser guards, runnable-doc secret-argv sentinel including attached and continued header forms | Closed |
| Deployment contract | Added loopback API/web, PostgreSQL verify-full, role-separated secrets, exact HTTPS origin, mTLS Caddy, HSTS/anti-framing headers, exact vNext-only public matcher, monitoring/backup/upgrade instructions | Adversarial validator, production-startup and migration fail-on-old tests, five input hashes, safe local receipt | Closed as configuration contract |
| Runtime admin credential | Removed the production API startup requirement, excludes `DATABASE_ADMIN_URL` from runtime environment, and requires one-shot injection for migration/recovery | Production startup without admin DSN; migration fails clearly without it; owner receipt requires absent env plus `session_user` and `current_user` equal `alicebot_app` | Closed |
| Real-host evidence | Owner receipt requires mTLS positive/negative/rotation probes, security headers, exact negative API perimeter probes, runtime role/env proof, backup/restore, auth, and monitoring timestamps | Must be executed on the deployed host; repository smoke reports `owner_real_host_deployment_receipt` | Owner gate open |

## Explicitly open or out of scope

- **5.1.c OWNER GATE OPEN:** the owner-appointed Stage B external security
  assessment is not replaced by Stage A or by the internal code reviewer.
- **5.4 OWNER GATE OPEN:** the owner-run real-host deployment receipt remains
  required; local configuration evidence cannot close it.
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
