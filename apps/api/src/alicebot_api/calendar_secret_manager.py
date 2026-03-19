from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from alicebot_api.store import JsonObject

CALENDAR_SECRET_MANAGER_KIND_FILE_V1 = "file_v1"


class CalendarSecretManagerError(RuntimeError):
    """Raised when the configured Calendar secret manager cannot service a request."""


class CalendarSecretManager:
    kind: str

    def load_secret(self, *, secret_ref: str) -> JsonObject:
        raise NotImplementedError

    def write_secret(self, *, secret_ref: str, payload: JsonObject) -> None:
        raise NotImplementedError

    def delete_secret(self, *, secret_ref: str) -> None:
        raise NotImplementedError


class FileCalendarSecretManager(CalendarSecretManager):
    kind = CALENDAR_SECRET_MANAGER_KIND_FILE_V1

    def __init__(self, *, root: Path) -> None:
        self._root = root.expanduser().resolve()

    def load_secret(self, *, secret_ref: str) -> JsonObject:
        path = self._resolve_secret_path(secret_ref)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CalendarSecretManagerError(f"calendar secret {secret_ref} was not found") from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CalendarSecretManagerError(f"calendar secret {secret_ref} could not be loaded") from exc
        if not isinstance(payload, dict):
            raise CalendarSecretManagerError(f"calendar secret {secret_ref} could not be loaded")
        return payload

    def write_secret(self, *, secret_ref: str, payload: JsonObject) -> None:
        path = self._resolve_secret_path(secret_ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            temp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            temp_path.replace(path)
        except OSError as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise CalendarSecretManagerError(f"calendar secret {secret_ref} could not be written") from exc

    def delete_secret(self, *, secret_ref: str) -> None:
        path = self._resolve_secret_path(secret_ref)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise CalendarSecretManagerError(f"calendar secret {secret_ref} could not be deleted") from exc

    def _resolve_secret_path(self, secret_ref: str) -> Path:
        candidate = (self._root / secret_ref).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise CalendarSecretManagerError(
                f"calendar secret {secret_ref} is outside the configured root"
            ) from exc
        return candidate


def build_calendar_secret_manager(secret_manager_url: str) -> CalendarSecretManager:
    if secret_manager_url.strip() == "":
        raise ValueError("CALENDAR_SECRET_MANAGER_URL must be configured")

    parsed = urlparse(secret_manager_url)
    if parsed.scheme != "file":
        raise ValueError("CALENDAR_SECRET_MANAGER_URL must use the file:// scheme")

    root_path = Path(unquote(parsed.path or "/"))
    if parsed.netloc not in ("", "localhost"):
        root_path = Path(f"/{parsed.netloc}{root_path.as_posix()}")

    return FileCalendarSecretManager(root=root_path)
