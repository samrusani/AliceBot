# REVIEW_REPORT

## verdict
PASS

## criteria met
- `P11-S2` local provider registration APIs are implemented and functioning:
  - `POST /v1/providers/ollama/register`
  - `POST /v1/providers/llamacpp/register`
- Existing in-scope APIs are functioning with local adapters:
  - `POST /v1/providers/test`
  - `POST /v1/runtime/invoke`
  - `GET /v1/providers`
  - `GET /v1/providers/{provider_id}`
- Ollama and llama.cpp adapters are integrated through the shipped provider abstraction and registry.
- Capability snapshots include deterministic local model enumeration and health posture fields.
- Additive provider config fields are migrated and wired (`auth_mode`, `model_list_path`, `healthcheck_path`, `invoke_path`).
- Local setup documentation and runnable e2e example path are present.
- Regression fix validated: legacy `/v1/providers` path now correctly passes `store` into shared registration helper (`apps/api/src/alicebot_api/main.py:6174-6177`).
- Credential handling tightened: `auth_mode="none"` now rejects non-empty `api_key`, preventing plaintext persistence (`apps/api/src/alicebot_api/main.py:1562-1568`).
- New regression coverage added:
  - OpenAI-compatible registration still works and stores secret ref, not plaintext (`tests/integration/test_phase11_provider_runtime_api.py:470-491`).
  - `auth_mode="none"` rejects provided `api_key` (`tests/integration/test_phase11_provider_runtime_api.py:494-514`).
- Required verification commands pass on the current branch head:
  - `python3 scripts/check_control_doc_truth.py` -> PASS
  - `./.venv/bin/python -m pytest tests/unit tests/integration -q` -> PASS (`1118 passed in 183.14s`)
  - `pnpm --dir apps/web test` -> PASS (`62 files`, `199 tests`, duration `4.82s`)

## criteria missed
- None identified for `P11-S2` acceptance criteria.

## quality issues
- No blocking quality issues remain in sprint-owned scope after fixes.

## regression risks
- Low. Full required verification is passing, including new regression tests for the previously broken path.
- Residual operational risk remains external local-provider availability (Ollama/llama.cpp process reachability), which is surfaced via explicit discovery/test failure posture.

## docs issues
- No local identifiers (local computer paths, names) were found in sprint-owned changed code/docs reviewed here.
- Out-of-scope dirty local docs remain and should stay excluded from sprint merge scope:
  - `ARCHITECTURE.md`
  - `PRODUCT_BRIEF.md`

## should anything be added to RULES.md?
- Optional improvement: require backward-compat regression tests for already-shipped endpoints whenever shared registration/runtime helpers are refactored.

## should anything update ARCHITECTURE.md?
- Optional improvement: add a concise note clarifying auth-mode credential invariants (`bearer` uses secret refs; `none` must not persist API keys).

## recommended next action
1. Ready for Control Tower merge approval with the updated build and review evidence on this branch head.
2. Keep `ARCHITECTURE.md` and `PRODUCT_BRIEF.md` excluded from the sprint PR.
