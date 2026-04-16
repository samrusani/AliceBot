from __future__ import annotations

import json
from pathlib import Path

from alicebot_api.contracts import CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0, ContinuityBriefRecord


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    REPO_ROOT / "fixtures" / "reference_integrations" / "continuity_brief_agent_handoff_v1.json"
)


def test_reference_agent_fixture_tracks_continuity_brief_contract() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    brief = payload["brief"]

    required_top_level_keys = set(ContinuityBriefRecord.__annotations__)
    assert required_top_level_keys.issubset(set(brief))
    assert brief["assembly_version"] == CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0
    assert brief["brief_type"] == "agent_handoff"
    assert brief["next_suggested_action"]["title"] == "Next Action: Run release smoke"
    assert brief["open_loops"]["summary"]["total_count"] == 1
    assert brief["trust_posture"]["open_conflict_count"] == 0
