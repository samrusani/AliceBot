"""PostgreSQL extraction accounting and source-carrier persistence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
from typing import cast
from uuid import UUID

from psycopg.types.json import Jsonb

from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_occurrence_predicates import (
    occurrence_claim_facts_digest,
    occurrence_evidence_facts_digest,
    occurrence_evidence_review_receipt_digest,
    occurrence_memory_carrier_facts_digest,
    occurrence_unit_review_receipt_digest,
)
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_stores.postgres.occurrences import (
    MEMORY_COLUMNS,
    OCCURRENCE_CLAIM_COLUMNS,
    OCCURRENCE_EVIDENCE_COLUMNS,
    OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS,
    OCCURRENCE_EXTRACTION_MEMORY_LIMIT,
    OCCURRENCE_UNIT_COLUMNS,
    VNextRow,
    _OCCURRENCE_MEMORY_SCOPE_SQL,
    _OCCURRENCE_SOURCE_SCOPE_SQL,
    _canonical_text_values,
    _column_sql,
    _extraction_review_receipt_digest,
    _extraction_snapshot_sha256,
    _lock_occurrence_graph_mutation,
    _same_value,
    get_occurrence_claim,
    invalidate_occurrence_coverage,
    review_occurrence_unit,
)


def lock_source_occurrence_envelope(
    self,
    source_id: str,
) -> VNextRow:
    """Serialize source-envelope occurrence lifecycle work and re-read it."""

    _lock_occurrence_graph_mutation(self)
    locked = self._fetch_optional_one(
        """
        SELECT source.id
        FROM sources AS source
        WHERE source.user_id = app.current_user_id()
          AND source.id = %s::uuid
          AND source.deleted_at IS NULL
        FOR UPDATE OF source
        """,
        (str(source_id),),
    )
    if locked is None:
        raise ContinuityStoreInvariantError("source occurrence envelope lock requires a current owned source")
    current = self.get_source(str(source_id))
    if current is None:
        raise ContinuityStoreInvariantError("source occurrence envelope lock lost its current source")
    return current


def get_source_chunks_by_ids(
    self,
    chunk_ids: Sequence[str],
) -> list[VNextRow]:
    """Resolve a bounded set of current-user source chunk ownership pairs."""

    ids = list(dict.fromkeys(str(value) for value in chunk_ids if value))
    if not ids:
        return []
    if len(ids) > 200:
        raise ValueError("source chunk batch cannot exceed 200 chunks")
    return self._fetch_all(
        """
        SELECT chunk.id, chunk.source_id
        FROM source_chunks AS chunk
        WHERE chunk.user_id = app.current_user_id()
          AND chunk.id = ANY(%s::uuid[])
        ORDER BY chunk.id ASC
        """,
        (ids,),
    )


def get_source_chunk_for_occurrence_accounting(
    self,
    source_chunk_id: str,
) -> VNextRow | None:
    """Resolve one owned chunk and its exact signed extraction envelope."""

    chunk = _current_extraction_chunk(self, str(source_chunk_id))
    if chunk is None:
        return None
    return {
        "id": chunk["source_chunk_id"],
        "source_id": chunk["source_id"],
        "text": chunk["chunk_text"],
        "source_title": chunk.get("source_title"),
        "snapshot_sha256": _extraction_snapshot_sha256(chunk),
    }


def list_memories_for_source_chunk(
    self,
    source_chunk_id: str,
) -> list[VNextRow]:
    """Return one complete, bounded occurrence-memory slice for a chunk."""

    rows = self._fetch_all(
        f"""
        SELECT {MEMORY_COLUMNS}
        FROM memories
        WHERE user_id = app.current_user_id()
          AND deleted_at IS NULL
          AND metadata_json ->> 'source_chunk_id' = %s
          AND metadata_json #>> '{{occurrence_proposal,source_chunk_id}}' = %s
        ORDER BY id ASC
        LIMIT %s
        """,
        (
            str(source_chunk_id),
            str(source_chunk_id),
            OCCURRENCE_EXTRACTION_MEMORY_LIMIT + 1,
        ),
    )
    if len(rows) > OCCURRENCE_EXTRACTION_MEMORY_LIMIT:
        raise ContinuityStoreInvariantError("source chunk occurrence reconciliation exceeds the bounded memory limit")
    return rows


def _occurrence_metadata_source_chunk_ids(
    metadata: Mapping[str, object],
) -> tuple[str, ...]:
    """Return canonical current-chunk references carried by occurrence metadata."""

    candidates: list[object] = [metadata.get("source_chunk_id")]
    proposal = metadata.get("occurrence_proposal")
    if isinstance(proposal, Mapping):
        candidates.append(proposal.get("source_chunk_id"))
    chunk_ids: set[str] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            chunk_ids.add(str(UUID(str(candidate))))
        except ValueError:
            continue
    return tuple(sorted(chunk_ids))


def write_occurrence_memory_metadata(
    self,
    *,
    memory_id: str,
    metadata_json: JsonObject,
    expected_metadata_json: JsonObject | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> VNextRow:
    """CAS-replace occurrence-only memory metadata without touching lifecycle facts."""

    _lock_occurrence_graph_mutation(self)
    replacement = dict(metadata_json)
    current = self._fetch_optional_one(
        f"""
        SELECT {MEMORY_COLUMNS}
        FROM memories
        WHERE id = %s::uuid
          AND user_id = app.current_user_id()
          AND deleted_at IS NULL
        """,
        (str(memory_id),),
    )
    if current is None:
        raise ContinuityStoreInvariantError("write_occurrence_memory_metadata requires a current owned memory")
    current_metadata = current.get("metadata_json")
    if not isinstance(current_metadata, Mapping):
        raise ContinuityStoreInvariantError("current memory metadata is not an object")
    if expected_metadata_json is not None and dict(current_metadata) != dict(expected_metadata_json):
        raise ContinuityStoreInvariantError("write_occurrence_memory_metadata lost its metadata CAS")
    changed_keys = {
        key for key in set(current_metadata) | set(replacement) if current_metadata.get(key) != replacement.get(key)
    }
    if any(not str(key).startswith("occurrence_") for key in changed_keys):
        raise ContinuityStoreInvariantError("write_occurrence_memory_metadata may change occurrence-prefixed keys only")
    if not changed_keys:
        return current
    row = self._fetch_optional_one(
        f"""
        UPDATE memories
        SET metadata_json = %s
        WHERE id = %s::uuid
          AND user_id = app.current_user_id()
          AND deleted_at IS NULL
          AND metadata_json = %s
        RETURNING {MEMORY_COLUMNS}
        """,
        (
            Jsonb(replacement),
            str(memory_id),
            Jsonb(dict(current_metadata)),
        ),
    )
    if row is None:
        raise ContinuityStoreInvariantError("write_occurrence_memory_metadata lost its metadata CAS")
    chunk_ids = sorted(
        set(_occurrence_metadata_source_chunk_ids(current_metadata))
        | set(_occurrence_metadata_source_chunk_ids(replacement))
    )
    for source_chunk_id in chunk_ids:
        if _current_extraction_chunk(self, source_chunk_id) is None:
            continue
        invalidate_occurrence_extraction_dispositions(
            self,
            source_chunk_id=source_chunk_id,
            reason="Occurrence proposal metadata changed current chunk accounting.",
            actor_type=actor_type,
            actor_id=actor_id,
            _defer_occurrence_coverage=True,
        )
    invalidate_occurrence_coverage(
        self,
        reason="Occurrence proposal metadata changed.",
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return row


def list_occurrence_claims_for_source_chunk(
    self,
    source_chunk_id: str,
    *,
    limit: int = 201,
) -> list[VNextRow]:
    """Return current direct claim carriers for one live owned source chunk."""

    if not 1 <= limit <= 201:
        raise ValueError("limit must be between 1 and 201")
    return self._fetch_all(
        f"""
        SELECT DISTINCT {_column_sql(OCCURRENCE_CLAIM_COLUMNS, prefix="claim.")}
        FROM occurrence_evidence AS evidence
        JOIN occurrence_claims AS claim
          ON claim.id = evidence.claim_id
         AND claim.user_id = evidence.user_id
        JOIN source_chunks AS chunk
          ON chunk.id = evidence.source_chunk_id
         AND chunk.user_id = evidence.user_id
        JOIN sources AS source
          ON source.id = chunk.source_id
         AND source.user_id = chunk.user_id
        WHERE evidence.user_id = app.current_user_id()
          AND evidence.source_chunk_id = %s::uuid
          AND evidence.review_status IN ('candidate', 'accepted')
          AND claim.review_status IN ('candidate', 'accepted')
          AND source.deleted_at IS NULL
          AND (evidence.source_id IS NULL OR evidence.source_id = source.id)
        ORDER BY claim.id ASC
        LIMIT %s
        """,
        (str(source_chunk_id), limit),
    )


def list_accepted_occurrence_extraction_dispositions_for_claims(
    self,
    claim_ids: Sequence[str],
    *,
    limit: int = 201,
) -> list[VNextRow]:
    """Return bounded accepted proof carriers that explicitly bind claim ids."""

    if not 1 <= limit <= 201:
        raise ValueError("limit must be between 1 and 201")
    ids = _canonical_text_values(
        claim_ids,
        field="claim_ids",
        uuid_values=True,
    )
    if len(ids) > 200:
        raise ValueError("occurrence claim proof batch cannot exceed 200 claims")
    if not ids:
        return []
    return self._fetch_all(
        f"""
        SELECT
          {
            _column_sql(
                OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS,
                prefix="disposition.",
            )
        }
        FROM occurrence_extraction_dispositions AS disposition
        JOIN source_chunks AS chunk
          ON chunk.id = disposition.source_chunk_id
         AND chunk.user_id = disposition.user_id
        JOIN sources AS source
          ON source.id = disposition.source_id
         AND source.id = chunk.source_id
         AND source.user_id = disposition.user_id
        WHERE disposition.user_id = app.current_user_id()
          AND disposition.review_status = 'accepted'
          AND source.deleted_at IS NULL
          AND EXISTS (
            SELECT 1
            FROM jsonb_array_elements_text(
              disposition.claim_ids
            ) AS bound_claim(claim_id)
            WHERE bound_claim.claim_id = ANY(%s::text[])
          )
        ORDER BY disposition.source_chunk_id ASC, disposition.id ASC
        LIMIT %s
        """,
        (ids, limit),
    )


def _current_extraction_chunk(
    self,
    source_chunk_id: str,
) -> VNextRow | None:
    return self._fetch_optional_one(
        f"""
        SELECT
          source.id AS source_id,
          source.content_hash AS source_content_hash,
          source.domain AS source_domain,
          source.sensitivity AS source_sensitivity,
          source.title AS source_title,
          source.source_created_at,
          source.metadata_json ->> 'session_date'
            AS source_session_date,
          source.metadata_json ->> 'provenance_role'
            AS source_provenance_role,
          ({_OCCURRENCE_SOURCE_SCOPE_SQL}) AS source_project_scope,
          chunk.id AS source_chunk_id,
          chunk.chunk_index,
          chunk.text AS chunk_text,
          chunk.created_at AS chunk_created_at
        FROM source_chunks AS chunk
        JOIN sources AS source
          ON source.id = chunk.source_id
         AND source.user_id = chunk.user_id
        WHERE chunk.user_id = app.current_user_id()
          AND chunk.id = %s::uuid
          AND source.deleted_at IS NULL
        """,
        (str(source_chunk_id),),
    )


def _current_reviewed_supporting_evidence(
    self,
    occurrence_id: str,
) -> list[VNextRow]:
    return self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_EVIDENCE_COLUMNS, prefix="evidence.")}
        FROM occurrence_evidence AS evidence
        JOIN occurrence_units AS evidence_unit
          ON evidence_unit.id = evidence.occurrence_id
         AND evidence_unit.user_id = evidence.user_id
        WHERE evidence.user_id = app.current_user_id()
          AND evidence.occurrence_id = %s::uuid
          AND evidence.evidence_role = 'supports'
          AND evidence.review_status IN ('candidate', 'accepted')
          AND (
            evidence.quote IS NULL
            OR encode(digest(evidence.quote, 'sha256'), 'hex')
              = evidence.quote_sha256
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
                AND ({_OCCURRENCE_SOURCE_SCOPE_SQL})
                  = evidence_unit.project_scope
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
                AND source.domain = evidence_unit.domain
                AND source.sensitivity = evidence_unit.sensitivity
                AND ({_OCCURRENCE_SOURCE_SCOPE_SQL})
                  = evidence_unit.project_scope
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
                  OR memory.valid_to >= clock_timestamp()
                )
                AND memory.domain = evidence_unit.domain
                AND memory.sensitivity = evidence_unit.sensitivity
                AND ({_OCCURRENCE_MEMORY_SCOPE_SQL})
                  = evidence_unit.project_scope
            )
          )
        ORDER BY evidence.evidence_key ASC, evidence.id ASC
        """,
        (str(occurrence_id),),
    )


