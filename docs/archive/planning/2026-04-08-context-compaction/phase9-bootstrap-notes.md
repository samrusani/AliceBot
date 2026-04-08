# Phase 9 Bootstrap Notes

## Brief Distillation Summary

Phase 9 is not a new core-product reinvention phase. It is the public packaging and interoperability phase.

The durable product truth is:

- Alice is a memory and continuity layer for AI agents.
- The public v0.1 contract is capture, recall, resume, correct, and open loops.
- The launch path is local-first, CLI-first, MCP-enabled, and interop-proven through at least one external adapter.

The highest-value execution sequence is:

1. public core packaging
2. CLI
3. MCP server
4. OpenClaw adapter
5. importers and eval harness
6. docs and public release

## Recommended ADR List

### ADR 1: Public Core Package Boundary

- Why it deserves an ADR: defines what becomes `alice-core` versus what remains internal or deferred.
- Status in `P9-S33`: Accepted

### ADR 2: Public Runtime Baseline

- Why it deserves an ADR: decides whether Postgres + `pgvector` is the only supported runtime or whether a fallback such as SQLite exists.
- Status in `P9-S33`: Accepted

### ADR 3: MCP Tool Surface Contract

- Why it deserves an ADR: determines the size, naming, and stability promises of the public Alice MCP tool set.
- Status in `P9-S33`: Accepted

### ADR 4: OpenClaw Integration Boundary

- Why it deserves an ADR: defines whether the first external adapter is file-import only, MCP augmentation only, or both.
- Proposed status: Proposed

### ADR 5: Import Provenance and Dedupe Strategy

- Why it deserves an ADR: imported-memory correctness and duplicate handling are central to trust.
- Proposed status: Proposed

### ADR 6: OSS Boundary and License

- Why it deserves an ADR: determines what is public-safe, what is deferred, and how community usage is allowed.
- Proposed status: Proposed

### ADR 7: Public Evaluation Harness Scope

- Why it deserves an ADR: defines what benchmark claims Alice is allowed to make publicly and how they are reproduced.
- Proposed status: Proposed

## Archive Recommendations

Archive rather than keep in active agent memory:

- launch copy ideas beyond the product wedge
- broad go-to-market brainstorming not tied to build decisions
- long comparison-page prose
- team-role notes that do not affect ownership or architecture
- redundant sprint-by-sprint rationale once canonical phase docs exist
- any “nice to have” launch wishlist that is not part of the must-ship contract

Keep active:

- public wedge
- public v0.1 contract
- sprint sequencing
- package/runtime boundary decisions
- MCP surface decisions
- importer/eval requirements

## Suggested Folder Structure

```text
project-root/
├── README.md
├── PRODUCT_BRIEF.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── RULES.md
├── CHANGELOG.md
├── docs/
│   ├── adr/
│   ├── runbooks/
│   ├── archive/
│   ├── quickstart/
│   ├── architecture/
│   ├── integrations/
│   ├── mcp/
│   └── examples/
├── .ai/
│   ├── active/
│   ├── handoff/
│   ├── archive/
│   └── templates/
├── apps/
│   ├── api/
│   ├── web/
│   ├── cli/
│   └── mcp-server/
├── packages/
│   ├── alice-core/
│   ├── alice-importers/
│   ├── alice-openclaw/
│   └── alice-sdk-python/
├── eval/
├── examples/
├── fixtures/
├── scripts/
└── tests/
```

This should be treated as the target public-core structure for Phase 9, not necessarily an all-at-once refactor in Sprint 33.
