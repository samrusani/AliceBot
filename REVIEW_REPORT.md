# REVIEW_REPORT

## sprint
`P11-R1` Phase 11 Security Remediation Sprint 1: Provider Runtime Hardening

## verdict
PASS

## criteria met
- Registration and runtime test/invoke flows hard-reject disallowed provider targets, including metadata/link-local, loopback, and RFC1918/private ranges.
- No outbound call is attempted after disallowed target detection in provider test/runtime flow coverage.
- Provider HTTP failures do not expose raw upstream provider detail in API responses.
- Persisted provider discovery/runtime errors are sanitized and redacted.
- Provider URLs containing embedded userinfo are rejected on registration, and serialized provider rows redact legacy userinfo.
- Existing Phase 11 provider/runtime/model-pack behavior remains intact outside intended hardening.
- Sprint closes the three in-scope security findings without feature-scope expansion.

## criteria missed
- None.

## quality issues
- None blocking.
- Residual operational note: repo-level URL policy is strong, but production should still enforce network-layer egress policy as defense in depth.

## regression risks
- Low. Core risk area (SSRF validation bypass via non-canonical IPv4 encodings) is now covered by both unit and integration tests.

## docs issues
- No local machine identifiers (paths/usernames) found in sprint-owned files.
- Review docs are now aligned with implemented security behavior.

## should anything be added to RULES.md?
- Recommended: add a permanent rule requiring provider URL validation tests for non-canonical IPv4 forms (hex/octal/shorthand/integer) whenever URL policy is touched.

## should anything update ARCHITECTURE.md?
- Recommended: add one short provider-runtime egress boundary note clarifying that application URL validation and infra egress controls are complementary controls.

## recommended next action
1. Approve `P11-R1` for merge.
2. Keep the new non-canonical host blocked-target tests as required coverage for future provider-runtime URL policy changes.
3. Clear the release `HOLD` once security sign-off records this closure evidence.

## evidence summary
- Code fix for bypass class:
  - `apps/api/src/alicebot_api/provider_security.py`: URL validator now canonicalizes IPv4 integer/hex/octal/shorthand forms via `socket.inet_aton` and blocks disallowed resolved IPs.
- Added/updated security regression tests:
  - `tests/unit/test_provider_security.py`
  - `tests/integration/test_phase11_provider_runtime_api.py`
- Required verification commands (re-run):
  - `python3 scripts/check_control_doc_truth.py` -> PASS
  - `./.venv/bin/python -m pytest tests/unit tests/integration -q` -> `1169 passed in 185.41s (0:03:05)`
  - `./.venv/bin/bandit -r apps/api/src/alicebot_api/provider_runtime.py apps/api/src/alicebot_api/local_provider_helpers.py apps/api/src/alicebot_api/azure_provider_helpers.py apps/api/src/alicebot_api/main.py` -> No issues identified
