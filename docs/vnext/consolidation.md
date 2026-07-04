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

- **Near-duplicate clustering.** Pairwise cosine similarity (numpy) over the
  user's active/accepted memories that have embeddings, single-linkage
  grouping at a configurable threshold (default `0.88`), minimum cluster size
  `2`. The pass is capped at the **5000** most recently updated in-scope
  memories; when the cap truncates, the bound is logged
  (`alicebot_api.vnext_consolidation` at INFO) and recorded in the artifact's
  *Skipped / Bounds* section.
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

1. re-derives each memory's vector from the exact embed-on-write text
   (`memory_embedding_text`: title + canonical_text + summary), which
   reproduces the stored vector for unmodified rows;
2. issues **one** `search_memories_vector` probe to learn which rows actually
   have stored embeddings (and records the probe row's self-distance as a
   staleness check — a non-zero value means the stored embeddings drifted and
   the backfill should be rerun);
3. computes the pairwise cosine matrix in numpy over that intersection.

Without a provider (or on a store without vector search) the run still
produces the report artifact, with an explicit skip reason and **zero**
candidates — there is no keyword-scan fallback and no placeholder candidate.

## Review-first guarantees

- Every proposal is a **candidate** memory (`status="candidate"`) and the
  report artifact is `needs_review`. Nothing enters trusted recall until a
  human accepts it.
- Accepting the candidate **is** the promotion decision.
- Members are never superseded automatically. Each candidate carries
  `metadata_json.consolidation.proposed_supersede` (all members for `merge`;
  everyone except the survivor for `dedup`) plus explicit
  `reviewer_instructions`: after accepting, supersede the listed members
  through the existing memory review/undo flows.
- Idempotent by digest: each cluster's candidate is keyed by a digest of its
  member ids, so re-running on the same input set reuses the existing
  candidate instead of duplicating it. The run-level artifact digest also
  covers cluster membership.
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

- At most 5000 memories are embedded and compared per run (`O(n^2)` cosine in
  float32; roughly 100 MB peak at the hard cap).
- At most `max_clusters` (default 20) proposals per run; extra clusters are
  reported in *Skipped / Bounds* and picked up on later runs.
- One embedding-provider batch pass over the in-scope memories and one
  vector-search probe per run; one model completion per cluster only in
  model-backed mode.
