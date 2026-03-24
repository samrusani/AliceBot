from __future__ import annotations

from dataclasses import dataclass

from alicebot_api.contracts import AgentProfileRecord, DEFAULT_AGENT_PROFILE_ID


@dataclass(frozen=True, slots=True)
class AgentProfileDefinition:
    profile_id: str
    name: str
    description: str

    def as_record(self) -> AgentProfileRecord:
        return {
            "id": self.profile_id,
            "name": self.name,
            "description": self.description,
        }


_PHASE3_PROFILE_REGISTRY: tuple[AgentProfileDefinition, ...] = (
    AgentProfileDefinition(
        profile_id="assistant_default",
        name="Assistant Default",
        description="General-purpose assistant profile for baseline conversations.",
    ),
    AgentProfileDefinition(
        profile_id="coach_default",
        name="Coach Default",
        description="Coaching-oriented profile focused on guidance and accountability.",
    ),
)

_PHASE3_PROFILE_LOOKUP: dict[str, AgentProfileDefinition] = {
    profile.profile_id: profile for profile in _PHASE3_PROFILE_REGISTRY
}


def list_agent_profiles() -> list[AgentProfileRecord]:
    return [profile.as_record() for profile in _PHASE3_PROFILE_REGISTRY]


def list_agent_profile_ids() -> list[str]:
    return [profile.profile_id for profile in _PHASE3_PROFILE_REGISTRY]


def get_agent_profile(profile_id: str) -> AgentProfileRecord | None:
    profile = _PHASE3_PROFILE_LOOKUP.get(profile_id)
    if profile is None:
        return None
    return profile.as_record()


def get_default_agent_profile_id() -> str:
    return DEFAULT_AGENT_PROFILE_ID
