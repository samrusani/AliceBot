PYTHON ?= ./.venv/bin/python
ALICEBOT ?= ./.venv/bin/alicebot
PNPM ?= pnpm
WEB_DIR ?= apps/web
DIST_DIR ?= dist
PROJECT_VERSION = $(shell $(PYTHON) -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
ALICE_WEB_HOST ?= 127.0.0.1
ALICE_WEB_PORT ?= 3000

.PHONY: setup migrate api dev runtime web-build doctor vnext scheduler alpha-check test-web test-python test-longmemeval release-static release-identity release-finalization-check release-artifacts release-check

setup:
	@python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' || \
		{ echo "ERROR: Alice requires Python 3.12+ but python3 is $$(python3 -V 2>&1 | cut -d' ' -f2)." ; \
		  echo "Point python3 at 3.12+ (e.g. 'uv python install 3.12' or your package manager) and re-run." ; exit 1; }
	@test -f .env || cp .env.example .env
	@test -f .env.lite || cp .env.lite.example .env.lite
	@test -f $(WEB_DIR)/.env.local || cp $(WEB_DIR)/.env.local.example $(WEB_DIR)/.env.local
	./scripts/validate_env.sh .env .env.lite $(WEB_DIR)/.env.local
	python3 -m venv .venv
	$(PYTHON) -m pip install -e '.[dev]'
	PNPM="$(PNPM)" WEB_DIR="$(WEB_DIR)" ./scripts/pnpm_web_install.sh
	@echo "Setup complete. Next: make migrate && make doctor"

migrate:
	./scripts/dev_up.sh

api:
	APP_RELOAD=false ./scripts/api_dev.sh

doctor:
	$(ALICEBOT) vnext doctor --fix-safe --ci

dev:
	./scripts/dev_up.sh
	APP_RELOAD=false ./scripts/api_dev.sh & \
	api_pid=$$!; \
	$(PNPM) --dir $(WEB_DIR) dev & \
	web_pid=$$!; \
	trap 'kill $$api_pid $$web_pid 2>/dev/null || true' INT TERM EXIT; \
	wait $$api_pid $$web_pid

runtime:
	./scripts/dev_up.sh
	$(PNPM) --dir $(WEB_DIR) build
	APP_RELOAD=false ./scripts/api_dev.sh & \
	api_pid=$$!; \
	$(PNPM) --dir $(WEB_DIR) start --hostname $(ALICE_WEB_HOST) --port $(ALICE_WEB_PORT) & \
	web_pid=$$!; \
	trap 'kill $$api_pid $$web_pid 2>/dev/null || true' INT TERM EXIT; \
	wait $$api_pid $$web_pid

web-build:
	$(PNPM) --dir $(WEB_DIR) build

vnext:
	@echo "Start the low-CPU local runtime with: make runtime"
	@echo "Use make dev only when editing the web UI."
	@echo "Then open: http://localhost:$(ALICE_WEB_PORT)/vnext"

scheduler:
	$(ALICEBOT) vnext scheduler daemon start --foreground

alpha-check:
	$(ALICEBOT) vnext alpha check

test-python:
	$(PYTHON) -m pytest tests/unit -q --cov=alicebot_api --cov-report=term --cov-fail-under=50
	$(PYTHON) -m pytest tests/integration -q

test-web:
	$(PNPM) --dir $(WEB_DIR) test
	$(PNPM) --dir $(WEB_DIR) lint
	$(PNPM) --dir $(WEB_DIR) build

test-longmemeval:
	$(PYTHON) -m pytest eval/longmemeval -q
	$(PYTHON) scripts/check_longmemeval_evidence.py

release-static:
	$(PYTHON) scripts/check_control_doc_truth.py
	$(PYTHON) scripts/release_check.py
	$(PYTHON) -m ruff check apps/api/src/alicebot_api scripts tests eval/longmemeval
	$(PYTHON) -m mypy --follow-imports=skip --ignore-missing-imports scripts/release_check.py scripts/test_distribution_artifact.py scripts/check_control_doc_truth.py scripts/check_github_release_checks.py

release-identity:
	git fetch --no-tags origin main
	$(PYTHON) scripts/release_check.py --require-clean --require-main-head

release-finalization-check: release-identity
	$(PYTHON) scripts/release_check.py --require-clean --require-main-head --require-finalized-release-docs

release-artifacts:
	$(PYTHON) -m build --outdir $(DIST_DIR)
	$(PYTHON) -m twine check $(DIST_DIR)/*
	$(PYTHON) scripts/release_check.py --dist-dir $(DIST_DIR) --write-checksums
	$(PYTHON) scripts/test_distribution_artifact.py $(DIST_DIR)/*.whl $(DIST_DIR)/*.tar.gz --expected-version $(PROJECT_VERSION)

# Canonical pre-publication gate. PostgreSQL must be available with the same
# role-separated environment used by tests/integration.
release-check: release-identity release-static test-python test-longmemeval test-web release-artifacts
	ALICEBOT_EVAL_DATABASE_URL=sqlite:///:memory: $(PYTHON) -m alicebot_api eval run --suite all
