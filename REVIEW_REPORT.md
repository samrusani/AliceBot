# REVIEW_REPORT

## verdict

PASS

## criteria met

- Sprint stayed narrow. The code changes are limited to the Gmail renewal seam, the ingest endpoint error mapping, Gmail-focused tests, and `BUILD_REPORT.md`.
- Rotated refresh tokens are now handled in the protected credential seam. `apps/api/src/alicebot_api/gmail.py` captures an optional provider-returned `refresh_token` during renewal and persists it back through `gmail_account_credentials`.
- The replacement rule matches the packet:
  - if the provider returns a non-empty replacement `refresh_token`, persist it
  - otherwise keep the existing stored `refresh_token`
- Gmail account reads remain secret-free. No secret fields were added to list/detail/connect/ingest responses, and existing account list/detail isolation tests still pass.
- Single-message Gmail ingestion still works for both cases:
  - stable refresh-token renewal
  - rotated refresh-token renewal
- Rotated-credential persistence failures are deterministic and happen before Gmail fetch/artifact writes. The new error is mapped to the existing `409` envelope, and tests verify no artifact or credential corruption when persistence fails.
- Required verification passed:
  - `./.venv/bin/python -m pytest tests/unit` -> `437 passed in 0.63s`
  - `./.venv/bin/python -m pytest tests/integration` -> `139 passed in 42.27s`
- No out-of-scope Gmail search, sync, attachments, write actions, Calendar, external secret-manager, compile-contract, runner, or UI work entered the sprint.

## criteria missed

- None.

## quality issues

- None material for Sprint 5R.

## regression risks

- Low. The change is localized to the existing Gmail renewal path and is covered by both unit and Postgres-backed integration tests for stable-token renewal, rotated-token renewal, failure handling, secret-free responses, and user isolation.

## docs issues

- None. `BUILD_REPORT.md` includes the rotation change summary, replacement rule, commands run, test results, secret-free account example, rotation-capable ingestion example, and deferred scope.

## should anything be added to RULES.md?

- No. This is a narrow connector implementation detail, not a new repository-wide rule.

## should anything update ARCHITECTURE.md?

- No. The sprint does not introduce a new architectural boundary or subsystem; it hardens the existing Gmail protected-credential seam.

## recommended next action

- Accept Sprint 5R and move to the next narrow auth-adjacent milestone without broadening scope.
