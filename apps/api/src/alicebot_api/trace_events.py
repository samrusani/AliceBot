from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, cast
from uuid import UUID

from alicebot_api.store import JsonObject


class TraceEventWriter(Protocol):
    """Small persistence seam shared by trace-producing domains."""

    def append_trace_event(
        self,
        *,
        trace_id: UUID,
        sequence_no: int,
        kind: str,
        payload: JsonObject,
    ) -> object: ...


def append_trace_events(
    store: TraceEventWriter,
    *,
    trace_id: UUID,
    trace_events: Sequence[tuple[str, Mapping[str, object]]],
) -> None:
    """Append an ordered trace batch using the canonical one-based sequence."""

    for sequence_no, (kind, payload) in enumerate(trace_events, start=1):
        store.append_trace_event(
            trace_id=trace_id,
            sequence_no=sequence_no,
            kind=kind,
            payload=cast(JsonObject, dict(payload)),
        )


__all__ = ["TraceEventWriter", "append_trace_events"]
