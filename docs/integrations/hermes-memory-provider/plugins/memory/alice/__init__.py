"""Alice memory plugin for Hermes MemoryProvider.

This provider connects Hermes's external memory provider interface to Alice's
continuity APIs.

Design goals:
- Keep Hermes built-in MEMORY.md / USER.md active (additive integration).
- Provide deterministic recall and resumption tools.
- Support prefetch for next-turn context without blocking the tool loop.
"""

from __future__ import annotations

import json
import ipaddress
import logging
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error

logger = logging.getLogger(__name__)

_CONFIG_FILENAME = "alice_memory_provider.json"
_DEFAULT_BASE_URL = "http://127.0.0.1:8000"
_DEFAULT_TIMEOUT_SECONDS = 8.0
_DEFAULT_PREFETCH_LIMIT = 5
_DEFAULT_MAX_RECENT_CHANGES = 5
_DEFAULT_MAX_OPEN_LOOPS = 5
_DEFAULT_CAPTURE_CHAR_LIMIT = 3800

_RECALL_LIMIT_MIN = 1
_RECALL_LIMIT_MAX = 50

_OPEN_LOOP_LIMIT_MIN = 0
_OPEN_LOOP_LIMIT_MAX = 50

_RECENT_CHANGES_MIN = 0
_RECENT_CHANGES_MAX = 25

_AUTH_USER_HEADER = "X-AliceBot-User-Id"
_SAFE_TOOL_ERROR_MESSAGES = (
    "internal provider error",
    "provider is not initialized",
    "provider configuration is invalid",
    "Alice API connection failed",
    "Alice API returned an invalid response payload",
)


ALICE_RECALL_TOOL = {
    "name": "alice_recall",
    "description": (
        "Recall continuity records from Alice with deterministic ranking and provenance. "
        "Use for prior decisions, commitments, blockers, and history-backed answers."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional query text."},
            "thread_id": {"type": "string", "description": "Optional thread UUID."},
            "task_id": {"type": "string", "description": "Optional task UUID."},
            "project": {"type": "string", "description": "Optional project filter."},
            "person": {"type": "string", "description": "Optional person filter."},
            "since": {"type": "string", "description": "Optional ISO timestamp lower bound."},
            "until": {"type": "string", "description": "Optional ISO timestamp upper bound."},
            "limit": {"type": "integer", "description": "Result limit (1-50)."},
        },
        "required": [],
    },
}

ALICE_RESUME_TOOL = {
    "name": "alice_resumption_brief",
    "description": (
        "Build a scoped resumption brief from Alice continuity state with last decision, "
        "open loops, recent changes, and next action."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional query text."},
            "thread_id": {"type": "string", "description": "Optional thread UUID."},
            "task_id": {"type": "string", "description": "Optional task UUID."},
            "project": {"type": "string", "description": "Optional project filter."},
            "person": {"type": "string", "description": "Optional person filter."},
            "since": {"type": "string", "description": "Optional ISO timestamp lower bound."},
            "until": {"type": "string", "description": "Optional ISO timestamp upper bound."},
            "max_recent_changes": {
                "type": "integer",
                "description": "Maximum recent changes to include (0-25).",
            },
            "max_open_loops": {
                "type": "integer",
                "description": "Maximum open loops to include (0-25).",
            },
            "include_non_promotable_facts": {
                "type": "boolean",
                "description": "Include non-promotable continuity facts.",
            },
        },
        "required": [],
    },
}

ALICE_OPEN_LOOPS_TOOL = {
    "name": "alice_open_loops",
    "description": (
        "List open loops from Alice continuity grouped and ranked for execution follow-through."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional query text."},
            "thread_id": {"type": "string", "description": "Optional thread UUID."},
            "task_id": {"type": "string", "description": "Optional task UUID."},
            "project": {"type": "string", "description": "Optional project filter."},
            "person": {"type": "string", "description": "Optional person filter."},
            "since": {"type": "string", "description": "Optional ISO timestamp lower bound."},
            "until": {"type": "string", "description": "Optional ISO timestamp upper bound."},
            "limit": {"type": "integer", "description": "Result limit (0-50)."},
        },
        "required": [],
    },
}


