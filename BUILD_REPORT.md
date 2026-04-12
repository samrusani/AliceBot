# BUILD_REPORT

## sprint objective
Implement `P11-R1` provider-runtime security hardening to close the release-blocking findings: SSRF via provider `base_url`, upstream error-detail reflection/persistence, and URL userinfo credential exposure.

## completed work
- Added centralized provider URL security policy:
  - allowed schemes restricted to `http`/`https`
  - rejects userinfo in `base_url`
  - blocks loopback, link-local/metadata, RFC1918/private, and other non-global IP literal targets
- Enforced URL policy before persistence and before outbound execution:
  - registration paths validate `base_url` before provider row creation
  - runtime adapter outbound paths validate `base_url` before helper/network calls
  - runtime/test flows hard-reject disallowed stored provider targets
- Sanitized upstream provider error handling:
  - provider test/discovery/invoke errors now map to bounded safe messages for API and persistence
  - persisted `provider_capabilities.discovery_error` now stores sanitized values
  - runtime failure traces store sanitized provider failure messages
- Added serialization hygiene:
  - provider serialization now redacts userinfo from `base_url` (defense in depth for legacy rows)
- Added/updated sprint verification coverage:
  - blocked target registration cases (`169.254.169.254`, loopback, RFC1918 ranges)
  - blocked target runtime/test rejection with no outbound attempt
  - userinfo rejection and legacy serialization redaction
  - raw upstream detail not reflected or persisted
- Updated control-doc truth rules and roadmap marker to align with active `P11-R1`.
- Updated `REVIEW_REPORT.md` to grade `P11-R1` and explicitly close each in-scope finding.

## incomplete work
- None within the `P11-R1` sprint packet scope.

## files changed
- `apps/api/src/alicebot_api/provider_security.py` (new)
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/provider_runtime.py`
- `apps/api/src/alicebot_api/local_provider_helpers.py`
- `apps/api/src/alicebot_api/azure_provider_helpers.py`
- `tests/unit/test_provider_security.py` (new)
- `tests/unit/test_provider_runtime.py`
- `tests/integration/test_phase11_provider_runtime_api.py`
- `ROADMAP.md`
- `scripts/check_control_doc_truth.py`
- `REVIEW_REPORT.md`
- `BUILD_REPORT.md`

## tests run
1. `python3 scripts/check_control_doc_truth.py`
   - Result: PASS
   - Output: `Control-doc truth check: PASS`

2. `./.venv/bin/python -m pytest tests/unit tests/integration -q`
   - Result: PASS
   - Output: `1169 passed in 185.41s (0:03:05)`

3. `./.venv/bin/bandit -r apps/api/src/alicebot_api/provider_runtime.py apps/api/src/alicebot_api/local_provider_helpers.py apps/api/src/alicebot_api/azure_provider_helpers.py apps/api/src/alicebot_api/main.py`
   - Result: PASS
   - Output: `No issues identified`

## blockers/issues
- No implementation blockers in sprint scope.
- Workspace contains a pre-existing unrelated dirty file not modified by this sprint:
  - `README.md`

## recommended next step
Proceed to security review sign-off for `P11-R1`, then merge once the release hold is formally cleared against the three closed findings.
