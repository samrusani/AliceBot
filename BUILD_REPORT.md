# BUILD_REPORT

## sprint objective

Implement narrow RFC822 email artifact parsing on the existing artifact-ingestion seam so already-registered visible RFC822 email artifacts can be ingested into durable `task_artifact_chunks` rows without changing retrieval contracts, compile contracts, connectors, or UI.

## completed work

- Extended the existing artifact media-type support to accept RFC822 email artifacts:
  - media type: `message/rfc822`
  - extension inference: `.eml`
- Implemented deterministic local RFC822 parsing in `apps/api/src/alicebot_api/artifacts.py` by:
  - parsing email bytes locally with Python's standard-library email parser under `raise_on_defect=True`
  - extracting a narrow header block from top-level headers only
  - extracting plain-text body content from `text/plain` leaf parts only
  - excluding nested `message/rfc822` payloads from body extraction
  - rejecting malformed RFC822 payloads deterministically
  - rejecting textless or unsupported-body emails when no extractable plain-text body exists
- Reused the existing ingestion seam after extraction:
  - rooted workspace path enforcement remains unchanged
  - normalization still runs through `normalize_artifact_text()`
  - chunk persistence still targets `task_artifact_chunks`
  - ingestion status still transitions from `pending` to `ingested` on success
- Kept request, response, schema, retrieval, and compile contracts unchanged while updating extension-based media-type inference for semantic artifact retrieval so `.eml` artifacts remain typed consistently when `media_type_hint` is absent.
- Added unit coverage for:
  - deterministic RFC822 chunk persistence
  - multipart plain-text-part selection while ignoring HTML and attachments
  - nested-email exclusion for encapsulated `message/rfc822` parts
  - stable unsupported-media validation text
  - textless RFC822 rejection
  - malformed RFC822 rejection
  - rooted RFC822 path enforcement
- Added integration coverage for:
  - supported RFC822 ingestion with stable response shape
  - deterministic RFC822 chunk ordering and boundaries
  - per-user isolation for RFC822 ingestion and chunk listing
  - nested-email exclusion for encapsulated `message/rfc822` parts
  - textless RFC822 rejection
  - malformed RFC822 rejection
  - rooted-path enforcement during RFC822 ingestion

## exact RFC822-ingestion contract changes introduced

- No request contract changes.
- No response shape changes.
- No schema changes.
- Existing artifact-ingestion behavior now additionally accepts `message/rfc822`.
- Extension-based media-type inference now recognizes `.eml` for the existing artifact and semantic-retrieval response paths.

## email extraction path and chunking rule used

- Extraction path:
  - existing `POST /v0/task-artifacts/{task_artifact_id}/ingest`
  - resolve persisted workspace `local_path` plus persisted artifact `relative_path`
  - enforce rooted workspace boundary before any read
  - read the local RFC822 email from disk
  - parse it locally with the standard-library email parser
  - extract a deterministic header block plus plain-text body text while excluding nested encapsulated emails
  - reject invalid or textless RFC822 artifacts deterministically
- Chunking rule:
  - normalize extracted text with CRLF/CR to LF conversion
  - split into fixed windows of 1000 characters
  - persist ordered rows with `sequence_no`, `char_start`, `char_end_exclusive`, and `text`
  - reported chunking rule string: `normalized_utf8_text_fixed_window_1000_chars_v1`

## header/body selection rule used

- Header rule:
  - include only these top-level headers, in this order, when present and non-empty:
    - `From`
    - `To`
    - `Cc`
    - `Bcc`
    - `Reply-To`
    - `Subject`
    - `Date`
    - `Message-ID`
  - normalize header whitespace by collapsing internal whitespace runs to single spaces
- Body rule:
  - recurse through multipart body structure only
  - include only leaf `text/plain` parts
  - skip multipart containers as extracted content
  - skip parts marked as attachments
  - skip parts with filenames
  - skip nested descendant `message/*` parts, including `message/rfc822`
  - strip each selected part and join non-empty body parts with a blank line
  - reject the artifact if no extractable plain-text body part remains

## incomplete work

- None within Sprint 5N scope.

## files changed

- `apps/api/src/alicebot_api/artifacts.py`
- `apps/api/src/alicebot_api/semantic_retrieval.py`
- `tests/unit/test_artifacts.py`
- `tests/unit/test_artifacts_main.py`
- `tests/unit/test_semantic_retrieval.py`
- `tests/integration/test_task_artifacts_api.py`
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_artifacts.py tests/unit/test_semantic_retrieval.py tests/unit/test_artifacts_main.py`
  - Result: `59 passed in 0.31s`
- `./.venv/bin/python -m pytest tests/integration/test_task_artifacts_api.py`
  - Result: `15 passed in 5.08s`
- `./.venv/bin/python -m pytest tests/unit`
  - Result: `394 passed in 0.61s`
- `./.venv/bin/python -m pytest tests/integration`
  - Result: `127 passed in 37.01s`

## unit and integration test results

- Unit suite passed in full.
- Integration suite passed in full against the Postgres-backed test path.
- The RFC822-specific API coverage now includes nested-email exclusion and is included in the passing `tests/integration/test_task_artifacts_api.py` module.

## one example email artifact-ingestion response

Example verified by `test_task_artifact_rfc822_ingestion_and_chunk_endpoints_are_deterministic_and_isolated`:

```json
{
  "artifact": {
    "id": "<artifact-id>",
    "task_id": "<task-id>",
    "task_workspace_id": "<task-workspace-id>",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "mail/update.eml",
    "media_type_hint": "message/rfc822",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "summary": {
    "total_count": 2,
    "total_characters": 1006,
    "media_type": "message/rfc822",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## one example chunk list response produced from an email artifact

Example verified by `test_task_artifact_rfc822_ingestion_and_chunk_endpoints_are_deterministic_and_isolated`:

```json
{
  "items": [
    {
      "id": "<chunk-1-id>",
      "task_artifact_id": "<artifact-id>",
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 1000,
      "text": "From: Alice <alice@example.com>\nTo: Bob <bob@example.com>\nSubject: Sprint Update\n\n<916 times 'A'>\nB",
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
    "media_type": "message/rfc822",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- No implementation blockers remained.

## what remains intentionally deferred to later milestones

- live Gmail connector work
- OAuth
- Calendar connector work
- HTML-to-text rendering beyond the current explicit plain-text-only rule
- attachment extraction
- OCR
- retrieval-contract changes
- semantic-retrieval-contract changes
- compile-contract changes
- runner-style orchestration
- UI work

## recommended next step

If the product needs to move from local RFC822 files to inbox access, open a separate sprint for read-only Gmail connector and auth work while keeping this extracted-text-to-chunk seam unchanged.
