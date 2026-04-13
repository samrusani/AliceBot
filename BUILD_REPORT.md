# BUILD_REPORT

## sprint objective
Implement Bridge Sprint 2 (`B2`) auto-capture pipeline on top of the shipped Hermes provider and B1 contract foundation: candidate extraction, commit policy, mode support (`manual`, `assist`, `auto`), review-queue persistence for non-auto-saved items, and deterministic idempotent/no-op behavior.

## completed work
- Added B2 capture pipeline core in Alice continuity:
  - implemented `alice_capture_candidates` extraction from user/assistant turn pairs
  - implemented `alice_commit_captures` commit policy over extracted candidates
  - implemented candidate classes: `decision`, `commitment`, `waiting_for`, `blocker`, `preference`, `correction`, `note`, `no_op`
  - candidate payloads now include confidence, trust class, evidence snippet, and proposed action
- Implemented commit policy operating modes:
  - `manual`: routes non-`no_op` candidates to review persistence
  - `assist`: auto-saves only explicit high-confidence allowlist candidates
  - `auto`: auto-saves allowlist candidates at the auto-mode confidence gate
- Implemented policy allowlist and review routing evidence:
  - auto-save allowlist categories: `correction`, `preference`, `decision`, `commitment`, `waiting_for`, `blocker`
  - review-routed categories by type policy: `note`
  - additionally, low-confidence or policy-disallowed candidates route to review under mode gates
- Added idempotent commit behavior using commit fingerprint + candidate fingerprint lookup to prevent duplicate writes on repeated sync attempts.
- Added no-op protection so no-op turns (`no_op`) produce no memory writes.
- Wired new HTTP surfaces:
  - `POST /v0/continuity/captures/candidates`
  - `POST /v0/continuity/captures/commit`
- Wired new MCP surfaces:
  - `alice_capture_candidates`
  - `alice_commit_captures`
  - preserved existing `alice_capture` and other shipped tools for fallback/manual workflows
- Wired Hermes provider B2 flow in `sync_turn`:
  - `assist`/`auto` modes now run candidate extraction then commit
  - `manual` mode suppresses automatic `sync_turn` capture
  - fallback to legacy `/v0/continuity/captures` path when B2 endpoints are unavailable
  - preserved dedupe queue and session-end flush behavior
- Updated sprint-scoped integration docs and smoke script for B2 mode/pipeline truth.
- Updated control-doc truth checker markers from B1-active to B2-active so required verification reflects active sprint state.

## incomplete work
- None in B2 packet scope.

## files changed
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `REVIEW_REPORT.md`
- `ROADMAP.md`
- `apps/api/src/alicebot_api/continuity_capture.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/mcp_tools.py`
- `apps/api/src/alicebot_api/store.py`
- `docs/integrations/hermes-memory-provider/plugins/memory/alice/__init__.py`
- `docs/integrations/hermes-memory-provider.md`
- `docs/integrations/mcp.md`
- `scripts/run_hermes_memory_provider_smoke.py`
- `scripts/check_control_doc_truth.py`
- `tests/unit/test_continuity_capture.py`
- `tests/integration/test_continuity_capture_api.py`
- `tests/unit/test_mcp.py`
- `tests/unit/test_hermes_memory_provider.py`

## tests run
1. `python3 scripts/check_control_doc_truth.py`
   - Result: PASS
   - Output summary: verified README, ROADMAP, sprint packet, RULES, current state, archive planning marker
2. `./.venv/bin/python -m pytest tests/unit tests/integration -q`
   - Result: PASS
   - Output: `1188 passed in 191.85s (0:03:11)`
3. `./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py`
   - Result: PASS
   - Output summary:
     - single external provider enforcement validated
     - provider registered with expected tool schemas
     - `bridge_contract_version` reported as `bridge_b2`
     - bridge status `ready=true`, `errors=[]`
     - config includes `bridge_mode=assist`
     - lifecycle hooks report `prefetch`, `queue_prefetch`, `sync_turn`, `on_session_end`, and `bridge_mode`

## blockers/issues
- None.

## recommended next step
Run B2 review against acceptance criteria with focus on policy calibration (confidence thresholds) and confirm desired `auto`-mode aggressiveness before promoting B3 review actions.
