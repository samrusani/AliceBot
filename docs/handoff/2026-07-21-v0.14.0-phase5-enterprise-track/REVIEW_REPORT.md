# Phase 5 Enterprise Track Independent Review Report

## Verdict

- **Code carrier: GO for release-engineer integration.** The reviewed carrier
  has no remaining P0-P3 findings.
- **Phase 5 completion: NO-GO pending owner-only gates.** This verdict covers
  the repository carrier only; it is not permission to tag or publish.
- **5.1.c OWNER GATE OPEN:** the owner-appointed independent external security
  assessment has not been supplied. The repository threat model, test sweeps,
  and this internal review are Stage A evidence; they do not close Stage B.
- **5.4 OWNER GATE OPEN:** `owner_real_host_deployment_receipt` has not been
  supplied. A checked-in deployment contract cannot prove the real DNS, public
  CA, firewall, mTLS perimeter, runtime environment, scheduled backup, or alert
  delivery.
- **COMMITTED-SHA CI GATE OPEN:** this carrier is intentionally uncommitted and
  unstaged. The normal PR/main matrix must run on the release-engineer commit.

## Carrier and receipt verification

I reviewed the uncommitted carrier relative to source commit
`c9d24243920a694eaf00ad595da392a1478710dd`, source tree
`ecc16a53f580308959e97e8b1f02edd04bbe3bfc`, on `main`.

- The explicit manifest contains 122 unique, bytewise-sorted paths and exactly
  matches the live carrier.
- Two independent receipt reads each serialized 20,845 bytes and reproduced
  `4cf7e08b6faddd681daf2217fe3c7184746be4ca34cf7b71098637ce7eb2ed34`.
- The only receipt-loop exclusions are `BUILD_REPORT.md` and this reviewer-owned
  `REVIEW_REPORT.md`; neither can alter the carrier digest.
- The index is empty. Python and web versions remain `0.13.1` for the release
  engineer's later `0.14.0` cut.
- The protected SQLite `memory_access.py`, `docs/release`, prior handoffs, and
  immutable release records are unchanged from the source commit.
- The integrated-mode guard now requires the receipt-trailed carrier in
  ancestry, verifies its exact content, rejects later drift in every
  receipt-listed path, preserves the full five-file handoff, and rejects drift
  in the protected SQLite path. It does not predict the eventual release SHA.

## Review findings closed before freeze

The independent review stopped the carrier and required corrections before
this verdict:

- The PostgreSQL evidence drill initially attempted a timestamp update blocked
  by the immutable audit trigger and later indexed a mapping row positionally.
  Both defects were corrected and reproduced on PostgreSQL 16.
- PostgreSQL 18 client tools could emit a dump archive that PostgreSQL 16 could
  not restore. The runner now fails before database creation unless client and
  server majors are 16, and CI installs the matching PostgreSQL 16 client.
- Dashboard/demo checks were tightened to use only the authenticated `/vnext`
  path, preserve read-only source-trace evidence, report unavailable states
  honestly, and detect attached or continued secret-bearing curl headers.
- Deployment checks were tightened around the exact public route boundary,
  runtime/admin DSN separation, live database-role proof, and negative remote
  probes.
- The first handoff guard preserved only the handoff directory after the
  carrier commit. It now also rejects post-carrier drift across all 122 receipt
  inputs and the protected SQLite path, with fail-on-old tests.

No unresolved finding from those review cycles remains in the code carrier.

## Evidence reviewed and reproduced

I reviewed the complete builder matrix in `BUILD_REPORT.md`, including 4,012
Python unit tests, 405 role-separated PostgreSQL integration tests, the
non-skipping default-surface lane, 236 web unit tests, both web coverage lanes,
24 browser tests, 135 LongMemEval tests, dependency checks, and the production
web build and budgets.

Independent reviewer evidence included:

- Browser-capability core/storage/migration checks: 58 passed, with replay,
  expiry, tamper, wrong-origin, digest-only storage, and backend-shape coverage.
- Public-error and release-polish checks: 31 passed.
- Review-dashboard focused web checks: 59 passed; focused browser flow: 3
  passed; keyed/keyless role-separated PostgreSQL demo: 3 passed.
- Deployment/config/production-auth checks: 89 passed; focused web trust checks:
  46 passed.
- A genuine PostgreSQL 16.13 `--backend all` ops drill passed with no proof gaps
  and no residual disposable databases. A PostgreSQL 18-to-16 client mismatch
  failed closed before creating a database.
- The final handoff truth guard passed 10 tests with the one integrated-mode
  test correctly skipped while `HEAD` remains the uncommitted source commit.
- Focused Ruff, mypy, workflow/YAML and shell checks, plus `git diff --check`,
  passed for the final carrier.

## Remaining proof boundaries

Local Caddy and ShellCheck executables were unavailable. Repository tests cover
the checked-in configuration contract, but actual Caddy parsing, public TLS,
DNS, firewall behavior, mTLS rotation, backup scheduling, alert delivery, and
live runtime-role evidence remain part of the 5.4 owner receipt.

The owner must separately commission and disposition the Stage B external
review required by 5.1.c. After both owner gates close, release engineering must
commit the exact carrier with the documented receipt trailers, run the full
matrix on that committed SHA, perform the governed `0.14.0` version cut, and
complete tag, publication, and external readback checks.

Accordingly: **Code carrier GO; Phase 5 completion NO-GO pending owner-only
gates.**
