# Phase 5 Enterprise Track Engineer Handoff

## Start here

- **Code carrier:** require the final `REVIEW_REPORT.md` verdict and reproduce
  the receipt before integrating.
- **Phase 5 completion:** **NO-GO pending owner-only gates**.
- **5.1.c OWNER GATE OPEN:** independent external security review.
- **5.4 OWNER GATE OPEN:** `owner_real_host_deployment_receipt`.
- **COMMITTED-SHA CI GATE OPEN:** PR/main workflows cannot certify this
  intentionally uncommitted carrier.

Base commit: `c9d24243920a694eaf00ad595da392a1478710dd`.
Base tree: `ecc16a53f580308959e97e8b1f02edd04bbe3bfc`.
Both version sources remain `0.13.1`; do not treat this handoff as the version
cut or publication receipt.

## Review order

1. Read the threat model and Stage A ledger under `docs/security/`, then confirm
   that neither claims to be the owner-appointed Stage B assessment.
2. Review browser-clip capability issuance, atomic consumption, migration 0094,
   simple-request transport, and recursive secret redaction across PostgreSQL
   and SQLite.
3. Review the production vNext auth boundary and the every-route authorization
   sweep; confirm legacy production gates were not opened.
4. Reproduce `scripts/run_phase5_ops_evidence.py --backend all` with PostgreSQL
   16 server and client tools, then confirm no disposable database remains.
5. Review `/vnext` same-origin key forwarding, unavailable states, and the
   keyed/keyless review-dashboard integration and browser tests.
6. Run the deployment validator and inspect the exact Caddy matcher, mTLS,
   headers, runtime-only DSN, one-shot migration DSN, and owner receipt fields.
7. Reconstruct the explicit receipt in `BUILD_REPORT.md`, then read the
   reviewer-authored `REVIEW_REPORT.md`.

## Required local gates

Use the exact environment expected by each lane. The PostgreSQL commands require
the role-separated application/admin URLs used by integration tests.

```bash
./.venv/bin/pytest tests/unit -q --cov=alicebot_api --cov-report=term --cov-report=json:/tmp/alicebot-python-coverage.json --cov-fail-under=50
make check-python-coverage PYTHON_COVERAGE_JSON=/tmp/alicebot-python-coverage.json PYTHON_API_COVERAGE_MIN=45
ALICE_LEGACY_SURFACES=1 ./.venv/bin/pytest tests/integration -q --require-executed-tests
unset ALICE_LEGACY_SURFACES ALICE_MCP_LEGACY_TOOLS ALICE_AGENT_API_KEY
./.venv/bin/python -m pytest \
  tests/integration/test_default_surface_integration.py \
  tests/integration/test_openai_agents_sdk_tool.py \
  -q -p no:cacheprovider --require-executed-tests
./.venv/bin/pytest eval/longmemeval -q
./.venv/bin/python scripts/check_longmemeval_evidence.py
pnpm --dir apps/web test
pnpm --dir apps/web test:coverage:core
pnpm --dir apps/web test:coverage:vnext
pnpm --dir apps/web typecheck
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web test:budget
pnpm --dir apps/web test:browser
make release-static
git diff --check
```

Also run both Phase 5 evidence entry points:

```bash
./.venv/bin/python scripts/run_phase5_ops_evidence.py --backend all --output /tmp/phase5-ops.json
./.venv/bin/python scripts/run_single_tenant_deployment_smoke.py
```

The deployment smoke must continue to report exactly one blocker:
`owner_real_host_deployment_receipt`. An empty blocker list before real-host
evidence is a failure, not success.

## Receipt and commit protocol

Receipt format:
`alice-v0.14.0-phase5-enterprise-track-explicit-carrier-v1`.

The receipt hashes the explicit sorted path list in `BUILD_REPORT.md`, including
mode, kind, and content/link-target hash, relative to the recorded base commit
and tree. It excludes exactly this handoff's `BUILD_REPORT.md` and reviewer-owned
`REVIEW_REPORT.md` to avoid a receipt loop. Do not stage by dirty-tree wildcard.

After independently reproducing the receipt, commit the exact carrier and both
reports with these trailers, using the values computed from the committed
bytes:

```text
Alice-Carrier-Receipt-SHA256: <carrier digest from BUILD_REPORT.md>
Alice-Build-Report-SHA256: <sha256 of BUILD_REPORT.md>
Alice-Review-Report-SHA256: <sha256 of REVIEW_REPORT.md>
```

The truth guard locates the integrated carrier by ancestry and these content
receipts. It does not predict the future commit, merge, release, or tag SHA.
Any receipt-listed edit requires a new bind and independent review.

## Release-engineer sequence

1. Confirm `git status`, no staged paths, base ancestry, version `0.13.1`, and
   the protected/immutable path checks in the truth guard.
2. Reproduce the local matrix and carrier receipt.
3. Commit through the protected workflow with the three receipt trailers.
4. Open the PR so PR-only workflows run; require the Phase 5 ops and deployment
   contract jobs plus the normal full matrix on the committed SHA.
5. Commission/receive the 5.1.c external review and close or disposition its
   findings. Do not relabel this internal review as Stage B.
6. Exercise the deployment guide on a real host and review the safe owner
   receipt. Do not infer it from the local configuration smoke.
7. Only after required owner gates and CI are green, cut both governed versions
   to `0.14.0`, build reproducible artifacts, run semantic/release gates, tag,
   publish, and perform external readback.

No step above authorizes a tag or publication from this uncommitted handoff.
