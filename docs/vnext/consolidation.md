# Memory Consolidation

`memory_consolidation` finds near-duplicate memories, proposes one
consolidated candidate per cluster, and reports repeated preferences — all
behind the review gate. It never promotes, merges, or supersedes anything on
its own.

Implementation: `apps/api/src/alicebot_api/vnext_consolidation.py`
(`VNextConsolidationService.generate_memory_consolidation`), with the
model-backed merge seam in
`apps/api/src/alicebot_api/vnext_model_intelligence.py`
(`generate_consolidation_merge`).

## What runs deterministically (no model, no cloud)

- **Near-duplicate clustering.** Blockwise cosine similarity over the user's
  active/accepted memories that have embeddings, with cohesive complete-link
  admission at a configurable threshold (default `0.88`) and minimum cluster size
  `2`. The pass is capped at the **2000** most recently updated in-scope
  memories; when the cap truncates, the bound is logged
  (`alicebot_api.vnext_consolidation` at INFO) and recorded in the artifact's
  *Skipped / Bounds* section. The bundled stores apply domain, sensitivity,
  status, and limit in the database, so the cap also bounds rows loaded into
  the consolidation process.
- **Dedup proposals.** Without a real model, each cluster produces a `dedup`
  proposal: the longest-text member is the survivor, its `canonical_text` is
  copied **verbatim** into the candidate, and the other members are listed as
  duplicates. No text is synthesized deterministically — dedup never invents
  a merged sentence.
- **Reinforced-preference detection.** Clusters whose members are all
  `preference`/`routine` memories and span **>= 3 distinct sources or >= 3
  distinct days** are flagged in the report as evidence of a stable
  preference, suggested (only suggested) for promotion or a confidence bump.
- **The report artifact** itself: sections for clusters found, proposals
  created, reinforced preferences, and skipped/bounds.

## What needs a model

Only the `merge` proposal kind. When the request runs with
`generation_mode="model_backed"` and routing resolves to a real provider
(`model_route_mode="cloud_allowed"` on a non-restricted scope — the same
`resolve_model_route` policy every other workflow uses), the service asks the
model to write one consolidated `canonical_text` + `title` per cluster via
`generate_consolidation_merge`. The prompt is grounded (member texts and
provenance counts, marked `[UNTRUSTED_CONTEXT_JSON]`), instructs "no new
facts", and the output passes through the shared injection-stripping filter
plus a token-overlap grounding check. If routing lands on the deterministic
or disabled provider, or the output is unparseable/ungrounded, the model path
returns a **structured refusal** and the cluster falls back to `dedup` — the
refusal reason is recorded in the candidate metadata.

## What needs embeddings

Everything upstream of the report: clustering requires an embedding provider
(`ALICE_EMBEDDINGS_BASE_URL` / `ALICE_EMBEDDINGS_MODEL` /
`ALICE_EMBEDDINGS_API_KEY`, the same embed-on-write configuration). Store
rows never expose the raw embedding column, so the service:

1. asks the store for exact embedding presence across the selected IDs before
   making a provider call; this is a non-null vector presence check and does
   not by itself claim signature compatibility;
2. re-derives each eligible memory's vector from the exact embed-on-write text
   (`memory_embedding_text`: title + canonical_text + summary), which
   reproduces the stored vector for unmodified rows;
3. evaluates cosine similarities in bounded float32 row blocks and admits a
   member only when it meets the threshold against every existing cluster
   member. It never materializes an `n x n` matrix.

Without a provider, or on a store without the exact-ID embedding-presence read,
the run still produces the report artifact with an explicit skip reason and
**zero** candidates. ANN/vector-search capability remains optional here:
clustering uses the exact presence read plus provider-rederived vectors, not a
nearest-neighbor query. There is no keyword-scan fallback or placeholder
candidate.

The roll-up pass's **semantic grouping tier** (`vnext_rollups`) shares this
access pattern, provider instance, and bounded per-run embedding cache: rows
already embedded for consolidation are not embedded again. When embeddings
are configured, memories that the deterministic entity/lexical roll-up passes
left unclaimed are grouped through the same cohesive all-pairs gate at one
conservatively swept threshold (chosen by a blockwise silhouette-style
criterion, disclosed in the outcome metadata as
`rollups.semantic_grouping`), so aggregation topics whose
instances share no anchor token ("kitchen items replaced" =
faucet/toaster/shelves) can still form one review-gated card. Every semantic
cluster passes the same roll-up utility gate, with mean pairwise similarity
standing in for the label-stem coherence test. Without a provider the tier
is dormant and the roll-up outputs are byte-identical to the
lexical/entity-only behavior.

