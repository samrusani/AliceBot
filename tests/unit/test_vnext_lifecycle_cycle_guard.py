from __future__ import annotations

from typing import Mapping

import pytest

from alicebot_api.vnext_lifecycle import (
    LifecycleTransitionError,
    supersession_would_cycle,
)


def _pointer(memory: Mapping[str, object] | None, key: str) -> str | None:
    if memory is None:
        return None
    value = memory.get(key)
    return str(value) if value else None


def test_supersession_would_cycle_detects_direct_predecessor_cycle() -> None:
    # Recording A -> B while B already leads back to A closes an A->B->A cycle.
    mems = {"A": {"id": "A"}, "B": {"id": "B", "superseded_by": "A"}}
    assert (
        supersession_would_cycle(
            memory_id="A",
            successor=mems["B"],
            load_memory=lambda i: mems.get(i),
            read_pointer=_pointer,
        )
        is True
    )


def test_supersession_would_cycle_allows_a_terminating_acyclic_chain() -> None:
    mems = {
        "A": {"id": "A"},
        "B": {"id": "B", "superseded_by": "C"},
        "C": {"id": "C"},
    }
    assert (
        supersession_would_cycle(
            memory_id="A",
            successor=mems["B"],
            load_memory=lambda i: mems.get(i),
            read_pointer=_pointer,
        )
        is False
    )


def test_supersession_would_cycle_fails_closed_on_depth_exhaustion() -> None:
    # A chain that does not terminate within max_depth cannot be confirmed
    # acyclic and must be REJECTED (fail closed), not silently allowed by
    # returning False (audit 2 P1 #1).
    chain: dict[str, dict[str, object]] = {}
    length = 12
    for index in range(length):
        chain[str(index)] = {"id": str(index), "superseded_by": str(index + 1)}
    chain[str(length)] = {"id": str(length)}  # terminal, but beyond max_depth

    with pytest.raises(LifecycleTransitionError):
        supersession_would_cycle(
            memory_id="target-not-on-chain",
            successor=chain["0"],
            load_memory=lambda i: chain.get(i),
            read_pointer=_pointer,
            max_depth=4,
        )


def test_supersession_would_cycle_fails_closed_on_preexisting_cycle() -> None:
    chain = {
        "B": {"id": "B", "superseded_by": "C"},
        "C": {"id": "C", "superseded_by": "B"},
    }

    with pytest.raises(LifecycleTransitionError, match="already contains a cycle"):
        supersession_would_cycle(
            memory_id="A",
            successor=chain["B"],
            load_memory=lambda i: chain.get(i),
            read_pointer=_pointer,
        )


def test_supersession_would_cycle_fails_closed_on_dangling_pointer() -> None:
    successor = {"id": "B", "superseded_by": "missing"}

    with pytest.raises(LifecycleTransitionError, match="points to missing memory"):
        supersession_would_cycle(
            memory_id="A",
            successor=successor,
            load_memory=lambda _i: None,
            read_pointer=_pointer,
        )
