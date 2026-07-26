"""SQLite persistence for reviewed one-unit occurrence counting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
import sqlite3
from typing import cast
from uuid import UUID

from alicebot_api.sqlite_schema import _PYTHON_312_STRIP_CHARS_SQL
from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_occurrence_predicates import (
    canonical_occurrence_selector_key,
    canonicalize_occurrence_accounting_metadata,
    canonicalize_occurrence_claim_aggregation,
    canonicalize_occurrence_predicate,
    canonicalize_occurrence_unit_aggregation,
    occurrence_aggregation_digest,
    occurrence_claim_facts_digest,
    occurrence_claim_review_receipt_digest,
    occurrence_coverage_review_receipt_digest,
    occurrence_evidence_facts_digest,
    occurrence_evidence_review_receipt_digest,
    occurrence_extraction_disposition_review_receipt_digest,
    occurrence_memory_carrier_facts_digest,
    occurrence_predicate_digest,
    occurrence_unit_review_receipt_digest,
)
from alicebot_api.vnext_occurrence_write import _reference_datetime
from alicebot_api.vnext_occurrences import normalize_count_key
from alicebot_api.vnext_project_scope import project_scope_identity
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_stores.memory_lifecycle_common import REDACTION_MARKER
from alicebot_api.vnext_stores.retrieval_common import _search_patterns
from alicebot_api.vnext_stores.sqlite.columns import MEMORY_COLUMNS
from alicebot_api.vnext_stores.sqlite.primitives import (
    _iso_or_none,
    _json_list_text,
    _json_object_text,
    _new_id,
    _utc_now_iso,
)


VNextRow = dict[str, object]
OCCURRENCE_READ_SNAPSHOT_PROOF = "occurrence_read_snapshot_v1"
OCCURRENCE_EXTRACTION_MEMORY_LIMIT = 200
_OCCURRENCE_SUCCESSOR_AGGREGATION_COMPATIBLE_SQL = """
json(
  json_set(
    successor.aggregation_json,
    '$.members[0].member_identity',
    unit.occurrence_key
  )
) = json(unit.aggregation_json)
""".strip()
_OCCURRENCE_OWNER_COUNT_KEY_SQL = """
EXISTS (
  SELECT 1
  FROM occurrence_claims AS owner_claim
  WHERE owner_claim.id = unit.claim_id
    AND owner_claim.user_id = unit.user_id
    AND owner_claim.count_key = unit.count_key
)
""".strip()

OCCURRENCE_COVERAGE_COLUMNS = (
    "id",
    "user_id",
    "coverage_mode",
    "coverage_started_at",
    "historical_review_status",
    "complete_through",
    "reviewed_at",
    "reviewer_id",
    "review_reason",
    "review_version",
    "review_receipt_digest",
    "metadata_json",
    "created_at",
    "updated_at",
)

OCCURRENCE_CLAIM_COLUMNS = (
    "id",
    "user_id",
    "claim_key",
    "count_key",
    "predicate_json",
    "canonical_text",
    "quantity_min",
    "quantity_max",
    "range_kind",
    "resolution_decision",
    "resolution_status",
    "identity_basis",
    "aggregation_json",
    "review_status",
    "occurred_at_start",
    "occurred_at_end",
    "domain",
    "sensitivity",
    "project_scope",
    "resolved_occurrence_id",
    "reviewed_at",
    "reviewer_id",
    "review_reason",
    "review_version",
    "review_receipt_digest",
    "metadata_json",
    "created_at",
    "updated_at",
)

OCCURRENCE_UNIT_COLUMNS = (
    "id",
    "user_id",
    "claim_id",
    "claim_ordinal",
    "occurrence_key",
    "count_key",
    "predicate_json",
    "canonical_text",
    "aggregation_json",
    "unit_value",
    "review_status",
    "identity_status",
    "ambiguity_group_key",
    "occurred_at_start",
    "occurred_at_end",
    "domain",
    "sensitivity",
    "project_scope",
    "reviewed_at",
    "reviewer_id",
    "review_reason",
    "review_version",
    "reviewed_evidence_count",
    "reviewed_evidence_digest",
    "review_receipt_digest",
    "review_receipt_action",
    "superseded_by",
    "retired_at",
    "retired_by",
    "retirement_reason",
    "metadata_json",
    "created_at",
    "updated_at",
)

OCCURRENCE_EVIDENCE_COLUMNS = (
    "id",
    "user_id",
    "claim_id",
    "occurrence_id",
    "source_id",
    "source_chunk_id",
    "memory_id",
    "evidence_key",
    "evidence_role",
    "quote",
    "quote_sha256",
    "confidence",
    "review_status",
    "reviewed_at",
    "reviewer_id",
    "review_reason",
    "review_receipt_digest",
    "review_receipt_action",
    "unit_review_receipt_digest",
    "metadata_json",
    "created_at",
)

OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS = (
    "id",
    "user_id",
    "source_id",
    "source_chunk_id",
    "snapshot_sha256",
    "extractor_version",
    "disposition",
    "predicate_keys",
    "claim_ids",
    "occurrence_ids",
    "review_status",
    "reviewed_at",
    "reviewer_id",
    "review_reason",
    "review_version",
    "review_receipt_digest",
    "metadata_json",
    "created_at",
    "updated_at",
)


def begin_occurrence_read_snapshot(self) -> VNextRow:
    """Anchor one SQLite transaction snapshot for a paged occurrence read."""

    if getattr(self, "_occurrence_snapshot_active", False):
        raise ContinuityStoreInvariantError("an occurrence read snapshot is already active")
    owns_transaction = not self.conn.in_transaction
    self._occurrence_snapshot_active = True
    self._occurrence_snapshot_owned_transaction = owns_transaction
    try:
        if owns_transaction:
            # Capture the lifecycle boundary before SQLite can pin a newer
            # snapshot, then take a writer reservation before the first read.
            # A commit racing between the clock and BEGIN IMMEDIATE remains
            # visible but is later than the lifecycle boundary, so the
            # updated_at/as_of and coverage guards fail closed.
            lifecycle_as_of = datetime.now(UTC)
            self.conn.execute("BEGIN IMMEDIATE")
        else:
            # A caller-owned transaction may already contain uncommitted eval
            # setup writes and therefore cannot be rejected wholesale. Force
            # a write-reservation upgrade without changing a row. A stale WAL
            # snapshot that another writer advanced cannot upgrade and raises
            # SQLITE_BUSY; the optional reader then fails closed while this
            # caller transaction remains untouched.
            self.conn.execute(
                """
                UPDATE occurrence_coverage
                SET id = id
                WHERE 0
                """
            )
            lifecycle_as_of = datetime.now(UTC)
        self.conn.execute(
            """
            SELECT 1
            FROM occurrence_coverage
            WHERE user_id = ?
            LIMIT 1
            """,
            (self.user_id,),
        ).fetchone()
    except BaseException:
        del self._occurrence_snapshot_active
        del self._occurrence_snapshot_owned_transaction
        if owns_transaction:
            self.conn.rollback()
        raise
    return {
        "proof": OCCURRENCE_READ_SNAPSHOT_PROOF,
        "acquired": True,
        "backend": "sqlite",
        "mode": "transaction_snapshot",
        "lifecycle_as_of": lifecycle_as_of,
    }


def end_occurrence_read_snapshot(self) -> None:
    """Release only a transaction opened by the occurrence reader."""

    if not getattr(self, "_occurrence_snapshot_active", False):
        raise ContinuityStoreInvariantError("no occurrence read snapshot is active")
    owns_transaction = bool(self._occurrence_snapshot_owned_transaction)
    del self._occurrence_snapshot_active
    del self._occurrence_snapshot_owned_transaction
    if owns_transaction:
        self.conn.rollback()


def _column_sql(columns: Sequence[str], *, prefix: str = "") -> str:
    return ", ".join(f"{prefix}{column}" for column in columns)


def _decode_cursor_row(
    self,
    cursor: sqlite3.Cursor,
    row: Mapping[str, object] | Sequence[object],
) -> VNextRow:
    """Decode RETURNING rows with either tuple or mapping row factories."""

    if isinstance(row, Mapping):
        raw = dict(row)
    else:
        description = cursor.description or ()
        raw = {str(column[0]): value for column, value in zip(description, row)}
    return self._decode_row(raw)


def _project_scope(value: object) -> list[str]:
    return list(project_scope_identity(value))


def _canonical_json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _same_value(left: object, right: object) -> bool:
    if isinstance(left, Mapping):
        return dict(left) == right
    if isinstance(left, UUID) or isinstance(right, UUID):
        return str(left) == str(right)
    return left == right


def _normalized_occurrence_timestamp(
    value: object | None,
    *,
    field: str,
) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{field} must be an ISO-8601 date or timestamp")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO-8601 date or timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _occurrence_timestamp_moment(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _canonical_count_key_input(value: object) -> str:
    raw = str(value)
    normalized = normalize_count_key(value)
    if raw != normalized:
        raise ValueError("count_key must already be canonical")
    return normalized


def _assert_immutable_winner(
    operation: str,
    row: Mapping[str, object],
    expected: Mapping[str, object],
) -> None:
    mismatches = [field for field, value in expected.items() if not _same_value(row.get(field), value)]
    if mismatches:
        raise ContinuityStoreInvariantError(
            f"{operation} idempotency winner differs in immutable fields: " + ", ".join(sorted(mismatches))
        )


def _lock_occurrence_graph_mutation(self: object) -> None:
    """Mirror the bundled pre-row graph boundary; SQLite is single-writer."""

    lock_graph_mutation = getattr(self, "lock_graph_mutation", None)
    if callable(lock_graph_mutation):
        lock_graph_mutation()


def _signed_source_reestablishment_unit(
    unit: Mapping[str, object],
    *,
    claim_id: str,
) -> bool:
    """Verify the narrow lifecycle-detached state that may receive fresh source evidence."""

    review_version = unit.get("review_version")
    reviewer_id = str(unit.get("reviewer_id") or "")
    reason = str(unit.get("review_reason") or "")
    evidence_digest = str(unit.get("reviewed_evidence_digest") or "")
    receipt = str(unit.get("review_receipt_digest") or "")
    if (
        unit.get("review_status") != "retired"
        or unit.get("review_receipt_action") != "retired"
        or str(unit.get("claim_id") or "") != claim_id
        or unit.get("retired_at") is None
        or unit.get("superseded_by") is not None
        or isinstance(review_version, bool)
        or not isinstance(review_version, int)
        or review_version < 1
        or not reviewer_id
        or not reason.endswith("(http_source_review_envelope_change)")
        or len(evidence_digest) != 64
        or len(receipt) != 64
    ):
        return False
    try:
        expected = occurrence_unit_review_receipt_digest(
            unit,
            action="retired",
            reviewer_id=reviewer_id,
            reason=reason,
            review_version=review_version,
            evidence_digest=evidence_digest,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return receipt == expected


def _lock_occurrence_memory_carrier(self, memory_id: str) -> None:
    cursor = self._execute(
        """
        UPDATE memories
        SET id = id
        WHERE id = ?
          AND user_id = ?
        """,
        (str(memory_id), self.user_id),
    )
    if cursor.rowcount != 1:
        raise ContinuityStoreInvariantError(
            "occurrence evidence memory carrier is not owned"
        )


def _lock_occurrence_claim_rows(
    self,
    claim_ids: Sequence[str],
) -> dict[str, VNextRow]:
    ordered = sorted(set(str(value) for value in claim_ids))
    if not ordered:
        return {}
    placeholders = ", ".join("?" for _value in ordered)
    cursor = self._execute(
        f"""
        UPDATE occurrence_claims
        SET review_version = review_version
        WHERE user_id = ?
          AND id IN ({placeholders})
        """,
        (self.user_id, *ordered),
    )
    if cursor.rowcount != len(ordered):
        raise ContinuityStoreInvariantError(
            "occurrence evidence claim lock lost an owned reference"
        )
    rows = self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_CLAIM_COLUMNS)}
        FROM occurrence_claims
        WHERE user_id = ?
          AND id IN ({placeholders})
        ORDER BY id ASC
        """,
        (self.user_id, *ordered),
    )
    return {str(row["id"]): row for row in rows}


