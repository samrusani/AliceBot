from __future__ import annotations

import socket

import pytest

from alicebot_api.provider_security import sanitize_provider_error_message, validate_provider_base_url


def _fake_getaddrinfo_factory(*addresses: str):
    def fake_getaddrinfo(hostname: str, port, type=0, proto=0):
        del hostname, port, type, proto
        resolved = []
        for address in addresses:
            family = socket.AF_INET6 if ":" in address else socket.AF_INET
            sockaddr = (address, 0) if family == socket.AF_INET else (address, 0, 0, 0)
            resolved.append((family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr))
        return resolved

    return fake_getaddrinfo


def test_validate_provider_base_url_accepts_public_targets(monkeypatch) -> None:
    monkeypatch.setattr(
        "alicebot_api.provider_security.socket.getaddrinfo",
        _fake_getaddrinfo_factory("93.184.216.34"),
    )

    assert validate_provider_base_url("https://provider.example/v1") == "https://provider.example/v1"
    assert validate_provider_base_url("http://provider.example:8080/api") == "http://provider.example:8080/api"


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@provider.example/v1",
        "http://token@provider.example/v1",
    ],
)
def test_validate_provider_base_url_rejects_userinfo(url: str) -> None:
    with pytest.raises(ValueError, match="embedded credentials"):
        validate_provider_base_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.7/v1",
        "http://192.168.1.12/v1",
        "http://172.16.5.10/v1",
        "http://localhost:8080",
        "http://service.localhost:8080",
        "http://[::1]:8080",
        "http://[fe80::1]:8080",
        "http://[fc00::1]:8080",
        "http://2130706433:80",
        "http://0x7f000001:80",
        "http://017700000001:80",
        "http://127.1:80",
        "http://0x7f.0.0.1:80",
        "http://0177.0.0.1:80",
    ],
)
def test_validate_provider_base_url_rejects_disallowed_targets(url: str) -> None:
    with pytest.raises(ValueError, match="not allowed by outbound policy"):
        validate_provider_base_url(url)


def test_validate_provider_base_url_rejects_hostname_resolving_to_private_ip(monkeypatch) -> None:
    monkeypatch.setattr(
        "alicebot_api.provider_security.socket.getaddrinfo",
        _fake_getaddrinfo_factory("10.0.0.8"),
    )

    with pytest.raises(ValueError, match="not allowed by outbound policy"):
        validate_provider_base_url("https://internal-resolver.example/v1")


def test_validate_provider_base_url_rechecks_hostname_resolution(monkeypatch) -> None:
    responses = iter(
        [
            _fake_getaddrinfo_factory("93.184.216.34"),
            _fake_getaddrinfo_factory("10.0.0.8"),
        ]
    )

    def fake_getaddrinfo(hostname: str, port, type=0, proto=0):
        return next(responses)(hostname, port, type=type, proto=proto)

    monkeypatch.setattr("alicebot_api.provider_security.socket.getaddrinfo", fake_getaddrinfo)

    assert validate_provider_base_url("https://rebind.example/v1") == "https://rebind.example/v1"
    with pytest.raises(ValueError, match="not allowed by outbound policy"):
        validate_provider_base_url("https://rebind.example/v1")


def test_sanitize_provider_error_message_removes_upstream_detail() -> None:
    assert (
        sanitize_provider_error_message(
            "model provider returned HTTP 502 with detail: credential=secret-value"
        )
        == "provider upstream request failed with HTTP 502"
    )
    assert sanitize_provider_error_message("model provider request failed: timed out to 10.0.0.5") == (
        "provider upstream request failed"
    )
