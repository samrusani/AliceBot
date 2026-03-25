from __future__ import annotations

from alicebot_api.contracts import AgentProfileRecord, DEFAULT_AGENT_PROFILE_ID
from alicebot_api.store import ContinuityStore


def list_agent_profiles(store: ContinuityStore) -> list[AgentProfileRecord]:
    return [
        {
            "id": profile["id"],
            "name": profile["name"],
            "description": profile["description"],
        }
        for profile in store.list_agent_profiles()
    ]


def list_agent_profile_ids(store: ContinuityStore) -> list[str]:
    return [profile["id"] for profile in store.list_agent_profiles()]


def get_agent_profile(store: ContinuityStore, profile_id: str) -> AgentProfileRecord | None:
    profile = store.get_agent_profile_optional(profile_id)
    if profile is None:
        return None
    return {
        "id": profile["id"],
        "name": profile["name"],
        "description": profile["description"],
    }


def get_default_agent_profile_id() -> str:
    return DEFAULT_AGENT_PROFILE_ID
