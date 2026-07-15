from __future__ import annotations

import hashlib
import json

from alicebot_api.store import JsonObject


def provider_config_fingerprint_v1(
    *,
    provider_key: str,
    model_provider: str,
    display_name: str,
    base_url: str,
    api_key: str,
    auth_mode: str,
    default_model: str,
    status: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    azure_api_version: str,
    azure_auth_secret_ref: str,
    metadata: JsonObject,
) -> str:
    """Return the immutable version-one provider-configuration fingerprint.

    Migration ``20260713_0088`` relies on these exact JSON and hashing
    semantics when installing a database from scratch.  Keep this function
    stable; a future fingerprint format must use a new versioned helper and a
    fix-forward migration rather than changing this implementation.
    """

    payload: JsonObject = {
        "provider_key": provider_key,
        "model_provider": model_provider,
        "display_name": display_name,
        "base_url": base_url,
        "api_key": api_key,
        "auth_mode": auth_mode,
        "default_model": default_model,
        "status": status,
        "model_list_path": model_list_path,
        "healthcheck_path": healthcheck_path,
        "invoke_path": invoke_path,
        "azure_api_version": azure_api_version,
        "azure_auth_secret_ref": azure_auth_secret_ref,
        "metadata": metadata,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def provider_config_fingerprint(
    *,
    provider_key: str,
    model_provider: str,
    display_name: str,
    base_url: str,
    api_key: str,
    auth_mode: str,
    default_model: str,
    status: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    azure_api_version: str,
    azure_auth_secret_ref: str,
    metadata: JsonObject,
) -> str:
    """Return the current provider-configuration fingerprint."""

    return provider_config_fingerprint_v1(
        provider_key=provider_key,
        model_provider=model_provider,
        display_name=display_name,
        base_url=base_url,
        api_key=api_key,
        auth_mode=auth_mode,
        default_model=default_model,
        status=status,
        model_list_path=model_list_path,
        healthcheck_path=healthcheck_path,
        invoke_path=invoke_path,
        azure_api_version=azure_api_version,
        azure_auth_secret_ref=azure_auth_secret_ref,
        metadata=metadata,
    )


__all__ = ["provider_config_fingerprint", "provider_config_fingerprint_v1"]