def _lock_occurrence_unit_rows(
    self,
    occurrence_ids: Sequence[str],
) -> dict[str, VNextRow]:
    ordered = sorted(set(str(value) for value in occurrence_ids))
    if not ordered:
        return {}
    placeholders = ", ".join("?" for _value in ordered)
    cursor = self._execute(
        f"""
        UPDATE occurrence_units
        SET review_version = review_version
        WHERE user_id = ?
          AND id IN ({placeholders})
        """,
        (self.user_id, *ordered),
    )
    if cursor.rowcount != len(ordered):
        raise ContinuityStoreInvariantError(
            "occurrence evidence unit lock lost an owned reference"
        )
    rows = self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS)}
        FROM occurrence_units
        WHERE user_id = ?
          AND id IN ({placeholders})
        ORDER BY id ASC
        """,
        (self.user_id, *ordered),
    )
    return {str(row["id"]): row for row in rows}


def _allows_retired_source_reestablishment_evidence(
    self,
    *,
    expected: Mapping[str, object],
    unit: Mapping[str, object],
    snapshot_sha256: str | None,
) -> bool:
    metadata = expected.get("metadata_json")
    if (
        snapshot_sha256 is None
        or len(snapshot_sha256) != 64
        or expected.get("memory_id") is not None
        or expected.get("source_id") is None
        or expected.get("source_chunk_id") is None
        or expected.get("evidence_role") != "supports"
        or not isinstance(metadata, Mapping)
        or metadata.get("source_snapshot_sha256") != snapshot_sha256
        or metadata.get("source_reestablishment_stage")
        != "http_source_review_envelope_change"
        or not _signed_source_reestablishment_unit(
            unit,
            claim_id=str(expected["claim_id"]),
        )
    ):
        return False
    current_chunk = self.get_source_chunk_for_occurrence_accounting(
        str(expected["source_chunk_id"])
    )
    return bool(
        isinstance(current_chunk, Mapping)
        and str(current_chunk.get("source_id") or "")
        == str(expected["source_id"])
        and current_chunk.get("snapshot_sha256") == snapshot_sha256
    )


def _canonical_text_values(
    values: Sequence[str] | None,
    *,
    field: str,
    uuid_values: bool = False,
) -> list[str]:
    normalized: set[str] = set()
    for raw in values or ():
        value = " ".join(str(raw).split()).strip()
        if not value:
            raise ValueError(f"{field} cannot contain an empty value")
        if uuid_values:
            try:
                value = str(UUID(value))
            except ValueError as exc:
                raise ValueError(f"{field} must contain UUID values") from exc
        normalized.add(value)
    return sorted(normalized)


def _normalized_source_title(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(value.split()).strip().rstrip(".")


def _extraction_snapshot_sha256(row: Mapping[str, object]) -> str:
    text = str(row["chunk_text"])
    reference = _reference_datetime(
        {
            "metadata_json": {
                "session_date": row.get("source_session_date"),
            },
            "source_created_at": row.get("source_created_at"),
        }
    )
    source_created_at = _reference_datetime(
        {
            "metadata_json": {},
            "source_created_at": row.get("source_created_at"),
        }
    )
    payload = {
        "chunk_index": int(cast(int, row["chunk_index"])),
        "source_created_at": (
            source_created_at.isoformat(timespec="microseconds") if source_created_at is not None else None
        ),
        "source_domain": str(row["source_domain"]),
        "source_chunk_id": str(row["source_chunk_id"]),
        "source_content_hash": str(row["source_content_hash"]),
        "source_id": str(row["source_id"]),
        "source_provenance_role": str(row.get("source_provenance_role") or "").casefold(),
        "source_project_scope": list(cast(Sequence[object], row["source_project_scope"])),
        "source_reference_datetime": (reference.isoformat(timespec="microseconds") if reference is not None else None),
        "source_sensitivity": str(row["source_sensitivity"]),
        "source_title": _normalized_source_title(row.get("source_title")),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _extraction_review_receipt_digest(
    row: Mapping[str, object],
    *,
    action: str,
    reviewer_id: str,
    reason: str,
    review_version: int,
) -> str:
    return occurrence_extraction_disposition_review_receipt_digest(
        row,
        action=action,
        reviewer_id=reviewer_id,
        reason=reason,
        review_version=review_version,
    )


def _receipt_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _coverage_receipt_digest(
    *,
    coverage_id: object,
    user_id: object,
    review_version: int,
    coverage_mode: str,
    coverage_started_at: object,
    historical_review_status: str,
    complete_through: object | None,
    reviewer_id: str,
    reason: str,
    accounting_metadata: Mapping[str, object] | None,
) -> str:
    return occurrence_coverage_review_receipt_digest(
        coverage_id=coverage_id,
        user_id=user_id,
        review_version=review_version,
        coverage_mode=coverage_mode,
        coverage_started_at=coverage_started_at,
        historical_review_status=historical_review_status,
        complete_through=complete_through,
        reviewer_id=reviewer_id,
        reason=reason,
        accounting_metadata=accounting_metadata,
    )


def _evidence_digest(rows: Sequence[Mapping[str, object]]) -> str:
    canonical = "|".join(
        occurrence_evidence_facts_digest(row)
        for row in sorted(
            rows,
            key=lambda row: (str(row["evidence_key"]), str(row["id"])),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_occurrence_coverage(
    self,
    *,
    started_at: datetime | str | None = None,
    actor_type: str = "system",
) -> VNextRow:
    """Create the forward-only boundary once; never infer historical coverage."""

    _lock_occurrence_graph_mutation(self)
    coverage_id = _new_id(None)
    cursor = self._execute(
        f"""
        INSERT OR IGNORE INTO occurrence_coverage (
          id,
          user_id,
          coverage_mode,
          coverage_started_at,
          historical_review_status,
          metadata_json,
          created_at,
          updated_at
        )
        VALUES (?, ?, 'forward_only', ?, 'not_reviewed', '{{}}', ?, ?)
        RETURNING {_column_sql(OCCURRENCE_COVERAGE_COLUMNS)}
        """,
        (
            coverage_id,
            self.user_id,
            _iso_or_none(started_at) or _utc_now_iso(),
            _utc_now_iso(),
            _utc_now_iso(),
        ),
    )
    raw_row = cursor.fetchone()
    created = raw_row is not None
    row = (
        _decode_cursor_row(self, cursor, raw_row)
        if raw_row is not None
        else self._fetch_one(
            "ensure_occurrence_coverage",
            f"""
            SELECT {_column_sql(OCCURRENCE_COVERAGE_COLUMNS)}
            FROM occurrence_coverage
            WHERE user_id = ?
            """,
            (self.user_id,),
        )
    )
    if created:
        self._append_mutation_event(
            event_type="occurrence.coverage_updated",
            actor_type=actor_type,
            target_type="occurrence_coverage",
            target_id=row["id"],
            payload={
                "coverage_mode": row["coverage_mode"],
                "coverage_started_at": row["coverage_started_at"],
                "historical_review_status": row["historical_review_status"],
            },
        )
    return row


def get_occurrence_coverage(self) -> VNextRow | None:
    return self._fetch_optional_one(
        f"""
        SELECT {_column_sql(OCCURRENCE_COVERAGE_COLUMNS)}
        FROM occurrence_coverage
        WHERE user_id = ?
        """,
        (self.user_id,),
    )


def invalidate_occurrence_coverage(
    self,
    *,
    reason: str,
    effective_at: datetime | str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> tuple[VNextRow | None, bool]:
    """CAS-revoke signed historical coverage after a relevant mutation."""

    _lock_occurrence_graph_mutation(self)
    invalidation_reason = reason.strip()
    if not invalidation_reason:
        raise ValueError("coverage invalidation requires a reason")
    current = get_occurrence_coverage(self)
    if current is None:
        return None, False
    lock = self._execute(
        """
        UPDATE occurrence_coverage
        SET review_version = review_version
        WHERE user_id = ?
          AND id = ?
          AND review_version = ?
        """,
        (self.user_id, current["id"], current["review_version"]),
    )
    if lock.rowcount != 1:
        raise ContinuityStoreInvariantError("coverage invalidation lost its lifecycle CAS")
    current = get_occurrence_coverage(self)
    if current is None:
        raise ContinuityStoreInvariantError("coverage invalidation lost its lifecycle CAS")
    if (
        current.get("coverage_mode") == "forward_only"
        and current.get("historical_review_status") == "not_reviewed"
        and current.get("complete_through") is None
        and current.get("review_receipt_digest") is None
    ):
        return current, False
    complete_through = current.get("complete_through")
    if effective_at is not None and complete_through is not None:
        if _receipt_timestamp(effective_at) > _receipt_timestamp(complete_through):
            return current, False
    expected_review_version = int(cast(int, current["review_version"]))
    cursor = self._execute(
        """
        UPDATE occurrence_coverage
        SET coverage_mode = 'forward_only',
            historical_review_status = 'not_reviewed',
            complete_through = NULL,
            reviewed_at = NULL,
            reviewer_id = NULL,
            review_reason = NULL,
            review_version = review_version + 1,
            review_receipt_digest = NULL,
            metadata_json = '{}',
            updated_at = ?
        WHERE user_id = ?
          AND id = ?
          AND review_version = ?
          AND NOT (
            coverage_mode = 'forward_only'
            AND historical_review_status = 'not_reviewed'
            AND complete_through IS NULL
            AND review_receipt_digest IS NULL
          )
        """,
        (
            _utc_now_iso(),
            self.user_id,
            str(current["id"]),
            expected_review_version,
        ),
    )
    if cursor.rowcount != 1:
        raise ContinuityStoreInvariantError("coverage invalidation lost its lifecycle CAS")
    row = self._fetch_one(
        "invalidate_occurrence_coverage",
        f"""
        SELECT {_column_sql(OCCURRENCE_COVERAGE_COLUMNS)}
        FROM occurrence_coverage
        WHERE user_id = ? AND id = ?
        """,
        (self.user_id, str(current["id"])),
    )
    self._append_mutation_event(
        event_type="occurrence.coverage_invalidated",
        actor_type=actor_type,
        actor_id=actor_id,
        target_type="occurrence_coverage",
        target_id=str(row["id"]),
        payload={
            "effective_at": (_receipt_timestamp(effective_at) if effective_at is not None else None),
            "previous_coverage_mode": current["coverage_mode"],
            "previous_complete_through": current.get("complete_through"),
            "previous_review_version": expected_review_version,
            "review_version": row["review_version"],
            "reason": invalidation_reason,
        },
    )
    return row, True


def review_occurrence_coverage(
    self,
    *,
    coverage_mode: str,
    historical_review_status: str,
    reviewer_id: str,
    reason: str,
    coverage_started_at: datetime | str | None = None,
    complete_through: datetime | str | None = None,
    accounting_metadata: Mapping[str, object] | None = None,
    expected_review_version: int = 0,
    actor_type: str = "user",
) -> VNextRow:
    """CAS-sign one non-regressive coverage qualification."""

    _lock_occurrence_graph_mutation(self)
    if coverage_mode not in {
        "forward_only",
        "partial_history",
        "complete_history",
    }:
        raise ValueError("invalid occurrence coverage_mode")
    if historical_review_status not in {
        "not_reviewed",
        "needs_review",
        "reviewed",
    }:
        raise ValueError("invalid occurrence historical_review_status")
    reviewer = reviewer_id.strip()
    review_reason = reason.strip()
    if not reviewer or not review_reason:
        raise ValueError("coverage review requires reviewer_id and reason")
    current = get_occurrence_coverage(self)
    if current is None:
        raise ContinuityStoreInvariantError("review_occurrence_coverage requires an initialized boundary")
    if int(cast(int, current["review_version"])) != expected_review_version:
        raise ContinuityStoreInvariantError("review_occurrence_coverage lost its lifecycle CAS")
    lock = self._execute(
        """
        UPDATE occurrence_coverage
        SET review_version = review_version
        WHERE user_id = ?
          AND id = ?
          AND review_version = ?
        """,
        (self.user_id, current["id"], expected_review_version),
    )
    if lock.rowcount != 1:
        raise ContinuityStoreInvariantError("review_occurrence_coverage lost its lifecycle CAS")
    mode_rank = {"forward_only": 0, "partial_history": 1, "complete_history": 2}
    review_rank = {"not_reviewed": 0, "needs_review": 1, "reviewed": 2}
    if mode_rank[coverage_mode] < mode_rank[str(current["coverage_mode"])]:
        raise ContinuityStoreInvariantError("coverage mode cannot regress")
    if review_rank[historical_review_status] < review_rank[str(current["historical_review_status"])]:
        raise ContinuityStoreInvariantError("coverage review status cannot regress")
    started = _receipt_timestamp(
        coverage_started_at if coverage_started_at is not None else current["coverage_started_at"]
    )
    complete_value = complete_through if complete_through is not None else current.get("complete_through")
    complete = _receipt_timestamp(complete_value) if complete_value is not None else None
    if _receipt_timestamp(started) > _receipt_timestamp(current["coverage_started_at"]):
        raise ContinuityStoreInvariantError("coverage start cannot move later")
    if current.get("complete_through") is not None and (
        complete is None or _receipt_timestamp(complete) < _receipt_timestamp(current["complete_through"])
    ):
        raise ContinuityStoreInvariantError("coverage completion cannot regress")
    if coverage_mode != "forward_only" and (historical_review_status != "reviewed" or complete is None):
        raise ContinuityStoreInvariantError("historical coverage modes require reviewed complete_through")
    if complete is not None and _receipt_timestamp(complete) < _receipt_timestamp(started):
        raise ContinuityStoreInvariantError("complete_through cannot precede the coverage boundary")
    canonical_accounting = (
        canonicalize_occurrence_accounting_metadata(accounting_metadata) if accounting_metadata is not None else None
    )
    if coverage_mode == "complete_history" and canonical_accounting is None:
        raise ContinuityStoreInvariantError("complete-history coverage requires signed occurrence accounting metadata")
    if coverage_mode != "complete_history" and canonical_accounting is not None:
        raise ContinuityStoreInvariantError("occurrence accounting metadata is reserved for complete-history coverage")
    if coverage_mode == "complete_history":
        assert canonical_accounting is not None
        from alicebot_api.vnext_stores.sqlite.occurrence_accounting import (
            summarize_occurrence_extraction_accounting,
        )

        summary = summarize_occurrence_extraction_accounting(
            self,
            extractor_version=str(canonical_accounting["extractor_version"]),
            source_ids=None,
        )
        authoritative_accounting = canonicalize_occurrence_accounting_metadata(
            {
                "accounting_schema": "occurrence_accounting_v1",
                "extractor_version": summary["extractor_version"],
                "source_ids": summary["source_ids"],
                "source_chunk_ids": summary["source_chunk_ids"],
                "snapshot_digest": summary["snapshot_digest"],
                "disposition_digest": summary["disposition_digest"],
            }
        )
        if summary.get("complete") is not True or canonical_accounting != authoritative_accounting:
            raise ContinuityStoreInvariantError(
                "complete-history coverage accounting does not match the current complete corpus"
            )
    receipt = _coverage_receipt_digest(
        coverage_id=current["id"],
        user_id=current["user_id"],
        review_version=expected_review_version + 1,
        coverage_mode=coverage_mode,
        coverage_started_at=started,
        historical_review_status=historical_review_status,
        complete_through=complete,
        reviewer_id=reviewer,
        reason=review_reason,
        accounting_metadata=canonical_accounting,
    )
    cursor = self._execute(
        """
        UPDATE occurrence_coverage
        SET coverage_mode = ?,
            coverage_started_at = ?,
            historical_review_status = ?,
            complete_through = ?,
            reviewed_at = ?,
            reviewer_id = ?,
            review_reason = ?,
            review_version = review_version + 1,
            review_receipt_digest = ?,
            metadata_json = ?,
            updated_at = ?
        WHERE user_id = ?
          AND id = ?
          AND review_version = ?
        """,
        (
            coverage_mode,
            started,
            historical_review_status,
            complete,
            _utc_now_iso(),
            reviewer,
            review_reason,
            receipt,
            _json_object_text(canonical_accounting or {}),
            _utc_now_iso(),
            self.user_id,
            current["id"],
            expected_review_version,
        ),
    )
    if cursor.rowcount != 1:
        raise ContinuityStoreInvariantError("review_occurrence_coverage lost its lifecycle CAS")
    row = self._fetch_one(
        "review_occurrence_coverage",
        f"""
        SELECT {_column_sql(OCCURRENCE_COVERAGE_COLUMNS)}
        FROM occurrence_coverage
        WHERE user_id = ? AND id = ?
        """,
        (self.user_id, current["id"]),
    )
    self._append_mutation_event(
        event_type="occurrence.coverage_updated",
        actor_type=actor_type,
        actor_id=reviewer,
        target_type="occurrence_coverage",
        target_id=row["id"],
        payload={
            "coverage_mode": row["coverage_mode"],
            "coverage_started_at": row["coverage_started_at"],
            "historical_review_status": row["historical_review_status"],
            "complete_through": row["complete_through"],
            "review_version": row["review_version"],
            "review_receipt_digest": row["review_receipt_digest"],
            "reason": review_reason,
        },
    )
    return row


def get_or_create_occurrence_claim(
    self,
    claim: JsonObject,
    *,
    actor_type: str = "system",
) -> tuple[VNextRow, bool]:
    _lock_occurrence_graph_mutation(self)
    identity_basis = str(claim.get("identity_basis") or "ambiguous")
    resolution_decision = str(
        claim.get("resolution_decision") or ("ambiguous" if identity_basis == "ambiguous" else "new")
    )
    project_scope = _project_scope(claim.get("project_scope"))
    quantity_min = int(cast(int, claim.get("quantity_min", 1)))
    quantity_max = claim.get("quantity_max")
    if quantity_max is None and claim.get("range_kind", "exact") == "exact":
        quantity_max = quantity_min
    occurred_at_start = _normalized_occurrence_timestamp(
        claim.get("occurred_at_start"),
        field="occurred_at_start",
    )
    occurred_at_end = _normalized_occurrence_timestamp(
        claim.get("occurred_at_end"),
        field="occurred_at_end",
    )
    if (
        occurred_at_start is not None
        and occurred_at_end is not None
        and _occurrence_timestamp_moment(occurred_at_end) < _occurrence_timestamp_moment(occurred_at_start)
    ):
        raise ValueError("occurred_at_end must not precede occurred_at_start")
    predicate = canonicalize_occurrence_predicate(
        claim.get("predicate_json"),
        allow_claim_ops=True,
    )
    aggregation = canonicalize_occurrence_claim_aggregation(claim.get("aggregation_json"))
    range_kind = str(claim.get("range_kind") or "exact")
    if len(cast(list[object], aggregation["bases"])) > 1 and (
        range_kind != "exact" or quantity_min != 1 or quantity_max != 1
    ):
        raise ValueError("object_member aggregation requires one exact event")
    expected = {
        "claim_key": str(claim["claim_key"]),
        "count_key": _canonical_count_key_input(claim["count_key"]),
        "predicate_json": predicate,
        "canonical_text": str(claim["canonical_text"]),
        "quantity_min": quantity_min,
        "quantity_max": quantity_max,
        "range_kind": range_kind,
        "resolution_decision": resolution_decision,
        "identity_basis": identity_basis,
        "aggregation_json": aggregation,
        "occurred_at_start": occurred_at_start,
        "occurred_at_end": occurred_at_end,
        "domain": str(claim.get("domain") or "unknown"),
        "sensitivity": str(claim.get("sensitivity") or "unknown"),
        "project_scope": project_scope,
    }
    cursor = self._execute(
        f"""
        INSERT OR IGNORE INTO occurrence_claims (
          id,
          user_id,
          claim_key,
          count_key,
          predicate_json,
          canonical_text,
          quantity_min,
          quantity_max,
          range_kind,
          resolution_decision,
          resolution_status,
          identity_basis,
          aggregation_json,
          review_status,
          occurred_at_start,
          occurred_at_end,
          domain,
          sensitivity,
          project_scope,
          metadata_json,
          created_at,
          updated_at
        )
        VALUES (
          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, 'candidate',
          ?, ?, ?, ?, ?, ?, ?, ?
        )
        RETURNING {_column_sql(OCCURRENCE_CLAIM_COLUMNS)}
        """,
        (
            _new_id(claim.get("id")),
            self.user_id,
            expected["claim_key"],
            expected["count_key"],
            _canonical_json_text(predicate),
            expected["canonical_text"],
            expected["quantity_min"],
            expected["quantity_max"],
            expected["range_kind"],
            expected["resolution_decision"],
            expected["identity_basis"],
            _canonical_json_text(aggregation),
            expected["occurred_at_start"],
            expected["occurred_at_end"],
            expected["domain"],
            expected["sensitivity"],
            _json_list_text(project_scope),
            _json_object_text(claim.get("metadata_json")),
            _utc_now_iso(),
            _utc_now_iso(),
        ),
    )
    raw_row = cursor.fetchone()
    created = raw_row is not None
    row = (
        _decode_cursor_row(self, cursor, raw_row)
        if raw_row is not None
        else self._fetch_one(
            "get_or_create_occurrence_claim",
            f"""
            SELECT {_column_sql(OCCURRENCE_CLAIM_COLUMNS)}
            FROM occurrence_claims
            WHERE user_id = ?
              AND claim_key = ?
            """,
            (self.user_id, expected["claim_key"]),
        )
    )
    _assert_immutable_winner("occurrence claim", row, expected)
    if created:
        self._append_mutation_event(
            event_type="occurrence.claim_created",
            actor_type=actor_type,
            target_type="occurrence_claim",
            target_id=row["id"],
            payload={
                "claim_key": row["claim_key"],
                "count_key": row["count_key"],
                "predicate_json": row["predicate_json"],
                "predicate_digest": occurrence_predicate_digest(
                    row["predicate_json"],
                    allow_claim_ops=True,
                ),
                "resolution_decision": row["resolution_decision"],
                "identity_basis": row["identity_basis"],
                "aggregation_json": row["aggregation_json"],
                "aggregation_digest": occurrence_aggregation_digest(
                    row["aggregation_json"],
                    occurrence_key=None,
                ),
            },
        )
        invalidate_occurrence_coverage(
            self,
            reason="An occurrence claim was added to the reviewed graph.",
            actor_type=actor_type,
        )
    return row, created


def get_occurrence_claim(self, claim_id: str) -> VNextRow | None:
    return self._fetch_optional_one(
        f"""
        SELECT {_column_sql(OCCURRENCE_CLAIM_COLUMNS)}
        FROM occurrence_claims
        WHERE id = ?
          AND user_id = ?
        """,
        (str(claim_id), self.user_id),
    )


def review_occurrence_claim(
    self,
    *,
    claim_id: str,
    resolution_status: str,
    resolution_decision: str,
    identity_basis: str,
    reviewer_id: str,
    reason: str,
    expected_review_version: int = 0,
    resolved_occurrence_id: str | None = None,
    actor_type: str = "user",
    _defer_occurrence_accounting: bool = False,
) -> VNextRow:
    """CAS one claim decision; accepted/rejected decisions are terminal."""

    _lock_occurrence_graph_mutation(self)
    reviewer_id = reviewer_id.strip()
    reason = reason.strip()
    if not reviewer_id or not reason:
        raise ValueError("occurrence claim review requires reviewer_id and reason")
    if resolution_status not in {"pending", "resolved", "rejected"}:
        raise ValueError("invalid occurrence claim resolution_status")
    if resolution_decision not in {"new", "link_existing", "ambiguous"}:
        raise ValueError("invalid occurrence claim resolution_decision")
    if resolution_status == "resolved":
        if resolution_decision == "new" and resolved_occurrence_id is not None:
            raise ValueError("resolved new claims must not select one occurrence")
        if resolution_decision == "link_existing" and resolved_occurrence_id is None:
            raise ValueError("resolved link_existing claims require an occurrence")
        if resolution_decision == "ambiguous":
            raise ValueError("ambiguous claims cannot be resolved")
    elif resolved_occurrence_id is not None:
        raise ValueError("only resolved link_existing claims select an occurrence")
    review_status = {
        "pending": "candidate",
        "resolved": "accepted",
        "rejected": "rejected",
    }[resolution_status]
    event_type = {
        "pending": "occurrence.marked_ambiguous",
        "resolved": "occurrence.claim_resolved",
        "rejected": "occurrence.claim_rejected",
    }[resolution_status]
    current = _lock_occurrence_claim_rows(self, [str(claim_id)])[str(claim_id)]
    owned_unit_rows = self._fetch_all(
        """
        SELECT id
        FROM occurrence_units
        WHERE user_id = ?
          AND claim_id = ?
        ORDER BY id ASC
        """,
        (self.user_id, str(claim_id)),
    )
    unit_ids = [str(unit["id"]) for unit in owned_unit_rows]
    if resolved_occurrence_id is not None:
        unit_ids.append(str(resolved_occurrence_id))
    _lock_occurrence_unit_rows(self, unit_ids)
    if (
        current.get("review_status") != "candidate"
        or current.get("resolution_status") != "pending"
        or int(cast(int, current["review_version"])) != expected_review_version
    ):
        raise ContinuityStoreInvariantError("review_occurrence_claim lost its lifecycle CAS")
    predicate = canonicalize_occurrence_predicate(
        current.get("predicate_json"),
        allow_claim_ops=True,
    )
    aggregation = canonicalize_occurrence_claim_aggregation(current.get("aggregation_json"))
    review_receipt = (
        occurrence_claim_review_receipt_digest(
            current,
            resolution_status=resolution_status,
            resolution_decision=resolution_decision,
            identity_basis=identity_basis,
            resolved_occurrence_id=resolved_occurrence_id,
            reviewer_id=reviewer_id,
            reason=reason,
            review_version=expected_review_version + 1,
        )
        if resolution_status != "pending"
        else None
    )
    cursor = self._execute(
        """
        UPDATE occurrence_claims AS claim
        SET resolution_status = ?,
            resolution_decision = ?,
            identity_basis = ?,
            review_status = ?,
            resolved_occurrence_id = ?,
            reviewed_at = ?,
            reviewer_id = ?,
            review_reason = ?,
            review_version = review_version + 1,
            review_receipt_digest = ?,
            updated_at = ?
        WHERE claim.id = ?
          AND claim.user_id = ?
          AND claim.review_status = 'candidate'
          AND claim.resolution_status = 'pending'
          AND claim.review_version = ?
          AND claim.predicate_json = ?
          AND claim.aggregation_json = ?
          AND claim.claim_key = ?
          AND claim.count_key = ?
          AND claim.canonical_text = ?
          AND claim.quantity_min = ?
          AND claim.quantity_max IS ?
          AND claim.range_kind = ?
          AND claim.resolution_decision = ?
          AND claim.identity_basis = ?
          AND claim.resolved_occurrence_id IS ?
          AND claim.occurred_at_start IS ?
          AND claim.occurred_at_end IS ?
          AND claim.domain = ?
          AND claim.sensitivity = ?
          AND json(claim.project_scope) = json(?)
          AND (
            ? <> 'resolved'
            OR (
              (
                ? = 'new'
                AND ? IS NULL
                AND claim.range_kind = 'exact'
                AND claim.quantity_max = claim.quantity_min
                AND (
                  SELECT COUNT(*)
                  FROM occurrence_units AS unit
                  WHERE unit.claim_id = claim.id
                    AND unit.user_id = claim.user_id
                ) = claim.quantity_min
                AND (
                  SELECT COUNT(DISTINCT unit.claim_ordinal)
                  FROM occurrence_units AS unit
                  WHERE unit.claim_id = claim.id
                    AND unit.user_id = claim.user_id
                ) = claim.quantity_min
                AND (
                  SELECT MIN(unit.claim_ordinal)
                  FROM occurrence_units AS unit
                  WHERE unit.claim_id = claim.id
                    AND unit.user_id = claim.user_id
                ) = 1
                AND (
                  SELECT MAX(unit.claim_ordinal)
                  FROM occurrence_units AS unit
                  WHERE unit.claim_id = claim.id
                    AND unit.user_id = claim.user_id
                ) = claim.quantity_min
                AND NOT EXISTS (
                  SELECT 1
                  FROM occurrence_units AS unit
                  WHERE unit.claim_id = claim.id
                    AND unit.user_id = claim.user_id
                    AND (
                      unit.review_status <> 'candidate'
                      OR unit.identity_status <> 'resolved'
                      OR unit.unit_value <> 1
                      OR unit.count_key <> claim.count_key
                      OR unit.predicate_json <> claim.predicate_json
                      OR EXISTS (
                        SELECT 1
                        FROM json_each(
                          unit.aggregation_json,
                          '$.members'
                        ) AS member
                        WHERE NOT EXISTS (
                          SELECT 1
                          FROM json_each(
                            claim.aggregation_json,
                            '$.bases'
                          ) AS basis
                          WHERE json_extract(basis.value, '$.basis')
                            = json_extract(member.value, '$.basis')
                            AND json_extract(basis.value, '$.identity_basis')
                              = json_extract(member.value, '$.identity_basis')
                        )
                      )
                      OR unit.domain <> claim.domain
                      OR unit.sensitivity <> claim.sensitivity
                      OR json(unit.project_scope) <> json(claim.project_scope)
                    )
                )
              )
              OR (
                ? = 'link_existing'
                AND ? IS NOT NULL
                AND claim.range_kind = 'exact'
                AND claim.quantity_min = 1
                AND claim.quantity_max = 1
                AND EXISTS (
                  SELECT 1
                  FROM occurrence_units AS unit
                  WHERE unit.id = ?
                    AND unit.user_id = claim.user_id
                    AND unit.review_status = 'accepted'
                    AND unit.identity_status = 'resolved'
                    AND unit.count_key = claim.count_key
                    AND unit.predicate_json = claim.predicate_json
                    AND NOT EXISTS (
                      SELECT 1
                      FROM json_each(
                        unit.aggregation_json,
                        '$.members'
                      ) AS member
                      WHERE NOT EXISTS (
                        SELECT 1
                        FROM json_each(
                          claim.aggregation_json,
                          '$.bases'
                        ) AS basis
                        WHERE json_extract(basis.value, '$.basis')
                          = json_extract(member.value, '$.basis')
                          AND json_extract(basis.value, '$.identity_basis')
                            = json_extract(member.value, '$.identity_basis')
                      )
                    )
                    AND unit.domain = claim.domain
                    AND unit.sensitivity = claim.sensitivity
                    AND json(unit.project_scope) = json(claim.project_scope)
                )
              )
            )
          )
        """,
        (
            resolution_status,
            resolution_decision,
            identity_basis,
            review_status,
            resolved_occurrence_id,
            _utc_now_iso(),
            reviewer_id,
            reason,
            review_receipt,
            _utc_now_iso(),
            str(claim_id),
            self.user_id,
            expected_review_version,
            _canonical_json_text(predicate),
            _canonical_json_text(aggregation),
            current["claim_key"],
            current["count_key"],
            current["canonical_text"],
            current["quantity_min"],
            current.get("quantity_max"),
            current["range_kind"],
            current["resolution_decision"],
            current["identity_basis"],
            current.get("resolved_occurrence_id"),
            current.get("occurred_at_start"),
            current.get("occurred_at_end"),
            current["domain"],
            current["sensitivity"],
            _json_list_text(current["project_scope"]),
            resolution_status,
            resolution_decision,
            resolved_occurrence_id,
            resolution_decision,
            resolved_occurrence_id,
            resolved_occurrence_id,
        ),
    )
    if cursor.rowcount != 1:
        raise ContinuityStoreInvariantError(
            "review_occurrence_claim lost its lifecycle CAS or failed its resolved-unit guard"
        )
    row = self._fetch_one(
        "review_occurrence_claim",
        f"""
        SELECT {_column_sql(OCCURRENCE_CLAIM_COLUMNS)}
        FROM occurrence_claims
        WHERE id = ? AND user_id = ?
        """,
        (str(claim_id), self.user_id),
    )
    self._append_mutation_event(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=reviewer_id,
        target_type="occurrence_claim",
        target_id=row["id"],
        payload={
            "resolution_status": row["resolution_status"],
            "resolution_decision": row["resolution_decision"],
            "identity_basis": row["identity_basis"],
            "resolved_occurrence_id": row["resolved_occurrence_id"],
            "review_version": row["review_version"],
            "review_receipt_digest": row["review_receipt_digest"],
            "reason": reason,
        },
    )
    if not _defer_occurrence_accounting:
        invalidate_occurrence_coverage(
            self,
            reason="An occurrence claim lifecycle decision changed.",
            actor_type=actor_type,
            actor_id=reviewer_id,
        )
    return row


def list_unresolved_occurrence_claims(
    self,
    *,
    count_key: str | None = None,
    projects: Sequence[str] | None = None,
    domains: Sequence[str] | None = None,
    sensitivity_allowed: Sequence[str] | None = None,
    occurred_at_start: datetime | None = None,
    occurred_at_end: datetime | None = None,
    include_timeless: bool = False,
    as_of: datetime | None = None,
    after_id: str | None = None,
    limit: int = 200,
) -> list[VNextRow]:
    if limit < 1:
        raise ValueError("limit must be positive")
    sensitivity = list(sensitivity_allowed or ())
    if not sensitivity:
        return []
    normalized_count_key = normalize_count_key(count_key) if count_key is not None else None
    params: list[object] = [
        self.user_id,
        normalized_count_key,
        normalized_count_key,
    ]
    domains_sql = ""
    if domains:
        domain_values = list(domains)
        domains_sql = f" AND claim.domain IN ({', '.join('?' for _value in domain_values)})"
        params.extend(domain_values)
    sensitivity_sql = f" AND claim.sensitivity IN ({', '.join('?' for _value in sensitivity)})"
    params.extend(sensitivity)
    project_values = list(project_scope_identity(projects or ()))
    projects_sql = ""
    if project_values:
        projects_sql = f"""
          AND EXISTS (
            SELECT 1
            FROM json_each(claim.project_scope) AS scoped_project
            WHERE CAST(scoped_project.value AS TEXT)
              IN ({", ".join("?" for _value in project_values)})
          )
        """
        params.extend(project_values)
    time_clauses: list[str] = []
    if occurred_at_start is not None:
        time_clauses.append("julianday(COALESCE(claim.occurred_at_end, claim.occurred_at_start)) >= julianday(?)")
        params.append(_iso_or_none(occurred_at_start))
    if occurred_at_end is not None:
        time_clauses.append("julianday(COALESCE(claim.occurred_at_start, claim.occurred_at_end)) < julianday(?)")
        params.append(_iso_or_none(occurred_at_end))
    time_sql = ""
    if time_clauses:
        dated_time_sql = " AND ".join(time_clauses)
        if include_timeless:
            time_sql = (
                f" AND ((claim.occurred_at_start IS NULL AND claim.occurred_at_end IS NULL) OR ({dated_time_sql}))"
            )
        else:
            time_sql = f" AND ({dated_time_sql})"
    after_sql = ""
    if after_id is not None:
        after_sql = " AND claim.id > ?"
        params.append(str(after_id))
    params.append(min(limit, 200))
    return self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_CLAIM_COLUMNS, prefix="claim.")}
        FROM occurrence_claims AS claim
        WHERE claim.user_id = ?
          AND (
            (
              claim.resolution_status = 'pending'
              AND claim.review_status = 'candidate'
            )
            OR (
              claim.resolution_status = 'resolved'
              AND claim.review_status = 'accepted'
              AND claim.resolution_decision = 'new'
              AND EXISTS (
                SELECT 1
                FROM occurrence_units AS materialized
                WHERE materialized.user_id = claim.user_id
                  AND materialized.claim_id = claim.id
                  AND materialized.review_status IN ('candidate', 'accepted')
              )
              AND EXISTS (
                SELECT 1
                FROM occurrence_units AS materialized
                WHERE materialized.user_id = claim.user_id
                  AND materialized.claim_id = claim.id
                  AND materialized.review_status IN ('candidate', 'accepted')
                  AND (
                    materialized.review_status <> 'accepted'
                    OR materialized.identity_status <> 'resolved'
                    OR materialized.unit_value <> 1
                    OR materialized.predicate_json <> claim.predicate_json
                    OR EXISTS (
                      SELECT 1
                      FROM json_each(
                        materialized.aggregation_json,
                        '$.members'
                      ) AS member
                      WHERE NOT EXISTS (
                        SELECT 1
                        FROM json_each(
                          claim.aggregation_json,
                          '$.bases'
                        ) AS basis
                        WHERE json_extract(basis.value, '$.basis')
                          = json_extract(member.value, '$.basis')
                          AND json_extract(basis.value, '$.identity_basis')
                            = json_extract(member.value, '$.identity_basis')
                      )
                    )
                    OR materialized.domain <> claim.domain
                    OR materialized.sensitivity <> claim.sensitivity
                    OR json(materialized.project_scope)
                      <> json(claim.project_scope)
                  )
              )
            )
            OR (
              claim.resolution_status = 'resolved'
              AND claim.review_status = 'accepted'
              AND claim.resolution_decision = 'link_existing'
              AND EXISTS (
                SELECT 1
                FROM occurrence_units AS linked
                WHERE linked.user_id = claim.user_id
                  AND linked.id = claim.resolved_occurrence_id
                  AND linked.review_status IN ('candidate', 'accepted')
              )
              AND NOT EXISTS (
                SELECT 1
                FROM occurrence_units AS linked
                WHERE linked.user_id = claim.user_id
                  AND linked.id = claim.resolved_occurrence_id
                  AND linked.review_status = 'accepted'
                  AND linked.identity_status = 'resolved'
                  AND linked.unit_value = 1
                  AND linked.predicate_json = claim.predicate_json
                  AND NOT EXISTS (
                    SELECT 1
                    FROM json_each(
                      linked.aggregation_json,
                      '$.members'
                    ) AS member
                    WHERE NOT EXISTS (
                      SELECT 1
                      FROM json_each(
                        claim.aggregation_json,
                        '$.bases'
                      ) AS basis
                      WHERE json_extract(basis.value, '$.basis')
                        = json_extract(member.value, '$.basis')
                        AND json_extract(basis.value, '$.identity_basis')
                          = json_extract(member.value, '$.identity_basis')
                    )
                  )
                  AND linked.domain = claim.domain
                  AND linked.sensitivity = claim.sensitivity
                  AND json(linked.project_scope) = json(claim.project_scope)
              )
            )
          )
          AND (? IS NULL OR claim.count_key = ?)
          {domains_sql}
          {sensitivity_sql}
          {projects_sql}
          {time_sql}
          {after_sql}
        ORDER BY claim.id ASC
        LIMIT ?
        """,
        tuple(params),
    )


