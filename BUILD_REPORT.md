# BUILD_REPORT

## sprint objective

Implement narrow PDF artifact parsing on the existing artifact-ingestion seam so already-registered visible PDF artifacts can be ingested into durable `task_artifact_chunks` rows without changing retrieval contracts, compile contracts, connectors, or UI.

## completed work

- Extended artifact media-type inference and validation to accept `application/pdf` and `.pdf` artifacts on the existing ingestion path.
- Implemented deterministic local PDF text extraction in `apps/api/src/alicebot_api/artifacts.py` by:
  - parsing the PDF object graph from local bytes only
  - walking the catalog/pages tree in page order
  - reading `/Contents` streams only
  - supporting unfiltered streams and `/FlateDecode` streams only
  - extracting text from PDF text-show operators (`Tj`, `TJ`, `'`, `"`) only
  - rejecting PDFs that are invalid, textless, or use unsupported stream filters/structures
- Kept ingestion status behavior unchanged: successful PDF ingestion updates `task_artifacts.ingestion_status` to `ingested`; rejected PDFs remain on the existing pending path and do not introduce a new status.
- Reused the existing normalization and chunking seam after extraction:
  - line endings normalize through `normalize_artifact_text()`
  - chunk persistence still uses `task_artifact_chunks`
  - chunk rule remains `normalized_utf8_text_fixed_window_1000_chars_v1`
- Added unit coverage for:
  - deterministic PDF chunk persistence
  - textless PDF rejection
  - PDF-rooted path enforcement
  - updated unsupported-media validation
- Added integration coverage for:
  - supported PDF ingestion with stable response shape
  - deterministic PDF chunk ordering and boundaries
  - PDF per-user isolation
  - textless PDF rejection
  - rooted-path enforcement during PDF ingestion

## exact PDF-ingestion contract changes introduced

- No request contract changes.
- No response contract shape changes.
- No schema changes.
- The only contract-level behavior change is that the existing artifact-ingestion seam now accepts `application/pdf` as a supported artifact media type and continues returning the existing `TaskArtifactIngestionResponse` and `TaskArtifactChunkListResponse` shapes.

## PDF extraction path and chunking rule used

- Extraction path:
  - existing `POST /v0/task-artifacts/{task_artifact_id}/ingest`
  - resolve persisted workspace `local_path` plus persisted artifact `relative_path`
  - enforce rooted workspace boundary before any read
  - for PDFs, parse local file bytes, walk the PDF page tree, decode supported content streams, and extract text-show operations in deterministic stream order
  - reject if no extractable text is found
- Chunking rule:
  - normalize extracted text with CRLF/CR to LF conversion
  - split into fixed windows of 1000 characters
  - persist ordered rows with `sequence_no`, `char_start`, `char_end_exclusive`, and `text`
  - reported chunking rule string: `normalized_utf8_text_fixed_window_1000_chars_v1`

## incomplete work

- None within Sprint 5L scope.

## files changed

- `apps/api/src/alicebot_api/artifacts.py`
- `tests/unit/test_artifacts.py`
- `tests/unit/test_artifacts_main.py`
- `tests/integration/test_task_artifacts_api.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_artifacts.py tests/unit/test_artifacts_main.py`
  - Result: `40 passed in 0.45s`
- `./.venv/bin/python -m pytest tests/integration/test_task_artifacts_api.py`
  - First sandboxed attempt failed because the suite could not reach the local Postgres instance (`psycopg.OperationalError: ... Operation not permitted`).
- `./.venv/bin/python -m pytest tests/unit`
  - Result: `382 passed in 0.73s`
- `./.venv/bin/python -m pytest tests/integration`
  - Result: `120 passed in 34.65s`

## unit and integration test results

- Unit suite passed in full.
- Integration suite passed in full against Postgres-backed tests.
- The new PDF-specific integration coverage is included in the passing `tests/integration/test_task_artifacts_api.py` module.

## one example PDF artifact-ingestion response

Example verified by the PDF integration assertion:

```json
{
  "artifact": {
    "id": "<artifact-id>",
    "task_id": "<task-id>",
    "task_workspace_id": "<task-workspace-id>",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "docs/spec.pdf",
    "media_type_hint": "application/pdf",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "summary": {
    "total_count": 2,
    "total_characters": 1006,
    "media_type": "application/pdf",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## one example chunk list response produced from a PDF artifact

Example verified by the PDF integration assertion:

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
    "media_type": "application/pdf",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- No repo-level implementation blockers remained.
- The integration suite required elevated access to reach the local Postgres test instance from this environment; after rerunning with that access, the full integration suite passed.

## what remains intentionally deferred to later milestones

- DOCX ingestion
- OCR
- image extraction from PDFs
- connector work
- runner-style orchestration
- retrieval-contract changes
- semantic-contract changes
- compile-contract changes
- UI work
- broader PDF compatibility beyond the current narrow text-only local content-stream extraction path

## recommended next step

Open a follow-up sprint only if broader document coverage is needed, starting with an explicit decision on whether to extend PDF compatibility further or add a separate DOCX ingestion seam without changing the current retrieval and compile contracts.
