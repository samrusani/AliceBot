# BUILD_REPORT

## sprint objective
Implement Bridge Sprint 1 (`B1`) Hermes provider contract foundation by extending the shipped provider with bridge-phase config normalization, deterministic lifecycle hooks (`prefetch`, `queue_prefetch`, `sync_turn`, `on_session_end`), provider status/readiness validation, and the new automation-oriented MCP prefetch surface `alice_prefetch_context`.

## completed work
- Extended (not replaced) the shipped Hermes Alice provider with bridge contract behavior:
  - normalized canonical bridge config keys for lifecycle operation
  - preserved legacy config-key compatibility
  - added provider status/readiness reporting without live network dependency
  - added deterministic session-end flush behavior
  - added duplicate-write suppression for repeated `sync_turn` and `on_memory_write` callback execution
  - fixed capture-queue worker start race and bounded dedupe behavior to avoid suppressing valid later repeats
- Added MCP tool `alice_prefetch_context` with deterministic prefetch text assembled from existing continuity resumption semantics.
- Updated smoke script to emit provider bridge status/lifecycle readiness evidence.
- Updated install and integration docs for bridge contract keys, lifecycle mapping, compatibility keys, and MCP tool surface.
- Added/updated unit and integration coverage for:
  - provider config compatibility and invalid-config status
  - deterministic lifecycle dedupe/flush behavior
  - MCP tool surface stability including `alice_prefetch_context`
- Aligned control-doc truth checks and active control docs to the current bridge-phase baseline.
- Clarified architecture docs so B2+ capture/review surfaces are marked as planned (not shipped in B1).

Legacy compatibility keys preserved:
- `prefetch_limit`
- `max_recent_changes`
- `max_open_loops`
- `include_non_promotable_facts`
- `auto_capture`
- `mirror_memory_writes`

## incomplete work
- No code deliverable remains incomplete in B1 scope.

## files changed
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `ROADMAP.md`
- `RULES.md`
- `docs/integrations/hermes-memory-provider/plugins/memory/alice/__init__.py`
- `apps/api/src/alicebot_api/mcp_tools.py`
- `docs/integrations/hermes-memory-provider.md`
- `docs/integrations/mcp.md`
- `scripts/check_control_doc_truth.py`
- `scripts/install_hermes_alice_memory_provider.py`
- `scripts/run_hermes_memory_provider_smoke.py`
- `tests/unit/test_hermes_memory_provider.py`
- `tests/unit/test_mcp.py`
- `tests/integration/test_mcp_server.py`

## tests run
1. `python3 scripts/check_control_doc_truth.py`
   - Result: PASS
   - Output: `Control-doc truth check: PASS`
2. `./.venv/bin/python -m pytest tests/unit tests/integration -q`
   - Result: PASS
   - Output: `1174 passed in 186.28s (0:03:06)`
3. `./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py`
   - Result: PASS
   - Output summary:
     - single external provider enforcement validated
     - provider registered with expected tool set
     - `structural.bridge_status.ready=true`
     - `structural.bridge_status.errors=[]`
     - lifecycle hooks status present for `prefetch`, `queue_prefetch`, `sync_turn`, `on_session_end`

## blockers/issues
- None.

## recommended next step
Proceed with reviewer re-check against B1 acceptance criteria using this updated evidence set.