def get_or_create_occurrence_unit(
    self,
    unit: JsonObject,
    *,
    actor_type: str = "system",
) -> tuple[VNextRow, bool]:
    _lock_occurrence_graph_mutation(self)
    project_scope = _project_scope(unit.get("project_scope"))
    occurred_at_start = _normalized_occurrence_timestamp(
        unit.get("occurred_at_start"),
        field="occurred_at_start",
    )
    occurred_at_end = _normalized_occurrence_timestamp(
        unit.get("occurred_at_end"),
        field="occurred_at_end",
    )
    if (
        occurred_at_start is not None
        and occurred_at_end is not None
        and _occurrence_timestamp_moment(occurred_at_end) < _occurrence_timestamp_moment(occurred_at_start)
    ):
        raise ValueError("occurred_at_end must not precede occurred_at_start")
    predicate = canonicalize_occurrence_predicate(
        unit.get("predicate_json"),
        allow_claim_ops=False,
    )
    occurrence_key = str(unit["occurrence_key"])
    claim_id = str(unit["claim_id"])
    claim_current = _lock_occurrence_claim_rows(self, [claim_id])[claim_id]
    claim_aggregation = canonicalize_occurrence_claim_aggregation(claim_current.get("aggregation_json"))
    aggregation = canonicalize_occurrence_unit_aggregation(
        unit.get("aggregation_json"),
        occurrence_key=occurrence_key,
        claim_aggregation=claim_aggregation,
    )
    count_key = _canonical_count_key_input(unit["count_key"])
    if count_key != claim_current.get("count_key"):
        raise ContinuityStoreInvariantError("occurrence unit count_key must match its owning claim")
    expected = {
        "claim_id": claim_id,
        "claim_ordinal": int(cast(int, unit.get("claim_ordinal", 1))),
        "occurrence_key": occurrence_key,
        "count_key": count_key,
        "predicate_json": predicate,
        "canonical_text": str(unit["canonical_text"]),
        "aggregation_json": aggregation,
        "unit_value": 1,
        "identity_status": str(unit.get("identity_status") or "ambiguous"),
        "ambiguity_group_key": unit.get("ambiguity_group_key"),
        "occurred_at_start": occurred_at_start,
        "occurred_at_end": occurred_at_end,
        "domain": str(unit.get("domain") or "unknown"),
        "sensitivity": str(unit.get("sensitivity") or "unknown"),
        "project_scope": project_scope,
    }
    if (
        claim_current.get("review_status") != "candidate"
        or claim_current.get("resolution_status") != "pending"
    ):
        if (
            claim_current.get("review_status") != "accepted"
            or claim_current.get("resolution_status") != "resolved"
        ):
            raise ContinuityStoreInvariantError(
                "get_or_create_occurrence_unit requires a candidate pending owning claim"
            )
        winner = self._fetch_optional_one(
            f"""
            SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS)}
            FROM occurrence_units
            WHERE user_id = ?
              AND occurrence_key = ?
            """,
            (self.user_id, occurrence_key),
        )
        if winner is None:
            raise ContinuityStoreInvariantError(
                "accepted occurrence claim may only replay an existing unit"
            )
        _assert_immutable_winner("occurrence unit", winner, expected)
        return winner, False
    cursor = self._execute(
        f"""
        INSERT OR IGNORE INTO occurrence_units (
          id,
          user_id,
          claim_id,
          claim_ordinal,
          occurrence_key,
          count_key,
          predicate_json,
          canonical_text,
          aggregation_json,
          unit_value,
          review_status,
          identity_status,
          ambiguity_group_key,
          occurred_at_start,
          occurred_at_end,
          domain,
          sensitivity,
          project_scope,
          metadata_json,
          created_at,
          updated_at
        )
        SELECT
          ?, claim.user_id, claim.id, ?, ?, ?, ?, ?, ?, 1, 'candidate',
          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        FROM occurrence_claims AS claim
        WHERE claim.id = ?
          AND claim.user_id = ?
          AND claim.review_status = 'candidate'
          AND claim.resolution_status = 'pending'
          AND claim.count_key = ?
          AND claim.predicate_json = ?
          AND claim.aggregation_json = ?
          AND claim.domain = ?
          AND claim.sensitivity = ?
          AND json(claim.project_scope) = json(?)
        RETURNING {_column_sql(OCCURRENCE_UNIT_COLUMNS)}
        """,
        (
            _new_id(unit.get("id")),
            expected["claim_ordinal"],
            expected["occurrence_key"],
            count_key,
            _canonical_json_text(predicate),
            expected["canonical_text"],
            _canonical_json_text(aggregation),
            expected["identity_status"],
            expected["ambiguity_group_key"],
            expected["occurred_at_start"],
            expected["occurred_at_end"],
            expected["domain"],
            expected["sensitivity"],
            _json_list_text(project_scope),
            _json_object_text(unit.get("metadata_json")),
            _utc_now_iso(),
            _utc_now_iso(),
            expected["claim_id"],
            self.user_id,
            count_key,
            _canonical_json_text(predicate),
            _canonical_json_text(claim_aggregation),
            expected["domain"],
            expected["sensitivity"],
            _json_list_text(project_scope),
        ),
    )
    raw_row = cursor.fetchone()
    created = raw_row is not None
    row = (
        _decode_cursor_row(self, cursor, raw_row)
        if raw_row is not None
        else self._fetch_one(
            "get_or_create_occurrence_unit",
            f"""
            SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS)}
            FROM occurrence_units
            WHERE user_id = ?
              AND occurrence_key = ?
            """,
            (self.user_id, expected["occurrence_key"]),
        )
    )
    _assert_immutable_winner("occurrence unit", row, expected)
    if created:
        self._append_mutation_event(
            event_type="occurrence.unit_created",
            actor_type=actor_type,
            target_type="occurrence_unit",
            target_id=row["id"],
            payload={
                "claim_id": row["claim_id"],
                "claim_ordinal": row["claim_ordinal"],
                "occurrence_key": row["occurrence_key"],
                "count_key": row["count_key"],
                "predicate_json": row["predicate_json"],
                "predicate_digest": occurrence_predicate_digest(
                    row["predicate_json"],
                    allow_claim_ops=False,
                ),
                "aggregation_json": row["aggregation_json"],
                "aggregation_digest": occurrence_aggregation_digest(
                    row["aggregation_json"],
                    occurrence_key=str(row["occurrence_key"]),
                ),
                "identity_status": row["identity_status"],
            },
        )
        invalidate_occurrence_coverage(
            self,
            reason="An occurrence unit was added to the reviewed graph.",
            actor_type=actor_type,
        )
    return row, created