def _reviewed_evidence_digest(
    rows: Sequence[Mapping[str, object]],
) -> str:
    canonical = "|".join(
        occurrence_evidence_facts_digest(row)
        for row in sorted(
            rows,
            key=lambda row: (
                str(row["evidence_key"]),
                str(row["id"]),
            ),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def reestablish_source_occurrence_unit(
    self,
    *,
    occurrence_id: str,
    source_chunk_id: str,
    stage: str,
    reason: str,
    reviewer_id: str,
    expected_review_version: int,
    actor_type: str = "user",
) -> VNextRow:
    """Re-sign one lifecycle-retired unit from a fresh current source snapshot."""

    _lock_occurrence_graph_mutation(self)
    if stage != "http_source_review":
        raise ContinuityStoreInvariantError("source occurrence re-establishment requires the source review stage")
    current_chunk = _current_extraction_chunk(self, str(source_chunk_id))
    if current_chunk is None:
        raise ContinuityStoreInvariantError("source occurrence re-establishment requires a current owned chunk")
    snapshot_sha256 = _extraction_snapshot_sha256(current_chunk)
    unit = self._fetch_optional_one(
        f"""
        SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS)}
        FROM occurrence_units
        WHERE user_id = app.current_user_id()
          AND id = %s::uuid
        """,
        (str(occurrence_id),),
    )
    if (
        unit is None
        or unit.get("review_status") != "retired"
        or unit.get("review_receipt_action") != "retired"
        or unit.get("retired_at") is None
        or unit.get("superseded_by") is not None
        or unit.get("review_version") != expected_review_version
    ):
        raise ContinuityStoreInvariantError("source occurrence re-establishment requires a lifecycle-retired unit")
    prior_reason = str(unit.get("review_reason") or "")
    prior_reviewer = str(unit.get("reviewer_id") or "")
    prior_digest = str(unit.get("reviewed_evidence_digest") or "")
    prior_receipt = str(unit.get("review_receipt_digest") or "")
    if (
        not prior_reviewer
        or not prior_reason.endswith("(http_source_review_envelope_change)")
        or len(prior_digest) != 64
        or occurrence_unit_review_receipt_digest(
            unit,
            action="retired",
            reviewer_id=prior_reviewer,
            reason=prior_reason,
            review_version=expected_review_version,
            evidence_digest=prior_digest,
        )
        != prior_receipt
    ):
        raise ContinuityStoreInvariantError("source occurrence re-establishment lacks a signed lifecycle detachment")

    source_id = str(current_chunk["source_id"])
    eligible = _current_reviewed_supporting_evidence(
        self,
        str(occurrence_id),
    )
    fresh = [
        evidence
        for evidence in eligible
        if evidence.get("review_status") == "candidate"
        and evidence.get("memory_id") is None
        and str(evidence.get("claim_id") or "") == str(unit["claim_id"])
        and str(evidence.get("source_id") or "") == source_id
        and str(evidence.get("source_chunk_id") or "") == str(source_chunk_id)
        and isinstance(evidence.get("metadata_json"), Mapping)
        and cast(Mapping[str, object], evidence["metadata_json"]).get("source_snapshot_sha256") == snapshot_sha256
        and cast(Mapping[str, object], evidence["metadata_json"]).get("source_reestablishment_stage")
        == "http_source_review_envelope_change"
    ]
    if not fresh:
        raise ContinuityStoreInvariantError("source occurrence re-establishment lacks fresh current-snapshot evidence")
    return review_occurrence_unit(
        self,
        occurrence_id=str(occurrence_id),
        action="reestablished",
        reason=reason,
        reviewer_id=reviewer_id,
        expected_status="retired",
        expected_review_version=expected_review_version,
        actor_type=actor_type,
        _source_reestablishment_snapshot_sha256=snapshot_sha256,
    )


def _require_current_reviewed_extraction_evidence(
    self,
    evidence_rows: Sequence[Mapping[str, object]],
    *,
    occurrence_ids: Sequence[str],
) -> None:
    """Reconstruct the complete unit/evidence receipt chain from current facts."""

    included = set(occurrence_ids)
    for occurrence_id in sorted(included):
        unit = self._fetch_optional_one(
            f"""
            SELECT {_column_sql(OCCURRENCE_UNIT_COLUMNS)}
            FROM occurrence_units
            WHERE user_id = app.current_user_id()
              AND id = %s::uuid
            """,
            (occurrence_id,),
        )
        supporting = _current_reviewed_supporting_evidence(
            self,
            occurrence_id,
        )
        evidence_digest = _reviewed_evidence_digest(supporting)
        if unit is None:
            raise ContinuityStoreInvariantError(
                "extraction disposition evidence is not bound to the current reviewed occurrence"
            )
        review_action = str(unit.get("review_receipt_action") or "")
        reviewer_id = str(unit.get("reviewer_id") or "")
        review_reason = str(unit.get("review_reason") or "")
        review_version = unit.get("review_version")
        unit_receipt = unit.get("review_receipt_digest")
        if (
            unit.get("review_status") != "accepted"
            or unit.get("identity_status") != "resolved"
            or review_action not in {"accepted", "refresh_evidence", "reestablished"}
            or not reviewer_id
            or not review_reason
            or isinstance(review_version, bool)
            or not isinstance(review_version, int)
            or review_version < 1
            or unit_receipt is None
            or not supporting
            or unit.get("reviewed_evidence_count") != len(supporting)
            or unit.get("reviewed_evidence_digest") != evidence_digest
        ):
            raise ContinuityStoreInvariantError(
                "extraction disposition evidence is not bound to the current reviewed occurrence"
            )
        expected_unit_receipt = occurrence_unit_review_receipt_digest(
            unit,
            action=review_action,
            reviewer_id=reviewer_id,
            reason=review_reason,
            review_version=review_version,
            evidence_digest=evidence_digest,
        )
        if unit_receipt != expected_unit_receipt:
            raise ContinuityStoreInvariantError("extraction disposition unit review receipt is stale")
        supporting_ids = {str(row["id"]) for row in supporting}
        chunk_ids = {
            str(row["evidence_id"])
            for row in evidence_rows
            if row.get("occurrence_id") is not None and str(row["occurrence_id"]) == occurrence_id
        }
        if not chunk_ids or not chunk_ids.issubset(supporting_ids):
            raise ContinuityStoreInvariantError(
                "extraction disposition evidence is not bound to the current reviewed occurrence"
            )
        for evidence in supporting:
            if (
                evidence.get("review_status") != "accepted"
                or evidence.get("review_receipt_action") != review_action
                or evidence.get("reviewer_id") != reviewer_id
                or evidence.get("review_reason") != review_reason
                or evidence.get("unit_review_receipt_digest") != unit_receipt
            ):
                raise ContinuityStoreInvariantError(
                    "extraction disposition evidence is not bound to the current reviewed occurrence"
                )
            expected_evidence_receipt = occurrence_evidence_review_receipt_digest(
                evidence,
                action=review_action,
                reviewer_id=reviewer_id,
                reason=review_reason,
                unit_review_receipt_digest=str(unit_receipt),
            )
            if evidence.get("review_receipt_digest") != expected_evidence_receipt:
                raise ContinuityStoreInvariantError("extraction disposition evidence review receipt is stale")


def _validate_extraction_references(
    self,
    *,
    source_chunk_id: str,
    disposition: str,
    claim_ids: Sequence[str],
    occurrence_ids: Sequence[str],
    require_reviewed_occurrences: bool,
) -> None:
    evidence_rows = self._fetch_all(
        """
        SELECT DISTINCT
          claim.id AS claim_id,
          claim.resolution_status,
          claim.review_status AS claim_review_status,
          evidence.id AS evidence_id,
          evidence.occurrence_id,
          evidence.review_status AS evidence_review_status,
          evidence.unit_review_receipt_digest
            AS evidence_unit_review_receipt_digest,
          unit.review_status AS unit_review_status,
          unit.identity_status AS unit_identity_status,
          unit.review_receipt_digest AS unit_review_receipt_digest
        FROM occurrence_evidence AS evidence
        JOIN occurrence_claims AS claim
          ON claim.id = evidence.claim_id
         AND claim.user_id = evidence.user_id
        LEFT JOIN occurrence_units AS unit
          ON unit.id = evidence.occurrence_id
         AND unit.user_id = evidence.user_id
        WHERE evidence.user_id = app.current_user_id()
          AND evidence.source_chunk_id = %s::uuid
          AND evidence.evidence_role = 'supports'
          AND evidence.review_status IN ('candidate', 'accepted')
        ORDER BY claim.id ASC, evidence.occurrence_id ASC
        """,
        (str(source_chunk_id),),
    )
    actual_claim_ids = {str(row["claim_id"]) for row in evidence_rows}
    actual_occurrence_ids = {str(row["occurrence_id"]) for row in evidence_rows if row.get("occurrence_id") is not None}
    actual_accepted_occurrence_ids = {
        str(row["occurrence_id"])
        for row in evidence_rows
        if row.get("occurrence_id") is not None
        and row.get("resolution_status") == "resolved"
        and row.get("claim_review_status") == "accepted"
    }
    if disposition == "no_occurrence":
        if claim_ids or occurrence_ids or evidence_rows:
            raise ContinuityStoreInvariantError("no_occurrence conflicts with current chunk occurrence evidence")
        return
    if disposition == "unresolved_claims":
        if not claim_ids or set(claim_ids) != actual_claim_ids:
            raise ValueError("unresolved_claims must exhaust current chunk claims")
        if set(occurrence_ids) != actual_accepted_occurrence_ids:
            raise ContinuityStoreInvariantError(
                "unresolved extraction disposition does not exhaust current accepted occurrences"
            )
        if not any(
            row.get("resolution_status") == "pending" and row.get("claim_review_status") == "candidate"
            for row in evidence_rows
        ):
            raise ContinuityStoreInvariantError("unresolved extraction disposition has no current unresolved claim")
        if require_reviewed_occurrences:
            _require_current_reviewed_extraction_evidence(
                self,
                evidence_rows,
                occurrence_ids=occurrence_ids,
            )
        return
    if disposition != "accepted_occurrences":
        raise ValueError("invalid occurrence extraction disposition")
    if not occurrence_ids:
        raise ValueError("accepted_occurrences requires at least one occurrence unit")
    if set(claim_ids) != actual_claim_ids:
        raise ContinuityStoreInvariantError("accepted extraction disposition does not exhaust current claims")
    if set(occurrence_ids) != actual_occurrence_ids:
        raise ContinuityStoreInvariantError("accepted extraction disposition does not exhaust current occurrences")
    if require_reviewed_occurrences and any(
        row.get("resolution_status") != "resolved" or row.get("claim_review_status") != "accepted"
        for row in evidence_rows
    ):
        raise ContinuityStoreInvariantError("accepted extraction disposition still has an unresolved claim")
    if require_reviewed_occurrences:
        _require_current_reviewed_extraction_evidence(
            self,
            evidence_rows,
            occurrence_ids=occurrence_ids,
        )
    review_predicate = (
        "AND unit.review_status = 'accepted' "
        "AND unit.identity_status = 'resolved' "
        "AND evidence.review_status = 'accepted' "
        "AND unit.review_receipt_digest IS NOT NULL "
        "AND evidence.unit_review_receipt_digest = unit.review_receipt_digest "
        if require_reviewed_occurrences
        else ""
    )
    rows = self._fetch_all(
        f"""
        SELECT DISTINCT unit.id
        FROM occurrence_units AS unit
        JOIN occurrence_evidence AS evidence
          ON evidence.occurrence_id = unit.id
         AND evidence.user_id = unit.user_id
        WHERE unit.user_id = app.current_user_id()
          AND unit.id = ANY(%s::uuid[])
          {review_predicate}
          AND evidence.source_chunk_id = %s::uuid
          AND evidence.evidence_role = 'supports'
          AND evidence.review_status IN ('candidate', 'accepted')
        """,
        (list(occurrence_ids), str(source_chunk_id)),
    )
    if {str(row["id"]) for row in rows} != set(occurrence_ids):
        raise ContinuityStoreInvariantError("accepted extraction disposition references an invalid occurrence")


def _require_current_disposition_claim_facts(
    self,
    disposition: Mapping[str, object],
) -> None:
    metadata = disposition.get("metadata_json")
    if not isinstance(metadata, Mapping):
        raise ContinuityStoreInvariantError("extraction disposition claim facts metadata is missing")
    supplied = metadata.get("claim_facts_digests")
    if not isinstance(supplied, Mapping):
        raise ContinuityStoreInvariantError("extraction disposition claim facts metadata is missing")
    claim_ids = [str(value) for value in cast(Sequence[object], disposition["claim_ids"])]
    if set(str(key) for key in supplied) != set(claim_ids):
        raise ContinuityStoreInvariantError("extraction disposition claim facts keyset is stale")
    for claim_id in claim_ids:
        claim = get_occurrence_claim(self, claim_id)
        if claim is None or supplied.get(claim_id) != occurrence_claim_facts_digest(claim):
            raise ContinuityStoreInvariantError("extraction disposition claim facts are stale")


def _current_disposition_claim_facts(
    self,
    claim_ids: Sequence[str],
) -> dict[str, str]:
    facts: dict[str, str] = {}
    for claim_id in claim_ids:
        claim = get_occurrence_claim(self, str(claim_id))
        if claim is None:
            raise ContinuityStoreInvariantError("extraction disposition claim facts are unavailable")
        facts[str(claim_id)] = occurrence_claim_facts_digest(claim)
    return dict(sorted(facts.items()))


def _current_disposition_memory_facts(
    self,
    source_chunk_id: str,
) -> dict[str, str]:
    """Digest every live memory currently and validly anchored to one chunk."""

    rows = self._fetch_all(
        f"""
        SELECT
          memory.id,
          memory.user_id,
          memory.memory_key,
          memory.value,
          memory.status,
          memory.source_event_ids,
          memory.memory_type,
          memory.valid_from,
          memory.valid_to,
          memory.title,
          memory.canonical_text,
          memory.summary,
          memory.domain,
          memory.sensitivity,
          memory.first_seen_at,
          memory.last_seen_at,
          memory.metadata_json,
          memory.project_id
        FROM memories AS memory
        JOIN source_chunks AS chunk
          ON chunk.id = %s::uuid
         AND chunk.user_id = memory.user_id
        JOIN sources AS source
          ON source.id = chunk.source_id
         AND source.user_id = chunk.user_id
        WHERE memory.user_id = app.current_user_id()
          AND memory.deleted_at IS NULL
          AND memory.status IN (
            'candidate',
            'active',
            'accepted',
            'needs_review',
            'private_only',
            'stale'
          )
          AND chunk.id::text
            = memory.metadata_json ->> 'source_chunk_id'
          AND NOT (
            memory.metadata_json ? 'occurrence_proposals'
          )
          AND (
            COALESCE(
              jsonb_typeof(
                memory.metadata_json -> 'occurrence_proposal'
              ),
              'null'
            ) = 'null'
            OR (
              jsonb_typeof(
                memory.metadata_json -> 'occurrence_proposal'
              ) = 'object'
              AND chunk.id::text
                = memory.metadata_json
                  #>> '{{occurrence_proposal,source_chunk_id}}'
            )
          )
          AND source.deleted_at IS NULL
          AND source.domain = memory.domain
          AND source.sensitivity = memory.sensitivity
          AND ({_OCCURRENCE_SOURCE_SCOPE_SQL})
            = ({_OCCURRENCE_MEMORY_SCOPE_SQL})
        ORDER BY memory.id ASC
        """,
        (str(source_chunk_id),),
    )
    return {str(row["id"]): occurrence_memory_carrier_facts_digest(row) for row in rows}


def _require_current_disposition_memory_facts(
    self,
    disposition: Mapping[str, object],
) -> None:
    metadata = disposition.get("metadata_json")
    if not isinstance(metadata, Mapping):
        raise ContinuityStoreInvariantError("extraction disposition memory facts metadata is missing")
    supplied = metadata.get("memory_facts_digests")
    if not isinstance(supplied, Mapping) or any(
        not isinstance(key, str) or not isinstance(value, str) for key, value in supplied.items()
    ):
        raise ContinuityStoreInvariantError("extraction disposition memory facts metadata is missing")
    current = _current_disposition_memory_facts(
        self,
        str(disposition["source_chunk_id"]),
    )
    if dict(supplied) != current:
        raise ContinuityStoreInvariantError("extraction disposition memory facts are stale")


def invalidate_occurrence_extraction_dispositions(
    self,
    *,
    source_chunk_id: str,
    reason: str,
    extractor_version: str | None = None,
    effective_at: datetime | str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    _defer_occurrence_coverage: bool = False,
) -> list[VNextRow]:
    """CAS-return reviewed chunk decisions to candidate after fact changes."""

    _lock_occurrence_graph_mutation(self)
    invalidation_reason = reason.strip()
    if not invalidation_reason:
        raise ValueError("extraction invalidation requires a reason")
    extractor = " ".join(extractor_version.split()).strip() if extractor_version is not None else None
    if extractor_version is not None and not extractor:
        raise ValueError("extractor_version cannot be empty")
    chunk = _current_extraction_chunk(self, str(source_chunk_id))
    if chunk is None:
        raise ContinuityStoreInvariantError("extraction invalidation requires a current owned chunk")
    rows = self._fetch_all(
        f"""
        SELECT {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
        FROM occurrence_extraction_dispositions
        WHERE user_id = app.current_user_id()
          AND source_chunk_id = %s::uuid
          AND (%s::text IS NULL OR extractor_version = %s)
          AND review_status <> 'candidate'
        ORDER BY id ASC
        """,
        (str(source_chunk_id), extractor, extractor),
    )
    invalidated: list[VNextRow] = []
    for current in rows:
        expected_review_version = int(cast(int, current["review_version"]))
        row = self._fetch_optional_one(
            f"""
            UPDATE occurrence_extraction_dispositions
            SET review_status = 'candidate',
                reviewed_at = NULL,
                reviewer_id = NULL,
                review_reason = NULL,
                review_version = review_version + 1,
                review_receipt_digest = NULL,
                updated_at = clock_timestamp()
            WHERE user_id = app.current_user_id()
              AND id = %s::uuid
              AND review_status = %s
              AND review_version = %s
            RETURNING {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
            """,
            (
                str(current["id"]),
                str(current["review_status"]),
                expected_review_version,
            ),
        )
        if row is None:
            raise ContinuityStoreInvariantError("extraction invalidation lost its lifecycle CAS")
        invalidated.append(row)
    if not _defer_occurrence_coverage:
        invalidate_occurrence_coverage(
            self,
            reason=invalidation_reason,
            effective_at=effective_at,
            actor_type=actor_type,
            actor_id=actor_id,
        )
    if invalidated:
        self._append_mutation_event(
            event_type="occurrence.extraction_dispositions_invalidated",
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="source_chunk",
            target_id=str(source_chunk_id),
            payload={
                "disposition_ids": [str(row["id"]) for row in invalidated],
                "extractor_version": extractor,
                "reason": invalidation_reason,
            },
        )
    return invalidated


def record_occurrence_extraction_disposition(
    self,
    *,
    source_chunk_id: str,
    extractor_version: str,
    expected_snapshot_sha256: str | None = None,
    disposition: str,
    predicate_keys: Sequence[str] = (),
    claim_ids: Sequence[str] = (),
    occurrence_ids: Sequence[str] = (),
    metadata_json: Mapping[str, object] | None = None,
    actor_type: str = "system",
) -> tuple[VNextRow, bool]:
    """Record one deterministic scan result for the current chunk snapshot."""

    _lock_occurrence_graph_mutation(self)
    extractor = " ".join(extractor_version.split()).strip()
    if not extractor or len(extractor) > 120:
        raise ValueError("extractor_version must contain 1 to 120 characters")
    if disposition not in {
        "accepted_occurrences",
        "unresolved_claims",
        "no_occurrence",
    }:
        raise ValueError("invalid occurrence extraction disposition")
    predicates = _canonical_text_values(predicate_keys, field="predicate_keys")
    claims = _canonical_text_values(
        claim_ids,
        field="claim_ids",
        uuid_values=True,
    )
    occurrences = _canonical_text_values(
        occurrence_ids,
        field="occurrence_ids",
        uuid_values=True,
    )
    if disposition == "no_occurrence" and predicates:
        raise ValueError("no_occurrence cannot include predicate keys")
    chunk = _current_extraction_chunk(self, str(source_chunk_id))
    if chunk is None:
        raise ContinuityStoreInvariantError("occurrence extraction disposition requires a current owned chunk")
    snapshot_sha256 = _extraction_snapshot_sha256(chunk)
    if expected_snapshot_sha256 is not None and expected_snapshot_sha256 != snapshot_sha256:
        raise ContinuityStoreInvariantError("extraction disposition snapshot CAS is stale")
    _validate_extraction_references(
        self,
        source_chunk_id=str(source_chunk_id),
        disposition=disposition,
        claim_ids=claims,
        occurrence_ids=occurrences,
        require_reviewed_occurrences=False,
    )
    metadata = dict(metadata_json or {})
    claim_facts = _current_disposition_claim_facts(self, claims)
    supplied_claim_facts = metadata.get("claim_facts_digests")
    if supplied_claim_facts is not None and supplied_claim_facts != claim_facts:
        raise ContinuityStoreInvariantError("extraction disposition supplied stale claim facts")
    metadata["claim_facts_digests"] = claim_facts
    memory_facts = _current_disposition_memory_facts(
        self,
        str(source_chunk_id),
    )
    supplied_memory_facts = metadata.get("memory_facts_digests")
    if supplied_memory_facts is not None and supplied_memory_facts != memory_facts:
        raise ContinuityStoreInvariantError("extraction disposition supplied stale memory facts")
    metadata["memory_facts_digests"] = memory_facts
    expected = {
        "source_id": str(chunk["source_id"]),
        "source_chunk_id": str(chunk["source_chunk_id"]),
        "snapshot_sha256": snapshot_sha256,
        "extractor_version": extractor,
        "disposition": disposition,
        "predicate_keys": predicates,
        "claim_ids": claims,
        "occurrence_ids": occurrences,
        "metadata_json": metadata,
    }
    row = self._fetch_optional_one(
        f"""
        INSERT INTO occurrence_extraction_dispositions (
          id,
          user_id,
          source_id,
          source_chunk_id,
          snapshot_sha256,
          extractor_version,
          disposition,
          predicate_keys,
          claim_ids,
          occurrence_ids,
          review_status,
          metadata_json
        )
        VALUES (
          gen_random_uuid(),
          app.current_user_id(),
          %s::uuid,
          %s::uuid,
          %s,
          %s,
          %s,
          %s,
          %s,
          %s,
          'candidate',
          %s
        )
        ON CONFLICT (
          user_id,
          source_chunk_id,
          snapshot_sha256,
          extractor_version
        ) DO NOTHING
        RETURNING {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
        """,
        (
            expected["source_id"],
            expected["source_chunk_id"],
            snapshot_sha256,
            extractor,
            disposition,
            Jsonb(predicates),
            Jsonb(claims),
            Jsonb(occurrences),
            Jsonb(metadata),
        ),
    )
    created = row is not None
    if row is None:
        row = self._fetch_one(
            "get occurrence extraction disposition",
            f"""
            SELECT {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
            FROM occurrence_extraction_dispositions
            WHERE user_id = app.current_user_id()
              AND source_chunk_id = %s::uuid
              AND snapshot_sha256 = %s
              AND extractor_version = %s
            """,
            (str(source_chunk_id), snapshot_sha256, extractor),
        )
        mismatches = [field for field, value in expected.items() if not _same_value(row.get(field), value)]
        if mismatches:
            if row.get("review_status") != "candidate":
                invalidate_occurrence_extraction_dispositions(
                    self,
                    source_chunk_id=str(source_chunk_id),
                    reason="Current chunk extraction facts changed.",
                    extractor_version=extractor,
                    actor_type=actor_type,
                )
                row = self._fetch_one(
                    "get invalidated occurrence extraction disposition",
                    f"""
                    SELECT {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
                    FROM occurrence_extraction_dispositions
                    WHERE user_id = app.current_user_id()
                      AND id = %s::uuid
                    """,
                    (str(row["id"]),),
                )
            replaced = self._fetch_optional_one(
                f"""
                UPDATE occurrence_extraction_dispositions
                SET disposition = %s,
                    predicate_keys = %s,
                    claim_ids = %s,
                    occurrence_ids = %s,
                    metadata_json = %s,
                    review_version = review_version + 1,
                    updated_at = clock_timestamp()
                WHERE user_id = app.current_user_id()
                  AND id = %s::uuid
                  AND review_status = 'candidate'
                  AND review_version = %s
                RETURNING {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
                """,
                (
                    disposition,
                    Jsonb(predicates),
                    Jsonb(claims),
                    Jsonb(occurrences),
                    Jsonb(metadata),
                    row["id"],
                    int(cast(int, row["review_version"])),
                ),
            )
            if replaced is None:
                raise ContinuityStoreInvariantError("extraction disposition replacement lost its lifecycle CAS")
            row = replaced
            self._append_mutation_event(
                event_type="occurrence.extraction_disposition_updated",
                actor_type=actor_type,
                target_type="source_chunk",
                target_id=str(source_chunk_id),
                payload={
                    "disposition_id": row["id"],
                    "disposition": disposition,
                    "extractor_version": extractor,
                    "snapshot_sha256": snapshot_sha256,
                },
            )
            invalidate_occurrence_coverage(
                self,
                reason="Current chunk extraction accounting changed.",
                actor_type=actor_type,
            )
        elif row.get("review_status") == "candidate":
            invalidate_occurrence_coverage(
                self,
                reason="Current chunk extraction accounting is unreviewed.",
                actor_type=actor_type,
            )
        return row, False
    self._append_mutation_event(
        event_type="occurrence.extraction_disposition_recorded",
        actor_type=actor_type,
        target_type="source_chunk",
        target_id=str(source_chunk_id),
        payload={
            "disposition_id": row["id"],
            "disposition": disposition,
            "extractor_version": extractor,
            "snapshot_sha256": snapshot_sha256,
        },
    )
    invalidate_occurrence_coverage(
        self,
        reason="A current chunk needs extraction review.",
        actor_type=actor_type,
    )
    return row, created


def review_occurrence_extraction_disposition(
    self,
    *,
    disposition_id: str,
    action: str,
    reviewer_id: str,
    reason: str,
    expected_review_version: int = 0,
    actor_type: str = "user",
) -> VNextRow:
    """CAS-sign one chunk extraction result against its current content."""

    _lock_occurrence_graph_mutation(self)
    if action not in {"accepted", "rejected"}:
        raise ValueError("invalid extraction disposition review action")
    reviewer = reviewer_id.strip()
    review_reason = reason.strip()
    if not reviewer or not review_reason:
        raise ValueError("extraction disposition review requires reviewer_id and reason")
    current = self._fetch_optional_one(
        f"""
        SELECT {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
        FROM occurrence_extraction_dispositions
        WHERE user_id = app.current_user_id()
          AND id = %s::uuid
        """,
        (str(disposition_id),),
    )
    if current is None:
        raise ContinuityStoreInvariantError("extraction disposition review did not find an owned row")
    if (
        current.get("review_status") != "candidate"
        or int(cast(int, current["review_version"])) != expected_review_version
    ):
        raise ContinuityStoreInvariantError("extraction disposition review lost its lifecycle CAS")
    chunk = _current_extraction_chunk(self, str(current["source_chunk_id"]))
    if chunk is None or _extraction_snapshot_sha256(chunk) != current["snapshot_sha256"]:
        raise ContinuityStoreInvariantError("extraction disposition snapshot is stale")
    if action == "accepted":
        _validate_extraction_references(
            self,
            source_chunk_id=str(current["source_chunk_id"]),
            disposition=str(current["disposition"]),
            claim_ids=cast(Sequence[str], current["claim_ids"]),
            occurrence_ids=cast(Sequence[str], current["occurrence_ids"]),
            require_reviewed_occurrences=True,
        )
        _require_current_disposition_claim_facts(self, current)
        _require_current_disposition_memory_facts(self, current)
    next_version = expected_review_version + 1
    receipt = _extraction_review_receipt_digest(
        current,
        action=action,
        reviewer_id=reviewer,
        reason=review_reason,
        review_version=next_version,
    )
    row = self._fetch_optional_one(
        f"""
        UPDATE occurrence_extraction_dispositions
        SET review_status = %s,
            reviewed_at = clock_timestamp(),
            reviewer_id = %s,
            review_reason = %s,
            review_version = review_version + 1,
            review_receipt_digest = %s,
            updated_at = clock_timestamp()
        WHERE user_id = app.current_user_id()
          AND id = %s::uuid
          AND review_status = 'candidate'
          AND review_version = %s
          AND source_id = %s::uuid
          AND source_chunk_id = %s::uuid
          AND snapshot_sha256 = %s
          AND extractor_version = %s
          AND disposition = %s
          AND predicate_keys = %s
          AND claim_ids = %s
          AND occurrence_ids = %s
          AND metadata_json = %s
        RETURNING {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
        """,
        (
            action,
            reviewer,
            review_reason,
            receipt,
            str(disposition_id),
            expected_review_version,
            str(current["source_id"]),
            str(current["source_chunk_id"]),
            str(current["snapshot_sha256"]),
            str(current["extractor_version"]),
            str(current["disposition"]),
            Jsonb(list(cast(Sequence[object], current["predicate_keys"]))),
            Jsonb(list(cast(Sequence[object], current["claim_ids"]))),
            Jsonb(list(cast(Sequence[object], current["occurrence_ids"]))),
            Jsonb(dict(cast(Mapping[str, object], current["metadata_json"]))),
        ),
    )
    if row is None:
        raise ContinuityStoreInvariantError("extraction disposition review lost its lifecycle CAS")
    self._append_mutation_event(
        event_type="occurrence.extraction_disposition_reviewed",
        actor_type=actor_type,
        actor_id=reviewer,
        target_type="source_chunk",
        target_id=str(row["source_chunk_id"]),
        payload={
            "action": action,
            "disposition_id": row["id"],
            "disposition": row["disposition"],
            "review_version": row["review_version"],
            "review_receipt_digest": row["review_receipt_digest"],
            "reason": review_reason,
        },
    )
    invalidate_occurrence_coverage(
        self,
        reason="A chunk extraction disposition review changed.",
        actor_type=actor_type,
        actor_id=reviewer,
    )
    return row


def summarize_occurrence_extraction_accounting(
    self,
    *,
    extractor_version: str,
    source_ids: Sequence[str] | None = None,
) -> VNextRow:
    """Return a deterministic, review-gated current-corpus accounting proof."""

    extractor = " ".join(extractor_version.split()).strip()
    if not extractor:
        raise ValueError("extractor_version is required")
    normalized_source_ids = _canonical_text_values(
        source_ids,
        field="source_ids",
        uuid_values=True,
    )
    authoritative_source_ids = (
        normalized_source_ids
        if source_ids is not None
        else [
            str(row["id"])
            for row in self._fetch_all(
                """
                SELECT id
                FROM sources
                WHERE user_id = app.current_user_id()
                  AND deleted_at IS NULL
                ORDER BY id ASC
                """
            )
        ]
    )
    if source_ids is not None and not normalized_source_ids:
        chunks: list[VNextRow] = []
    else:
        chunks = self._fetch_all(
            f"""
            SELECT
              source.id AS source_id,
              source.content_hash AS source_content_hash,
              source.domain AS source_domain,
              source.sensitivity AS source_sensitivity,
              source.title AS source_title,
              source.source_created_at,
              source.metadata_json ->> 'session_date'
                AS source_session_date,
              source.metadata_json ->> 'provenance_role'
                AS source_provenance_role,
              ({_OCCURRENCE_SOURCE_SCOPE_SQL}) AS source_project_scope,
              chunk.id AS source_chunk_id,
              chunk.chunk_index,
              chunk.text AS chunk_text
            FROM source_chunks AS chunk
            JOIN sources AS source
              ON source.id = chunk.source_id
             AND source.user_id = chunk.user_id
            WHERE chunk.user_id = app.current_user_id()
              AND source.deleted_at IS NULL
              AND (
                %s::uuid[] IS NULL
                OR source.id = ANY(%s::uuid[])
              )
            ORDER BY chunk.id ASC
            """,
            (
                normalized_source_ids if source_ids is not None else None,
                normalized_source_ids if source_ids is not None else None,
            ),
        )
    chunk_ids = [str(row["source_chunk_id"]) for row in chunks]
    dispositions = (
        self._fetch_all(
            f"""
            SELECT {_column_sql(OCCURRENCE_EXTRACTION_DISPOSITION_COLUMNS)}
            FROM occurrence_extraction_dispositions
            WHERE user_id = app.current_user_id()
              AND extractor_version = %s
              AND source_chunk_id = ANY(%s::uuid[])
            ORDER BY source_chunk_id ASC, updated_at DESC, id DESC
            """,
            (extractor, chunk_ids),
        )
        if chunk_ids
        else []
    )
    by_chunk: dict[str, list[VNextRow]] = {}
    for row in dispositions:
        by_chunk.setdefault(str(row["source_chunk_id"]), []).append(row)
    actual_source_ids = sorted({str(row["source_id"]) for row in chunks})
    missing_source_ids = sorted(set(authoritative_source_ids) - set(actual_source_ids))
    items: list[VNextRow] = [
        {
            "source_id": source_id,
            "source_chunk_id": None,
            "snapshot_sha256": None,
            "status": "missing",
        }
        for source_id in missing_source_ids
    ]
    missing_count = len(missing_source_ids)
    stale_count = 0
    unresolved_count = 0
    unreviewed_count = 0
    invalid_accepted_count = 0
    invalid_receipt_count = 0
    reviewed_current_count = 0
    snapshot_parts: list[str] = []
    disposition_parts: list[str] = []
    for chunk in chunks:
        chunk_id = str(chunk["source_chunk_id"])
        snapshot = _extraction_snapshot_sha256(chunk)
        snapshot_parts.append(f"{chunk_id}:{snapshot}")
        all_rows = by_chunk.get(chunk_id, [])
        current = next(
            (row for row in all_rows if row.get("snapshot_sha256") == snapshot),
            None,
        )
        item: VNextRow = {
            "source_id": str(chunk["source_id"]),
            "source_chunk_id": chunk_id,
            "snapshot_sha256": snapshot,
        }
        if current is None:
            if all_rows:
                stale_count += 1
                item["status"] = "stale"
            else:
                missing_count += 1
                item["status"] = "missing"
            items.append(item)
            continue
        item.update(
            {
                "disposition_id": str(current["id"]),
                "disposition": current["disposition"],
                "review_status": current["review_status"],
                "review_version": current["review_version"],
                "predicate_keys": current["predicate_keys"],
                "claim_ids": current["claim_ids"],
                "occurrence_ids": current["occurrence_ids"],
            }
        )
        receipt_valid = False
        if current.get("review_status") == "accepted":
            reviewer = str(current.get("reviewer_id") or "").strip()
            review_reason = str(current.get("review_reason") or "").strip()
            review_version = int(cast(int, current.get("review_version") or 0))
            if reviewer and review_reason and review_version > 0:
                expected_receipt = _extraction_review_receipt_digest(
                    current,
                    action="accepted",
                    reviewer_id=reviewer,
                    reason=review_reason,
                    review_version=review_version,
                )
                receipt_valid = current.get("review_receipt_digest") == expected_receipt
                if receipt_valid:
                    try:
                        _require_current_disposition_claim_facts(self, current)
                        _require_current_disposition_memory_facts(self, current)
                    except (ContinuityStoreInvariantError, ValueError):
                        receipt_valid = False
        if receipt_valid:
            reviewed_current_count += 1
            disposition_parts.append(f"{current['id']}:{current['review_receipt_digest']}")
        elif current.get("review_status") == "accepted":
            invalid_receipt_count += 1
            item["status"] = "invalid_receipt"
        else:
            unreviewed_count += 1
            item["status"] = "unreviewed"
        if current.get("disposition") == "unresolved_claims":
            unresolved_count += 1
            if receipt_valid:
                try:
                    _validate_extraction_references(
                        self,
                        source_chunk_id=chunk_id,
                        disposition="unresolved_claims",
                        claim_ids=cast(Sequence[str], current["claim_ids"]),
                        occurrence_ids=cast(Sequence[str], current["occurrence_ids"]),
                        require_reviewed_occurrences=True,
                    )
                except (ContinuityStoreInvariantError, ValueError):
                    invalid_accepted_count += 1
                    item["status"] = "invalid_accepted"
                else:
                    item["status"] = "complete_with_unresolved_claims"
            elif current.get("review_status") != "accepted":
                item["status"] = "unresolved"
        elif current.get("disposition") == "accepted_occurrences" and receipt_valid:
            try:
                _validate_extraction_references(
                    self,
                    source_chunk_id=chunk_id,
                    disposition="accepted_occurrences",
                    claim_ids=cast(Sequence[str], current["claim_ids"]),
                    occurrence_ids=cast(Sequence[str], current["occurrence_ids"]),
                    require_reviewed_occurrences=True,
                )
            except (ContinuityStoreInvariantError, ValueError):
                invalid_accepted_count += 1
                item["status"] = "invalid_accepted"
            else:
                item["status"] = "complete"
        elif receipt_valid:
            item["status"] = "complete"
        items.append(item)
    unanchored_memories = (
        self._fetch_all(
            f"""
            SELECT memory.id
            FROM memories AS memory
            WHERE memory.user_id = app.current_user_id()
              AND memory.deleted_at IS NULL
              AND memory.status IN (
                'candidate',
                'active',
                'accepted',
                'needs_review',
                'private_only',
                'stale'
              )
              AND NOT EXISTS (
                SELECT 1
                FROM source_chunks AS chunk
                JOIN sources AS source
                  ON source.id = chunk.source_id
                 AND source.user_id = chunk.user_id
                WHERE chunk.user_id = memory.user_id
                  AND chunk.id::text
                    = memory.metadata_json ->> 'source_chunk_id'
                  AND NOT (
                    memory.metadata_json ? 'occurrence_proposals'
                  )
                  AND (
                    COALESCE(
                      jsonb_typeof(
                        memory.metadata_json -> 'occurrence_proposal'
                      ),
                      'null'
                    ) = 'null'
                    OR (
                      jsonb_typeof(
                        memory.metadata_json -> 'occurrence_proposal'
                      ) = 'object'
                      AND chunk.id::text
                        = memory.metadata_json
                          #>> '{{occurrence_proposal,source_chunk_id}}'
                    )
                  )
                  AND source.deleted_at IS NULL
                  AND source.domain = memory.domain
                  AND source.sensitivity = memory.sensitivity
                  AND ({_OCCURRENCE_SOURCE_SCOPE_SQL})
                    = ({_OCCURRENCE_MEMORY_SCOPE_SQL})
              )
            ORDER BY memory.id ASC
            """
        )
        if source_ids is None
        else []
    )
    unanchored_memory_ids = [str(row["id"]) for row in unanchored_memories]
    accounted_memories = (
        self._fetch_all(
            f"""
            SELECT
              memory.id,
              memory.user_id,
              memory.memory_key,
              memory.value,
              memory.status,
              memory.source_event_ids,
              memory.memory_type,
              memory.valid_from,
              memory.valid_to,
              memory.title,
              memory.canonical_text,
              memory.summary,
              memory.domain,
              memory.sensitivity,
              memory.first_seen_at,
              memory.last_seen_at,
              memory.metadata_json,
              memory.project_id
            FROM memories AS memory
            WHERE memory.user_id = app.current_user_id()
              AND memory.deleted_at IS NULL
              AND memory.status IN (
                'candidate',
                'active',
                'accepted',
                'needs_review',
                'private_only',
                'stale'
              )
              AND EXISTS (
                SELECT 1
                FROM source_chunks AS chunk
                JOIN sources AS source
                  ON source.id = chunk.source_id
                 AND source.user_id = chunk.user_id
                WHERE chunk.user_id = memory.user_id
                  AND chunk.id::text
                    = memory.metadata_json ->> 'source_chunk_id'
                  AND NOT (
                    memory.metadata_json ? 'occurrence_proposals'
                  )
                  AND (
                    COALESCE(
                      jsonb_typeof(
                        memory.metadata_json -> 'occurrence_proposal'
                      ),
                      'null'
                    ) = 'null'
                    OR (
                      jsonb_typeof(
                        memory.metadata_json -> 'occurrence_proposal'
                      ) = 'object'
                      AND chunk.id::text
                        = memory.metadata_json
                          #>> '{{occurrence_proposal,source_chunk_id}}'
                    )
                  )
                  AND source.deleted_at IS NULL
                  AND source.domain = memory.domain
                  AND source.sensitivity = memory.sensitivity
                  AND ({_OCCURRENCE_SOURCE_SCOPE_SQL})
                    = ({_OCCURRENCE_MEMORY_SCOPE_SQL})
              )
            ORDER BY memory.id ASC
            """
        )
        if source_ids is None
        else []
    )
    memory_snapshot_parts = [
        f"memory:{row['id']}:{occurrence_memory_carrier_facts_digest(row)}" for row in accounted_memories
    ]
    snapshot_digest = hashlib.sha256("|".join(snapshot_parts + memory_snapshot_parts).encode("utf-8")).hexdigest()
    disposition_digest = hashlib.sha256("|".join(sorted(disposition_parts)).encode("utf-8")).hexdigest()
    complete = (
        bool(chunks)
        and reviewed_current_count == len(chunks)
        and missing_count == 0
        and stale_count == 0
        and unreviewed_count == 0
        and invalid_accepted_count == 0
        and invalid_receipt_count == 0
        and not unanchored_memory_ids
    )
    return {
        "extractor_version": extractor,
        "source_ids": actual_source_ids,
        "source_chunk_ids": chunk_ids,
        "current_chunk_count": len(chunks),
        "reviewed_current_count": reviewed_current_count,
        "missing_count": missing_count,
        "stale_count": stale_count,
        "unresolved_count": unresolved_count,
        "unreviewed_count": unreviewed_count,
        "invalid_accepted_count": invalid_accepted_count,
        "invalid_receipt_count": invalid_receipt_count,
        "unanchored_memory_count": len(unanchored_memory_ids),
        "unanchored_memory_ids": unanchored_memory_ids,
        "accounted_memory_count": len(accounted_memories),
        "accounted_memory_ids": [str(row["id"]) for row in accounted_memories],
        "snapshot_digest": snapshot_digest,
        "disposition_digest": disposition_digest,
        "complete": complete,
        "items": items,
    }


def list_occurrence_evidence_for_units(
    self,
    occurrence_ids: Sequence[str],
    *,
    as_of: datetime | None = None,
    after_id: str | None = None,
    limit: int = 200,
) -> list[VNextRow]:
    if limit < 1:
        raise ValueError("limit must be positive")
    ids = list(dict.fromkeys(str(value) for value in occurrence_ids if value))
    if not ids:
        return []
    if len(ids) > 200:
        raise ValueError("occurrence evidence batch cannot exceed 200 units")
    stable_as_of = as_of or datetime.now(UTC)
    return self._fetch_all(
        f"""
        SELECT
          {_column_sql(OCCURRENCE_EVIDENCE_COLUMNS, prefix="evidence.")},
          unit.count_key AS occurrence_count_key,
          unit.domain AS occurrence_domain,
          unit.sensitivity AS occurrence_sensitivity,
          unit.project_scope AS occurrence_project_scope,
          unit.review_receipt_action AS occurrence_review_receipt_action,
          unit.claim_id AS occurrence_claim_id,
          evidence_claim.review_status AS evidence_claim_review_status,
          evidence_claim.resolution_status AS evidence_claim_resolution_status,
          evidence_claim.resolution_decision AS evidence_claim_resolution_decision,
          evidence_claim.resolved_occurrence_id
            AS evidence_claim_resolved_occurrence_id
        FROM occurrence_evidence AS evidence
        JOIN occurrence_units AS unit
          ON unit.id = evidence.occurrence_id
         AND unit.user_id = evidence.user_id
        JOIN occurrence_claims AS evidence_claim
          ON evidence_claim.id = evidence.claim_id
         AND evidence_claim.user_id = evidence.user_id
        WHERE evidence.user_id = app.current_user_id()
          AND evidence.occurrence_id = ANY(%s::uuid[])
          AND unit.review_status = 'accepted'
          AND unit.identity_status = 'resolved'
          AND unit.unit_value = 1
          AND evidence.evidence_role = 'supports'
          AND evidence.review_status = 'accepted'
          AND evidence.unit_review_receipt_digest = unit.review_receipt_digest
          AND (
            evidence.source_id IS NULL
            OR EXISTS (
              SELECT 1 FROM sources AS source
              WHERE source.id = evidence.source_id
                AND source.user_id = evidence.user_id
                AND source.deleted_at IS NULL
                AND source.domain = unit.domain
                AND source.sensitivity = unit.sensitivity
                AND ({_OCCURRENCE_SOURCE_SCOPE_SQL}) = unit.project_scope
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
                AND source.domain = unit.domain
                AND source.sensitivity = unit.sensitivity
                AND ({_OCCURRENCE_SOURCE_SCOPE_SQL}) = unit.project_scope
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
                  OR memory.valid_to >= %s::timestamptz
                )
                AND memory.domain = unit.domain
                AND memory.sensitivity = unit.sensitivity
                AND ({_OCCURRENCE_MEMORY_SCOPE_SQL}) = unit.project_scope
            )
          )
          AND (%s::uuid IS NULL OR evidence.id > %s::uuid)
        ORDER BY evidence.id ASC
        LIMIT %s
        """,
        (ids, stable_as_of, after_id, after_id, min(limit, 200)),
    )


__all__ = [
    "lock_source_occurrence_envelope",
    "get_source_chunks_by_ids",
    "get_source_chunk_for_occurrence_accounting",
    "list_memories_for_source_chunk",
    "list_occurrence_claims_for_source_chunk",
    "list_accepted_occurrence_extraction_dispositions_for_claims",
    "write_occurrence_memory_metadata",
    "invalidate_occurrence_extraction_dispositions",
    "record_occurrence_extraction_disposition",
    "review_occurrence_extraction_disposition",
    "summarize_occurrence_extraction_accounting",
    "list_occurrence_evidence_for_units",
]
