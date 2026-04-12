#!/usr/bin/env python3
"""Smoke validation for the Alice Hermes memory provider integration.

Validates:
- provider module loads and exposes required tools
- MemoryManager keeps built-in provider and only one external provider
- optional live prefetch against an Alice API endpoint
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from agent.builtin_memory_provider import BuiltinMemoryProvider
from agent.memory_manager import MemoryManager
from agent.memory_provider import MemoryProvider


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROVIDER_FILE = (
    REPO_ROOT
    / "docs"
    / "integrations"
    / "hermes-memory-provider"
    / "plugins"
    / "memory"
    / "alice"
    / "__init__.py"
)


class _DummyStore:
    def load_from_disk(self) -> None:
        return None

    def format_for_system_prompt(self, target: str) -> str:
        if target == "memory":
            return "# MEMORY.md\n- Keep responses deterministic."
        if target == "user":
            return "# USER.md\n- Prefer concise output."
        return ""


class _SecondExternalProvider(MemoryProvider):
    @property
    def name(self) -> str:
        return "second-external"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        return None

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return []


def _load_provider_class(provider_file: Path) -> type:
    spec = importlib.util.spec_from_file_location("alice_provider_module", provider_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load provider module: {provider_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider_class = getattr(module, "AliceMemoryProvider", None)
    if provider_class is None:
        raise RuntimeError("provider module has no AliceMemoryProvider class")
    return provider_class


def _run_structural_validation(provider_class: type) -> Dict[str, Any]:
    manager = MemoryManager()

    builtin = BuiltinMemoryProvider(
        memory_store=_DummyStore(),
        memory_enabled=True,
        user_profile_enabled=True,
    )
    alice = provider_class()
    second_external = _SecondExternalProvider()

    manager.add_provider(builtin)
    manager.add_provider(alice)
    manager.add_provider(second_external)

    tool_names = sorted(schema.get("name", "") for schema in alice.get_tool_schemas())
    bridge_status: Dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="alice-hermes-provider-status-") as temp_dir:
        hermes_home = Path(temp_dir)
        config_path = hermes_home / "alice_memory_provider.json"
        config_path.write_text(
            json.dumps(
                {
                    "base_url": "http://127.0.0.1:8000",
                    "user_id": "00000000-0000-0000-0000-000000000001",
                    "prefetch_recall_limit": 5,
                    "prefetch_max_recent_changes": 5,
                    "prefetch_max_open_loops": 5,
                    "prefetch_include_non_promotable_facts": False,
                    "sync_turn_capture_enabled": False,
                    "memory_write_capture_enabled": False,
                    "session_end_flush_timeout_seconds": 5.0,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        alice.initialize(
            session_id="smoke-status-session",
            hermes_home=str(hermes_home),
            platform="cli",
            agent_context="primary",
        )
        if hasattr(alice, "get_status"):
            bridge_status = alice.get_status(hermes_home=str(hermes_home))

    return {
        "provider_names": manager.provider_names,
        "builtin_first": manager.provider_names[:1] == ["builtin"],
        "single_external_enforced": manager.provider_names.count("second-external") == 0,
        "alice_registered": "alice" in manager.provider_names,
        "alice_tools": tool_names,
        "bridge_status": bridge_status,
    }


def _run_live_prefetch(
    *,
    provider_class: type,
    base_url: str,
    user_id: str,
    query: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="alice-hermes-provider-") as temp_dir:
        hermes_home = Path(temp_dir)
        config_path = hermes_home / "alice_memory_provider.json"
        config_path.write_text(
            json.dumps(
                {
                    "base_url": base_url,
                    "user_id": user_id,
                    "timeout_seconds": timeout_seconds,
                    "prefetch_recall_limit": 5,
                    "prefetch_max_recent_changes": 3,
                    "prefetch_max_open_loops": 3,
                    "prefetch_include_non_promotable_facts": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        provider = provider_class()
        provider.initialize(
            session_id="smoke-session",
            hermes_home=str(hermes_home),
            platform="cli",
            agent_context="primary",
        )
        context = provider.prefetch(query, session_id="smoke-session")

    return {
        "query": query,
        "context_length": len(context),
        "context_preview": context[:400],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="run_hermes_memory_provider_smoke.py",
        description="Validate Alice memory provider behavior against Hermes provider contracts.",
    )
    parser.add_argument(
        "--provider-file",
        type=Path,
        default=DEFAULT_PROVIDER_FILE,
        help="Path to the Alice provider __init__.py implementation.",
    )
    parser.add_argument(
        "--live-prefetch-query",
        default="",
        help="If set, run a live prefetch call against Alice API using this query.",
    )
    parser.add_argument(
        "--alice-base-url",
        default="http://127.0.0.1:8000",
        help="Alice API base URL for live prefetch mode.",
    )
    parser.add_argument(
        "--alice-user-id",
        default="00000000-0000-0000-0000-000000000001",
        help="Alice user UUID for live prefetch mode.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=8.0,
        help="HTTP timeout for live prefetch mode.",
    )

    args = parser.parse_args()

    provider_file = args.provider_file.resolve()
    if not provider_file.exists():
        raise RuntimeError(f"provider file not found: {provider_file}")

    provider_class = _load_provider_class(provider_file)

    result: Dict[str, Any] = {
        "provider_file": str(provider_file),
        "structural": _run_structural_validation(provider_class),
    }

    if args.live_prefetch_query:
        result["live_prefetch"] = _run_live_prefetch(
            provider_class=provider_class,
            base_url=args.alice_base_url,
            user_id=args.alice_user_id,
            query=args.live_prefetch_query,
            timeout_seconds=args.timeout_seconds,
        )

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