def get_occurrence_unit_by_key(self, occurrence_key: str) -> VNextRow | None:
    """Return the same-user dedupe winner without a bounded search scan."""

    return self._fetch_optional_one(
        f"""
        SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS, prefix="unit.")}
        FROM occurrence_units AS unit
        WHERE unit.user_id = ?
          AND unit.occurrence_key = ?
          AND ({_OCCURRENCE_OWNER_COUNT_KEY_SQL})
        """,
        (self.user_id, str(occurrence_key)),
    )


def create_occurrence_evidence(
    self,
    evidence: JsonObject,
    *,
    actor_type: str = "system",
    _source_reestablishment_snapshot_sha256: str | None = None,
) -> VNextRow:
    """Idempotently attach provenance when every live reference is compatible."""

    _lock_occurrence_graph_mutation(self)
    quote = evidence.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        raise ContinuityStoreInvariantError("occurrence evidence requires a nonempty quote")
    computed_quote_sha256 = hashlib.sha256(quote.encode("utf-8")).hexdigest()
    supplied_quote_sha256 = evidence.get("quote_sha256")
    if supplied_quote_sha256 is not None and str(supplied_quote_sha256) != computed_quote_sha256:
        raise ValueError("quote_sha256 does not match quote")
    quote_sha256 = str(supplied_quote_sha256 or computed_quote_sha256)
    source_id = (str(evidence["source_id"]).strip() or None) if evidence.get("source_id") is not None else None
    source_chunk_id = (
        (str(evidence["source_chunk_id"]).strip() or None) if evidence.get("source_chunk_id") is not None else None
    )
    memory_id = (str(evidence["memory_id"]).strip() or None) if evidence.get("memory_id") is not None else None
    if source_chunk_id and not source_id:
        raise ContinuityStoreInvariantError("occurrence evidence source_chunk_id requires source_id")
    if not memory_id and not source_id:
        raise ContinuityStoreInvariantError(
            "occurrence evidence requires a memory_id or source_id authorization carrier"
        )
    metadata = evidence.get("metadata_json")
    expected = {
        "claim_id": str(evidence["claim_id"]),
        "occurrence_id": (str(evidence["occurrence_id"]) if evidence.get("occurrence_id") is not None else None),
        "source_id": source_id,
        "source_chunk_id": source_chunk_id,
        "memory_id": memory_id,
        "evidence_key": str(evidence["evidence_key"]),
        "evidence_role": str(evidence.get("evidence_role", "supports")),
        "quote": quote,
        "quote_sha256": quote_sha256,
        "confidence": float(cast(float, evidence.get("confidence", 0.5))),
        "metadata_json": (dict(metadata) if isinstance(metadata, Mapping) else {}),
    }
    if source_id is not None:
        self.lock_source_occurrence_envelope(source_id)
    if memory_id is not None:
        _lock_occurrence_memory_carrier(self, memory_id)
    claims = _lock_occurrence_claim_rows(
        self,
        [str(expected["claim_id"])],
    )
    claim = claims[str(expected["claim_id"])]
    if claim.get("review_status") not in {"candidate", "accepted"}:
        raise ContinuityStoreInvariantError(
            "occurrence evidence requires a live candidate or accepted claim"
        )
    if expected["occurrence_id"] is not None:
        units = _lock_occurrence_unit_rows(
            self,
            [str(expected["occurrence_id"])],
        )
        unit = units[str(expected["occurrence_id"])]
        if unit.get("review_status") not in {"candidate", "accepted"} and not (
            _allows_retired_source_reestablishment_evidence(
                self,
                expected=expected,
                unit=unit,
                snapshot_sha256=_source_reestablishment_snapshot_sha256,
            )
        ):
            raise ContinuityStoreInvariantError(
                "occurrence evidence requires a candidate or accepted unit"
            )
    cursor = self._execute(
        f"""
        INSERT OR IGNORE INTO occurrence_evidence (
          id,
          user_id,
          claim_id,
          occurrence_id,
          source_id,
          source_chunk_id,
          memory_id,
          evidence_key,
          evidence_role,
          quote,
          quote_sha256,
          confidence,
          review_status,
          metadata_json,
          created_at
        )
        SELECT
          ?, claim.user_id, claim.id, ?, ?, ?, ?, ?, ?, ?, ?,
          ?, 'candidate', ?, ?
        FROM occurrence_claims AS claim
        WHERE claim.id = ?
          AND claim.user_id = ?
          AND (
            ? IS NULL
            OR EXISTS (
              SELECT 1
              FROM occurrence_units AS unit
              WHERE unit.id = ?
                AND unit.user_id = claim.user_id
                AND unit.count_key = claim.count_key
                AND unit.predicate_json = claim.predicate_json
                AND NOT EXISTS (
                  SELECT 1
                  FROM json_each(
                    unit.aggregation_json,
                    '$.members'
                  ) AS member
                  WHERE NOT EXISTS (
                    SELECT 1
                    FROM json_each(
                      claim.aggregation_json,
                      '$.bases'
                    ) AS basis
                    WHERE json_extract(basis.value, '$.basis')
                      = json_extract(member.value, '$.basis')
                      AND json_extract(basis.value, '$.identity_basis')
                        = json_extract(member.value, '$.identity_basis')
                  )
                )
                AND unit.domain = claim.domain
                AND unit.sensitivity = claim.sensitivity
                AND json(unit.project_scope) = json(claim.project_scope)
            )
          )
          AND (
            ? IS NULL
            OR EXISTS (
              SELECT 1 FROM sources AS source
              WHERE source.id = ?
                AND source.user_id = claim.user_id
                AND source.deleted_at IS NULL
                AND source.domain = claim.domain
                AND source.sensitivity = claim.sensitivity
                AND json(
                  alice_source_project_scope_identity(source.metadata_json)
                ) = json(claim.project_scope)
            )
          )
          AND (
            ? IS NULL
            OR EXISTS (
              SELECT 1
              FROM source_chunks AS chunk
              JOIN sources AS source
                ON source.id = chunk.source_id
               AND source.user_id = chunk.user_id
              WHERE chunk.id = ?
                AND chunk.user_id = claim.user_id
                AND (? IS NULL OR chunk.source_id = ?)
                AND source.deleted_at IS NULL
                AND source.domain = claim.domain
                AND source.sensitivity = claim.sensitivity
                AND json(
                  alice_source_project_scope_identity(source.metadata_json)
                ) = json(claim.project_scope)
            )
          )
          AND (
            ? IS NULL
            OR EXISTS (
              SELECT 1 FROM memories AS memory
              WHERE memory.id = ?
                AND memory.user_id = claim.user_id
                AND memory.deleted_at IS NULL
                AND memory.status IN (
                  'candidate',
                  'active',
                  'accepted',
                  'needs_review',
                  'private_only'
                )
                AND (
                  memory.valid_to IS NULL
                  OR julianday(memory.valid_to) >= julianday('now')
                )
                AND memory.domain = claim.domain
                AND memory.sensitivity = claim.sensitivity
                AND json(
                  alice_project_scope_identity(
                    memory.metadata_json,
                    memory.project_id
                  )
                ) = json(claim.project_scope)
            )
          )
        RETURNING {_column_sql(OCCURRENCE_EVIDENCE_COLUMNS)}
        """,
        (
            _new_id(evidence.get("id")),
            expected["occurrence_id"],
            expected["source_id"],
            expected["source_chunk_id"],
            expected["memory_id"],
            expected["evidence_key"],
            expected["evidence_role"],
            expected["quote"],
            expected["quote_sha256"],
            expected["confidence"],
            _json_object_text(expected["metadata_json"]),
            _utc_now_iso(),
            expected["claim_id"],
            self.user_id,
            expected["occurrence_id"],
            expected["occurrence_id"],
            expected["source_id"],
            expected["source_id"],
            expected["source_chunk_id"],
            expected["source_chunk_id"],
            expected["source_id"],
            expected["source_id"],
            expected["memory_id"],
            expected["memory_id"],
        ),
    )
    raw_row = cursor.fetchone()
    created = raw_row is not None
    row = (
        _decode_cursor_row(self, cursor, raw_row)
        if raw_row is not None
        else self._fetch_optional_one(
            f"""
            SELECT {_column_sql(OCCURRENCE_EVIDENCE_COLUMNS, prefix="evidence.")}
            FROM occurrence_evidence AS evidence
            JOIN occurrence_claims AS claim
              ON claim.id = evidence.claim_id
             AND claim.user_id = evidence.user_id
            WHERE evidence.user_id = ?
              AND evidence.evidence_key = ?
              AND (
                evidence.occurrence_id IS NULL
                OR EXISTS (
                  SELECT 1 FROM occurrence_units AS unit
                  WHERE unit.id = evidence.occurrence_id
                    AND unit.user_id = claim.user_id
                    AND unit.count_key = claim.count_key
                    AND unit.predicate_json = claim.predicate_json
                    AND NOT EXISTS (
                      SELECT 1
                      FROM json_each(
                        unit.aggregation_json,
                        '$.members'
                      ) AS member
                      WHERE NOT EXISTS (
                        SELECT 1
                        FROM json_each(
                          claim.aggregation_json,
                          '$.bases'
                        ) AS basis
                        WHERE json_extract(basis.value, '$.basis')
                          = json_extract(member.value, '$.basis')
                          AND json_extract(basis.value, '$.identity_basis')
                            = json_extract(member.value, '$.identity_basis')
                      )
                    )
                    AND unit.domain = claim.domain
                    AND unit.sensitivity = claim.sensitivity
                    AND json(unit.project_scope) = json(claim.project_scope)
                )
              )
              AND (
                evidence.source_id IS NULL
                OR EXISTS (
                  SELECT 1 FROM sources AS source
                  WHERE source.id = evidence.source_id
                    AND source.user_id = claim.user_id
                    AND source.deleted_at IS NULL
                    AND source.domain = claim.domain
                    AND source.sensitivity = claim.sensitivity
                    AND json(
                      alice_source_project_scope_identity(source.metadata_json)
                    ) = json(claim.project_scope)
                )
              )
              AND (
                evidence.source_chunk_id IS NULL
                OR EXISTS (
                  SELECT 1
                  FROM source_chunks AS chunk
                  JOIN sources AS source
                    ON source.id = chunk.source_id
                   AND source.user_id = chunk.user_id
                  WHERE chunk.id = evidence.source_chunk_id
                    AND chunk.user_id = claim.user_id
                    AND (
                      evidence.source_id IS NULL
                      OR chunk.source_id = evidence.source_id
                    )
                    AND source.deleted_at IS NULL
                    AND source.domain = claim.domain
                    AND source.sensitivity = claim.sensitivity
                    AND json(
                      alice_source_project_scope_identity(source.metadata_json)
                    ) = json(claim.project_scope)
                )
              )
              AND (
                evidence.memory_id IS NULL
                OR EXISTS (
                  SELECT 1 FROM memories AS memory
                  WHERE memory.id = evidence.memory_id
                    AND memory.user_id = claim.user_id
                    AND memory.deleted_at IS NULL
                    AND memory.status IN (
                      'candidate',
                      'active',
                      'accepted',
                      'needs_review',
                      'private_only'
                    )
                    AND (
                      memory.valid_to IS NULL
                      OR julianday(memory.valid_to) >= julianday('now')
                    )
                    AND memory.domain = claim.domain
                    AND memory.sensitivity = claim.sensitivity
                    AND json(
                      alice_project_scope_identity(
                        memory.metadata_json,
                        memory.project_id
                      )
                    ) = json(claim.project_scope)
                )
              )
            """,
            (self.user_id, expected["evidence_key"]),
        )
    )
    if row is None:
        raise ContinuityStoreInvariantError(
            "create_occurrence_evidence rejected an unowned, deleted, or mismatched reference"
        )
    _assert_immutable_winner("occurrence evidence", row, expected)
    if not created:
        return row
    self._append_mutation_event(
        event_type="occurrence.evidence_attached",
        actor_type=actor_type,
        target_type=("occurrence_unit" if row["occurrence_id"] is not None else "occurrence_claim"),
        target_id=row["occurrence_id"] or row["claim_id"],
        payload={
            "evidence_id": row["id"],
            "claim_id": row["claim_id"],
            "occurrence_id": row["occurrence_id"],
            "evidence_key": row["evidence_key"],
            "evidence_role": row["evidence_role"],
        },
    )
    if row["source_chunk_id"] is not None:
        from alicebot_api.vnext_stores.sqlite.occurrence_accounting import (
            invalidate_occurrence_extraction_dispositions,
        )

        invalidate_occurrence_extraction_dispositions(
            self,
            source_chunk_id=str(row["source_chunk_id"]),
            reason="Occurrence evidence changed current chunk accounting.",
            actor_type=actor_type,
        )
    else:
        invalidate_occurrence_coverage(
            self,
            reason="Occurrence evidence was added to the reviewed graph.",
            actor_type=actor_type,
        )
    return row


