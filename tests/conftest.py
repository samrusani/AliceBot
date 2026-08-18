from __future__ import annotations

import pytest

from alicebot_api.surface_flags import MCP_FULL_TOOLS_ENV


@pytest.fixture(autouse=True)
def enable_full_mcp_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep existing full-surface tests on the eleven core tools.

    Tests that assert the default handshake must delete this env.
    """
    monkeypatch.setenv(MCP_FULL_TOOLS_ENV, "1")
