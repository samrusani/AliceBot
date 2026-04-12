from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlsplit


ALLOWED_PROVIDER_URL_SCHEMES = frozenset({"http", "https"})
_LOCALHOST_HOSTS = frozenset({"localhost", "localhost.localdomain"})
_HTTP_STATUS_PATTERN = re.compile(r"\bHTTP\s+(\d{3})\b", flags=re.IGNORECASE)


class ProviderURLValidationError(ValueError):
    """Raised when a provider base URL violates outbound security policy."""


def validate_provider_base_url(base_url: str) -> str:
    normalized = base_url.strip()
    if normalized == "":
        raise ProviderURLValidationError("base_url is required")

    parsed = urlsplit(normalized)
    scheme = parsed.scheme.strip().lower()
    if scheme not in ALLOWED_PROVIDER_URL_SCHEMES:
        raise ProviderURLValidationError("base_url scheme must be http or https")

    if parsed.hostname is None or parsed.hostname.strip() == "":
        raise ProviderURLValidationError("base_url host is required")
    if parsed.username is not None or parsed.password is not None:
        raise ProviderURLValidationError("base_url must not include embedded credentials")

    hostname = parsed.hostname.strip().rstrip(".").lower()
    if hostname in _LOCALHOST_HOSTS or hostname.endswith(".localhost"):
        raise ProviderURLValidationError("base_url host is not allowed by outbound policy")

    ip_literal = _parse_ip_literal(hostname)
    if ip_literal is not None and _is_disallowed_ip(ip_literal):
        raise ProviderURLValidationError("base_url host is not allowed by outbound policy")

    return normalized


def sanitize_provider_error_message(raw_message: str) -> str:
    message = raw_message.strip()
    if message == "":
        return "provider upstream request failed"

    status_match = _HTTP_STATUS_PATTERN.search(message)
    if status_match is not None:
        return f"provider upstream request failed with HTTP {status_match.group(1)}"

    lowered = message.lower()
    if "invalid json" in lowered:
        return "provider upstream payload was invalid JSON"
    if "did not include assistant output text" in lowered:
        return "provider upstream payload was missing assistant output text"
    if "unsupported model provider" in lowered:
        return "provider runtime request was invalid"
    if "unsupported provider auth_mode" in lowered:
        return "provider runtime authentication settings were invalid"
    return "provider upstream request failed"


def _parse_ip_literal(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    candidate = hostname
    if "%" in candidate:
        candidate = candidate.split("%", 1)[0]

    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        pass

    # Handle IPv4 integer/hex/octal/shorthand forms accepted by common socket parsers
    # (for example: 2130706433, 0x7f000001, 017700000001, 127.1).
    try:
        packed_v4 = socket.inet_aton(candidate)
    except OSError:
        return None
    try:
        return ipaddress.IPv4Address(packed_v4)
    except ipaddress.AddressValueError:
        return None

def _is_disallowed_ip(ip_address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip_address.is_multicast:
        return True
    return not ip_address.is_global