def _eligible_supporting_evidence(self, occurrence_id: str) -> list[VNextRow]:
    rows = self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_EVIDENCE_COLUMNS, prefix="evidence.")}
        FROM occurrence_evidence AS evidence
        JOIN occurrence_units AS evidence_unit
          ON evidence_unit.id = evidence.occurrence_id
         AND evidence_unit.user_id = evidence.user_id
        WHERE evidence.user_id = ?
          AND evidence.occurrence_id = ?
          AND evidence.evidence_role = 'supports'
          AND evidence.review_status IN ('candidate', 'accepted')
          AND evidence.quote IS NOT NULL
          AND length(
            trim(evidence.quote, {_PYTHON_312_STRIP_CHARS_SQL})
          ) > 0
          AND (
            evidence.memory_id IS NOT NULL
            OR evidence.source_id IS NOT NULL
          )
          AND (
            evidence.source_chunk_id IS NULL
            OR evidence.source_id IS NOT NULL
          )
          AND EXISTS (
            SELECT 1
            FROM occurrence_claims AS evidence_claim
            WHERE evidence_claim.id = evidence.claim_id
              AND evidence_claim.user_id = evidence.user_id
              AND evidence_claim.count_key = evidence_unit.count_key
              AND evidence_claim.predicate_json = evidence_unit.predicate_json
              AND NOT EXISTS (
                SELECT 1
                FROM json_each(
                  evidence_unit.aggregation_json,
                  '$.members'
                ) AS member
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM json_each(
                    evidence_claim.aggregation_json,
                    '$.bases'
                  ) AS basis
                  WHERE json_extract(basis.value, '$.basis')
                    = json_extract(member.value, '$.basis')
                    AND json_extract(basis.value, '$.identity_basis')
                      = json_extract(member.value, '$.identity_basis')
                )
              )
              AND evidence_claim.domain = evidence_unit.domain
              AND evidence_claim.sensitivity = evidence_unit.sensitivity
              AND json(evidence_claim.project_scope)
                = json(evidence_unit.project_scope)
              AND (
                evidence_claim.id = evidence_unit.claim_id
                OR (
                  evidence_claim.resolution_decision = 'link_existing'
                  AND evidence_claim.resolution_status = 'resolved'
                  AND evidence_claim.review_status = 'accepted'
                  AND evidence_claim.resolved_occurrence_id = evidence_unit.id
                )
              )
          )
          AND (
            evidence.source_id IS NULL
            OR EXISTS (
              SELECT 1 FROM sources AS source
              WHERE source.id = evidence.source_id
                AND source.user_id = evidence.user_id
                AND source.deleted_at IS NULL
                AND source.domain = evidence_unit.domain
                AND source.sensitivity = evidence_unit.sensitivity
                AND json(
                  alice_source_project_scope_identity(source.metadata_json)
                ) = json(evidence_unit.project_scope)
            )
          )
          AND (
            evidence.source_chunk_id IS NULL
            OR EXISTS (
              SELECT 1
              FROM source_chunks AS chunk
              JOIN sources AS source
                ON source.id = chunk.source_id
               AND source.user_id = chunk.user_id
              WHERE chunk.id = evidence.source_chunk_id
                AND chunk.user_id = evidence.user_id
                AND chunk.source_id = evidence.source_id
                AND source.deleted_at IS NULL
                AND source.domain = evidence_unit.domain
                AND source.sensitivity = evidence_unit.sensitivity
                AND json(
                  alice_source_project_scope_identity(source.metadata_json)
                ) = json(evidence_unit.project_scope)
            )
          )
          AND (
            evidence.memory_id IS NULL
            OR EXISTS (
              SELECT 1 FROM memories AS memory
                WHERE memory.id = evidence.memory_id
                  AND memory.user_id = evidence.user_id
                  AND memory.deleted_at IS NULL
                  AND memory.status IN ('active', 'accepted')
                  AND (
                    memory.valid_to IS NULL
                    OR julianday(memory.valid_to) >= julianday('now')
                  )
                  AND memory.domain = evidence_unit.domain
                  AND memory.sensitivity = evidence_unit.sensitivity
                  AND json(
                    alice_project_scope_identity(
                      memory.metadata_json,
                      memory.project_id
                    )
                  ) = json(evidence_unit.project_scope)
              )
            )
        ORDER BY evidence.evidence_key ASC, evidence.id ASC
        """,
        (self.user_id, str(occurrence_id)),
    )
    return [
        row
        for row in rows
        if isinstance(row.get("quote"), str)
        and bool(str(row["quote"]).strip())
        and hashlib.sha256(str(row["quote"]).encode("utf-8")).hexdigest() == row.get("quote_sha256")
    ]


def _review_occurrence_unit_locked(
    self,
    *,
    occurrence_id: str,
    action: str,
    reason: str,
    reviewer_id: str,
    expected_status: str = "candidate",
    expected_review_version: int = 0,
    superseded_by: str | None = None,
    actor_type: str = "user",
    _source_reestablishment_snapshot_sha256: str | None = None,
    _defer_occurrence_accounting: bool = False,
) -> VNextRow:
    """Apply one guarded lifecycle decision and sign its evidence snapshot."""

    if action not in {
        "accepted",
        "rejected",
        "ambiguous",
        "superseded",
        "retired",
        "refresh_evidence",
        "reestablished",
    }:
        raise ValueError("invalid occurrence review action")
    if action == "accepted" and expected_status != "candidate":
        raise ValueError("accepted occurrence review must start from candidate")
    if action in {"superseded", "retired"} and expected_status != "accepted":
        raise ValueError("occurrence retirement/supersession must start from accepted")
    if action == "refresh_evidence" and expected_status != "accepted":
        raise ValueError("occurrence evidence refresh must start from accepted")
    if action == "reestablished":
        if (
            expected_status != "retired"
            or _source_reestablishment_snapshot_sha256 is None
            or len(_source_reestablishment_snapshot_sha256) != 64
            or any(character not in "0123456789abcdef" for character in _source_reestablishment_snapshot_sha256)
        ):
            raise ValueError("source occurrence re-establishment requires a current snapshot proof")
    elif _source_reestablishment_snapshot_sha256 is not None:
        raise ValueError("source occurrence snapshot proof is valid only for re-establishment")
    normalized_superseded_by: str | None = None
    if action == "superseded":
        if superseded_by is None:
            raise ValueError("superseded occurrence review requires superseded_by")
        try:
            normalized_superseded_by = str(UUID(str(superseded_by)))
        except (TypeError, ValueError) as exc:
            raise ValueError("superseded occurrence review requires a UUID superseded_by") from exc
        if normalized_superseded_by == str(occurrence_id):
            raise ValueError("superseded occurrence review requires a different successor")

    unit_ids = [str(occurrence_id)]
    if normalized_superseded_by is not None:
        unit_ids.append(normalized_superseded_by)
    placeholders = ", ".join("?" for _value in sorted(set(unit_ids)))
    prelock_units = self._fetch_all(
        f"""
        SELECT id, claim_id
        FROM occurrence_units
        WHERE user_id = ?
          AND id IN ({placeholders})
        ORDER BY id ASC
        """,
        (self.user_id, *sorted(set(unit_ids))),
    )
    if {str(row["id"]) for row in prelock_units} != set(unit_ids):
        raise ContinuityStoreInvariantError(
            "review_occurrence_unit requires current owned unit references"
        )
    _lock_occurrence_claim_rows(
        self,
        [str(row["claim_id"]) for row in prelock_units],
    )
    locked_units = _lock_occurrence_unit_rows(self, unit_ids)
    current = locked_units[str(occurrence_id)]
    if normalized_superseded_by is not None:
        successor = locked_units[normalized_superseded_by]
        if (
            successor.get("review_status") != "accepted"
            or successor.get("identity_status") != "resolved"
        ):
            raise ContinuityStoreInvariantError(
                "superseded occurrence review requires an accepted resolved successor"
            )
    if (
        current.get("review_status") != expected_status
        or current.get("review_version") != expected_review_version
    ):
        raise ContinuityStoreInvariantError("review_occurrence_unit lost its lifecycle CAS")
    predicate = canonicalize_occurrence_predicate(
        current.get("predicate_json"),
        allow_claim_ops=False,
    )
    aggregation = canonicalize_occurrence_unit_aggregation(
        current.get("aggregation_json"),
        occurrence_key=str(current["occurrence_key"]),
    )
    supporting = _eligible_supporting_evidence(self, str(occurrence_id))
    if action in {"accepted", "refresh_evidence", "reestablished"} and not supporting:
        raise ContinuityStoreInvariantError("review_occurrence_unit requires eligible supporting evidence")
    if action == "reestablished":
        snapshot_current = False
        for evidence in supporting:
            metadata = evidence.get("metadata_json")
            source_id = str(evidence.get("source_id") or "")
            source_chunk_id = str(evidence.get("source_chunk_id") or "")
            if (
                evidence.get("review_status") != "candidate"
                or evidence.get("memory_id") is not None
                or not source_id
                or not source_chunk_id
                or str(evidence.get("claim_id") or "") != str(current["claim_id"])
                or not isinstance(metadata, Mapping)
                or metadata.get("source_snapshot_sha256") != _source_reestablishment_snapshot_sha256
                or metadata.get("source_reestablishment_stage") != "http_source_review_envelope_change"
            ):
                continue
            snapshot_row = self._fetch_optional_one(
                """
                SELECT
                  source.id AS source_id,
                  source.content_hash AS source_content_hash,
                  source.domain AS source_domain,
                  source.sensitivity AS source_sensitivity,
                  source.title AS source_title,
                  source.source_created_at,
                  json_extract(source.metadata_json, '$.session_date')
                    AS source_session_date,
                  json_extract(source.metadata_json, '$.provenance_role')
                    AS source_provenance_role,
                  alice_source_project_scope_identity(source.metadata_json)
                    AS source_project_scope,
                  chunk.id AS source_chunk_id,
                  chunk.chunk_index,
                  chunk.text AS chunk_text,
                  chunk.created_at AS chunk_created_at
                FROM source_chunks AS chunk
                JOIN sources AS source
                  ON source.id = chunk.source_id
                 AND source.user_id = chunk.user_id
                WHERE chunk.user_id = ?
                  AND chunk.id = ?
                  AND chunk.source_id = ?
                  AND source.deleted_at IS NULL
                  AND source.domain = ?
                  AND source.sensitivity = ?
                  AND json(
                    alice_source_project_scope_identity(source.metadata_json)
                  ) = json(?)
                """,
                (
                    self.user_id,
                    source_chunk_id,
                    source_id,
                    current["domain"],
                    current["sensitivity"],
                    _json_list_text(current["project_scope"]),
                ),
            )
            if (
                snapshot_row is not None
                and _extraction_snapshot_sha256(snapshot_row) == _source_reestablishment_snapshot_sha256
            ):
                snapshot_current = True
                break
        if not snapshot_current:
            raise ContinuityStoreInvariantError(
                "source occurrence re-establishment requires fresh current-snapshot evidence"
            )
    evidence_digest = _evidence_digest(supporting)
    next_version = expected_review_version + 1
    receipt_unit = {
        **current,
        "superseded_by": normalized_superseded_by,
    }
    review_receipt = occurrence_unit_review_receipt_digest(
        receipt_unit,
        action=action,
        reviewer_id=reviewer_id,
        reason=reason,
        review_version=next_version,
        evidence_digest=evidence_digest,
    )
    next_status = (
        "candidate"
        if action == "ambiguous"
        else "accepted"
        if action in {"refresh_evidence", "reestablished"}
        else action
    )
    next_identity_status = "ambiguous" if action == "ambiguous" else None
    reviewed_at = _utc_now_iso()
    cursor = self._execute(
        f"""
        UPDATE occurrence_units AS unit
        SET review_status = ?,
            identity_status = COALESCE(?, unit.identity_status),
            reviewed_at = ?,
            reviewer_id = ?,
            review_reason = ?,
            review_version = review_version + 1,
            reviewed_evidence_count = ?,
            reviewed_evidence_digest = ?,
            review_receipt_digest = ?,
            review_receipt_action = ?,
            superseded_by = CASE WHEN ? = 'superseded' THEN ? ELSE NULL END,
            retired_at = CASE
              WHEN ? = 'retired' THEN ?
              WHEN ? = 'reestablished' THEN NULL
              ELSE unit.retired_at
            END,
            retired_by = CASE
              WHEN ? = 'retired' THEN ?
              WHEN ? = 'reestablished' THEN NULL
              ELSE unit.retired_by
            END,
            retirement_reason = CASE
              WHEN ? = 'retired' THEN ?
              WHEN ? = 'reestablished' THEN NULL
              ELSE unit.retirement_reason
            END,
            updated_at = ?
        WHERE unit.id = ?
          AND unit.user_id = ?
          AND unit.review_status = ?
          AND unit.review_version = ?
          AND unit.predicate_json = ?
          AND unit.aggregation_json = ?
          AND unit.claim_id = ?
          AND unit.claim_ordinal = ?
          AND unit.occurrence_key = ?
          AND unit.count_key = ?
          AND unit.canonical_text = ?
          AND unit.unit_value = ?
          AND unit.identity_status = ?
          AND unit.ambiguity_group_key IS ?
          AND unit.occurred_at_start IS ?
          AND unit.occurred_at_end IS ?
          AND unit.domain = ?
          AND unit.sensitivity = ?
          AND json(unit.project_scope) = json(?)
          AND (
            ? NOT IN ('accepted', 'refresh_evidence', 'reestablished')
            OR unit.identity_status = 'resolved'
          )
          AND (
            ? NOT IN ('accepted', 'refresh_evidence', 'reestablished')
            OR EXISTS (
              SELECT 1 FROM occurrence_claims AS claim
              WHERE claim.user_id = unit.user_id
                AND claim.resolution_status = 'resolved'
                AND claim.review_status = 'accepted'
                AND claim.count_key = unit.count_key
                AND claim.predicate_json = unit.predicate_json
                AND NOT EXISTS (
                  SELECT 1
                  FROM json_each(
                    unit.aggregation_json,
                    '$.members'
                  ) AS member
                  WHERE NOT EXISTS (
                    SELECT 1
                    FROM json_each(
                      claim.aggregation_json,
                      '$.bases'
                    ) AS basis
                    WHERE json_extract(basis.value, '$.basis')
                      = json_extract(member.value, '$.basis')
                      AND json_extract(basis.value, '$.identity_basis')
                        = json_extract(member.value, '$.identity_basis')
                  )
                )
                AND claim.domain = unit.domain
                AND claim.sensitivity = unit.sensitivity
                AND json(claim.project_scope) = json(unit.project_scope)
                AND (
                  (
                    claim.resolution_decision = 'new'
                    AND claim.id = unit.claim_id
                    AND claim.resolved_occurrence_id IS NULL
                  )
                  OR (
                    claim.resolution_decision = 'link_existing'
                    AND claim.resolved_occurrence_id = unit.id
                  )
                )
            )
          )
          AND (
            ? <> 'superseded'
            OR EXISTS (
              SELECT 1 FROM occurrence_units AS successor
              WHERE successor.id = ?
                AND successor.user_id = unit.user_id
                AND successor.review_status = 'accepted'
                AND successor.identity_status = 'resolved'
                AND successor.count_key = unit.count_key
                AND successor.predicate_json = unit.predicate_json
                AND ({_OCCURRENCE_SUCCESSOR_AGGREGATION_COMPATIBLE_SQL})
                AND successor.domain = unit.domain
                AND successor.sensitivity = unit.sensitivity
                AND json(successor.project_scope) = json(unit.project_scope)
            )
          )
        """,
        (
            next_status,
            next_identity_status,
            reviewed_at,
            reviewer_id,
            reason,
            len(supporting),
            evidence_digest,
            review_receipt,
            action,
            action,
            normalized_superseded_by,
            action,
            reviewed_at,
            action,
            action,
            reviewer_id,
            action,
            action,
            reason,
            action,
            reviewed_at,
            str(occurrence_id),
            self.user_id,
            expected_status,
            expected_review_version,
            _canonical_json_text(predicate),
            _canonical_json_text(aggregation),
            current["claim_id"],
            current["claim_ordinal"],
            current["occurrence_key"],
            current["count_key"],
            current["canonical_text"],
            current["unit_value"],
            current["identity_status"],
            current.get("ambiguity_group_key"),
            current.get("occurred_at_start"),
            current.get("occurred_at_end"),
            current["domain"],
            current["sensitivity"],
            _json_list_text(current["project_scope"]),
            action,
            action,
            action,
            normalized_superseded_by,
        ),
    )
    if cursor.rowcount != 1:
        raise ContinuityStoreInvariantError("review_occurrence_unit failed its identity/evidence lifecycle guard")
    if action in {"accepted", "refresh_evidence", "reestablished"}:
        reviewed_at = _utc_now_iso()
        stamped = 0
        for evidence in supporting:
            evidence_id = str(evidence["id"])
            evidence_receipt = occurrence_evidence_review_receipt_digest(
                evidence,
                action=action,
                reviewer_id=reviewer_id,
                reason=reason,
                unit_review_receipt_digest=review_receipt,
            )
            evidence_cursor = self._execute(
                """
            UPDATE occurrence_evidence
            SET review_status = 'accepted',
                reviewed_at = ?,
                reviewer_id = ?,
                review_reason = ?,
                review_receipt_digest = ?,
                review_receipt_action = ?,
                unit_review_receipt_digest = ?
            WHERE user_id = ?
              AND id = ?
              AND review_status IN ('candidate', 'accepted')
              AND claim_id = ?
              AND occurrence_id IS ?
              AND evidence_key = ?
              AND evidence_role = ?
              AND memory_id IS ?
              AND source_id IS ?
              AND source_chunk_id IS ?
              AND quote IS ?
              AND quote_sha256 = ?
                """,
                (
                    reviewed_at,
                    reviewer_id,
                    reason,
                    evidence_receipt,
                    action,
                    review_receipt,
                    self.user_id,
                    evidence_id,
                    evidence["claim_id"],
                    evidence.get("occurrence_id"),
                    evidence["evidence_key"],
                    evidence["evidence_role"],
                    evidence.get("memory_id"),
                    evidence.get("source_id"),
                    evidence.get("source_chunk_id"),
                    evidence.get("quote"),
                    evidence["quote_sha256"],
                ),
            )
            stamped += evidence_cursor.rowcount
        if stamped != len(supporting):
            raise ContinuityStoreInvariantError("review_occurrence_unit could not stamp its complete evidence snapshot")
    row = self._fetch_one(
        "review_occurrence_unit",
        f"""
        SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS)}
        FROM occurrence_units
        WHERE id = ? AND user_id = ?
        """,
        (str(occurrence_id), self.user_id),
    )
    event_type = {
        "accepted": "occurrence.accepted",
        "rejected": "occurrence.rejected",
        "ambiguous": "occurrence.marked_ambiguous",
        "superseded": "occurrence.superseded",
        "retired": "occurrence.retired",
        "refresh_evidence": "occurrence.evidence_refreshed",
        "reestablished": "occurrence.reestablished",
    }[action]
    self._append_mutation_event(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=reviewer_id,
        target_type="occurrence_unit",
        target_id=row["id"],
        payload={
            "action": action,
            "reason": reason,
            "review_version": row["review_version"],
            "review_receipt_digest": row["review_receipt_digest"],
            "reviewed_evidence_count": row["reviewed_evidence_count"],
            "reviewed_evidence_digest": row["reviewed_evidence_digest"],
            "superseded_by": row["superseded_by"],
            "retired_at": row["retired_at"],
        },
    )
    if not _defer_occurrence_accounting:
        invalidate_occurrence_coverage(
            self,
            reason="An occurrence unit lifecycle decision changed.",
            actor_type=actor_type,
            actor_id=reviewer_id,
        )
    return row


def review_occurrence_unit(
    self,
    *,
    occurrence_id: str,
    action: str,
    reason: str,
    reviewer_id: str,
    expected_status: str = "candidate",
    expected_review_version: int = 0,
    superseded_by: str | None = None,
    actor_type: str = "user",
    _source_reestablishment_snapshot_sha256: str | None = None,
    _defer_occurrence_accounting: bool = False,
) -> VNextRow:
    """Run one occurrence review atomically even if a caller catches failure."""

    _lock_occurrence_graph_mutation(self)
    reviewer_id = reviewer_id.strip()
    reason = reason.strip()
    if not reviewer_id or not reason:
        raise ValueError("occurrence unit review requires reviewer_id and reason")
    self._execute("SAVEPOINT occurrence_unit_review")
    try:
        row = _review_occurrence_unit_locked(
            self,
            occurrence_id=occurrence_id,
            action=action,
            reason=reason,
            reviewer_id=reviewer_id,
            expected_status=expected_status,
            expected_review_version=expected_review_version,
            superseded_by=superseded_by,
            actor_type=actor_type,
            _source_reestablishment_snapshot_sha256=(_source_reestablishment_snapshot_sha256),
            _defer_occurrence_accounting=_defer_occurrence_accounting,
        )
    except BaseException:
        self._execute("ROLLBACK TO SAVEPOINT occurrence_unit_review")
        self._execute("RELEASE SAVEPOINT occurrence_unit_review")
        raise
    self._execute("RELEASE SAVEPOINT occurrence_unit_review")
    return row


def list_occurrence_units_for_claim(self, claim_id: str) -> list[VNextRow]:
    return self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS, prefix="unit.")}
        FROM occurrence_units AS unit
        WHERE unit.user_id = ?
          AND unit.claim_id = ?
          AND ({_OCCURRENCE_OWNER_COUNT_KEY_SQL})
        ORDER BY unit.claim_ordinal ASC, unit.id ASC
        """,
        (self.user_id, str(claim_id)),
    )


