# Hermes Reference Integration

Hermes is the reference path when another agent runtime owns orchestration and Alice supplies continuity, recall, resumption, and review workflows.

Recommended deployment shape: `provider_plus_mcp`.

- Provider gives Hermes always-on prefetch plus post-turn capture hooks.
- MCP gives Hermes the deeper Alice tool surface, including `alice_brief`, targeted recall, review, and correction flows.
- MCP-only remains available when provider install is blocked.

## What Stays Stable

Hermes does not create a second Alice runtime contract.

- one-call continuity stays `POST /v1/continuity/brief`, `alice brief`, and `alice_brief`
- provider registration and runtime shaping stay on the shipped Alice provider surface
- model packs stay Alice-side defaults layered on top of the shipped provider/runtime baseline

Use these docs when you need the underlying Alice runtime controls:

- `docs/integrations/one-call-continuity.md`
- `docs/integrations/phase14-provider-configuration.md`
- `docs/integrations/phase11-model-pack-compatibility.md`

## Choose A Mode

| Mode | Use it when | What you get |
|---|---|---|
| Provider + MCP | default Hermes deployment | prefetch, post-turn lifecycle hooks, plus full Alice tool access |
| MCP-only | provider plugin install is blocked | explicit Alice tools with no provider lifecycle hooks |
| Provider + MCP + skill pack | you want stronger prompting and workflow policy | recommended runtime shape plus Hermes-side policy guidance |

## Recommended Setup

1. Install the Alice Hermes memory provider:

```bash
./scripts/install_hermes_alice_memory_provider.py
```

2. Configure Hermes memory for `alice` and keep Alice attached through `mcp_servers`.

3. Validate the full bridge path:

```bash
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

Expected JSON output:

- `status` = `pass`
- `recommended_path` = `provider_plus_mcp`
- provider smoke returns `structural.bridge_status.ready = true`
- MCP smoke validates recall, open-loop, capture, and review flows

## Minimal Config Shape

```yaml
memory:
  provider: alice

mcp_servers:
  alice_core:
    command: "/path/to/alice/.venv/bin/python"
    args: ["-m", "alicebot_api.mcp_server"]
    env:
      DATABASE_URL: "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
      ALICEBOT_AUTH_USER_ID: "00000000-0000-0000-0000-000000000001"
      PYTHONPATH: "/path/to/alice/apps/api/src:/path/to/alice/workers"
```

Use the full operator examples for production config details:

- `docs/integrations/examples/hermes-config.provider-plus-mcp.yaml`
- `docs/integrations/examples/hermes-config.mcp-only.yaml`

## One-Call Continuity Inside Hermes

For generic continuity lookups, start with `alice_brief`.

That keeps Hermes on the shipped one-call continuity surface instead of manually choreographing recall plus resumption plus conflict checks. Reach for narrower tools only when Hermes explicitly needs them:

- `alice_recall` for ranked facts only
- `alice_resume` for the legacy resume layout
- `alice_review_queue` and `alice_review_apply` for explicit review workflows

## Provider And Pack Guidance

Hermes should treat Alice provider and model-pack decisions as Alice runtime configuration, not Hermes configuration.

- register or update provider connections through the Alice provider endpoints documented in `docs/integrations/phase14-provider-configuration.md`
- bind model packs in Alice when you want provider-aware defaults without changing Hermes orchestration
- keep Hermes focused on when to call Alice, not on reproducing Alice runtime policy

## Fallback Path

If provider install is not available yet, keep:

- `memory.provider: builtin`
- the Alice `mcp_servers` block
- the same `alice_brief` / `alice_recall` / review tool usage

Then validate with:

```bash
hermes mcp test alice_core
./.venv/bin/python scripts/run_hermes_mcp_smoke.py
```

## Related Docs

- `docs/integrations/hermes-bridge-operator-guide.md`
- `docs/integrations/hermes-memory-provider.md`
- `docs/integrations/hermes-skill-pack.md`
- `docs/integrations/reference-paths.md`