## Review-first guarantees

- Every proposal is a **candidate** memory (`status="candidate"`) and the
  report artifact is `needs_review`. Nothing enters trusted recall until a
  human accepts it.
- Accepting the candidate **is** the promotion decision.
- Members are never superseded automatically. Each candidate carries
  `metadata_json.consolidation.proposed_supersede` (all members for `merge`;
  everyone except the survivor for `dedup`) plus explicit
  `reviewer_instructions`. The canonical acceptance transaction validates
  every reviewed input, promotes the candidate, and then executes exactly
  those supersessions. Roll-up cards keep their member memories active;
  accepting a roll-up revision retires only the previous card.
- Every merge, dedup, and roll-up candidate persists a version snapshot for
  each reviewed input: id, status, `updated_at`, and a digest of its content.
  Acceptance locks and validates the complete snapshot set before its first
  write. A missing, corrected, forgotten, redacted, or superseded member
  therefore stale-fails with no partial promotion or supersession.
- Correcting or retiring a member also marks related pending candidates
  `stale` and `not_promotable` in the same transaction. The invalidation is
  recorded in candidate metadata, a revision, and an event. Stores without
  the optional proactive lookup still fail closed during snapshot validation.
- Idempotent by versioned digest: candidate identity covers the member ids,
  status, and content versions, so re-running unchanged input reuses the
  existing candidate while a corrected same-id member produces a new review
  proposal. The run-level artifact digest also covers cluster membership.
- Candidate provenance: `source_refs` link back to every member
  (`memory:<id>`) and to the members' own sources; `source_event_ids` are the
  union of the members'.

## Candidate metadata shape

```json
{
  "candidate_kind": "memory_consolidation",
  "consolidation_digest": "<cluster digest>",
  "source_refs": ["memory:...", "source:..."],
  "review_required": true,
  "consolidation": {
    "cluster_member_ids": ["..."],
    "member_snapshots": [
      {"id": "...", "status": "active", "updated_at": "...", "content_digest": "..."}
    ],
    "similarity_stats": {"pair_count": 3, "min": 0.99, "max": 1.0, "mean": 0.99},
    "proposal_kind": "merge | dedup",
    "model_provenance": {"provider": "...", "model": "...", "prompt_hash": "sha256:..."},
    "survivor_memory_id": "... (dedup only)",
    "proposed_supersede": ["..."],
    "merge_refusal": "reason when a model merge fell back to dedup",
    "reviewer_instructions": ["..."]
  }
}
```

## How to schedule it

The scheduler already dispatches the `memory_consolidation` workflow type
(`vnext_scheduler.py`); enable it like any other workflow and it runs
deterministically by default. Workflow options pass through the scheduler's
generation kwargs (`generation_mode`, `model_route_mode`, `model_provider`,
`model`, `model_temperature`, `allow_cloud_private`,
`create_candidate_memories`, plus the report-scan limits). Clustering knobs
(`similarity_threshold`, `max_embedded_memories`, `min_cluster_size`,
`max_clusters`) are fields on `MemoryConsolidationRequest` and can also be
supplied by direct callers via
`metadata_json["consolidation_options"] = {"similarity_threshold": 0.9, ...}`.

## Bounds and costs

- At most 2000 memories are compared per run (`O(n^2)` cosine work in
  float32). Similarities are processed in bounded row blocks (about 1 MB at
  the default 128 x 2000 cap), not a dense 16 MB matrix; the report records
  peak block bytes and the logical unique-pair count under
  `metadata_json.consolidation.resource_guard`.
- At most `max_clusters` (default 20) proposals per run; extra clusters are
  reported in *Skipped / Bounds* and picked up on later runs.
- One exact store presence read precedes provider work. The provider embeds
  only eligible rows, and semantic rollups reuse the consolidation cache; one
  model completion per cluster occurs only in model-backed mode.