def refresh_occurrence_unit_evidence(
    self,
    *,
    occurrence_id: str,
    reason: str,
    reviewer_id: str,
    expected_review_version: int,
    actor_type: str = "user",
    _defer_occurrence_accounting: bool = False,
) -> VNextRow:
    """Explicitly re-sign an accepted unit after reviewed evidence is added."""

    return review_occurrence_unit(
        self,
        occurrence_id=occurrence_id,
        action="refresh_evidence",
        reason=reason,
        reviewer_id=reviewer_id,
        expected_status="accepted",
        expected_review_version=expected_review_version,
        actor_type=actor_type,
        _defer_occurrence_accounting=_defer_occurrence_accounting,
    )


def reconcile_occurrence_evidence_carrier(
    self,
    *,
    memory_id: str | None = None,
    source_id: str | None = None,
    reviewer_id: str,
    reason: str,
    actor_type: str = "user",
    _defer_occurrence_accounting: bool = False,
) -> list[VNextRow]:
    """Atomically reject one carrier's evidence and preserve valid deduped units."""

    _lock_occurrence_graph_mutation(self)
    if (memory_id is None) == (source_id is None):
        raise ValueError("exactly one occurrence evidence carrier is required")
    reviewer = reviewer_id.strip()
    review_reason = reason.strip()
    if not reviewer or not review_reason:
        raise ValueError("carrier reconciliation requires reviewer_id and reason")
    carrier_type = "memory" if memory_id is not None else "source"
    carrier_id = str(memory_id if memory_id is not None else source_id)
    self._execute("SAVEPOINT occurrence_carrier_reconcile")
    try:
        if source_id is not None:
            self.lock_source_occurrence_envelope(str(source_id))
        else:
            _lock_occurrence_memory_carrier(self, str(memory_id))

        def load_evidence_rows() -> list[VNextRow]:
            return self._fetch_all(
                f"""
                SELECT {_column_sql(OCCURRENCE_EVIDENCE_COLUMNS, prefix="evidence.")}
                FROM occurrence_evidence AS evidence
                WHERE evidence.user_id = ?
                  AND evidence.review_status <> 'rejected'
                  AND (
                    (? IS NOT NULL AND evidence.memory_id = ?)
                    OR (
                      ? IS NOT NULL
                      AND (
                        evidence.source_id = ?
                        OR EXISTS (
                          SELECT 1 FROM source_chunks AS chunk
                          WHERE chunk.id = evidence.source_chunk_id
                            AND chunk.user_id = evidence.user_id
                            AND chunk.source_id = ?
                        )
                      )
                    )
                  )
                ORDER BY evidence.id ASC
                """,
                (
                    self.user_id,
                    memory_id,
                    memory_id,
                    source_id,
                    source_id,
                    source_id,
                ),
            )

        discovered = load_evidence_rows()
        claim_ids = sorted(
            {str(row["claim_id"]) for row in discovered}
        )
        unit_ids = sorted(
            {
                str(row["occurrence_id"])
                for row in discovered
                if row.get("occurrence_id") is not None
            }
        )
        _lock_occurrence_claim_rows(self, claim_ids)
        locked_units = _lock_occurrence_unit_rows(self, unit_ids)
        evidence_rows = load_evidence_rows()
        if not evidence_rows:
            self._execute("RELEASE SAVEPOINT occurrence_carrier_reconcile")
            return []
        units = {
            occurrence_id: row
            for occurrence_id, row in locked_units.items()
            if row.get("review_status") in {"candidate", "accepted"}
        }
        for evidence in evidence_rows:
            evidence_id = str(evidence["id"])
            receipt = occurrence_evidence_review_receipt_digest(
                evidence,
                action="rejected",
                reviewer_id=reviewer,
                reason=review_reason,
                unit_review_receipt_digest=None,
            )
            cursor = self._execute(
                """
                UPDATE occurrence_evidence
                SET review_status = 'rejected',
                    reviewed_at = ?,
                    reviewer_id = ?,
                    review_reason = ?,
                    review_receipt_digest = ?,
                    review_receipt_action = 'rejected',
                    unit_review_receipt_digest = NULL
                WHERE user_id = ?
                  AND id = ?
                  AND review_status = ?
                  AND claim_id = ?
                  AND occurrence_id IS ?
                  AND evidence_key = ?
                  AND evidence_role = ?
                  AND memory_id IS ?
                  AND source_id IS ?
                  AND source_chunk_id IS ?
                  AND quote IS ?
                  AND quote_sha256 = ?
                """,
                (
                    _utc_now_iso(),
                    reviewer,
                    review_reason,
                    receipt,
                    self.user_id,
                    evidence_id,
                    evidence["review_status"],
                    evidence["claim_id"],
                    evidence.get("occurrence_id"),
                    evidence["evidence_key"],
                    evidence["evidence_role"],
                    evidence.get("memory_id"),
                    evidence.get("source_id"),
                    evidence.get("source_chunk_id"),
                    evidence.get("quote"),
                    evidence["quote_sha256"],
                ),
            )
            if cursor.rowcount != 1:
                raise ContinuityStoreInvariantError("carrier reconciliation lost its evidence CAS")
        outcomes: list[VNextRow] = []
        for occurrence_id in unit_ids:
            unit = units.get(occurrence_id)
            if unit is None:
                continue
            status = str(unit["review_status"])
            version = int(cast(int, unit["review_version"]))
            survives = bool(_eligible_supporting_evidence(self, occurrence_id))
            if status == "accepted" and survives:
                final = refresh_occurrence_unit_evidence(
                    self,
                    occurrence_id=occurrence_id,
                    reason=review_reason,
                    reviewer_id=reviewer,
                    expected_review_version=version,
                    actor_type=actor_type,
                    _defer_occurrence_accounting=_defer_occurrence_accounting,
                )
                outcome = "refreshed"
            elif status == "accepted":
                final = review_occurrence_unit(
                    self,
                    occurrence_id=occurrence_id,
                    action="retired",
                    reason=review_reason,
                    reviewer_id=reviewer,
                    expected_status="accepted",
                    expected_review_version=version,
                    actor_type=actor_type,
                    _defer_occurrence_accounting=_defer_occurrence_accounting,
                )
                outcome = "retired"
            elif not survives:
                final = review_occurrence_unit(
                    self,
                    occurrence_id=occurrence_id,
                    action="rejected",
                    reason=review_reason,
                    reviewer_id=reviewer,
                    expected_status="candidate",
                    expected_review_version=version,
                    actor_type=actor_type,
                    _defer_occurrence_accounting=_defer_occurrence_accounting,
                )
                outcome = "rejected"
            else:
                continue
            outcomes.append(
                {
                    "occurrence_id": final["id"],
                    "outcome": outcome,
                    "review_status": final["review_status"],
                    "review_version": final["review_version"],
                }
            )
        self._append_mutation_event(
            event_type="occurrence.evidence_reconciled",
            actor_type=actor_type,
            actor_id=reviewer,
            target_type=carrier_type,
            target_id=carrier_id,
            payload={
                "carrier_type": carrier_type,
                "evidence_rejected": len(evidence_rows),
                "outcomes": outcomes,
                "reason": review_reason,
            },
        )
        if not _defer_occurrence_accounting:
            invalidate_occurrence_coverage(
                self,
                reason="Occurrence evidence carriers were reconciled.",
                actor_type=actor_type,
                actor_id=reviewer,
            )
    except BaseException:
        self._execute("ROLLBACK TO SAVEPOINT occurrence_carrier_reconcile")
        self._execute("RELEASE SAVEPOINT occurrence_carrier_reconcile")
        raise
    self._execute("RELEASE SAVEPOINT occurrence_carrier_reconcile")
    return outcomes


