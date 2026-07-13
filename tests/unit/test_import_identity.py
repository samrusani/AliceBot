from __future__ import annotations

from pathlib import Path
import sys

import alicebot_api.main as canonical_main


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
# Keep the forbidden identity split so the mechanical rewrite used to repair
# test imports cannot accidentally rewrite the guard itself.
ALIAS_PREFIX = "apps.api.src." + "alicebot_api"


def test_test_and_gate_sources_use_the_installed_package_identity() -> None:
    offenders: list[str] = []
    for root_name in ("tests", "eval", "scripts"):
        for path in (REPOSITORY_ROOT / root_name).rglob("*.py"):
            if ALIAS_PREFIX in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(REPOSITORY_ROOT)))

    assert offenders == [], (
        "Repository-only alicebot_api import aliases create duplicate module globals and evade "
        f"canonical coverage: {offenders}"
    )


def test_alicebot_main_has_one_runtime_module_identity() -> None:
    assert sys.modules["alicebot_api.main"] is canonical_main
    assert not any(name == ALIAS_PREFIX or name.startswith(f"{ALIAS_PREFIX}.") for name in sys.modules)
