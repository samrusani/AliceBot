# Alice

Alice is a local-first memory and continuity engine for AI agents.

Phase 9 Sprint 33 (`P9-S33`) defines one public-core path: install locally, load deterministic sample data, run recall, and run resumption from documented commands.

## Canonical Local Startup Path (`P9-S33`)

1. Copy environment defaults:
   `cp .env.example .env`
2. Create a virtualenv and install dependencies:
   `python3 -m venv .venv && ./.venv/bin/python -m pip install -e '.[dev]'`
3. Start local infrastructure:
   `docker compose up -d`
4. Apply migrations:
   `./scripts/migrate.sh`
5. Load deterministic sample data:
   `./scripts/load_sample_data.sh`
6. Start the API:
   `./scripts/api_dev.sh`

The sample fixture path is `fixtures/public_sample_data/continuity_v1.json` and defaults through `PUBLIC_SAMPLE_DATA_PATH`.

## Recall And Resumption Proof Commands

Run these after `./scripts/api_dev.sh` is serving on `127.0.0.1:8000`.

```bash
curl -sS "http://127.0.0.1:8000/v0/continuity/recall?user_id=00000000-0000-0000-0000-000000000001&query=local-first"
curl -sS "http://127.0.0.1:8000/v0/continuity/resumption-brief?user_id=00000000-0000-0000-0000-000000000001"
```

If `ALICEBOT_AUTH_USER_ID` is set in `.env`, the middleware rewrites `user_id` automatically and these query parameters can be omitted.

## Essential Verification Commands

- API health: `curl -sS http://127.0.0.1:8000/healthz`
- Backend tests: `./.venv/bin/python -m pytest tests/unit tests/integration`
- Web tests: `pnpm --dir apps/web test`

## Repo Structure

- `apps/api`: FastAPI runtime and continuity core seams
- `apps/web`: operator shell
- `fixtures/public_sample_data`: deterministic public-core sample dataset
- `scripts`: startup, migration, and sample-data load scripts
- `docs`: product, architecture, ADRs, and Phase 9 planning docs

## Canonical Docs

- [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [RULES.md](RULES.md)
- [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- [docs/phase9-product-spec.md](docs/phase9-product-spec.md)
- [docs/phase9-sprint-33-38-plan.md](docs/phase9-sprint-33-38-plan.md)
- [docs/phase9-public-core-boundary.md](docs/phase9-public-core-boundary.md)
- [docs/phase9-bootstrap-notes.md](docs/phase9-bootstrap-notes.md)

## Legacy Compatibility Marker

Repository lineage remains continuous through Phase 3 Sprint 9.

Canonical gate entrypoints: `scripts/run_phase4_*.py` are the control-plane canonical MVP release gates.
