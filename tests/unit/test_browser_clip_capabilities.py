from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import re

import pytest

from alicebot_api.browser_clip_capabilities import (
    BROWSER_CLIP_CAPABILITY_PREFIX,
    BROWSER_CLIP_CAPABILITY_TTL_SECONDS,
    BrowserClipCapabilityValidationError,
    browser_clip_capability_hash,
    browser_clip_url_origin,
    consume_browser_clip_capability,
    issue_browser_clip_capability,
    normalize_browser_clip_origin,
)


class _MemoryCapabilityStore:
    def __init__(self, *, now: datetime, return_iso_expiry: bool = False) -> None:
        self.now = now
        self.return_iso_expiry = return_iso_expiry
        self.records: dict[str, dict[str, object]] = {}
        self.create_calls: list[dict[str, object]] = []
        self.consume_calls: list[dict[str, str]] = []

    def create_browser_clip_capability(
        self,
        *,
        capability_hash: str,
        origin: str,
        ttl_seconds: int,
    ) -> dict[str, object]:
        call = {
            "capability_hash": capability_hash,
            "origin": origin,
            "ttl_seconds": ttl_seconds,
        }
        self.create_calls.append(call)
        expires_at = self.now + timedelta(seconds=ttl_seconds)
        row: dict[str, object] = {
            "origin": origin,
            "expires_at": expires_at,
            "consumed_at": None,
        }
        self.records[capability_hash] = row
        result = dict(row)
        if self.return_iso_expiry:
            result["expires_at"] = expires_at.isoformat().replace("+00:00", "Z")
        return result

    def consume_browser_clip_capability(
        self,
        *,
        capability_hash: str,
        origin: str,
    ) -> dict[str, object] | None:
        self.consume_calls.append({"capability_hash": capability_hash, "origin": origin})
        row = self.records.get(capability_hash)
        expires_at = row.get("expires_at") if row is not None else None
        if (
            row is None
            or row["origin"] != origin
            or row["consumed_at"] is not None
            or not isinstance(expires_at, datetime)
            or expires_at <= self.now
        ):
            return None
        row["consumed_at"] = self.now
        return dict(row)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HTTPS://ExAmPle.COM:443", "https://example.com"),
        ("http://EXAMPLE.com:80", "http://example.com"),
        ("https://BÜCHER.example:8443", "https://xn--bcher-kva.example:8443"),
        ("https://BÜCHER.example.", "https://xn--bcher-kva.example."),
        ("https://[2001:0DB8:0:0::1]:443", "https://[2001:db8::1]"),
        ("http://[::1]:8080", "http://[::1]:8080"),
        ("http://127.0.0.1:80", "http://127.0.0.1"),
        ("http://127.0.0.1.:80", "http://127.0.0.1"),
    ],
)
def test_normalize_browser_clip_origin_canonicalizes_browser_origins(raw: str, expected: str) -> None:
    assert normalize_browser_clip_origin(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "null",
        "data:text/plain,hello",
        "file:///tmp/capture",
        "https://user@example.test",
        "https://user:password@example.test",
        "https://example.test/",
        "https://example.test/path",
        "https://example.test?",
        "https://example.test?query=1",
        "https://example.test#",
        "https://example.test#fragment",
        "https://example.test:",
        "https://127.1",
        "https://0x7f000001",
        "https://[fe80::1%25en0]",
        " https://example.test",
        "https://example.test ",
        "https://exa\nmple.test",
        "https://exa\x00mple.test",
        "https://exa\u200emple.test",
        "https://exa\u00a0mple.test",
        "https:\\example.test",
    ],
)
def test_normalize_browser_clip_origin_rejects_non_origins_and_ambiguous_text(raw: str) -> None:
    with pytest.raises(BrowserClipCapabilityValidationError):
        normalize_browser_clip_origin(raw)


def test_browser_clip_url_origin_allows_page_components_but_normalizes_only_the_origin() -> None:
    assert (
        browser_clip_url_origin("HTTPS://BÜCHER.example:443/articles/1?q=memory#selection")
        == "https://xn--bcher-kva.example"
    )


@pytest.mark.parametrize(
    "capture_url",
    [
        "null",
        "blob:https://example.test/id",
        "https://user:password@example.test/page",
        "https://exa\nmple.test/page",
        "https:\\example.test/page",
    ],
)
def test_browser_clip_url_origin_rejects_opaque_credentialed_and_controlled_urls(capture_url: str) -> None:
    with pytest.raises(BrowserClipCapabilityValidationError):
        browser_clip_url_origin(capture_url)


@pytest.mark.parametrize("return_iso_expiry", [False, True])
def test_issue_uses_256_bit_opaque_token_hash_only_and_database_expiry(return_iso_expiry: bool) -> None:
    database_now = datetime(2040, 2, 3, 4, 5, 6, tzinfo=UTC)
    store = _MemoryCapabilityStore(now=database_now, return_iso_expiry=return_iso_expiry)

    issued = issue_browser_clip_capability(store, origin="HTTPS://BÜCHER.example:443")

    assert re.fullmatch(r"alice_clip_[A-Za-z0-9_-]{43}", issued.capability)
    assert issued.origin == "https://xn--bcher-kva.example"
    assert issued.expires_at == database_now + timedelta(seconds=BROWSER_CLIP_CAPABILITY_TTL_SECONDS)
    assert store.create_calls == [
        {
            "capability_hash": sha256(issued.capability.encode("utf-8")).hexdigest(),
            "origin": issued.origin,
            "ttl_seconds": BROWSER_CLIP_CAPABILITY_TTL_SECONDS,
        }
    ]
    assert issued.capability not in repr(store.create_calls)
    assert issued.capability not in repr(store.records)
    assert len(str(store.create_calls[0]["capability_hash"])) == 64


