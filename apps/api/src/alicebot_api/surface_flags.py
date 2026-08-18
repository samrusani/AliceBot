from __future__ import annotations

import os
from collections.abc import Mapping


LEGACY_SURFACES_ENV = "ALICE_LEGACY_SURFACES"
MCP_LEGACY_TOOLS_ENV = "ALICE_MCP_LEGACY_TOOLS"
MCP_FULL_TOOLS_ENV = "ALICE_MCP_FULL_TOOLS"


def env_flag_enabled(name: str, *, environ: Mapping[str, str] | None = None) -> bool:
    """Return true only for Alice's explicit, fail-closed ``1`` flag value."""

    source = os.environ if environ is None else environ
    return source.get(name) == "1"


def legacy_surfaces_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    return env_flag_enabled(LEGACY_SURFACES_ENV, environ=environ)


def mcp_legacy_tools_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    source = os.environ if environ is None else environ
    return source.get(MCP_LEGACY_TOOLS_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def mcp_full_tools_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    source = os.environ if environ is None else environ
    return source.get(MCP_FULL_TOOLS_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


__all__ = [
    "LEGACY_SURFACES_ENV",
    "MCP_FULL_TOOLS_ENV",
    "MCP_LEGACY_TOOLS_ENV",
    "env_flag_enabled",
    "legacy_surfaces_enabled",
    "mcp_full_tools_enabled",
    "mcp_legacy_tools_enabled",
]
