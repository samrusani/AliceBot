verdict: PASS

criteria met
- Sprint 5N stays within the existing artifact-ingestion seam. The runtime changes remain limited to RFC822 ingestion in `apps/api/src/alicebot_api/artifacts.py` plus `.eml` media-type inference in `apps/api/src/alicebot_api/semantic_retrieval.py`; no live Gmail, Calendar, OAuth, runner, compile-contract, or UI scope entered the sprint.
- RFC822 ingestion reuses the existing rooted `task_workspaces`, `task_artifacts`, and `task_artifact_chunks` seams without schema or response-shape changes.
- Rooted-path safety, deterministic chunk persistence, malformed/textless RFC822 rejection, per-user isolation, and stable response shapes are covered by unit and Postgres-backed integration tests.
- The prior scope bug is fixed. The RFC822 extractor no longer descends into nested `message/*` parts when selecting body text, so encapsulated `message/rfc822` payloads do not contribute persisted chunk text.
- Regression coverage for nested-email exclusion is now present in `tests/unit/test_artifacts.py` and `tests/integration/test_task_artifacts_api.py`.
- `BUILD_REPORT.md` and `ARCHITECTURE.md` now reflect Sprint 5N and describe the RFC822 boundary accurately, including exclusion of nested `message/rfc822` content.
- Review verification:
  - `./.venv/bin/python -m pytest tests/unit` -> `394 passed in 0.64s`
  - `./.venv/bin/python -m pytest tests/integration` -> `127 passed in 38.15s`

criteria missed
- None.

quality issues
- No blocking implementation or test issues remain for Sprint 5N scope.

regression risks
- Residual risk remains limited to the intentionally narrow richer-document boundary already documented in the sprint packet and architecture notes: HTML rendering, attachment extraction, and live connector behavior are still deferred.

docs issues
- None. `BUILD_REPORT.md` and `ARCHITECTURE.md` are consistent with the implemented slice and the corrected RFC822 extraction rule.

should anything be added to RULES.md?
- No.

should anything update ARCHITECTURE.md?
- No further update is required for this sprint.

recommended next action
- Accept Sprint 5N as complete and merge after normal approval flow.
