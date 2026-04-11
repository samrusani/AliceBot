from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import UUID, uuid4

from alicebot_api.config import Settings

_SECRET_REF_PREFIX = "provider_secret_ref:"
_SECRET_DIRECTORY_MODE = 0o700
_SECRET_FILE_MODE = 0o600


class ProviderSecretManagerError(RuntimeError):
    """Raised when provider secret storage cannot service a request."""


def _secret_root(settings: Settings) -> Path:
    configured_url = settings.provider_secret_manager_url.strip()
    if configured_url == "":
        return (Path(settings.task_workspace_root) / "provider-secrets").expanduser().resolve()

    parsed = urlparse(configured_url)
    if parsed.scheme != "file":
        raise ProviderSecretManagerError("PROVIDER_SECRET_MANAGER_URL must use the file:// scheme")

    root_path = Path(unquote(parsed.path or "/"))
    if parsed.netloc not in ("", "localhost"):
        root_path = Path(f"/{parsed.netloc}{root_path.as_posix()}")
    return root_path.expanduser().resolve()


def _ensure_private_directory(directory: Path) -> None:
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=_SECRET_DIRECTORY_MODE)
        directory.chmod(_SECRET_DIRECTORY_MODE)
    except OSError as exc:
        raise ProviderSecretManagerError("provider secret directory permissions could not be secured") from exc


def _resolve_secret_path(*, root: Path, secret_ref: str) -> Path:
    candidate = (root / secret_ref).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ProviderSecretManagerError(
            f"provider secret {secret_ref} is outside the configured root"
        ) from exc
    return candidate


def encode_provider_secret_ref(*, secret_ref: str) -> str:
    return f"{_SECRET_REF_PREFIX}{secret_ref}"


def is_provider_secret_ref(value: str) -> bool:
    return value.startswith(_SECRET_REF_PREFIX)


def _decode_provider_secret_ref(value: str) -> str:
    if not is_provider_secret_ref(value):
        raise ProviderSecretManagerError("provider API key is not a provider secret reference")
    return value[len(_SECRET_REF_PREFIX) :]


def build_provider_secret_ref(*, workspace_id: UUID, secret_id: UUID | None = None) -> str:
    if secret_id is None:
        secret_id = uuid4()
    return f"workspaces/{workspace_id}/model-provider-secrets/{secret_id}.json"


def write_provider_api_key(*, settings: Settings, secret_ref: str, api_key: str) -> None:
    root = _secret_root(settings)
    _ensure_private_directory(root)
    path = _resolve_secret_path(root=root, secret_ref=secret_ref)
    _ensure_private_directory(path.parent)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = {"api_key": api_key}
    try:
        with os.fdopen(
            os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _SECRET_FILE_MODE),
            "w",
            encoding="utf-8",
        ) as secret_file:
            secret_file.write(json.dumps(payload, sort_keys=True))
        temp_path.chmod(_SECRET_FILE_MODE)
        temp_path.replace(path)
        path.chmod(_SECRET_FILE_MODE)
    except OSError as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ProviderSecretManagerError(
            f"provider secret {secret_ref} could not be written"
        ) from exc


def resolve_provider_api_key(*, settings: Settings, api_key_field: str) -> str:
    if not is_provider_secret_ref(api_key_field):
        return api_key_field

    secret_ref = _decode_provider_secret_ref(api_key_field)
    path = _resolve_secret_path(root=_secret_root(settings), secret_ref=secret_ref)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProviderSecretManagerError(f"provider secret {secret_ref} was not found") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderSecretManagerError(f"provider secret {secret_ref} could not be loaded") from exc

    if not isinstance(payload, dict):
        raise ProviderSecretManagerError(f"provider secret {secret_ref} could not be loaded")
    api_key = payload.get("api_key")
    if not isinstance(api_key, str) or api_key.strip() == "":
        raise ProviderSecretManagerError(f"provider secret {secret_ref} did not include a valid api_key")
    return api_key
