"""Alice — the continuity layer for AI agents.

This is an early name-holding release. The packaged runtime (including the
zero-infrastructure SQLite on-ramp and the MCP server) ships from the main
repository until it lands on PyPI under this name.
"""

from __future__ import annotations

__version__ = "0.0.1"

REPOSITORY = "https://github.com/samrusani/AliceBot"


def main() -> None:
    print("Alice — the continuity layer for AI agents.")
    print(f"This is a pre-alpha placeholder release ({__version__}).")
    print(f"Install and run Alice from the repository for now: {REPOSITORY}")
    print("The packaged runtime and MCP server will ship under this name.")
