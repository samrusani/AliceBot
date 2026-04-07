from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from alicebot_api.store import JsonObject

GMAIL_SECRET_MANAGER_KIND_FILE_V1 = "file_v1"
SECRET_DIRECTORY_MODE = 0o700
SECRET_FILE_MODE = 0o600


class GmailSecretManagerError(RuntimeError):
    """Raised when the configured Gmail secret manager cannot service a request."""


@dataclass(frozen=True, slots=True)
class GmailSecretReference:
    kind: str
    ref: str


class GmailSecretManager:
    kind: str

    def load_secret(self, *, secret_ref: str) -> JsonObject:
        raise NotImplementedError

    def write_secret(self, *, secret_ref: str, payload: JsonObject) -> None:
        raise NotImplementedError

    def delete_secret(self, *, secret_ref: str) -> None:
        raise NotImplementedError


class FileGmailSecretManager(GmailSecretManager):
    kind = GMAIL_SECRET_MANAGER_KIND_FILE_V1

    def __init__(self, *, root: Path) -> None:
        self._root = root.expanduser().resolve()
        try:
            self._root.mkdir(parents=True, exist_ok=True, mode=SECRET_DIRECTORY_MODE)
            self._root.chmod(SECRET_DIRECTORY_MODE)
        except OSError as exc:
            raise GmailSecretManagerError("gmail secret manager root is not writable") from exc

    def load_secret(self, *, secret_ref: str) -> JsonObject:
        path = self._resolve_secret_path(secret_ref)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise GmailSecretManagerError(f"gmail secret {secret_ref} was not found") from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GmailSecretManagerError(f"gmail secret {secret_ref} could not be loaded") from exc
        if not isinstance(payload, dict):
            raise GmailSecretManagerError(f"gmail secret {secret_ref} could not be loaded")
        return payload

    def write_secret(self, *, secret_ref: str, payload: JsonObject) -> None:
        path = self._resolve_secret_path(secret_ref)
        self._ensure_private_directory(path.parent)
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with os.fdopen(
                os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, SECRET_FILE_MODE),
                "w",
                encoding="utf-8",
            ) as secret_file:
                secret_file.write(json.dumps(payload, sort_keys=True))
            temp_path.chmod(SECRET_FILE_MODE)
            temp_path.replace(path)
            path.chmod(SECRET_FILE_MODE)
        except OSError as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise GmailSecretManagerError(f"gmail secret {secret_ref} could not be written") from exc

    def delete_secret(self, *, secret_ref: str) -> None:
        path = self._resolve_secret_path(secret_ref)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise GmailSecretManagerError(f"gmail secret {secret_ref} could not be deleted") from exc

    def _resolve_secret_path(self, secret_ref: str) -> Path:
        candidate = (self._root / secret_ref).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise GmailSecretManagerError(f"gmail secret {secret_ref} is outside the configured root") from exc
        return candidate

    def _ensure_private_directory(self, directory: Path) -> None:
        try:
            directory.mkdir(parents=True, exist_ok=True, mode=SECRET_DIRECTORY_MODE)
            directory.chmod(SECRET_DIRECTORY_MODE)
        except OSError as exc:
            raise GmailSecretManagerError("gmail secret directory permissions could not be secured") from exc


def build_gmail_secret_manager(secret_manager_url: str) -> GmailSecretManager:
    if secret_manager_url.strip() == "":
        raise ValueError("GMAIL_SECRET_MANAGER_URL must be configured")

    parsed = urlparse(secret_manager_url)
    if parsed.scheme != "file":
        raise ValueError("GMAIL_SECRET_MANAGER_URL must use the file:// scheme")

    root_path = Path(unquote(parsed.path or "/"))
    if parsed.netloc not in ("", "localhost"):
        root_path = Path(f"/{parsed.netloc}{root_path.as_posix()}")

    return FileGmailSecretManager(root=root_path)
