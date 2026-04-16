# Reference Integration Paths

This page is the path-selection guide for external builders adopting Alice on top of the shipped `v0.4.0` continuity, provider, and model-pack baseline.

## Default Recommendation

Start with the narrowest path that solves the integration need:

| Need | Default path | Demo or example |
|---|---|---|
| Generic external agent needs continuity in one call | `POST /v1/continuity/brief` or `alice_brief` | `docs/examples/reference-agent-examples.md` |
| Hermes owns orchestration and Alice supplies continuity workflows | provider plus MCP | `./.venv/bin/python scripts/run_hermes_bridge_demo.py` |
| Existing OpenClaw workspace data must become queryable in Alice | import, then use normal brief/recall/resume surfaces | `./scripts/use_alice_with_openclaw.sh` |
| Alice must target a non-default runtime provider or provider-aware pack | supporting Alice-side configuration for the paths above | `docs/integrations/phase14-provider-configuration.md` |

The three major adoption paths in this sprint are Generic Agent, Hermes, and OpenClaw. Provider and model-pack controls support those paths; they are not presented as a fourth standalone demo path.

## Path Details

### Generic Agent

Use this when you are integrating Alice into a Python or TypeScript agent without adopting a framework-specific bridge.

- prefer one-call continuity first
- use `alice_recall` or `alice_resume` only when your agent truly needs narrower output
- examples: `docs/examples/generic_python_agent.py` and `docs/examples/generic_typescript_agent.ts`
- reproducible demo: `./.venv/bin/python scripts/run_reference_agent_examples_demo.py`

### Hermes

Use Hermes when another runtime owns planning and execution, and Alice should stay focused on continuity plus review workflows.

- default recommendation: provider plus MCP
- fallback: MCP-only
- docs: `docs/integrations/hermes.md`
- reproducible demo: `./.venv/bin/python scripts/run_hermes_bridge_demo.py`

### OpenClaw

Use OpenClaw when the main requirement is importing existing workspace memory into Alice and then querying it through the normal Alice surfaces.

- imported data augments Alice continuity objects with explicit `OpenClaw` provenance
- after import, keep using the same brief, recall, resume, CLI, and MCP paths
- docs: `docs/integrations/openclaw.md`
- reproducible demo: `./scripts/use_alice_with_openclaw.sh`

### Provider And Pack Controls

Use the provider and model-pack docs when Alice itself owns runtime selection and prompting defaults.

- provider registration and capability discovery: `docs/integrations/phase14-provider-configuration.md`
- pack compatibility and binding posture: `docs/integrations/phase11-model-pack-compatibility.md`
- keep these controls in Alice rather than cloning them into Hermes or importer flows
- treat these controls as supporting configuration for the three major adoption paths above, not as a separate reference integration path

## Scope Guard

These paths package the shipped Alice surface. They do not introduce a second continuity contract, a second provider substrate, or a new pack system.
