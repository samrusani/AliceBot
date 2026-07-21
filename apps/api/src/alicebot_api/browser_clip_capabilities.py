"""Short-lived, origin-bound, one-time browser clip capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from ipaddress import IPv4Address, IPv6Address
import re
import secrets
from typing import Protocol
import unicodedata
from urllib.parse import urlsplit

from alicebot_api.vnext_repositories import JsonObject


BROWSER_CLIP_CAPABILITY_PREFIX = "alice_clip_"
BROWSER_CLIP_CAPABILITY_TTL_SECONDS = 120
_BROWSER_CLIP_CAPABILITY_PATTERN = re.compile(
    rf"{re.escape(BROWSER_CLIP_CAPABILITY_PREFIX)}[A-Za-z0-9_-]{{43}}\Z",
    flags=re.ASCII,
)
_DNS_LABEL_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z", flags=re.ASCII)


class BrowserClipCapabilityValidationError(ValueError):
    """Raised when a browser clip capability is malformed or cannot be redeemed."""


class BrowserClipCapabilityStore(Protocol):
    def create_browser_clip_capability(
        self,
        *,
        capability_hash: str,
        origin: str,
        ttl_seconds: int,
    ) -> JsonObject: ...

    def consume_browser_clip_capability(
        self,
        *,
        capability_hash: str,
        origin: str,
    ) -> JsonObject | None: ...


@dataclass(frozen=True, slots=True)
class IssuedBrowserClipCapability:
    capability: str
    origin: str
    expires_at: datetime

    def to_record(self) -> JsonObject:
        return {
            "status": "issued",
            "capability": self.capability,
            "origin": self.origin,
            "expires_at": self.expires_at,
            "one_time": True,
        }


def _validated_url_text(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise BrowserClipCapabilityValidationError("browser clip origin is required")
    if "\\" in value or any(
        character.isspace() or unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in value
    ):
        raise BrowserClipCapabilityValidationError("browser clip origin is invalid")
    return value


def _canonical_hostname(hostname: str) -> str:
    if ":" in hostname:
        if "%" in hostname:
            raise BrowserClipCapabilityValidationError("browser clip origin is invalid")
        try:
            return f"[{IPv6Address(hostname).compressed}]"
        except ValueError as exc:
            raise BrowserClipCapabilityValidationError("browser clip origin is invalid") from exc

    ipv4_candidate = hostname[:-1] if hostname.endswith(".") else hostname
    try:
        return str(IPv4Address(ipv4_candidate))
    except ValueError:
        # Numeric-looking alternatives such as 127.1 and 0x7f000001 are
        # interpreted as IPv4 by browsers but not by ipaddress. Reject them
        # instead of binding a capability to a different serialized origin.
        if ipv4_candidate.rsplit(".", 1)[-1].isdigit() or ipv4_candidate.casefold().startswith("0x"):
            raise BrowserClipCapabilityValidationError("browser clip origin is invalid")

    try:
        ascii_hostname = hostname.casefold().encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise BrowserClipCapabilityValidationError("browser clip origin is invalid") from exc
    rooted = ascii_hostname.endswith(".")
    unrooted_hostname = ascii_hostname[:-1] if rooted else ascii_hostname
    if len(unrooted_hostname) > 253:
        raise BrowserClipCapabilityValidationError("browser clip origin is invalid")
    labels = unrooted_hostname.split(".")
    if not labels or any(_DNS_LABEL_PATTERN.fullmatch(label) is None for label in labels):
        raise BrowserClipCapabilityValidationError("browser clip origin is invalid")
    return f"{unrooted_hostname}." if rooted else unrooted_hostname


def _normalized_http_origin(value: str, *, allow_url_path: bool) -> str:
    candidate = _validated_url_text(value)
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise BrowserClipCapabilityValidationError("browser clip origin is invalid") from exc
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or parsed.hostname is None or not parsed.netloc:
        raise BrowserClipCapabilityValidationError("browser clip origin must use http or https")
    if parsed.username is not None or parsed.password is not None:
        raise BrowserClipCapabilityValidationError("browser clip origin must not contain credentials")
    if parsed.netloc.endswith(":"):
        raise BrowserClipCapabilityValidationError("browser clip origin is invalid")
    if not allow_url_path and (parsed.path or "?" in candidate or "#" in candidate):
        raise BrowserClipCapabilityValidationError("browser clip origin must not contain a path, query, or fragment")
    hostname = _canonical_hostname(parsed.hostname)
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    authority = hostname if port is None or default_port else f"{hostname}:{port}"
    return f"{scheme}://{authority}"


def normalize_browser_clip_origin(value: str) -> str:
    """Normalize an operator-supplied origin and reject URL-shaped values."""

    return _normalized_http_origin(value, allow_url_path=False)


def browser_clip_url_origin(value: str) -> str:
    """Extract the normalized origin from a captured page URL."""

    return _normalized_http_origin(value, allow_url_path=True)


def browser_clip_capability_hash(capability: str) -> str:
    return sha256(capability.encode("utf-8")).hexdigest()


def _capability_expiry(row: JsonObject) -> datetime:
    raw_expiry = row.get("expires_at")
    if isinstance(raw_expiry, datetime):
        expiry = raw_expiry
    elif isinstance(raw_expiry, str):
        try:
            expiry = datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError("browser clip capability store returned an invalid expiry") from exc
    else:
        raise RuntimeError("browser clip capability store did not return an expiry")
    if expiry.tzinfo is None:
        raise RuntimeError("browser clip capability store returned a timezone-naive expiry")
    return expiry.astimezone(UTC)


def issue_browser_clip_capability(
    store: BrowserClipCapabilityStore,
    *,
    origin: str,
) -> IssuedBrowserClipCapability:
    normalized_origin = normalize_browser_clip_origin(origin)
    capability = f"{BROWSER_CLIP_CAPABILITY_PREFIX}{secrets.token_urlsafe(32)}"
    if _BROWSER_CLIP_CAPABILITY_PATTERN.fullmatch(capability) is None:  # pragma: no cover - stdlib contract guard
        raise RuntimeError("secure token generation returned an invalid browser clip capability")
    row = store.create_browser_clip_capability(
        capability_hash=browser_clip_capability_hash(capability),
        origin=normalized_origin,
        ttl_seconds=BROWSER_CLIP_CAPABILITY_TTL_SECONDS,
    )
    if row.get("origin") != normalized_origin:
        raise RuntimeError("browser clip capability store returned a different origin")
    return IssuedBrowserClipCapability(
        capability=capability,
        origin=normalized_origin,
        expires_at=_capability_expiry(row),
    )


def consume_browser_clip_capability(
    store: BrowserClipCapabilityStore,
    *,
    capability: str,
    capture_url: str,
    request_origin: str | None,
) -> JsonObject:
    if not isinstance(capability, str) or _BROWSER_CLIP_CAPABILITY_PATTERN.fullmatch(capability) is None:
        raise BrowserClipCapabilityValidationError("browser clip capability is invalid")
    if request_origin is None:
        raise BrowserClipCapabilityValidationError("browser clip origin is required")
    normalized_request_origin = normalize_browser_clip_origin(request_origin)
    if browser_clip_url_origin(capture_url) != normalized_request_origin:
        raise BrowserClipCapabilityValidationError("browser clip capability origin does not match")
    row = store.consume_browser_clip_capability(
        capability_hash=browser_clip_capability_hash(capability),
        origin=normalized_request_origin,
    )
    if row is None:
        raise BrowserClipCapabilityValidationError("browser clip capability is invalid")
    return row


__all__ = [
    "BROWSER_CLIP_CAPABILITY_PREFIX",
    "BROWSER_CLIP_CAPABILITY_TTL_SECONDS",
    "BrowserClipCapabilityStore",
    "BrowserClipCapabilityValidationError",
    "IssuedBrowserClipCapability",
    "browser_clip_capability_hash",
    "browser_clip_url_origin",
    "consume_browser_clip_capability",
    "issue_browser_clip_capability",
    "normalize_browser_clip_origin",
]