def reconcile_occurrence_claim_evidence(
    self,
    *,
    claim_id: str,
    reviewer_id: str,
    reason: str,
    actor_type: str = "user",
    _defer_occurrence_accounting: bool = False,
) -> list[VNextRow]:
    """Reject one proposal claim's evidence while preserving shared units."""

    _lock_occurrence_graph_mutation(self)
    reviewer = reviewer_id.strip()
    review_reason = reason.strip()
    if not reviewer or not review_reason:
        raise ValueError("claim reconciliation requires reviewer_id and reason")
    self._execute("SAVEPOINT occurrence_claim_reconcile")
    try:
        _lock_occurrence_claim_rows(self, [str(claim_id)])

        def load_evidence_rows() -> list[VNextRow]:
            return self._fetch_all(
                f"""
                SELECT {_column_sql(OCCURRENCE_EVIDENCE_COLUMNS, prefix="evidence.")}
                FROM occurrence_evidence AS evidence
                WHERE evidence.user_id = ?
                  AND evidence.claim_id = ?
                  AND evidence.review_status <> 'rejected'
                ORDER BY evidence.id ASC
                """,
                (self.user_id, str(claim_id)),
            )

        discovered = load_evidence_rows()
        unit_ids = sorted(
            {
                str(row["occurrence_id"])
                for row in discovered
                if row.get("occurrence_id") is not None
            }
        )
        locked_units = _lock_occurrence_unit_rows(self, unit_ids)
        evidence_rows = load_evidence_rows()
        if not evidence_rows:
            self._execute("RELEASE SAVEPOINT occurrence_claim_reconcile")
            return []
        units = {
            occurrence_id: row
            for occurrence_id, row in locked_units.items()
            if row.get("review_status") in {"candidate", "accepted"}
        }
        for evidence in evidence_rows:
            evidence_id = str(evidence["id"])
            receipt = occurrence_evidence_review_receipt_digest(
                evidence,
                action="rejected",
                reviewer_id=reviewer,
                reason=review_reason,
                unit_review_receipt_digest=None,
            )
            cursor = self._execute(
                """
                UPDATE occurrence_evidence
                SET review_status = 'rejected',
                    reviewed_at = ?,
                    reviewer_id = ?,
                    review_reason = ?,
                    review_receipt_digest = ?,
                    review_receipt_action = 'rejected',
                    unit_review_receipt_digest = NULL
                WHERE user_id = ?
                  AND id = ?
                  AND review_status = ?
                  AND claim_id = ?
                  AND occurrence_id IS ?
                  AND evidence_key = ?
                  AND evidence_role = ?
                  AND memory_id IS ?
                  AND source_id IS ?
                  AND source_chunk_id IS ?
                  AND quote IS ?
                  AND quote_sha256 = ?
                """,
                (
                    _utc_now_iso(),
                    reviewer,
                    review_reason,
                    receipt,
                    self.user_id,
                    evidence_id,
                    evidence["review_status"],
                    evidence["claim_id"],
                    evidence.get("occurrence_id"),
                    evidence["evidence_key"],
                    evidence["evidence_role"],
                    evidence.get("memory_id"),
                    evidence.get("source_id"),
                    evidence.get("source_chunk_id"),
                    evidence.get("quote"),
                    evidence["quote_sha256"],
                ),
            )
            if cursor.rowcount != 1:
                raise ContinuityStoreInvariantError("claim reconciliation lost its evidence CAS")
        outcomes: list[VNextRow] = []
        for occurrence_id in unit_ids:
            unit = units.get(occurrence_id)
            if unit is None:
                continue
            status = str(unit["review_status"])
            version = int(cast(int, unit["review_version"]))
            survives = bool(_eligible_supporting_evidence(self, occurrence_id))
            if status == "accepted" and survives:
                final = refresh_occurrence_unit_evidence(
                    self,
                    occurrence_id=occurrence_id,
                    reason=review_reason,
                    reviewer_id=reviewer,
                    expected_review_version=version,
                    actor_type=actor_type,
                    _defer_occurrence_accounting=_defer_occurrence_accounting,
                )
                outcome = "refreshed"
            elif status == "accepted":
                final = review_occurrence_unit(
                    self,
                    occurrence_id=occurrence_id,
                    action="retired",
                    reason=review_reason,
                    reviewer_id=reviewer,
                    expected_status="accepted",
                    expected_review_version=version,
                    actor_type=actor_type,
                    _defer_occurrence_accounting=_defer_occurrence_accounting,
                )
                outcome = "retired"
            elif not survives:
                final = review_occurrence_unit(
                    self,
                    occurrence_id=occurrence_id,
                    action="rejected",
                    reason=review_reason,
                    reviewer_id=reviewer,
                    expected_status="candidate",
                    expected_review_version=version,
                    actor_type=actor_type,
                    _defer_occurrence_accounting=_defer_occurrence_accounting,
                )
                outcome = "rejected"
            else:
                continue
            outcomes.append(
                {
                    "occurrence_id": final["id"],
                    "outcome": outcome,
                    "review_status": final["review_status"],
                    "review_version": final["review_version"],
                }
            )
        self._append_mutation_event(
            event_type="occurrence.claim_evidence_reconciled",
            actor_type=actor_type,
            actor_id=reviewer,
            target_type="occurrence_claim",
            target_id=str(claim_id),
            payload={
                "evidence_rejected": len(evidence_rows),
                "outcomes": outcomes,
                "reason": review_reason,
            },
        )
        if not _defer_occurrence_accounting:
            invalidate_occurrence_coverage(
                self,
                reason="Occurrence claim evidence was reconciled.",
                actor_type=actor_type,
                actor_id=reviewer,
            )
    except BaseException:
        self._execute("ROLLBACK TO SAVEPOINT occurrence_claim_reconcile")
        self._execute("RELEASE SAVEPOINT occurrence_claim_reconcile")
        raise
    self._execute("RELEASE SAVEPOINT occurrence_claim_reconcile")
    return outcomes


def _claim_has_eligible_supporting_evidence(self, claim_id: str) -> bool:
    row = self._fetch_optional_one(
        """
        SELECT evidence.id
        FROM occurrence_evidence AS evidence
        JOIN occurrence_claims AS claim
          ON claim.id = evidence.claim_id
         AND claim.user_id = evidence.user_id
        WHERE evidence.user_id = ?
          AND evidence.claim_id = ?
          AND evidence.evidence_role = 'supports'
          AND evidence.review_status IN ('candidate', 'accepted')
          AND (
            evidence.source_id IS NULL
            OR EXISTS (
              SELECT 1 FROM sources AS source
              WHERE source.id = evidence.source_id
                AND source.user_id = evidence.user_id
                AND source.deleted_at IS NULL
                AND source.domain = claim.domain
                AND source.sensitivity = claim.sensitivity
                AND json(
                  alice_source_project_scope_identity(source.metadata_json)
                ) = json(claim.project_scope)
            )
          )
          AND (
            evidence.source_chunk_id IS NULL
            OR EXISTS (
              SELECT 1
              FROM source_chunks AS chunk
              JOIN sources AS source
                ON source.id = chunk.source_id
               AND source.user_id = chunk.user_id
              WHERE chunk.id = evidence.source_chunk_id
                AND chunk.user_id = evidence.user_id
                AND source.deleted_at IS NULL
                AND source.domain = claim.domain
                AND source.sensitivity = claim.sensitivity
                AND json(
                  alice_source_project_scope_identity(source.metadata_json)
                ) = json(claim.project_scope)
            )
          )
          AND (
            evidence.memory_id IS NULL
            OR EXISTS (
              SELECT 1 FROM memories AS memory
              WHERE memory.id = evidence.memory_id
                AND memory.user_id = evidence.user_id
                AND memory.deleted_at IS NULL
                AND memory.status IN ('active', 'accepted')
                AND (
                  memory.valid_to IS NULL
                  OR julianday(memory.valid_to) >= julianday(?)
                )
                AND memory.domain = claim.domain
                AND memory.sensitivity = claim.sensitivity
                AND json(
                  alice_project_scope_identity(
                    memory.metadata_json,
                    memory.project_id
                  )
                ) = json(claim.project_scope)
            )
          )
        LIMIT 1
        """,
        (self.user_id, str(claim_id), _utc_now_iso()),
    )
    return row is not None


def redact_occurrence_memory_content(
    self,
    *,
    memory_id: str,
) -> VNextRow:
    """Scrub memory-derived occurrence text without erasing shared truth."""

    _lock_occurrence_graph_mutation(self)
    _lock_occurrence_memory_carrier(self, str(memory_id))
    rows = self._fetch_all(
        """
        SELECT id, claim_id, occurrence_id, quote, quote_sha256
        FROM occurrence_evidence
        WHERE user_id = ?
          AND memory_id = ?
        ORDER BY id ASC
        """,
        (self.user_id, str(memory_id)),
    )
    if not rows:
        return {
            "redacted_occurrence_evidence": 0,
            "redacted_occurrence_claims": 0,
            "redacted_occurrence_units": 0,
        }
    claim_ids = sorted({str(row["claim_id"]) for row in rows})
    unit_ids = sorted({str(row["occurrence_id"]) for row in rows if row.get("occurrence_id") is not None})
    _lock_occurrence_claim_rows(self, claim_ids)
    _lock_occurrence_unit_rows(self, unit_ids)
    marker_digest = hashlib.sha256(REDACTION_MARKER.encode("utf-8")).hexdigest()
    evidence_cursor = self._execute(
        """
        UPDATE occurrence_evidence
        SET quote = CASE WHEN quote IS NULL THEN NULL ELSE ? END,
            quote_sha256 = ?
        WHERE user_id = ?
          AND memory_id = ?
          AND (
            quote IS NOT CASE WHEN quote IS NULL THEN NULL ELSE ? END
            OR quote_sha256 IS NOT ?
          )
        """,
        (
            REDACTION_MARKER,
            marker_digest,
            self.user_id,
            str(memory_id),
            REDACTION_MARKER,
            marker_digest,
        ),
    )
    redacted_units = 0
    for occurrence_id in unit_ids:
        if _eligible_supporting_evidence(self, occurrence_id):
            continue
        cursor = self._execute(
            """
            UPDATE occurrence_units
            SET canonical_text = ?,
                updated_at = ?
            WHERE user_id = ?
              AND id = ?
              AND canonical_text IS NOT ?
            """,
            (
                REDACTION_MARKER,
                _utc_now_iso(),
                self.user_id,
                occurrence_id,
                REDACTION_MARKER,
            ),
        )
        redacted_units += cursor.rowcount
    redacted_claims = 0
    for claim_id in claim_ids:
        if _claim_has_eligible_supporting_evidence(self, claim_id):
            continue
        cursor = self._execute(
            """
            UPDATE occurrence_claims
            SET canonical_text = ?,
                updated_at = ?
            WHERE user_id = ?
              AND id = ?
              AND canonical_text IS NOT ?
            """,
            (
                REDACTION_MARKER,
                _utc_now_iso(),
                self.user_id,
                claim_id,
                REDACTION_MARKER,
            ),
        )
        redacted_claims += cursor.rowcount
    result: VNextRow = {
        "redacted_occurrence_evidence": evidence_cursor.rowcount,
        "redacted_occurrence_claims": redacted_claims,
        "redacted_occurrence_units": redacted_units,
    }
    if any(int(cast(int, value)) > 0 for value in result.values()):
        invalidate_occurrence_coverage(
            self,
            reason="Occurrence graph content was redacted.",
        )
    return result


def occurrence_memory_redaction_is_exact(self, memory_id: str) -> bool:
    rows = self._fetch_all(
        """
        SELECT id, claim_id, occurrence_id, quote, quote_sha256
        FROM occurrence_evidence
        WHERE user_id = ?
          AND memory_id = ?
        ORDER BY id ASC
        """,
        (self.user_id, str(memory_id)),
    )
    marker_digest = hashlib.sha256(REDACTION_MARKER.encode("utf-8")).hexdigest()
    if any(
        (row.get("quote") is not None and row.get("quote") != REDACTION_MARKER)
        or row.get("quote_sha256") != marker_digest
        for row in rows
    ):
        return False
    unit_ids = {str(row["occurrence_id"]) for row in rows if row.get("occurrence_id") is not None}
    for occurrence_id in unit_ids:
        if _eligible_supporting_evidence(self, occurrence_id):
            continue
        unit = self._fetch_optional_one(
            """
            SELECT canonical_text
            FROM occurrence_units
            WHERE user_id = ? AND id = ?
            """,
            (self.user_id, occurrence_id),
        )
        if unit is not None and unit.get("canonical_text") != REDACTION_MARKER:
            return False
    for claim_id in {str(row["claim_id"]) for row in rows}:
        if _claim_has_eligible_supporting_evidence(self, claim_id):
            continue
        claim = self._fetch_optional_one(
            """
            SELECT canonical_text
            FROM occurrence_claims
            WHERE user_id = ? AND id = ?
            """,
            (self.user_id, claim_id),
        )
        if claim is not None and claim.get("canonical_text") != REDACTION_MARKER:
            return False
    return True