def _parse_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _parse_int(value: Any, *, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _parse_float(value: Any, *, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if normalized.endswith("/v0"):
        normalized = normalized[:-3]
    parsed = urllib.parse.urlsplit(normalized)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").strip().lower()
    if scheme not in {"http", "https"}:
        raise ValueError("base_url must start with http:// or https://")
    if parsed.netloc.strip() == "":
        raise ValueError("base_url must include a host")
    if parsed.query or parsed.fragment:
        raise ValueError("base_url must not include query parameters or fragments")
    if scheme != "https" and not _is_loopback_host(hostname):
        raise ValueError("base_url must use https:// unless host is loopback")
    return urllib.parse.urlunsplit((scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def _is_loopback_host(hostname: str) -> bool:
    if hostname == "":
        return False
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _sanitize_tool_exception_message(error: Exception) -> str:
    message = str(error).strip()
    if message == "":
        return "internal provider error"
    for prefix in _SAFE_TOOL_ERROR_MESSAGES:
        if message.startswith(prefix):
            return message
    if message.startswith("Alice API request failed with HTTP status "):
        return message
    return "internal provider error"


def _config_path(hermes_home: str) -> Path:
    return Path(hermes_home) / _CONFIG_FILENAME


def _default_config() -> Dict[str, Any]:
    return {
        "base_url": os.environ.get("ALICE_API_BASE_URL", _DEFAULT_BASE_URL),
        "user_id": os.environ.get("ALICE_MEMORY_USER_ID", os.environ.get("ALICEBOT_AUTH_USER_ID", "")),
        "timeout_seconds": _parse_float(
            os.environ.get("ALICE_MEMORY_TIMEOUT_SECONDS"),
            default=_DEFAULT_TIMEOUT_SECONDS,
            min_value=0.5,
            max_value=30.0,
        ),
        "prefetch_limit": _parse_int(
            os.environ.get("ALICE_MEMORY_PREFETCH_LIMIT"),
            default=_DEFAULT_PREFETCH_LIMIT,
            min_value=_RECALL_LIMIT_MIN,
            max_value=_RECALL_LIMIT_MAX,
        ),
        "max_recent_changes": _parse_int(
            os.environ.get("ALICE_MEMORY_MAX_RECENT_CHANGES"),
            default=_DEFAULT_MAX_RECENT_CHANGES,
            min_value=_RECENT_CHANGES_MIN,
            max_value=_RECENT_CHANGES_MAX,
        ),
        "max_open_loops": _parse_int(
            os.environ.get("ALICE_MEMORY_MAX_OPEN_LOOPS"),
            default=_DEFAULT_MAX_OPEN_LOOPS,
            min_value=_RECENT_CHANGES_MIN,
            max_value=_RECENT_CHANGES_MAX,
        ),
        "include_non_promotable_facts": _parse_bool(
            os.environ.get("ALICE_MEMORY_INCLUDE_NON_PROMOTABLE"),
            default=False,
        ),
        "auto_capture": _parse_bool(
            os.environ.get("ALICE_MEMORY_AUTO_CAPTURE"),
            default=False,
        ),
        "mirror_memory_writes": _parse_bool(
            os.environ.get("ALICE_MEMORY_MIRROR_WRITES"),
            default=False,
        ),
    }


def _load_config(hermes_home: str) -> Dict[str, Any]:
    config = _default_config()

    path = _config_path(hermes_home)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if value is not None and value != "":
                        config[key] = value
        except Exception:
            logger.debug("Failed to parse %s", path, exc_info=True)

    try:
        return _load_config_dict_from_values(config)
    except ValueError:
        logger.warning("Invalid Alice memory provider config; falling back to defaults", exc_info=True)
        return _load_config_dict_from_values(_default_config())


def _validate_uuid(value: str) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class AliceMemoryProvider(MemoryProvider):
    """Hermes external memory provider backed by Alice continuity APIs."""

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._session_id: str = ""
        self._hermes_home: str = ""
        self._agent_context: str = "primary"

        self._prefetch_cache: Dict[str, str] = {}
        self._prefetch_threads: Dict[str, threading.Thread] = {}
        self._prefetch_lock = threading.Lock()

        self._capture_thread: Optional[threading.Thread] = None

    @property
    def name(self) -> str:
        return "alice"

    def is_available(self) -> bool:
        from hermes_constants import get_hermes_home

        try:
            cfg = _load_config(str(get_hermes_home()))
        except ValueError:
            return False
        base_url = str(cfg.get("base_url", "")).strip()
        user_id = str(cfg.get("user_id", "")).strip()
        try:
            _normalize_base_url(base_url)
        except ValueError:
            return False
        return _validate_uuid(user_id)

    def initialize(self, session_id: str, **kwargs) -> None:
        from hermes_constants import get_hermes_home

        self._session_id = session_id or ""
        self._hermes_home = str(kwargs.get("hermes_home") or get_hermes_home())
        self._agent_context = str(kwargs.get("agent_context") or "primary")
        self._config = _load_config(self._hermes_home)

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "base_url",
                "description": "Alice API base URL",
                "required": True,
                "default": _DEFAULT_BASE_URL,
            },
            {
                "key": "user_id",
                "description": "Alice user UUID used for continuity scope",
                "required": True,
            },
            {
                "key": "timeout_seconds",
                "description": "HTTP timeout for Alice API calls",
                "default": str(_DEFAULT_TIMEOUT_SECONDS),
            },
            {
                "key": "prefetch_limit",
                "description": "Default prefetch recall limit",
                "default": str(_DEFAULT_PREFETCH_LIMIT),
            },
            {
                "key": "max_recent_changes",
                "description": "Resumption brief recent changes cap",
                "default": str(_DEFAULT_MAX_RECENT_CHANGES),
            },
            {
                "key": "max_open_loops",
                "description": "Resumption brief open-loop cap",
                "default": str(_DEFAULT_MAX_OPEN_LOOPS),
            },
            {
                "key": "include_non_promotable_facts",
                "description": "Include non-promotable facts in resumption brief",
                "choices": ["true", "false"],
                "default": "false",
            },
            {
                "key": "auto_capture",
                "description": "Auto-capture completed turns into Alice continuity",
                "choices": ["true", "false"],
                "default": "false",
            },
            {
                "key": "mirror_memory_writes",
                "description": "Mirror built-in MEMORY.md / USER.md writes to Alice",
                "choices": ["true", "false"],
                "default": "false",
            },
        ]

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        cfg = _load_config(hermes_home)
        cfg.update(values)
        cfg = _load_config_dict_from_values(cfg)
        path = _config_path(hermes_home)
        path.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def system_prompt_block(self) -> str:
        return (
            "# Alice Continuity Memory\n"
            "Active as an external Hermes memory provider.\n"
            "Hermes built-in MEMORY.md and USER.md remain active.\n"
            "Use alice_recall for scoped history lookup and alice_resumption_brief "
            "to recover last decision, open loops, and next action."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        key = self._session_key(session_id)

        with self._prefetch_lock:
            cached = self._prefetch_cache.pop(key, "")
        if cached:
            return cached

        return self._build_prefetch_context(query)

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        if not query:
            return

        key = self._session_key(session_id)
        with self._prefetch_lock:
            existing = self._prefetch_threads.get(key)
            if existing and existing.is_alive():
                return

        def _run_prefetch() -> None:
            context = ""
            try:
                context = self._build_prefetch_context(query)
            except Exception as exc:
                logger.debug("Alice prefetch failed: %s", exc)
            with self._prefetch_lock:
                self._prefetch_cache[key] = context

        thread = threading.Thread(
            target=_run_prefetch,
            daemon=True,
            name=f"alice-prefetch-{key[:8] if key else 'default'}",
        )
        with self._prefetch_lock:
            self._prefetch_threads[key] = thread
        thread.start()

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        if not self._config.get("auto_capture", False):
            return
        if self._agent_context != "primary":
            return

        raw_content = self._build_turn_capture_payload(user_content, assistant_content)
        if not raw_content:
            return

        def _capture() -> None:
            try:
                self._post_capture(raw_content)
            except Exception as exc:
                logger.debug("Alice sync_turn capture failed: %s", exc)

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=5.0)

        self._capture_thread = threading.Thread(target=_capture, daemon=True, name="alice-sync-capture")
        self._capture_thread.start()

    def on_memory_write(self, action: str, target: str, content: str) -> None:
        if not self._config.get("mirror_memory_writes", False):
            return
        if action not in {"add", "replace"}:
            return
        if not content.strip():
            return

        raw_content = f"Hermes built-in memory update ({target}): {content.strip()}"

        def _capture() -> None:
            try:
                self._post_capture(raw_content)
            except Exception as exc:
                logger.debug("Alice memory-write mirror failed: %s", exc)

        thread = threading.Thread(target=_capture, daemon=True, name="alice-memory-write")
        thread.start()

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [ALICE_RECALL_TOOL, ALICE_RESUME_TOOL, ALICE_OPEN_LOOPS_TOOL]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        try:
            if tool_name == "alice_recall":
                payload = self._tool_recall(args)
            elif tool_name == "alice_resumption_brief":
                payload = self._tool_resumption_brief(args)
            elif tool_name == "alice_open_loops":
                payload = self._tool_open_loops(args)
            else:
                return tool_error(f"unknown tool: {tool_name}")
            return json.dumps(payload)
        except Exception as exc:
            logger.debug("Alice provider tool call failed for %s", tool_name, exc_info=True)
            return tool_error(f"{tool_name} failed: {_sanitize_tool_exception_message(exc)}")

    def shutdown(self) -> None:
        with self._prefetch_lock:
            threads = list(self._prefetch_threads.values())
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=5.0)

    def _session_key(self, session_id: str) -> str:
        return session_id or self._session_id or "default"

    def _tool_recall(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = self._scope_params(args)
        params["limit"] = _parse_int(
            args.get("limit"),
            default=self._config.get("prefetch_limit", _DEFAULT_PREFETCH_LIMIT),
            min_value=_RECALL_LIMIT_MIN,
            max_value=_RECALL_LIMIT_MAX,
        )
        return self._request_json("GET", "/v0/continuity/recall", params=params)

    def _tool_resumption_brief(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = self._scope_params(args)
        params["max_recent_changes"] = _parse_int(
            args.get("max_recent_changes"),
            default=self._config.get("max_recent_changes", _DEFAULT_MAX_RECENT_CHANGES),
            min_value=_RECENT_CHANGES_MIN,
            max_value=_RECENT_CHANGES_MAX,
        )
        params["max_open_loops"] = _parse_int(
            args.get("max_open_loops"),
            default=self._config.get("max_open_loops", _DEFAULT_MAX_OPEN_LOOPS),
            min_value=_RECENT_CHANGES_MIN,
            max_value=_RECENT_CHANGES_MAX,
        )
        params["include_non_promotable_facts"] = _parse_bool(
            args.get("include_non_promotable_facts"),
            default=bool(self._config.get("include_non_promotable_facts", False)),
        )
        return self._request_json("GET", "/v0/continuity/resumption-brief", params=params)

    def _tool_open_loops(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = self._scope_params(args)
        params["limit"] = _parse_int(
            args.get("limit"),
            default=self._config.get("max_open_loops", _DEFAULT_MAX_OPEN_LOOPS),
            min_value=_OPEN_LOOP_LIMIT_MIN,
            max_value=_OPEN_LOOP_LIMIT_MAX,
        )
        return self._request_json("GET", "/v0/continuity/open-loops", params=params)

    def _scope_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        for key in ("query", "thread_id", "task_id", "project", "person", "since", "until"):
            value = args.get(key)
            if isinstance(value, str):
                value = value.strip()
            if value not in (None, ""):
                params[key] = value
        return params

    def _build_prefetch_context(self, query: str) -> str:
        params: Dict[str, Any] = {}
        normalized_query = (query or "").strip()
        if normalized_query:
            params["query"] = normalized_query
        params["max_recent_changes"] = self._config.get("max_recent_changes", _DEFAULT_MAX_RECENT_CHANGES)
        params["max_open_loops"] = self._config.get("max_open_loops", _DEFAULT_MAX_OPEN_LOOPS)
        params["include_non_promotable_facts"] = bool(self._config.get("include_non_promotable_facts", False))

        payload = self._request_json("GET", "/v0/continuity/resumption-brief", params=params)
        brief = payload.get("brief")
        if not isinstance(brief, dict):
            return ""

        lines: List[str] = ["## Alice Continuity Prefetch"]

        last_decision = _extract_single_title(brief.get("last_decision"))
        if last_decision:
            lines.append(f"- Last decision: {last_decision}")

        next_action = _extract_single_title(brief.get("next_action"))
        if next_action:
            lines.append(f"- Next action: {next_action}")

        open_loop_lines = _extract_titles(brief.get("open_loops"), limit=self._config.get("max_open_loops", 3))
        if open_loop_lines:
            lines.append("- Open loops:")
            lines.extend([f"  - {item}" for item in open_loop_lines])

        recent_change_lines = _extract_titles(
            brief.get("recent_changes"),
            limit=self._config.get("max_recent_changes", 3),
        )
        if recent_change_lines:
            lines.append("- Recent changes:")
            lines.extend([f"  - {item}" for item in recent_change_lines])

        if len(lines) == 1:
            return ""
        return "\n".join(lines)

    def _post_capture(self, raw_content: str) -> None:
        payload = {
            "raw_content": raw_content[:_DEFAULT_CAPTURE_CHAR_LIMIT],
        }
        self._request_json("POST", "/v0/continuity/captures", payload=payload)

    def _build_turn_capture_payload(self, user_content: str, assistant_content: str) -> str:
        user_text = (user_content or "").strip()
        assistant_text = (assistant_content or "").strip()
        if not user_text and not assistant_text:
            return ""

        segments: List[str] = []
        if user_text:
            segments.append(f"User: {user_text}")
        if assistant_text:
            segments.append(f"Assistant: {assistant_text}")

        payload = "\n".join(segments)
        if len(payload) > _DEFAULT_CAPTURE_CHAR_LIMIT:
            payload = payload[:_DEFAULT_CAPTURE_CHAR_LIMIT]
        return payload

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._config:
            raise RuntimeError("provider is not initialized")

        query = dict(params or {})
        user_id = str(self._config.get("user_id", "")).strip()
        if not _validate_uuid(user_id):
            raise RuntimeError("provider configuration is invalid")

        try:
            base_url = _normalize_base_url(str(self._config.get("base_url", _DEFAULT_BASE_URL)))
        except ValueError as exc:
            raise RuntimeError("provider configuration is invalid") from exc
        encoded = urllib.parse.urlencode(query, doseq=True)
        url = f"{base_url}{path}"
        if encoded:
            url = f"{url}?{encoded}"

        data = None
        headers = {
            "Accept": "application/json",
            _AUTH_USER_HEADER: user_id,
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)

        timeout = float(self._config.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS))

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
                body = response.read().decode("utf-8", errors="replace")
                if not body:
                    return {}
                decoded = json.loads(body)
                if isinstance(decoded, dict):
                    return decoded
                raise RuntimeError("Alice API returned an invalid response payload")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Alice API request failed with HTTP status {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Alice API connection failed") from exc


def _load_config_dict_from_values(values: Dict[str, Any]) -> Dict[str, Any]:
    config: Dict[str, Any] = dict(values)
    config["base_url"] = _normalize_base_url(str(config.get("base_url", _DEFAULT_BASE_URL)))
    config["user_id"] = str(config.get("user_id", "")).strip()
    config["timeout_seconds"] = _parse_float(
        config.get("timeout_seconds"),
        default=_DEFAULT_TIMEOUT_SECONDS,
        min_value=0.5,
        max_value=30.0,
    )
    config["prefetch_limit"] = _parse_int(
        config.get("prefetch_limit"),
        default=_DEFAULT_PREFETCH_LIMIT,
        min_value=_RECALL_LIMIT_MIN,
        max_value=_RECALL_LIMIT_MAX,
    )
    config["max_recent_changes"] = _parse_int(
        config.get("max_recent_changes"),
        default=_DEFAULT_MAX_RECENT_CHANGES,
        min_value=_RECENT_CHANGES_MIN,
        max_value=_RECENT_CHANGES_MAX,
    )
    config["max_open_loops"] = _parse_int(
        config.get("max_open_loops"),
        default=_DEFAULT_MAX_OPEN_LOOPS,
        min_value=_RECENT_CHANGES_MIN,
        max_value=_RECENT_CHANGES_MAX,
    )
    config["include_non_promotable_facts"] = _parse_bool(
        config.get("include_non_promotable_facts"),
        default=False,
    )
    config["auto_capture"] = _parse_bool(config.get("auto_capture"), default=False)
    config["mirror_memory_writes"] = _parse_bool(config.get("mirror_memory_writes"), default=False)
    return config


def _extract_single_title(section: Any) -> str:
    if not isinstance(section, dict):
        return ""
    item = section.get("item")
    if not isinstance(item, dict):
        return ""
    title = item.get("title")
    if isinstance(title, str):
        return title.strip()
    return ""


def _extract_titles(section: Any, *, limit: int) -> List[str]:
    if not isinstance(section, dict):
        return []
    items = section.get("items")
    if not isinstance(items, list):
        return []

    titles: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not isinstance(title, str):
            continue
        normalized = title.strip()
        if not normalized:
            continue
        titles.append(normalized)
        if len(titles) >= limit:
            break
    return titles


# Plugin entry point ---------------------------------------------------------

def register(ctx) -> None:
    """Register Alice as a Hermes external memory provider."""

    ctx.register_memory_provider(AliceMemoryProvider())
