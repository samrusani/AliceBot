# Phase 5 Enterprise Track Engineer Handoff

## Start here

- **Code carrier:** **NO-GO** until the repaired carrier has a fresh
  `BUILD_REPORT.md` receipt and reviewer-authored `REVIEW_REPORT.md` verdict.
- **Phase 5 completion:** **NO-GO pending the 5.4 owner gate and green
  committed-SHA CI**.
- **5.1.c OWNER DISPOSITION ACCEPTED:** the accepted claim is "automated
  security scanning under OpenAI Trusted Access on the repository, plus
  internal adversarial review." No external auditor is required, no third-party
  assessment occurred, and this carrier must never be described as
  independently audited or security-certified.
- **5.4 OWNER GATE OPEN:** `owner_real_host_deployment_receipt`.
- **COMMITTED-SHA CI GATE OPEN:** commit `e8d2018` failed; PR/main workflows
  must certify the repaired, intentionally uncommitted carrier after commit.

Base commit: `c9d24243920a694eaf00ad595da392a1478710dd`.
Base tree: `ecc16a53f580308959e97e8b1f02edd04bbe3bfc`.
Both version sources remain `0.13.1`; do not treat this handoff as the version
cut or publication receipt.

## Superseded carrier and required seven-defect proof

Receipt `4cf7e08b...` and commit `e8d2018` are superseded and **not shippable**.
The replacement repair scope covers the six reported CI defects:
shallow-history handoff truth, tagless shallow-lane delegation to the
authoritative full-history ops drill, stable negative-path validation order,
migration precondition/error precedence before the existing fixed-location
`.venv` interpreter check, the example-file Gitleaks false positive, and the
browser one-time-capability timing race. Aggregate CodeQL alerts #515-#522 are a
seventh carrier defect; repair them without suppressions. Keep the repair
uncommitted and unstaged while its
focused, shallow-clone, full-history ops, and local scan proofs run; then mint a
fresh receipt and send the exact delta through independent control-tower
re-review. Only the fresh committed-SHA Gitleaks and CodeQL jobs may close the
two scan findings.

Gitleaks scans the entire `c9d2424..HEAD` PR range. Do not append the repair to
`e8d2018`: that history would retain the old high-entropy placeholder. Release
engineering must create the replacement as one fresh commit directly on base
`c9d2424`, with the fresh trailers below and without `e8d2018` in its ancestry.
Do not use a historical allowlist or CodeQL suppression as a substitute for the
repaired committed-SHA checks.

## Review order

1. Read the threat model, Stage A ledger, and retained Stage B disposition under
   `docs/security/`; confirm they claim only the owner-accepted Trusted Access
   scanning plus internal adversarial review, not an external or independent
   audit.
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

After independently reproducing the receipt, start from base `c9d2424` and
commit the exact carrier and both reports as one fresh replacement commit, not
as a child of `e8d2018`. Use these trailers with values computed from the
committed bytes:

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
3. From a fresh branch or worktree at `c9d2424`, create one replacement commit
   with the three receipt trailers. Verify `e8d2018` is not in its ancestry.
4. Open the PR so PR-only workflows run; require the Phase 5 ops and deployment
   contract jobs plus the normal full matrix on the committed SHA.
5. Verify that release notes preserve the accepted 5.1.c wording and do not
   claim an external review, independent audit, or security certification.
6. Exercise the deployment guide on a real host and review the safe owner
   receipt. Do not infer it from the local configuration smoke.
7. Only after required owner gates and CI are green, cut both governed versions
   to `0.14.0`, build reproducible artifacts, run semantic/release gates, tag,
   publish, and perform external readback.

No step above authorizes a tag or publication from this uncommitted handoff.
