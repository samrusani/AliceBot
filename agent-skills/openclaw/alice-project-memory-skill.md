# OpenClaw Alice Project Memory Skill

Use Alice as the project-scoped memory and continuity layer.

Default loop — one first call, then act, then write back:

1. Identify as OpenClaw.
2. Call `alice_context_pack` ONCE, project-scoped, before build or review work. The pack already carries decisions, procedures, open loops, sources, and contradictions — do not run raw searches first.
3. Perform the assigned build or review task, treating `staleness` notes and `contradicting_evidence` as caution signals.
4. Commit project-scoped memory via `alice_memory_commit` whenever you learn something worth keeping and the domain is `project`, including when the user has not asked you to remember it. It is the write verb for ordinary memory and what it records is immediately recallable. Use `alice_capture` for source documents, external evidence and raw notes: it is review-gated, so `alice_recall` will not return it until a human reviews it. Submit sprint outputs as reviewable agent outputs.
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

Submit sprint output:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","agent_run_id":"openclaw-sprint-001","task_id":"public-alpha-packaging","project_scope":["Alice"],"title":"OpenClaw sprint summary","content":"Decision: Agents use scoped context packs and review-only memory proposals.","output_type":"sprint_summary","domain":"project","sensitivity":"private","propose_memory":true}
```

Explicit project memory commit:

```json
{"agent_id":"openclaw","agent_type":"coding_agent","permission_profile":"project_scoped_agent","project_scope":["Alice"],"intent":"explicit_remember","title":"Release gate decision","canonical_text":"Alice public alpha release gates require doctor, smokes, evals, and git diff checks before merge.","domain":"project","sensitivity":"private","confidence":0.94,"source_type":"direct_user_instruction"}
```

Use `alice_vnext_undo_memory`, `alice_vnext_correct_memory`, or `alice_vnext_forget_memory` through Alice if a committed project memory needs reversal or repair. Never edit Postgres directly. The `alice_vnext_*` MCP tools are on the legacy surface and require `ALICE_MCP_LEGACY_TOOLS=1` on the Alice MCP server.

See `docs/alpha/openclaw-skill.md` for full recipes.
