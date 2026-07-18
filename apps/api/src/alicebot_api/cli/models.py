from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from alicebot_api.config import Settings


@dataclass(frozen=True, slots=True)
class CLIContext:
    settings: Settings
    database_url: str
    user_id: UUID


class ModelGenerationKwargs(TypedDict):
    generation_mode: str
    model_route_mode: str | None
    model_provider: str | None
    model: str | None
    model_temperature: float
    allow_cloud_private: bool