def list_occurrence_units_for_memory(self, memory_id: str) -> list[VNextRow]:
    return self._fetch_all(
        f"""
        SELECT DISTINCT {_column_sql(OCCURRENCE_UNIT_COLUMNS, prefix="unit.")}
        FROM occurrence_units AS unit
        JOIN occurrence_evidence AS evidence
          ON evidence.occurrence_id = unit.id
         AND evidence.user_id = unit.user_id
        WHERE unit.user_id = ?
          AND evidence.memory_id = ?
          AND ({_OCCURRENCE_OWNER_COUNT_KEY_SQL})
        ORDER BY unit.id ASC
        """,
        (self.user_id, str(memory_id)),
    )


def list_occurrence_units_for_source(self, source_id: str) -> list[VNextRow]:
    return self._fetch_all(
        f"""
        SELECT DISTINCT {_column_sql(OCCURRENCE_UNIT_COLUMNS, prefix="unit.")}
        FROM occurrence_units AS unit
        JOIN occurrence_evidence AS evidence
          ON evidence.occurrence_id = unit.id
         AND evidence.user_id = unit.user_id
        WHERE unit.user_id = ?
          AND ({_OCCURRENCE_OWNER_COUNT_KEY_SQL})
          AND (
            evidence.source_id = ?
            OR EXISTS (
              SELECT 1
              FROM source_chunks AS chunk
              WHERE chunk.id = evidence.source_chunk_id
                AND chunk.user_id = evidence.user_id
                AND chunk.source_id = ?
            )
          )
        ORDER BY unit.id ASC
        """,
        (self.user_id, str(source_id), str(source_id)),
    )


def search_accepted_occurrence_units(
    self,
    *,
    query: str,
    exact_count_key: str | None = None,
    projects: Sequence[str] | None = None,
    domains: Sequence[str] | None = None,
    sensitivity_allowed: Sequence[str] | None = None,
    occurred_at_start: datetime | None = None,
    occurred_at_end: datetime | None = None,
    include_timeless: bool = False,
    as_of: datetime | None = None,
    after_id: str | None = None,
    limit: int = 200,
) -> list[VNextRow]:
    """Return auditable accepted units; callers reconstruct counts from rows."""

    if limit < 1:
        raise ValueError("limit must be positive")
    sensitivity = list(sensitivity_allowed or ())
    if not sensitivity:
        return []
    params: list[object] = [self.user_id]
    if exact_count_key is not None:
        match_sql = "unit.count_key = ?"
        params.append(_canonical_count_key_input(exact_count_key))
    else:
        patterns = [pattern.casefold() for pattern in _search_patterns(query)]
        match_sql = " OR ".join(
            "(lower(COALESCE(unit.count_key, '')) LIKE ? OR lower(COALESCE(unit.canonical_text, '')) LIKE ?)"
            for _pattern in patterns
        )
        for pattern in patterns:
            params.extend((pattern, pattern))
    domains_sql = ""
    if domains:
        domain_values = list(domains)
        domains_sql = f" AND unit.domain IN ({', '.join('?' for _value in domain_values)})"
        params.extend(domain_values)
    sensitivity_sql = f" AND unit.sensitivity IN ({', '.join('?' for _value in sensitivity)})"
    params.extend(sensitivity)
    project_values = list(project_scope_identity(projects or ()))
    projects_sql = ""
    if project_values:
        projects_sql = f"""
          AND EXISTS (
            SELECT 1
            FROM json_each(unit.project_scope) AS scoped_project
            WHERE CAST(scoped_project.value AS TEXT)
              IN ({", ".join("?" for _value in project_values)})
          )
        """
        params.extend(project_values)
    time_clauses: list[str] = []
    if occurred_at_start is not None:
        time_clauses.append("julianday(COALESCE(unit.occurred_at_end, unit.occurred_at_start)) >= julianday(?)")
        params.append(_iso_or_none(occurred_at_start))
    if occurred_at_end is not None:
        time_clauses.append("julianday(COALESCE(unit.occurred_at_start, unit.occurred_at_end)) < julianday(?)")
        params.append(_iso_or_none(occurred_at_end))
    time_sql = ""
    if time_clauses:
        dated_time_sql = " AND ".join(time_clauses)
        if include_timeless:
            time_sql = f" AND ((unit.occurred_at_start IS NULL AND unit.occurred_at_end IS NULL) OR ({dated_time_sql}))"
        else:
            time_sql = f" AND ({dated_time_sql})"
    after_sql = ""
    if after_id is not None:
        after_sql = " AND unit.id > ?"
        params.append(after_id)
    params.append(min(limit, 200))
    return self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS, prefix="unit.")}
        FROM occurrence_units AS unit
        WHERE unit.user_id = ?
          AND unit.review_status = 'accepted'
          AND unit.identity_status = 'resolved'
          AND unit.unit_value = 1
          AND ({_OCCURRENCE_OWNER_COUNT_KEY_SQL})
          AND ({match_sql})
          {domains_sql}
          {sensitivity_sql}
          {projects_sql}
          {time_sql}
          {after_sql}
        ORDER BY unit.id ASC
        LIMIT ?
        """,
        tuple(params),
    )


def search_accepted_occurrence_units_by_selector(
    self,
    *,
    selector_key: str,
    projects: Sequence[str] | None = None,
    domains: Sequence[str] | None = None,
    sensitivity_allowed: Sequence[str] | None = None,
    occurred_at_start: datetime | None = None,
    occurred_at_end: datetime | None = None,
    include_timeless: bool = False,
    as_of: datetime | None = None,
    after_id: str | None = None,
    limit: int = 200,
) -> list[VNextRow]:
    """Page one exact signed selector after all tenant/scope/time filters."""

    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    selector = canonical_occurrence_selector_key(selector_key)
    sensitivity = list(sensitivity_allowed or ())
    if not sensitivity:
        return []
    params: list[object] = [self.user_id, selector]
    domains_sql = ""
    if domains:
        domain_values = list(domains)
        domains_sql = f" AND unit.domain IN ({', '.join('?' for _value in domain_values)})"
        params.extend(domain_values)
    sensitivity_sql = f" AND unit.sensitivity IN ({', '.join('?' for _value in sensitivity)})"
    params.extend(sensitivity)
    project_values = list(project_scope_identity(projects or ()))
    projects_sql = ""
    if project_values:
        projects_sql = f"""
          AND EXISTS (
            SELECT 1
            FROM json_each(unit.project_scope) AS scoped_project
            WHERE CAST(scoped_project.value AS TEXT)
              IN ({", ".join("?" for _value in project_values)})
          )
        """
        params.extend(project_values)
    time_clauses: list[str] = []
    if occurred_at_start is not None:
        time_clauses.append("julianday(COALESCE(unit.occurred_at_end, unit.occurred_at_start)) >= julianday(?)")
        params.append(_iso_or_none(occurred_at_start))
    if occurred_at_end is not None:
        time_clauses.append("julianday(COALESCE(unit.occurred_at_start, unit.occurred_at_end)) < julianday(?)")
        params.append(_iso_or_none(occurred_at_end))
    time_sql = ""
    if time_clauses:
        dated_time_sql = " AND ".join(time_clauses)
        if include_timeless:
            time_sql = f" AND ((unit.occurred_at_start IS NULL AND unit.occurred_at_end IS NULL) OR ({dated_time_sql}))"
        else:
            time_sql = f" AND ({dated_time_sql})"
    as_of_sql = ""
    if as_of is not None:
        as_of_sql = " AND julianday(unit.updated_at) <= julianday(?)"
        params.append(_iso_or_none(as_of))
    after_sql = ""
    if after_id is not None:
        after_sql = " AND unit.id > ?"
        params.append(str(after_id))
    params.append(limit)
    return self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS, prefix="unit.")}
        FROM occurrence_units AS unit
        WHERE unit.user_id = ?
          AND unit.review_status = 'accepted'
          AND unit.identity_status = 'resolved'
          AND unit.unit_value = 1
          AND ({_OCCURRENCE_OWNER_COUNT_KEY_SQL})
          AND EXISTS (
            SELECT 1
            FROM json_each(
              unit.predicate_json,
              '$.selector_keys'
            ) AS signed_selector
            WHERE CAST(signed_selector.value AS TEXT) = ?
          )
          {domains_sql}
          {sensitivity_sql}
          {projects_sql}
          {time_sql}
          {as_of_sql}
          {after_sql}
        ORDER BY unit.id ASC
        LIMIT ?
        """,
        tuple(params),
    )


def list_accepted_occurrence_units(
    self,
    *,
    projects: Sequence[str] | None = None,
    domains: Sequence[str] | None = None,
    sensitivity_allowed: Sequence[str] | None = None,
    occurred_at_start: datetime | None = None,
    occurred_at_end: datetime | None = None,
    include_timeless: bool = False,
    as_of: datetime | None = None,
    after_id: str | None = None,
    limit: int = 200,
) -> list[VNextRow]:
    """Page every accepted unit after the exact reader scope filters."""

    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    sensitivity = list(sensitivity_allowed or ())
    if not sensitivity:
        return []
    params: list[object] = [self.user_id]
    domains_sql = ""
    if domains:
        domain_values = list(domains)
        domains_sql = f" AND unit.domain IN ({', '.join('?' for _value in domain_values)})"
        params.extend(domain_values)
    sensitivity_sql = f" AND unit.sensitivity IN ({', '.join('?' for _value in sensitivity)})"
    params.extend(sensitivity)
    project_values = list(project_scope_identity(projects or ()))
    projects_sql = ""
    if project_values:
        projects_sql = f"""
          AND EXISTS (
            SELECT 1
            FROM json_each(unit.project_scope) AS scoped_project
            WHERE CAST(scoped_project.value AS TEXT)
              IN ({", ".join("?" for _value in project_values)})
          )
        """
        params.extend(project_values)
    time_clauses: list[str] = []
    if occurred_at_start is not None:
        time_clauses.append("julianday(COALESCE(unit.occurred_at_end, unit.occurred_at_start)) >= julianday(?)")
        params.append(_iso_or_none(occurred_at_start))
    if occurred_at_end is not None:
        time_clauses.append("julianday(COALESCE(unit.occurred_at_start, unit.occurred_at_end)) < julianday(?)")
        params.append(_iso_or_none(occurred_at_end))
    time_sql = ""
    if time_clauses:
        dated_time_sql = " AND ".join(time_clauses)
        if include_timeless:
            time_sql = f" AND ((unit.occurred_at_start IS NULL AND unit.occurred_at_end IS NULL) OR ({dated_time_sql}))"
        else:
            time_sql = f" AND ({dated_time_sql})"
    as_of_sql = ""
    if as_of is not None:
        as_of_sql = " AND julianday(unit.updated_at) <= julianday(?)"
        params.append(_iso_or_none(as_of))
    after_sql = ""
    if after_id is not None:
        after_sql = " AND unit.id > ?"
        params.append(str(after_id))
    params.append(limit)
    return self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS, prefix="unit.")}
        FROM occurrence_units AS unit
        WHERE unit.user_id = ?
          AND unit.review_status = 'accepted'
          AND unit.identity_status = 'resolved'
          AND unit.unit_value = 1
          AND ({_OCCURRENCE_OWNER_COUNT_KEY_SQL})
          {domains_sql}
          {sensitivity_sql}
          {projects_sql}
          {time_sql}
          {as_of_sql}
          {after_sql}
        ORDER BY unit.id ASC
        LIMIT ?
        """,
        tuple(params),
    )


_OCCURRENCE_ACCOUNTING_EXPORTS = frozenset(
    {
        "_occurrence_metadata_source_chunk_ids",
        "_current_extraction_chunk",
        "_require_current_reviewed_extraction_evidence",
        "_validate_extraction_references",
        "_require_current_disposition_claim_facts",
        "_current_disposition_claim_facts",
        "_current_disposition_memory_facts",
        "_require_current_disposition_memory_facts",
        "lock_source_occurrence_envelope",
        "get_source_chunks_by_ids",
        "get_source_chunk_for_occurrence_accounting",
        "list_memories_for_source_chunk",
        "list_occurrence_claims_for_source_chunk",
        "list_accepted_occurrence_extraction_dispositions_for_claims",
        "write_occurrence_memory_metadata",
        "invalidate_occurrence_extraction_dispositions",
        "record_occurrence_extraction_disposition",
        "reestablish_source_occurrence_unit",
        "review_occurrence_extraction_disposition",
        "summarize_occurrence_extraction_accounting",
        "list_occurrence_evidence_for_units",
    }
)


def __getattr__(name: str) -> object:
    if name in _OCCURRENCE_ACCOUNTING_EXPORTS:
        from alicebot_api.vnext_stores.sqlite import occurrence_accounting

        return getattr(occurrence_accounting, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


for _method in (
    begin_occurrence_read_snapshot,
    end_occurrence_read_snapshot,
    ensure_occurrence_coverage,
    get_occurrence_coverage,
    invalidate_occurrence_coverage,
    review_occurrence_coverage,
    get_or_create_occurrence_claim,
    get_occurrence_claim,
    review_occurrence_claim,
    list_unresolved_occurrence_claims,
    get_or_create_occurrence_unit,
    get_occurrence_unit_by_key,
    create_occurrence_evidence,
    review_occurrence_unit,
    refresh_occurrence_unit_evidence,
    reconcile_occurrence_evidence_carrier,
    reconcile_occurrence_claim_evidence,
    redact_occurrence_memory_content,
    occurrence_memory_redaction_is_exact,
    list_occurrence_units_for_claim,
    list_occurrence_units_for_memory,
    list_occurrence_units_for_source,
    search_accepted_occurrence_units,
    search_accepted_occurrence_units_by_selector,
    list_accepted_occurrence_units,
):
    _method.__module__ = "alicebot_api.sqlite_store"
    _method.__qualname__ = f"SQLiteVNextStore.{_method.__name__}"
del _method


__all__ = [
    "OCCURRENCE_CLAIM_COLUMNS",
    "OCCURRENCE_COVERAGE_COLUMNS",
    "OCCURRENCE_EVIDENCE_COLUMNS",
    "OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS",
    "OCCURRENCE_EXTRACTION_MEMORY_LIMIT",
    "OCCURRENCE_READ_SNAPSHOT_PROOF",
    "OCCURRENCE_UNIT_COLUMNS",
    "begin_occurrence_read_snapshot",
    "end_occurrence_read_snapshot",
    "create_occurrence_evidence",
    "ensure_occurrence_coverage",
    "get_occurrence_claim",
    "get_occurrence_coverage",
    "invalidate_occurrence_coverage",
    "get_or_create_occurrence_claim",
    "get_or_create_occurrence_unit",
    "get_occurrence_unit_by_key",
    "list_occurrence_units_for_claim",
    "list_occurrence_units_for_memory",
    "list_occurrence_units_for_source",
    "list_unresolved_occurrence_claims",
    "occurrence_memory_redaction_is_exact",
    "reconcile_occurrence_claim_evidence",
    "reconcile_occurrence_evidence_carrier",
    "redact_occurrence_memory_content",
    "review_occurrence_claim",
    "review_occurrence_unit",
    "refresh_occurrence_unit_evidence",
    "review_occurrence_coverage",
    "list_accepted_occurrence_units",
    "search_accepted_occurrence_units",
    "search_accepted_occurrence_units_by_selector",
]
