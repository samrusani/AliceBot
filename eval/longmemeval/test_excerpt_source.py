"""The benchmark must be able to measure the product, not only the harness.

Background, established 2026-08-17. Every published Alice benchmark number,
81.2% included, was produced by a harness that called
``store.list_source_chunks`` directly and rendered its own excerpts. No MCP tool
ever exposed that capability, so the number described a retrieval path no user
had. The context pack returned sources as bibliography entries with no text.

The product side of that gap is now closed: packs and ``alice_recall`` carry a
windowed excerpt per source. The two are still not equivalent, though. The
harness reads every chunk of every retrieved source under its own budget; an
agent gets one windowed excerpt per source. So a run can still measure more than
the product delivers.

``ALICE_LME_EXCERPT_SOURCE`` makes that a run-level choice instead of a hidden
property of the code, and these tests pin what each setting means.

The default is deliberately unchanged. Flipping it would silently restate 81.2%
as measuring something else, and the honest product-path number does not exist
until someone pays for a run that produces it. Unmeasured is a fine thing to be;
quietly reported is not.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

_EVAL_DIR = Path(__file__).resolve().parent.parent
_API_SRC = _EVAL_DIR.parent / "apps" / "api" / "src"
for _path in (_EVAL_DIR, _API_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from longmemeval.adapter import (  # noqa: E402
    DEFAULT_EXCERPT_SOURCE,
    EXCERPT_SOURCE_ENV,
    EXCERPT_SOURCE_PACK_EXCERPTS,
    EXCERPT_SOURCE_STORE_CHUNKS,
    QuestionRun,
    excerpt_source_from_env,
)


class _PrivilegeTrackingStore:
    """Records whether the harness reached past the pack into the store."""

    def __init__(self) -> None:
        self.list_source_chunks_calls: list[str] = []

    def list_source_chunks(self, source_id: str) -> list[dict[str, object]]:
        self.list_source_chunks_calls.append(source_id)
        return [
            {"text": "chunk one, straight from the store", "chunk_index": 0},
            {"text": "chunk two, which no MCP tool returns", "chunk_index": 1},
        ]


def _run(excerpt_source: str) -> tuple[QuestionRun, _PrivilegeTrackingStore]:
    store = _PrivilegeTrackingStore()
    run = QuestionRun.__new__(QuestionRun)
    run.store = store  # type: ignore[assignment]
    run.excerpt_source = excerpt_source
    return run, store


PACK_SOURCE: dict[str, object] = {
    "id": "source-1",
    "excerpt": "the windowed excerpt an agent actually receives",
    "excerpt_kind": "imported_source_material",
}


def test_default_is_unchanged_so_existing_numbers_stay_comparable() -> None:
    assert DEFAULT_EXCERPT_SOURCE == EXCERPT_SOURCE_STORE_CHUNKS
    assert excerpt_source_from_env() == EXCERPT_SOURCE_STORE_CHUNKS


def test_store_chunks_mode_still_reads_the_whole_document() -> None:
    """The path every published number was measured on, pinned so it is legible."""

    run, store = _run(EXCERPT_SOURCE_STORE_CHUNKS)

    chunks = run._source_chunks_for(PACK_SOURCE, source_id="source-1")

    assert store.list_source_chunks_calls == ["source-1"]
    assert len(chunks) == 2, "the harness no longer reads every chunk in the privileged mode"


def test_pack_excerpts_mode_never_touches_the_store() -> None:
    """The whole point. Claiming to use the product path is not using it.

    If this passes while ``list_source_chunks`` is still reachable, the mode is
    decorative and the number it produces is not a product-path number.
    """

    run, store = _run(EXCERPT_SOURCE_PACK_EXCERPTS)

    chunks = run._source_chunks_for(PACK_SOURCE, source_id="source-1")

    assert store.list_source_chunks_calls == [], (
        "the harness reached into the store while claiming to measure the product path"
    )
    assert [chunk["text"] for chunk in chunks] == [PACK_SOURCE["excerpt"]]


def test_pack_excerpts_mode_yields_nothing_when_the_pack_carried_no_text() -> None:
    """A source with no excerpt is the pre-fix state, and must score as a miss.

    Silently falling back to the store here would restore the exact gap this
    setting exists to expose.
    """

    run, store = _run(EXCERPT_SOURCE_PACK_EXCERPTS)

    for empty in ({"id": "source-1"}, {"id": "source-1", "excerpt": "   "}):
        assert run._source_chunks_for(empty, source_id="source-1") == []
    assert store.list_source_chunks_calls == []


def test_an_unknown_setting_fails_loudly(monkeypatch) -> None:
    """A typo must not quietly fall back to the privileged reader."""

    monkeypatch.setenv(EXCERPT_SOURCE_ENV, "pack")

    with pytest.raises(ValueError, match="pack"):
        excerpt_source_from_env()


@pytest.mark.parametrize(
    "value", (EXCERPT_SOURCE_STORE_CHUNKS, EXCERPT_SOURCE_PACK_EXCERPTS)
)
def test_both_settings_are_accepted_from_the_environment(monkeypatch, value: str) -> None:
    monkeypatch.setenv(EXCERPT_SOURCE_ENV, value)

    assert excerpt_source_from_env() == value


def test_the_mode_is_fixed_for_a_whole_run(monkeypatch) -> None:
    """Resolved once in __init__, so one run cannot mix the two readers."""

    monkeypatch.setenv(EXCERPT_SOURCE_ENV, EXCERPT_SOURCE_PACK_EXCERPTS)
    run = QuestionRun.__new__(QuestionRun)
    run.excerpt_source = excerpt_source_from_env()

    monkeypatch.setenv(EXCERPT_SOURCE_ENV, EXCERPT_SOURCE_STORE_CHUNKS)

    assert run.excerpt_source == EXCERPT_SOURCE_PACK_EXCERPTS, (
        "the reader changed mid-run, so the resulting number describes neither path"
    )
