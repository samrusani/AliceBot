# OpenClaw Alice Project Memory Skill

Use Alice as the project-scoped memory and continuity layer.

Default loop — one first call, then act, then write back:

1. Identify as OpenClaw.
2. Call `alice_context_pack` ONCE, project-scoped, before build or review work. The pack already carries decisions, procedures, open loops, sources, and contradictions — do not run raw searches first.
3. Perform the assigned build or review task, treating `staleness` notes and `contradicting_evidence` as caution signals.
4. Commit project-scoped memory via `alice_memory_commit` whenever you learn something worth keeping and the domain is `project`, including when the user has not asked you to remember it. It is the write verb for ordinary memory and what it records is immediately recallable. Use `alice_capture` for source documents, external evidence, raw notes and generated sprint summaries: it is review-gated, so `alice_recall` will not return it until a human reviews it.
5. Finish lifecycle work with `alice_memory_manage` (`confirm`/`undo`/`forget`) and create open loops for unresolved work with `alice_open_loops`.
6. Do not access or write non-project personal domains.

Context depth (request field `context_depth`; deterministic retrieval, never model synthesis): `minimal` for quick fact checks (full-text only, max 4 memories, no sources/contradictions), `low` (default) for normal pre-task context, `medium` for reviews and status reports (contradiction check on for every query type), `high` for audits and revision history (adds supersession chain notes). Explicit `include_sources`/`include_contradictions` override the tier default. The matching MCP tool arguments arrive in the same release — follow the server's `tools/list` schema.

Default identity:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","permission_profile":"project_scoped_agent","project_scope":["Alice"]}
```

Allowed direct commit domain: `project`.

Context/read domains may include `project`, `professional`, and `system` when policy allows.

Restricted by default: `personal`, `family`, `health`, `spiritual`, `legal`, `financial`, `regulated`.

Submit a sprint output with `alice_capture`. It is review-gated, which is what you want for a generated summary; the field carrying the text is `raw_text`:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","agent_run_id":"openclaw-sprint-001","task_id":"public-alpha-packaging","project_scope":["Alice"],"title":"OpenClaw sprint summary","raw_text":"Decision: Agents use scoped context packs and review-only memory proposals.","domain":"project","sensitivity":"private"}
```

Project memory commit:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","permission_profile":"project_scoped_agent","project_scope":["Alice"],"title":"Release gate decision","canonical_text":"Alice public alpha release gates require doctor, smokes, evals, and git diff checks before merge.","domain":"project","sensitivity":"private","confidence":0.94,"source_type":"direct_user_instruction"}
```

`title` and `canonical_text` are the only required fields on a commit. Everything else is optional, and any field not in the server's `tools/list` schema is rejected outright rather than ignored. A `project_scoped_agent` must send `domain: "project"`, or the commit is rejected.

Use `alice_memory_manage` for reversal or repair of a committed project memory: `action` of `undo`, `forget`, or `expire`, with the `memory_id` Alice returned. Never edit the database directly.

See `docs/alpha/openclaw-skill.md` for full recipes.