def test_capability_can_be_redeemed_once_and_replay_and_tamper_fail() -> None:
    store = _MemoryCapabilityStore(now=datetime(2040, 2, 3, tzinfo=UTC))
    issued = issue_browser_clip_capability(store, origin="https://example.test")

    replacement = "A" if issued.capability[-1] != "A" else "B"
    tampered = f"{issued.capability[:-1]}{replacement}"
    with pytest.raises(BrowserClipCapabilityValidationError):
        consume_browser_clip_capability(
            store,
            capability=tampered,
            capture_url="https://example.test/article",
            request_origin="https://example.test",
        )

    redeemed = consume_browser_clip_capability(
        store,
        capability=issued.capability,
        capture_url="https://example.test/article?id=1#selection",
        request_origin="https://example.test",
    )
    assert redeemed["origin"] == "https://example.test"

    with pytest.raises(BrowserClipCapabilityValidationError):
        consume_browser_clip_capability(
            store,
            capability=issued.capability,
            capture_url="https://example.test/article",
            request_origin="https://example.test",
        )


def test_expired_capability_is_rejected_by_the_store() -> None:
    store = _MemoryCapabilityStore(now=datetime(2040, 2, 3, tzinfo=UTC))
    issued = issue_browser_clip_capability(store, origin="https://example.test")
    store.now = issued.expires_at

    with pytest.raises(BrowserClipCapabilityValidationError):
        consume_browser_clip_capability(
            store,
            capability=issued.capability,
            capture_url="https://example.test/article",
            request_origin="https://example.test",
        )


def test_wrong_origin_attempts_do_not_consume_the_capability() -> None:
    store = _MemoryCapabilityStore(now=datetime(2040, 2, 3, tzinfo=UTC))
    issued = issue_browser_clip_capability(store, origin="https://example.test")
    capability_hash = browser_clip_capability_hash(issued.capability)

    with pytest.raises(BrowserClipCapabilityValidationError):
        consume_browser_clip_capability(
            store,
            capability=issued.capability,
            capture_url="https://attacker.test/article",
            request_origin="https://attacker.test",
        )
    assert store.records[capability_hash]["consumed_at"] is None

    calls_before_url_mismatch = len(store.consume_calls)
    with pytest.raises(BrowserClipCapabilityValidationError, match="origin does not match"):
        consume_browser_clip_capability(
            store,
            capability=issued.capability,
            capture_url="https://attacker.test/article",
            request_origin="https://example.test",
        )
    assert len(store.consume_calls) == calls_before_url_mismatch
    assert store.records[capability_hash]["consumed_at"] is None

    redeemed = consume_browser_clip_capability(
        store,
        capability=issued.capability,
        capture_url="HTTPS://EXAMPLE.test:443/article",
        request_origin="HTTPS://EXAMPLE.test:443",
    )
    assert redeemed["consumed_at"] == store.now


@pytest.mark.parametrize(
    "capability",
    [
        "",
        BROWSER_CLIP_CAPABILITY_PREFIX,
        f"{BROWSER_CLIP_CAPABILITY_PREFIX}{'A' * 42}",
        f"{BROWSER_CLIP_CAPABILITY_PREFIX}{'A' * 44}",
        f"{BROWSER_CLIP_CAPABILITY_PREFIX}{'A' * 42}=",
        f"{BROWSER_CLIP_CAPABILITY_PREFIX}{'A' * 42}!",
        f" {BROWSER_CLIP_CAPABILITY_PREFIX}{'A' * 43}",
        f"{BROWSER_CLIP_CAPABILITY_PREFIX}{'A' * 43}\n",
        f"other_clip_{'A' * 43}",
    ],
)
def test_malformed_capability_is_rejected_without_touching_the_store(capability: str) -> None:
    store = _MemoryCapabilityStore(now=datetime(2040, 2, 3, tzinfo=UTC))

    with pytest.raises(BrowserClipCapabilityValidationError):
        consume_browser_clip_capability(
            store,
            capability=capability,
            capture_url="https://example.test/article",
            request_origin="https://example.test",
        )

    assert store.consume_calls == []


def test_missing_origin_is_rejected_without_touching_the_store() -> None:
    store = _MemoryCapabilityStore(now=datetime(2040, 2, 3, tzinfo=UTC))
    capability = f"{BROWSER_CLIP_CAPABILITY_PREFIX}{'A' * 43}"

    with pytest.raises(BrowserClipCapabilityValidationError, match="origin is required"):
        consume_browser_clip_capability(
            store,
            capability=capability,
            capture_url="https://example.test/article",
            request_origin=None,
        )

    assert store.consume_calls == []
