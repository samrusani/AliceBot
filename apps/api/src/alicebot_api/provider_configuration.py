from __future__ import annotations

from alicebot_api.response_jobs import request_fingerprint
from alicebot_api.store import JsonObject


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
    """Return the version-one canonical fingerprint for a provider config."""

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
    return request_fingerprint(payload)


__all__ = ["provider_config_fingerprint"]
