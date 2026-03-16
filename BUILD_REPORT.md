# BUILD_REPORT

## sprint objective

Implement narrow DOCX artifact parsing on the existing artifact-ingestion seam so already-registered visible DOCX artifacts can be ingested into durable `task_artifact_chunks` rows without changing retrieval contracts, compile contracts, connectors, or UI.

## completed work

- Extended the existing artifact media-type support to accept DOCX artifacts:
  - media type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - extension inference: `.docx`
- Implemented deterministic local DOCX text extraction in `apps/api/src/alicebot_api/artifacts.py` by:
  - opening local DOCX bytes as a ZIP package
  - reading `word/document.xml` only
  - parsing WordprocessingML locally with `xml.etree.ElementTree`
  - extracting paragraph text in document order from `w:t`
  - preserving explicit DOCX tabs and line breaks via `w:tab`, `w:br`, and `w:cr`
  - joining non-empty paragraphs with `\n`
  - rejecting malformed packages/XML as invalid DOCX
  - rejecting textless DOCX files when no extractable text is present
- Reused the existing ingestion seam after extraction:
  - rooted workspace path enforcement remains unchanged
  - normalization still runs through `normalize_artifact_text()`
  - chunk persistence still targets `task_artifact_chunks`
  - ingestion status still transitions from `pending` to `ingested` on success
- Kept retrieval/compile contracts unchanged while updating extension-based media-type inference for semantic artifact retrieval so `.docx` artifacts remain typed consistently when `media_type_hint` is absent.
- Added unit coverage for:
  - deterministic DOCX chunk persistence
  - stable unsupported-media validation text
  - textless DOCX rejection
  - malformed DOCX rejection
  - rooted DOCX path enforcement
- Added integration coverage for:
  - supported DOCX ingestion with stable response shape
  - deterministic DOCX chunk ordering and boundaries
  - per-user isolation for DOCX ingestion/chunk listing
  - textless DOCX rejection
  - malformed DOCX rejection
  - rooted-path enforcement during DOCX ingestion

## exact DOCX-ingestion contract changes introduced

- No request contract changes.
- No response shape changes.
- No schema changes.
- Existing artifact-ingestion behavior now additionally accepts `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
- Extension-based media-type inference now recognizes `.docx` for the existing artifact and semantic-retrieval response paths.

## DOCX extraction path and chunking rule used

- Extraction path:
  - existing `POST /v0/task-artifacts/{task_artifact_id}/ingest`
  - resolve persisted workspace `local_path` plus persisted artifact `relative_path`
  - enforce rooted workspace boundary before any read
  - read the local DOCX package from disk
  - extract text from `word/document.xml` only
  - emit paragraph-ordered text from `w:t`, `w:tab`, `w:br`, and `w:cr`
  - reject invalid or textless DOCX artifacts deterministically
- Chunking rule:
  - normalize extracted text with CRLF/CR to LF conversion
  - split into fixed windows of 1000 characters
  - persist ordered rows with `sequence_no`, `char_start`, `char_end_exclusive`, and `text`
  - reported chunking rule string: `normalized_utf8_text_fixed_window_1000_chars_v1`

## incomplete work

- None within Sprint 5M scope.

## files changed

- `apps/api/src/alicebot_api/artifacts.py`
- `apps/api/src/alicebot_api/semantic_retrieval.py`
- `tests/unit/test_artifacts.py`
- `tests/unit/test_artifacts_main.py`
- `tests/integration/test_task_artifacts_api.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_artifacts.py tests/unit/test_artifacts_main.py`
  - Result: `44 passed in 0.43s`
- `./.venv/bin/python -m pytest tests/integration/test_task_artifacts_api.py`
  - Result: blocked in the sandbox because local Postgres access was denied (`psycopg.OperationalError: ... Operation not permitted`)
- `./.venv/bin/python -m pytest tests/unit`
  - Result: `386 passed in 0.63s`
- `./.venv/bin/python -m pytest tests/integration`
  - Result: `123 passed in 36.27s`

## unit and integration test results

- Unit suite passed in full.
- Integration suite passed in full against the Postgres-backed test path.
- The DOCX-specific API coverage is included in the passing `tests/integration/test_task_artifacts_api.py` module.

## one example DOCX artifact-ingestion response

Example verified by `test_task_artifact_docx_ingestion_and_chunk_endpoints_are_deterministic_and_isolated`:

```json
{
  "artifact": {
    "id": "<artifact-id>",
    "task_id": "<task-id>",
    "task_workspace_id": "<task-workspace-id>",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "docs/spec.docx",
    "media_type_hint": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "summary": {
    "total_count": 2,
    "total_characters": 1006,
    "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## one example chunk list response produced from a DOCX artifact

Example verified by `test_task_artifact_docx_ingestion_and_chunk_endpoints_are_deterministic_and_isolated`:

```json
{
  "items": [
    {
      "id": "<chunk-1-id>",
      "task_artifact_id": "<artifact-id>",
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 1000,
      "text": "<998 times 'A'>\nB",
      "created_at": "<created-at>",
      "updated_at": "<updated-at>"
    },
    {
      "id": "<chunk-2-id>",
      "task_artifact_id": "<artifact-id>",
      "sequence_no": 2,
      "char_start": 1000,
      "char_end_exclusive": 1006,
      "text": "BBBB\nC",
      "created_at": "<created-at>",
      "updated_at": "<updated-at>"
    }
  ],
  "summary": {
    "total_count": 2,
    "total_characters": 1006,
    "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- No implementation blockers remained.
- The first direct integration-test attempt from the sandbox could not reach local Postgres; rerunning the required integration suite with elevated local access succeeded.

## what remains intentionally deferred to later milestones

- broader PDF compatibility work
- OCR
- image extraction from DOCX
- document-layout reconstruction
- headers/footers/comments/track-changes-specific DOCX extraction expansion
- connector work
- runner-style orchestration
- retrieval-contract changes
- semantic-contract changes
- compile-contract changes
- UI work

## recommended next step

If richer document support is needed later, open a separate sprint for either broader DOCX coverage beyond `word/document.xml` or broader PDF compatibility, but keep both on the existing rooted artifact/chunk seam.
