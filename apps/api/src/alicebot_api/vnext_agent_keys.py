from __future__ import annotations

from dataclasses import replace
import hashlib
import hmac
import secrets
from typing import Mapping, Protocol

from alicebot_api.vnext_agent_control import (
    PERMISSION_PROFILES,
    AgentIdentity,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


AGENT_KEY_PREFIX = "alice_sk_"
AGENT_KEY_PREFIX_LENGTH = 12
AGENT_KEY_AUTH = "agent_api_key"
UNAUTHENTICATED_LOCAL_AUTH = "unauthenticated_local"

# Privilege ordering used to reject payloads that claim a higher profile than
# the key grants. Downgrades (claiming a lower profile) are always allowed.
PROFILE_PRIVILEGE_ORDER = (
    "read_only_agent",
    "memory_proposal_agent",
    "project_scoped_agent",
    "trusted_local_agent",
    "admin_agent",
)
_PROFILE_RANKS = {profile: rank for rank, profile in enumerate(PROFILE_PRIVILEGE_ORDER)}


class AgentKeyValidationError(ValueError):
    """Raised when an agent API key request is malformed."""


class AgentKeyAuthenticationError(PermissionError):
    """Raised when agent API key authentication or authorization fails."""

    def __init__(self, message: str, *, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


class AgentKeyStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def create_agent_api_key(self, key: JsonObject) -> JsonObject: ...

    def get_agent_api_key_by_hash(self, key_hash: str) -> JsonObject | None: ...

    def list_agent_api_keys(self, *, limit: int = 50) -> list[JsonObject]: ...

    def revoke_agent_api_key(self, *, key_id: str) -> JsonObject | None: ...

    def touch_agent_api_key(self, *, key_id: str) -> JsonObject: ...

    def count_active_agent_api_keys(self) -> int: ...


def mint_agent_key() -> str:
    """Mint a new raw agent API key. Only its sha256 hash is ever stored."""

    return f"{AGENT_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_agent_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def agent_key_prefix(raw_key: str) -> str:
    return raw_key[:AGENT_KEY_PREFIX_LENGTH]


def agent_key_from_authorization(authorization: object) -> str | None:
    """Extract a raw agent API key from an Authorization header value.

    Only ``Bearer alice_sk_...`` (or a bare ``alice_sk_...`` value) is treated
    as an agent API key; other Authorization values are ignored so unrelated
    bearer tokens never reach the key verifier.
    """

    if not isinstance(authorization, str):
        return None
    value = authorization.strip()
    if not value:
        return None
    scheme, _, token = value.partition(" ")
    token = token.strip()
    if scheme.casefold() == "bearer" and token.startswith(AGENT_KEY_PREFIX):
        return token
    if value.startswith(AGENT_KEY_PREFIX):
        return value
    return None


def create_agent_key(
    store: AgentKeyStore,
    *,
    user_id: object,
    agent_id: str,
    permission_profile: str,
    label: str | None = None,
) -> tuple[JsonObject, str]:
    """Create an agent API key. Returns (record, raw_key).

    The raw key is returned exactly once and never persisted; the store keeps
    only its sha256 hash plus a short prefix for identification.
    """

    normalized_agent_id = " ".join(str(agent_id).split()).strip()
    if not normalized_agent_id:
        raise AgentKeyValidationError("agent_id is required")
    if permission_profile not in PERMISSION_PROFILES:
        raise AgentKeyValidationError(
            f"permission_profile must be one of {', '.join(PERMISSION_PROFILES)}"
        )
    normalized_label = " ".join(str(label).split()).strip() if label is not None else None
    raw_key = mint_agent_key()
    record = store.create_agent_api_key(
        {
            "user_id": str(user_id),
            "agent_id": normalized_agent_id,
            "permission_profile": permission_profile,
            "key_hash": hash_agent_key(raw_key),
            "key_prefix": agent_key_prefix(raw_key),
            "label": normalized_label or None,
        }
    )
    return record, raw_key


def verify_agent_key(store: AgentKeyStore, raw_key: str) -> JsonObject | None:
    """Verify a raw agent API key. Returns the key record or None."""

    if not isinstance(raw_key, str) or not raw_key.startswith(AGENT_KEY_PREFIX):
        return None
    candidate_hash = hash_agent_key(raw_key)
    record = store.get_agent_api_key_by_hash(candidate_hash)
    if record is None:
        return None
    if not hmac.compare_digest(str(record.get("key_hash") or ""), candidate_hash):
        return None
    if record.get("revoked_at") is not None:
        return None
    return store.touch_agent_api_key(key_id=str(record["id"]))


def resolve_agent_identity(
    store: AgentKeyStore,
    *,
    user_id: object,
    raw_key: str | None,
    payload: Mapping[str, object],
) -> AgentIdentity | None:
    """Resolve an authenticated agent identity for a request payload.

    With a valid key, agent_id and permission_profile come from the key
    record; the payload may claim a lower profile (downgrade) but claiming a
    different agent_id or a higher profile is rejected. Without a key, the
    payload identity is honored only while the user has no active keys at all
    and is marked ``auth: "unauthenticated_local"``.
    """

    claimed = AgentIdentity.from_payload(payload)

    if raw_key is None:
        if claimed is None:
            return None
        if int(store.count_active_agent_api_keys()) > 0:
            raise AgentKeyAuthenticationError(
                "agent API keys are configured for this user; agent calls must "
                "authenticate with 'Authorization: Bearer alice_sk_...' "
                "(create a key with 'alicebot agent keys create')",
                status_code=401,
            )
        return replace(claimed, auth=UNAUTHENTICATED_LOCAL_AUTH)

    record = verify_agent_key(store, raw_key)
    if record is None:
        raise AgentKeyAuthenticationError(
            "agent API key is invalid or has been revoked", status_code=401
        )
    if str(record.get("user_id")) != str(user_id):
        raise AgentKeyAuthenticationError(
            "agent API key does not belong to this user", status_code=401
        )

    key_agent_id = str(record["agent_id"])
    key_profile = str(record["permission_profile"])
    source = _identity_source(payload)
    claimed_agent_id = _claimed_text(source.get("agent_id"))
    claimed_profile = _claimed_text(source.get("permission_profile"))

    if claimed_agent_id is not None and claimed_agent_id != key_agent_id:
        _append_key_rejection_event(
            store,
            record=record,
            reason="agent_id_mismatch",
            claimed={"claimed_agent_id": claimed_agent_id},
        )
        raise AgentKeyAuthenticationError(
            f"agent API key was issued to agent '{key_agent_id}' but the payload "
            f"claims agent '{claimed_agent_id}'",
            status_code=403,
        )

    effective_profile = key_profile
    if claimed_profile is not None:
        claimed_rank = _PROFILE_RANKS.get(claimed_profile)
        if claimed_rank is None or claimed_rank > _PROFILE_RANKS[key_profile]:
            _append_key_rejection_event(
                store,
                record=record,
                reason="permission_profile_escalation",
                claimed={"claimed_permission_profile": claimed_profile},
            )
            raise AgentKeyAuthenticationError(
                f"agent API key grants permission_profile '{key_profile}'; the "
                f"payload claims '{claimed_profile}', which is higher. Remove the "
                "claim or request a new key with the required profile.",
                status_code=403,
            )
        effective_profile = claimed_profile

    if claimed is None:
        claimed = AgentIdentity.from_payload(
            {"agent_id": key_agent_id, "permission_profile": key_profile}
        ) or AgentIdentity(agent_id=key_agent_id, permission_profile=key_profile)
    return replace(
        claimed,
        agent_id=key_agent_id,
        permission_profile=effective_profile,
        auth=AGENT_KEY_AUTH,
    )


def _identity_source(payload: Mapping[str, object]) -> Mapping[str, object]:
    nested = payload.get("agent_identity")
    if isinstance(nested, Mapping):
        return nested
    nested = payload.get("agent")
    if isinstance(nested, Mapping):
        return nested
    return payload


def _claimed_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _append_key_rejection_event(
    store: AgentKeyStore,
    *,
    record: Mapping[str, object],
    reason: str,
    claimed: JsonObject,
) -> None:
    append_event(
        store,
        event_type="agent.key_escalation_rejected",
        actor_type="agent",
        actor_id=str(record["agent_id"]),
        target_type="agent_api_key",
        target_id=str(record["id"]),
        payload={
            "reason": reason,
            "key_prefix": str(record.get("key_prefix") or ""),
            "granted_permission_profile": str(record["permission_profile"]),
            **claimed,
        },
    )


__all__ = [
    "AGENT_KEY_AUTH",
    "AGENT_KEY_PREFIX",
    "AGENT_KEY_PREFIX_LENGTH",
    "PROFILE_PRIVILEGE_ORDER",
    "UNAUTHENTICATED_LOCAL_AUTH",
    "AgentKeyAuthenticationError",
    "AgentKeyStore",
    "AgentKeyValidationError",
    "agent_key_from_authorization",
    "agent_key_prefix",
    "create_agent_key",
    "hash_agent_key",
    "mint_agent_key",
    "resolve_agent_identity",
    "verify_agent_key",
]
