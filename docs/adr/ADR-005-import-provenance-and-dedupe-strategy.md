# ADR-005: Import Provenance and Dedupe Strategy

## Status

Accepted (2026-04-08)

## Context

`P9-S37` broadens importer coverage from a single OpenClaw adapter to multiple production-usable import paths. Without one shared persistence strategy, importer behavior can drift on provenance fields, dedupe semantics, and replay outcomes.

The sprint requires deterministic duplicate-memory posture and explicit provenance across every shipped importer.

## Decision

Adopt one shared importer persistence strategy for all shipped `P9-S37` importers:

- all importer writes go through one shared persistence seam (`importers/common.py`)
- each importer must persist explicit `source_kind`
- each importer must persist a source-specific deterministic dedupe key in provenance (`<source>_dedupe_key`)
- each importer must persist source-specific context metadata (`<source>_workspace_id`, `<source>_source_path`, `<source>_source_item_id`, etc.)
- dedupe posture is deterministic and measured by replaying the same fixture and expecting `status=noop` with full duplicate skip counts
- importers map into the same shipped continuity capture/object model; they do not introduce source-specific retrieval semantics

## Consequences

Positive:

- importer behavior stays consistent and auditable across OpenClaw, Markdown, and ChatGPT import paths
- dedupe and provenance posture are testable with one shared expectation model
- future importer additions can reuse the same persistence contract

Negative:

- importer-specific provenance key names remain source-prefixed, so field vocabulary is intentionally explicit rather than fully normalized
- importer adapters still need source-specific normalization logic before shared persistence

## Alternatives Considered

### Keep per-importer persistence logic fully separate

Rejected because it encourages dedupe/provenance drift and makes cross-importer evaluation less reliable.

### Normalize all importer provenance into one unprefixed schema immediately

Rejected in `P9-S37` because it increases migration risk and coupling without improving short-term reproducibility goals.
