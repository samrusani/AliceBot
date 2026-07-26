"""Pure contracts for review-gated occurrence counting.

This module deliberately has no store, provider, or retrieval dependencies.
It creates deterministic write-time proposal identities from structured
evidence and reconstructs reader counts only from signed, reviewed one-unit
rows. Prose alone is never promoted into an occurrence identity here.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import cast
import unicodedata

from alicebot_api.vnext_occurrence_predicates import (
    OCCURRENCE_AGGREGATION_BASES,
    OCCURRENCE_PREDICATE_TAXONOMY,
    canonicalize_occurrence_accounting_metadata,
    canonicalize_occurrence_claim_aggregation,
    canonicalize_occurrence_predicate,
    canonicalize_occurrence_unit_aggregation,
    occurrence_claim_facts_digest,
    occurrence_coverage_review_receipt_digest,
    occurrence_evidence_facts_digest,
    occurrence_evidence_review_receipt_digest,
    occurrence_extraction_disposition_review_receipt_digest,
    occurrence_aggregation_digest,
    occurrence_predicate_digest,
    occurrence_unit_review_receipt_digest,
)
from alicebot_api.vnext_project_scope import project_scope_identity
from alicebot_api.vnext_repositories import JsonObject


OCCURRENCE_AGGREGATION_KIND = "occurrence_count"
OCCURRENCE_AGGREGATION_UNIT = "reviewed_occurrence_units"
OCCURRENCE_OBJECT_AGGREGATION_UNIT = "reviewed_object_members"
OCCURRENCE_AGGREGATION_UNITS = {
    "event_instance": OCCURRENCE_AGGREGATION_UNIT,
    "object_member": OCCURRENCE_OBJECT_AGGREGATION_UNIT,
}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OBJECT_MEMBER_ID_PATTERN = re.compile(r"^object:v1:[0-9a-f]{64}$")
_COUNT_KEY_SEPARATORS = re.compile(r"[^\w]+", re.UNICODE)


def _normalized_text(value: object, *, field_name: str) -> str:
    text = " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).strip()
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    return text


def normalize_count_key(value: object) -> str:
    """Return the stable lexical predicate used by claims and queries."""

    text = _normalized_text(value, field_name="count_key").casefold()
    normalized = " ".join(part for part in _COUNT_KEY_SEPARATORS.split(text) if part)
    if not normalized:
        raise ValueError("count_key must contain a letter or number")
    return normalized


def _canonical_scope(value: object) -> tuple[str, ...]:
    return project_scope_identity(value)


def _digest_payload(namespace: str, payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        {"namespace": namespace, **payload},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = " ".join(unicodedata.normalize("NFKC", str(value)).split()).strip()
    return text or None


def _identity_anchor(
    *,
    external_event_id: str | None,
    external_event_namespace: str | None,
    occurred_at_start: str | None,
    occurred_at_end: str | None,
    stable_actors: tuple[str, ...],
    stable_object: str | None,
    reviewed_manual_identity: str | None,
    reviewed_date_ordinal: int | None,
) -> tuple[str, JsonObject] | None:
    if external_event_id is not None and external_event_namespace is not None:
        return (
            "external_event_id",
            {
                "external_event_id": external_event_id,
                "external_event_namespace": external_event_namespace,
            },
        )
    date_only = bool(occurred_at_start is not None and re.fullmatch(r"\d{4}-\d{2}-\d{2}", occurred_at_start))
    if occurred_at_start is not None and not date_only and (stable_actors or stable_object is not None):
        return (
            "exact_time",
            {
                "occurred_at_start": occurred_at_start,
                "occurred_at_end": occurred_at_end,
                "stable_actors": list(stable_actors),
                "stable_object": stable_object,
            },
        )
    if (
        occurred_at_start is not None
        and date_only
        and reviewed_date_ordinal
        and (stable_actors or stable_object is not None)
    ):
        return (
            "date_and_ordinal",
            {
                "occurred_on": occurred_at_start,
                "reviewed_date_ordinal": reviewed_date_ordinal,
                "stable_actors": list(stable_actors),
                "stable_object": stable_object,
            },
        )
    if reviewed_manual_identity is not None:
        return "reviewed_manual", {"reviewed_manual_identity": reviewed_manual_identity}
    return None


def _compatible_existing_occurrence(
    existing: Mapping[str, object],
    *,
    occurrence_key: str,
    count_key: str,
    predicate_json: Mapping[str, object],
    domain: str,
    sensitivity: str,
    project_scope: tuple[str, ...],
) -> bool:
    try:
        existing_count_key = normalize_count_key(existing.get("count_key"))
        existing_predicate = canonicalize_occurrence_predicate(
            existing.get("predicate_json"),
            allow_claim_ops=False,
        )
    except (TypeError, ValueError):
        return False
    return bool(
        str(existing.get("occurrence_key") or "") == occurrence_key
        and existing_count_key == count_key
        and existing_predicate == predicate_json
        and str(existing.get("domain") or "unknown") == domain
        and str(existing.get("sensitivity") or "unknown") == sensitivity
        and _canonical_scope(existing.get("project_scope")) == project_scope
        and existing.get("review_status") == "accepted"
        and existing.get("identity_status") == "resolved"
        and existing.get("superseded_by") is None
        and existing.get("retired_at") is None
        and existing.get("id")
    )


def build_occurrence_proposal(
    *,
    canonical_text: str,
    count_key: str,
    predicate_json: Mapping[str, object],
    aggregation_json: Mapping[str, object],
    object_member_identity: str | None = None,
    object_member_identities: Sequence[str] = (),
    domain: str = "unknown",
    sensitivity: str = "unknown",
    project_scope: Sequence[str] = (),
    occurred_at_start: str | None = None,
    occurred_at_end: str | None = None,
    external_event_id: str | None = None,
    external_event_namespace: str | None = None,
    stable_actors: Sequence[str] = (),
    stable_object: str | None = None,
    reviewed_manual_identity: str | None = None,
    reviewed_date_ordinal: int | None = None,
    quantity_min: int = 1,
    quantity_max: int | None = 1,
    memory_id: str | None = None,
    source_id: str | None = None,
    source_chunk_id: str | None = None,
    quote: str | None = None,
    existing_occurrence: Mapping[str, object] | None = None,
) -> JsonObject:
    """Build one idempotent claim plus zero or more one-unit proposals.

    Strong identity requires a stable external event ID, an explicit event
    time plus stable actor/object, or a separately reviewed manual identity.
    Weak evidence stays ambiguous and produces no countable unit proposal.
    """

    text = _normalized_text(canonical_text, field_name="canonical_text")
    normalized_count_key = normalize_count_key(count_key)
    predicate = canonicalize_occurrence_predicate(
        predicate_json,
        allow_claim_ops=True,
    )
    aggregation = canonicalize_occurrence_claim_aggregation(aggregation_json)
    if isinstance(object_member_identities, (str, bytes)):
        raise ValueError("object_member_identities must be a sequence of stable keys")
    raw_object_members: list[object] = list(object_member_identities)
    if object_member_identity is not None:
        raw_object_members.append(object_member_identity)
    if len(raw_object_members) > 31:
        raise ValueError("object_member_identities must contain at most 31 stable keys")
    if any(
        not isinstance(value, str) or _OBJECT_MEMBER_ID_PATTERN.fullmatch(value) is None for value in raw_object_members
    ):
        raise ValueError("object members require exact object:v1:<64 lowercase hex> stable keys")
    reviewed_object_members = sorted(cast(list[str], raw_object_members))
    if len(reviewed_object_members) != len(set(reviewed_object_members)):
        raise ValueError("object_member_identities must be unique")
    normalized_domain = _normalized_text(domain or "unknown", field_name="domain")
    normalized_sensitivity = _normalized_text(sensitivity or "unknown", field_name="sensitivity")
    scope = _canonical_scope(project_scope)
    raw_start = _optional_text(occurred_at_start)
    raw_end = _optional_text(occurred_at_end)
    start = raw_start
    end = raw_end
    parsed_start = _parse_datetime(start)
    parsed_end = _parse_datetime(end)
    if start is not None and parsed_start is None:
        raise ValueError("occurred_at_start must be an ISO-8601 date or timestamp")
    if end is not None and parsed_end is None:
        raise ValueError("occurred_at_end must be an ISO-8601 date or timestamp")
    if parsed_start is not None and raw_start is not None and "T" in raw_start:
        start = parsed_start.isoformat().replace("+00:00", "Z")
    if parsed_end is not None and raw_end is not None and "T" in raw_end:
        end = parsed_end.isoformat().replace("+00:00", "Z")
    if parsed_start is not None and parsed_end is not None and parsed_end < parsed_start:
        raise ValueError("occurred_at_end must not precede occurred_at_start")
    if isinstance(quantity_min, bool) or not isinstance(quantity_min, int) or quantity_min < 1:
        raise ValueError("quantity_min must be a positive integer")
    if quantity_max is not None and (
        isinstance(quantity_max, bool) or not isinstance(quantity_max, int) or quantity_max < quantity_min
    ):
        raise ValueError("quantity_max must be at least quantity_min")
    if quantity_max is not None and quantity_max > 1000:
        raise ValueError("quantity_max must not exceed 1000")
    if reviewed_object_members and (quantity_min != 1 or quantity_max != 1):
        raise ValueError(
            "object members require one exact event; submit multiple events as separate single-event claims"
        )
    if reviewed_date_ordinal is not None and (
        isinstance(reviewed_date_ordinal, bool)
        or not isinstance(reviewed_date_ordinal, int)
        or reviewed_date_ordinal < 1
    ):
        raise ValueError("reviewed_date_ordinal must be a positive integer")

    actors = tuple(
        sorted(
            {
                _normalized_text(value, field_name="stable_actor").casefold()
                for value in stable_actors
                if str(value or "").strip()
            }
        )
    )
    normalized_external_id = _optional_text(external_event_id)
    normalized_external_namespace = _optional_text(external_event_namespace)
    normalized_object = _optional_text(stable_object)
    normalized_manual = _optional_text(reviewed_manual_identity)
    anchor = _identity_anchor(
        external_event_id=normalized_external_id,
        external_event_namespace=normalized_external_namespace,
        occurred_at_start=start,
        occurred_at_end=end,
        stable_actors=actors,
        stable_object=normalized_object,
        reviewed_manual_identity=normalized_manual,
        reviewed_date_ordinal=reviewed_date_ordinal,
    )
    identity_basis = anchor[0] if anchor is not None else "ambiguous"
    range_kind = "at_least" if quantity_max is None else "exact" if quantity_min == quantity_max else "bounded"
    claim_key = _digest_payload(
        "occurrence-claim-v1",
        {
            "canonical_text": text,
            "count_key": normalized_count_key,
            "predicate_digest": occurrence_predicate_digest(
                predicate,
                allow_claim_ops=True,
            ),
            "aggregation_digest": occurrence_aggregation_digest(
                aggregation,
                occurrence_key=None,
            ),
            "reviewed_object_members": reviewed_object_members,
            "domain": normalized_domain,
            "sensitivity": normalized_sensitivity,
            "project_scope": list(scope),
            "occurred_at_start": start,
            "occurred_at_end": end,
            "identity_basis": identity_basis,
            "identity_anchor": anchor[1] if anchor is not None else None,
            "quantity_min": quantity_min,
            "quantity_max": quantity_max,
            "memory_id": _optional_text(memory_id),
            "source_id": _optional_text(source_id),
            "source_chunk_id": _optional_text(source_chunk_id),
        },
    )

    unit_proposals: list[JsonObject] = []
    resolution_decision = "ambiguous"
    resolved_occurrence_id: str | None = None
    if anchor is not None and range_kind == "exact" and quantity_max is not None:
        for ordinal in range(1, quantity_max + 1):
            occurrence_key = _digest_payload(
                "occurrence-unit-v1",
                {
                    "domain": normalized_domain,
                    "sensitivity": normalized_sensitivity,
                    "project_scope": list(scope),
                    "identity_basis": identity_basis,
                    "identity_anchor": anchor[1],
                    "claim_ordinal": ordinal,
                },
            )
            if predicate.get("op") != "atom":
                break
            unit_aggregation = canonicalize_occurrence_unit_aggregation(
                {
                    "schema": aggregation["schema"],
                    "members": [
                        {
                            "basis": "event_instance",
                            "identity_basis": "occurrence_key",
                            "member_identity": occurrence_key,
                        },
                        *[
                            {
                                "basis": "object_member",
                                "identity_basis": "reviewed_stable_object_v1",
                                "member_identity": member_identity,
                            }
                            for member_identity in reviewed_object_members
                        ],
                    ],
                },
                occurrence_key=occurrence_key,
                claim_aggregation=aggregation,
            )
            unit_proposals.append(
                {
                    "claim_ordinal": ordinal,
                    "occurrence_key": occurrence_key,
                    "count_key": normalized_count_key,
                    "predicate_json": predicate,
                    "canonical_text": text,
                    "aggregation_json": unit_aggregation,
                    "unit_value": 1,
                    "identity_status": "resolved",
                    "occurred_at_start": start,
                    "occurred_at_end": end,
                    "domain": normalized_domain,
                    "sensitivity": normalized_sensitivity,
                    "project_scope": list(scope),
                }
            )
        resolution_decision = "new"
        if existing_occurrence is not None:
            if (
                identity_basis != "date_and_ordinal"
                and len(unit_proposals) == 1
                and _compatible_existing_occurrence(
                    existing_occurrence,
                    occurrence_key=str(unit_proposals[0]["occurrence_key"]),
                    count_key=normalized_count_key,
                    predicate_json=predicate,
                    domain=normalized_domain,
                    sensitivity=normalized_sensitivity,
                    project_scope=scope,
                )
            ):
                resolution_decision = "link_existing"
                resolved_occurrence_id = str(existing_occurrence["id"])
                unit_proposals = []
            else:
                resolution_decision = "ambiguous"
                unit_proposals = []

    quote_text = _optional_text(quote) or text
    quote_sha256 = sha256(quote_text.encode("utf-8")).hexdigest()
    evidence_targets: list[str | None]
    if unit_proposals:
        evidence_targets = [str(unit["occurrence_key"]) for unit in unit_proposals]
    else:
        evidence_targets = [resolved_occurrence_id]
    evidence_proposals: list[JsonObject] = []
    for target in evidence_targets:
        evidence_key = _digest_payload(
            "occurrence-evidence-v1",
            {
                "claim_key": claim_key,
                "occurrence_target": target,
                "memory_id": _optional_text(memory_id),
                "source_id": _optional_text(source_id),
                "source_chunk_id": _optional_text(source_chunk_id),
                "quote_sha256": quote_sha256,
            },
        )
        evidence_proposals.append(
            {
                "evidence_key": evidence_key,
                "occurrence_key": target if unit_proposals else None,
                "occurrence_id": resolved_occurrence_id,
                "evidence_role": "supports",
                "memory_id": _optional_text(memory_id),
                "source_id": _optional_text(source_id),
                "source_chunk_id": _optional_text(source_chunk_id),
                "quote": quote_text,
                "quote_sha256": quote_sha256,
            }
        )
    return {
        "claim_key": claim_key,
        "count_key": normalized_count_key,
        "predicate_json": predicate,
        "canonical_text": text,
        "quantity_min": quantity_min,
        "quantity_max": quantity_max,
        "range_kind": range_kind,
        "resolution_decision": resolution_decision,
        "resolution_status": "pending",
        "identity_basis": identity_basis,
        "aggregation_json": aggregation,
        "identity_anchor": anchor[1] if anchor is not None else None,
        "review_status": "candidate",
        "occurred_at_start": start,
        "occurred_at_end": end,
        "domain": normalized_domain,
        "sensitivity": normalized_sensitivity,
        "project_scope": list(scope),
        "resolved_occurrence_id": resolved_occurrence_id,
        "unit_proposals": unit_proposals,
        "evidence_proposals": evidence_proposals,
    }


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _sha256_text(value: object) -> str | None:
    text = str(value or "")
    return text if _SHA256_PATTERN.fullmatch(text) is not None else None


def _nonblank_text(value: object) -> bool:
    """Mirror Python's Unicode whitespace policy for signed text fields."""

    return value is not None and bool(str(value).strip())


def _json_scalar_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = _parse_datetime(value)
        return parsed.isoformat().replace("+00:00", "Z") if parsed is not None else None
    return str(value)


def _evidence_digest(rows: Sequence[Mapping[str, object]]) -> str:
    canonical = "|".join(
        occurrence_evidence_facts_digest(row)
        for row in sorted(
            rows,
            key=lambda row: (
                str(row.get("evidence_key") or ""),
                str(row.get("id") or row.get("evidence_id") or ""),
            ),
        )
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _evidence_claim_is_authorized(
    row: Mapping[str, object],
    *,
    owner_claim_id: str,
    occurrence_id: str,
) -> bool:
    evidence_claim_id = str(row.get("claim_id") or "")
    return bool(
        _nonblank_text(evidence_claim_id)
        and (
            evidence_claim_id == owner_claim_id
            or (
                row.get("evidence_claim_review_status") == "accepted"
                and row.get("evidence_claim_resolution_status") == "resolved"
                and row.get("evidence_claim_resolution_decision") == "link_existing"
                and str(row.get("evidence_claim_resolved_occurrence_id") or "") == occurrence_id
            )
        )
    )


def _receipt_timestamp(value: object) -> str | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _coverage_receipt_is_valid(row: Mapping[str, object]) -> bool:
    """Reconstruct the store's signed coverage qualification receipt."""

    coverage_id = str(row.get("id") or "")
    user_id = str(row.get("user_id") or "")
    coverage_mode = str(row.get("coverage_mode") or "")
    historical_review_status = str(row.get("historical_review_status") or "")
    coverage_started_at = _receipt_timestamp(row.get("coverage_started_at"))
    complete_through = (
        _receipt_timestamp(row.get("complete_through")) if row.get("complete_through") is not None else None
    )
    reviewer_id = str(row.get("reviewer_id") or "")
    reason = str(row.get("review_reason") or "")
    review_version = row.get("review_version")
    receipt = _sha256_text(row.get("review_receipt_digest"))
    if (
        not _nonblank_text(coverage_id)
        or not _nonblank_text(user_id)
        or coverage_mode not in {"forward_only", "partial_history", "complete_history"}
        or historical_review_status not in {"not_reviewed", "needs_review", "reviewed"}
        or coverage_started_at is None
        or isinstance(review_version, bool)
        or not isinstance(review_version, int)
        or review_version < 1
        or not _nonblank_text(reviewer_id)
        or not _nonblank_text(reason)
        or receipt is None
    ):
        return False
    raw_accounting = row.get("metadata_json")
    try:
        if coverage_mode == "complete_history":
            accounting = canonicalize_occurrence_accounting_metadata(raw_accounting)
        else:
            if raw_accounting not in (None, {}):
                return False
            accounting = None
        expected = occurrence_coverage_review_receipt_digest(
            coverage_id=coverage_id,
            user_id=user_id,
            review_version=review_version,
            coverage_mode=coverage_mode,
            coverage_started_at=coverage_started_at,
            historical_review_status=historical_review_status,
            complete_through=complete_through,
            reviewer_id=reviewer_id,
            reason=reason,
            accounting_metadata=accounting,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return receipt == expected


def _coverage_record(
    coverage: Mapping[str, object] | None,
    *,
    requested_start: datetime | str | None,
    requested_end: datetime | str | None,
) -> JsonObject:
    row = dict(coverage or {})
    mode = str(row.get("coverage_mode") or "unavailable")
    historical = str(row.get("historical_review_status") or "not_reviewed")
    coverage_start = _parse_datetime(row.get("coverage_started_at"))
    complete_through = _parse_datetime(row.get("complete_through"))
    start = _parse_datetime(requested_start)
    end = _parse_datetime(requested_end)
    signed = _coverage_receipt_is_valid(row)
    coverage_interval_valid = bool(
        coverage_start is not None and complete_through is not None and complete_through >= coverage_start
    )
    if requested_start is not None and start is None:
        fully_covered = False
    elif requested_end is not None and end is None:
        fully_covered = False
    elif (
        mode == "complete_history"
        and historical == "reviewed"
        and signed
        and coverage_interval_valid
        and coverage_start is not None
        and complete_through is not None
        and end is not None
    ):
        fully_covered = (start is None or start >= coverage_start) and end <= complete_through
    elif mode == "forward_only" or (mode == "partial_history" and historical == "reviewed"):
        fully_covered = bool(
            signed
            and coverage_interval_valid
            and start is not None
            and end is not None
            and coverage_start is not None
            and start >= coverage_start
            and complete_through is not None
            and end <= complete_through
        )
    else:
        fully_covered = False
    legacy_gap = not fully_covered
    return {
        "id": _json_scalar_text(row.get("id")),
        "coverage_mode": mode,
        "coverage_started_at": _json_scalar_text(row.get("coverage_started_at")),
        "historical_review_status": historical,
        "complete_through": _json_scalar_text(row.get("complete_through")),
        "review_version": row.get("review_version"),
        "reviewer_id": row.get("reviewer_id"),
        "review_reason": row.get("review_reason"),
        "review_receipt_digest": row.get("review_receipt_digest"),
        "receipt_valid": signed,
        "requested_start": (requested_start.isoformat() if isinstance(requested_start, datetime) else requested_start),
        "requested_end": (requested_end.isoformat() if isinstance(requested_end, datetime) else requested_end),
        "fully_covered": fully_covered,
        "legacy_gap": legacy_gap,
    }


def build_occurrence_aggregation(
    *,
    units: Sequence[Mapping[str, object]],
    evidence: Sequence[Mapping[str, object]],
    coverage: Mapping[str, object] | None,
    accounting_summary: Mapping[str, object] | None = None,
    unresolved_claims: Sequence[Mapping[str, object]] = (),
    unresolved_dispositions: Sequence[Mapping[str, object]] = (),
    requested_start: datetime | str | None = None,
    requested_end: datetime | str | None = None,
    query_selector_keys: Sequence[str] = (),
    query_predicates: Sequence[Mapping[str, object]] = (),
    aggregation_basis: str = "event_instance",
    expected_user_id: str | None = None,
    projects: Sequence[str] = (),
    domains: Sequence[str] = (),
    sensitivity_allowed: Sequence[str] = (),
    allow_timeless_units: bool = False,
    units_saturated: bool = False,
    evidence_saturated: bool = False,
    unresolved_saturated: bool = False,
) -> JsonObject | None:
    """Reconstruct a signed projection over reviewed occurrence units.

    Selection is driven by the query formula, while the aggregate cardinality
    is the number of distinct signed member identities for the requested
    basis. Any malformed row, stale receipt, missing projection, or unknown
    unresolved-claim relation fails closed.
    """

    if (
        coverage is None
        or not isinstance(allow_timeless_units, bool)
        or aggregation_basis not in OCCURRENCE_AGGREGATION_BASES
        or not query_selector_keys
    ):
        return None
    try:
        selectors = tuple(dict.fromkeys(str(value) for value in query_selector_keys if _nonblank_text(value)))
        canonical_query_atoms = tuple(
            canonicalize_occurrence_predicate(
                value,
                allow_claim_ops=False,
            )
            for value in query_predicates
        )
    except (TypeError, ValueError):
        return None
    if not selectors or len(selectors) != len(query_selector_keys):
        return None
    selector_set = set(selectors)
    window_start = _parse_datetime(requested_start)
    window_end = _parse_datetime(requested_end)
    if (
        (requested_start is not None and window_start is None)
        or (requested_end is not None and window_end is None)
        or (window_start is not None and window_end is not None and window_end <= window_start)
    ):
        return None

    coverage_user_id = str(coverage.get("user_id") or "")
    if (
        not _nonblank_text(coverage.get("id"))
        or not _nonblank_text(coverage_user_id)
        or (coverage.get("reviewer_id") is not None and not _nonblank_text(coverage.get("reviewer_id")))
        or (coverage.get("review_reason") is not None and not _nonblank_text(coverage.get("review_reason")))
        or (expected_user_id is not None and coverage_user_id != expected_user_id)
    ):
        return None
    coverage_accounting: JsonObject | None = None
    accounting_items_by_disposition: dict[str, Mapping[str, object]] = {}
    if coverage.get("coverage_mode") == "complete_history":
        try:
            coverage_accounting = canonicalize_occurrence_accounting_metadata(coverage.get("metadata_json"))
        except (TypeError, ValueError):
            return None
        if not isinstance(accounting_summary, Mapping) or accounting_summary.get("complete") is not True:
            return None
        for field in (
            "extractor_version",
            "source_ids",
            "source_chunk_ids",
            "snapshot_digest",
            "disposition_digest",
        ):
            if accounting_summary.get(field) != coverage_accounting.get(field):
                return None
        raw_items = accounting_summary.get("items")
        if not isinstance(raw_items, Sequence) or isinstance(
            raw_items,
            (str, bytes),
        ):
            return None
        item_chunk_ids: list[str] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, Mapping):
                return None
            chunk_id = str(raw_item.get("source_chunk_id") or "")
            disposition_id = str(raw_item.get("disposition_id") or "")
            if not _nonblank_text(chunk_id) or not _nonblank_text(disposition_id):
                return None
            if disposition_id in accounting_items_by_disposition:
                return None
            item_chunk_ids.append(chunk_id)
            accounting_items_by_disposition[disposition_id] = raw_item
        if sorted(item_chunk_ids) != cast(
            list[str],
            coverage_accounting["source_chunk_ids"],
        ):
            return None
    elif accounting_summary is not None:
        # Source-accounting summaries are meaningful only when the coverage
        # receipt binds their exact digests.
        return None

    coverage_payload = _coverage_record(
        coverage,
        requested_start=requested_start,
        requested_end=requested_end,
    )
    expected_projects = set(_canonical_scope(projects))
    expected_domains = {str(value) for value in domains if str(value)}
    expected_sensitivity = {str(value) for value in sensitivity_allowed if str(value)}

    exact_query_atoms: dict[tuple[str, str], set[tuple[str, ...]]] = defaultdict(set)
    for atom in canonical_query_atoms:
        action = str(cast(Mapping[str, object], atom["action"])["leaf"])
        object_value = cast(Mapping[str, object], atom["object"])
        object_leaf = str(object_value["leaf"])
        qualifiers = tuple(cast(Sequence[str], object_value["qualifiers"]))
        exact_query_atoms[(action, object_leaf)].add(qualifiers)

    def predicate_matches_query(predicate: Mapping[str, object]) -> bool:
        signed_selectors = {str(value) for value in cast(Sequence[object], predicate["selector_keys"])}
        if not signed_selectors.intersection(selector_set):
            return False
        action = str(cast(Mapping[str, object], predicate["action"])["leaf"])
        object_value = cast(Mapping[str, object], predicate["object"])
        object_leaf = str(object_value["leaf"])
        qualifiers = tuple(cast(Sequence[str], object_value["qualifiers"]))
        wildcard = f"v1|a=exact:{action}|o=*"
        if wildcard in selector_set:
            return True
        return qualifiers in exact_query_atoms.get((action, object_leaf), set())

    by_unit: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in evidence:
        occurrence_id = str(row.get("occurrence_id") or "")
        if _nonblank_text(occurrence_id):
            by_unit[occurrence_id].append(row)

    unit_ids: list[str] = []
    member_keys: set[str] = set()
    provenance: list[JsonObject] = []
    seen_ids: set[str] = set()
    seen_occurrence_keys: set[str] = set()
    seen_claim_ordinals: set[tuple[str, int]] = set()
    seen_evidence_ids: set[str] = set()
    accepted_matching = 0
    accepted_disjoint_proven = 0
    accepted_relation_unknown = 0
    for unit in sorted(units, key=lambda row: str(row.get("id") or "")):
        occurrence_id = str(unit.get("id") or "")
        occurrence_key = str(unit.get("occurrence_key") or "")
        claim_id = str(unit.get("claim_id") or "")
        claim_ordinal = unit.get("claim_ordinal")
        user_id = str(unit.get("user_id") or "")
        unit_domain = str(unit.get("domain") or "")
        unit_sensitivity = str(unit.get("sensitivity") or "")
        unit_scope = set(_canonical_scope(unit.get("project_scope")))
        review_version = unit.get("review_version")
        review_action = str(unit.get("review_receipt_action") or "")
        reviewer_id = str(unit.get("reviewer_id") or "")
        review_reason = str(unit.get("review_reason") or "")
        review_receipt = _sha256_text(unit.get("review_receipt_digest"))
        reviewed_evidence_digest = _sha256_text(unit.get("reviewed_evidence_digest"))
        reviewed_evidence_count = unit.get("reviewed_evidence_count")
        try:
            normalize_count_key(unit.get("count_key"))
            predicate = canonicalize_occurrence_predicate(
                unit.get("predicate_json"),
                allow_claim_ops=False,
            )
            unit_aggregation = canonicalize_occurrence_unit_aggregation(
                unit.get("aggregation_json"),
                occurrence_key=occurrence_key,
            )
        except (KeyError, TypeError, ValueError):
            return None
        if (
            not _nonblank_text(occurrence_id)
            or occurrence_id in seen_ids
            or not _nonblank_text(occurrence_key)
            or occurrence_key in seen_occurrence_keys
            or not _nonblank_text(claim_id)
            or isinstance(claim_ordinal, bool)
            or not isinstance(claim_ordinal, int)
            or claim_ordinal < 1
            or (claim_id, claim_ordinal) in seen_claim_ordinals
            or not _nonblank_text(user_id)
            or user_id != coverage_user_id
            or isinstance(unit.get("unit_value"), bool)
            or unit.get("unit_value") != 1
            or unit.get("review_status") != "accepted"
            or unit.get("identity_status") != "resolved"
            or unit.get("superseded_by") is not None
            or unit.get("retired_at") is not None
            or isinstance(review_version, bool)
            or not isinstance(review_version, int)
            or review_version < 1
            or review_action
            not in {
                "accepted",
                "refresh_evidence",
                "reestablished",
            }
            or not _nonblank_text(reviewer_id)
            or not _nonblank_text(review_reason)
            or review_receipt is None
            or reviewed_evidence_digest is None
            or isinstance(reviewed_evidence_count, bool)
            or not isinstance(reviewed_evidence_count, int)
            or reviewed_evidence_count < 1
            or (expected_domains and unit_domain not in expected_domains)
            or (expected_sensitivity and unit_sensitivity not in expected_sensitivity)
            or (expected_projects and not unit_scope.intersection(expected_projects))
        ):
            return None
        raw_unit_start = unit.get("occurred_at_start")
        raw_unit_end = unit.get("occurred_at_end")
        unit_start = _parse_datetime(raw_unit_start)
        parsed_unit_end = _parse_datetime(raw_unit_end)
        if (raw_unit_start is not None and unit_start is None) or (
            raw_unit_end is not None and parsed_unit_end is None
        ):
            return None
        if unit_start is not None and parsed_unit_end is not None and parsed_unit_end < unit_start:
            return None
        if requested_start is not None or requested_end is not None:
            unit_end = parsed_unit_end or unit_start
            if unit_start is None or unit_end is None:
                if not allow_timeless_units:
                    return None
            elif (window_start is not None and unit_end < window_start) or (
                window_end is not None and unit_start >= window_end
            ):
                return None

        signed_rows = [
            row
            for row in by_unit.get(occurrence_id, ())
            if row.get("review_status") == "accepted"
            and row.get("evidence_role") == "supports"
            and row.get("unit_review_receipt_digest") == review_receipt
            and _sha256_text(row.get("review_receipt_digest")) is not None
            and _sha256_text(row.get("quote_sha256")) is not None
            and isinstance(row.get("quote"), str)
            and bool(str(row.get("quote")).strip())
            and sha256(str(row["quote"]).encode("utf-8")).hexdigest() == row.get("quote_sha256")
            and _nonblank_text(row.get("evidence_key"))
            and _nonblank_text(row.get("id") or row.get("evidence_id"))
            and _evidence_claim_is_authorized(
                row,
                owner_claim_id=claim_id,
                occurrence_id=occurrence_id,
            )
            and str(row.get("user_id") or "") == user_id
            and all(
                row.get(field) is None or _nonblank_text(row.get(field))
                for field in ("memory_id", "source_id", "source_chunk_id")
            )
            and (_nonblank_text(row.get("memory_id")) or _nonblank_text(row.get("source_id")))
            and (row.get("source_chunk_id") is None or _nonblank_text(row.get("source_id")))
        ]
        try:
            evidence_digest = _evidence_digest(signed_rows)
        except (KeyError, TypeError, ValueError):
            return None
        if len(signed_rows) != reviewed_evidence_count or evidence_digest != reviewed_evidence_digest:
            return None
        try:
            expected_unit_receipt = occurrence_unit_review_receipt_digest(
                unit,
                action=review_action,
                reviewer_id=reviewer_id,
                reason=review_reason,
                review_version=review_version,
                evidence_digest=reviewed_evidence_digest,
            )
        except (KeyError, TypeError, ValueError):
            return None
        if review_receipt != expected_unit_receipt:
            return None
        for row in signed_rows:
            evidence_id = str(row.get("id") or row.get("evidence_id") or "")
            evidence_action = str(row.get("review_receipt_action") or "")
            evidence_reviewer = str(row.get("reviewer_id") or "")
            evidence_reason = str(row.get("review_reason") or "")
            if (
                evidence_id in seen_evidence_ids
                or not _nonblank_text(evidence_id)
                or evidence_action not in {"accepted", "refresh_evidence", "reestablished"}
                or not _nonblank_text(evidence_reviewer)
                or not _nonblank_text(evidence_reason)
            ):
                return None
            try:
                expected_evidence_receipt = occurrence_evidence_review_receipt_digest(
                    row,
                    action=evidence_action,
                    reviewer_id=evidence_reviewer,
                    reason=evidence_reason,
                    unit_review_receipt_digest=review_receipt,
                )
            except (KeyError, TypeError, ValueError):
                return None
            if row.get("review_receipt_digest") != expected_evidence_receipt:
                return None
            seen_evidence_ids.add(evidence_id)

        seen_ids.add(occurrence_id)
        seen_occurrence_keys.add(occurrence_key)
        seen_claim_ordinals.add((claim_id, claim_ordinal))
        if not predicate_matches_query(predicate):
            if predicate.get("closure_complete") is True:
                accepted_disjoint_proven += 1
            else:
                accepted_relation_unknown += 1
            continue

        selected_members = [
            str(member["member_identity"])
            for member in cast(
                Sequence[Mapping[str, object]],
                unit_aggregation["members"],
            )
            if member["basis"] == aggregation_basis
        ]
        if not selected_members:
            # Cardinality is dormant unless every selected event carries the
            # explicitly reviewed projection requested by the query.
            return None
        member_keys.update(selected_members)
        accepted_matching += 1
        unit_ids.append(occurrence_id)
        provenance.append(
            {
                "occurrence_unit_id": occurrence_id,
                "counted_member_keys": sorted(selected_members),
                "review_receipt_digest": review_receipt,
                "reviewed_evidence_count": reviewed_evidence_count,
                "reviewed_evidence_digest": reviewed_evidence_digest,
                "evidence": [
                    {
                        key: (
                            _json_scalar_text(row.get(source_key))
                            if source_key
                            in {
                                "id",
                                "memory_id",
                                "source_id",
                                "source_chunk_id",
                            }
                            else row.get(source_key)
                        )
                        for key, source_key in (
                            ("evidence_id", "id"),
                            ("evidence_key", "evidence_key"),
                            ("evidence_role", "evidence_role"),
                            ("review_status", "review_status"),
                            (
                                "review_receipt_digest",
                                "review_receipt_digest",
                            ),
                            (
                                "unit_review_receipt_digest",
                                "unit_review_receipt_digest",
                            ),
                            ("memory_id", "memory_id"),
                            ("source_id", "source_id"),
                            ("source_chunk_id", "source_chunk_id"),
                            ("quote_sha256", "quote_sha256"),
                        )
                        if row.get(source_key) is not None
                    }
                    for row in sorted(
                        signed_rows,
                        key=lambda item: (
                            str(item.get("evidence_key") or ""),
                            str(item.get("id") or item.get("evidence_id") or ""),
                        ),
                    )
                ],
            }
        )

    proof_rows = list(unresolved_dispositions)
    proof_ids = [str(row.get("id") or "") for row in proof_rows]
    unresolved_ids_for_proofs = {
        str(claim.get("id") or "") for claim in unresolved_claims if _nonblank_text(claim.get("id"))
    }
    if any(not _nonblank_text(proof_id) for proof_id in proof_ids) or len(proof_ids) != len(set(proof_ids)):
        return None
    for proof in proof_rows:
        proof_claim_ids = proof.get("claim_ids")
        item = accounting_items_by_disposition.get(str(proof.get("id") or ""))
        if (
            coverage_accounting is None
            or item is None
            or proof.get("disposition") != "unresolved_claims"
            or proof.get("extractor_version") != coverage_accounting.get("extractor_version")
            or not _nonblank_text(proof.get("source_id"))
            or not _nonblank_text(proof.get("source_chunk_id"))
            or str(proof.get("source_id") or "") not in set(cast(list[str], coverage_accounting["source_ids"]))
            or str(proof.get("source_chunk_id") or "") != str(item.get("source_chunk_id") or "")
            or str(proof.get("snapshot_sha256") or "") != str(item.get("snapshot_sha256") or "")
            or item.get("status") != "complete_with_unresolved_claims"
            or not isinstance(proof_claim_ids, Sequence)
            or isinstance(proof_claim_ids, (str, bytes))
            or not unresolved_ids_for_proofs.intersection(str(value) for value in proof_claim_ids)
        ):
            return None

    def disposition_proves_claim(
        claim: Mapping[str, object],
        *,
        claim_digest: str,
    ) -> bool:
        claim_id = str(claim.get("id") or "")
        for proof in proof_rows:
            claim_ids = proof.get("claim_ids")
            metadata = proof.get("metadata_json")
            if (
                proof.get("review_status") != "accepted"
                or proof.get("disposition") != "unresolved_claims"
                or not isinstance(claim_ids, Sequence)
                or isinstance(claim_ids, (str, bytes))
                or claim_id not in {str(value) for value in claim_ids}
                or not isinstance(metadata, Mapping)
            ):
                continue
            facts = metadata.get("claim_facts_digests")
            review_version = proof.get("review_version")
            reviewer_id = str(proof.get("reviewer_id") or "")
            reason = str(proof.get("review_reason") or "")
            receipt = _sha256_text(proof.get("review_receipt_digest"))
            if (
                not isinstance(facts, Mapping)
                or set(str(key) for key in facts) != {str(value) for value in claim_ids}
                or facts.get(claim_id) != claim_digest
                or isinstance(review_version, bool)
                or not isinstance(review_version, int)
                or review_version < 1
                or not _nonblank_text(reviewer_id)
                or not _nonblank_text(reason)
                or receipt is None
            ):
                continue
            try:
                expected = occurrence_extraction_disposition_review_receipt_digest(
                    proof,
                    action="accepted",
                    reviewer_id=reviewer_id,
                    reason=reason,
                    review_version=review_version,
                )
            except (KeyError, TypeError, ValueError):
                continue
            if receipt == expected:
                return True
        return False

    unresolved_match_or_unknown = 0
    unresolved_disjoint = 0
    unresolved_finite_upper = 0
    all_blocking_unresolved_finite = True
    for claim in unresolved_claims:
        claim_id = str(claim.get("id") or "")
        claim_user_id = str(claim.get("user_id") or "")
        claim_domain = str(claim.get("domain") or "")
        claim_sensitivity = str(claim.get("sensitivity") or "")
        claim_scope = set(_canonical_scope(claim.get("project_scope")))
        try:
            normalize_count_key(claim.get("count_key"))
            predicate = canonicalize_occurrence_predicate(
                claim.get("predicate_json"),
                allow_claim_ops=True,
            )
            canonicalize_occurrence_claim_aggregation(claim.get("aggregation_json"))
            claim_digest = occurrence_claim_facts_digest(claim)
        except (KeyError, TypeError, ValueError):
            return None
        if (
            not _nonblank_text(claim_id)
            or not _nonblank_text(claim_user_id)
            or claim_user_id != coverage_user_id
            or (expected_domains and claim_domain not in expected_domains)
            or (expected_sensitivity and claim_sensitivity not in expected_sensitivity)
            or (expected_projects and not claim_scope.intersection(expected_projects))
        ):
            return None
        range_kind = str(claim.get("range_kind") or "")
        quantity_min = claim.get("quantity_min")
        quantity_max = claim.get("quantity_max")
        if (
            isinstance(quantity_min, bool)
            or not isinstance(quantity_min, int)
            or quantity_min < 1
            or range_kind not in {"exact", "bounded", "at_least"}
            or (
                quantity_max is not None
                and (isinstance(quantity_max, bool) or not isinstance(quantity_max, int) or quantity_max < quantity_min)
            )
        ):
            return None
        finite_max = (
            quantity_max
            if range_kind in {"exact", "bounded"}
            and isinstance(quantity_max, int)
            and not isinstance(quantity_max, bool)
            else None
        )
        raw_claim_start = claim.get("occurred_at_start")
        raw_claim_end = claim.get("occurred_at_end")
        claim_start = _parse_datetime(raw_claim_start)
        parsed_claim_end = _parse_datetime(raw_claim_end)
        if (raw_claim_start is not None and claim_start is None) or (
            raw_claim_end is not None and parsed_claim_end is None
        ):
            return None
        if claim_start is not None and parsed_claim_end is not None and parsed_claim_end < claim_start:
            return None
        if requested_start is not None or requested_end is not None:
            claim_end = parsed_claim_end or claim_start
            if (
                claim_start is not None
                and claim_end is not None
                and (
                    (window_start is not None and claim_end < window_start)
                    or (window_end is not None and claim_start >= window_end)
                )
            ):
                return None
        predicate_selectors = {
            str(value)
            for value in cast(
                Sequence[object],
                predicate["selector_keys"],
            )
        }
        if predicate_selectors.intersection(selector_set):
            unresolved_match_or_unknown += 1
            if finite_max is None:
                all_blocking_unresolved_finite = False
            else:
                unresolved_finite_upper += finite_max
            continue
        if (
            predicate.get("taxonomy") == OCCURRENCE_PREDICATE_TAXONOMY
            and predicate.get("closure_complete") is True
            and disposition_proves_claim(
                claim,
                claim_digest=claim_digest,
            )
        ):
            unresolved_disjoint += 1
            continue
        unresolved_match_or_unknown += 1
        if finite_max is None:
            all_blocking_unresolved_finite = False
        else:
            unresolved_finite_upper += finite_max

    saturated = bool(units_saturated or evidence_saturated or unresolved_saturated)
    exact = bool(
        coverage.get("coverage_mode") == "complete_history"
        and coverage_accounting is not None
        and accounting_summary is not None
        and coverage_payload["fully_covered"]
        and not coverage_payload["legacy_gap"]
        and not saturated
        and unresolved_match_or_unknown == 0
        and accepted_relation_unknown == 0
    )
    counted_member_keys = sorted(member_keys)
    lower_bound = len(counted_member_keys)
    if not exact and lower_bound == 0:
        return None
    range_answer = bool(
        not exact
        and coverage.get("coverage_mode") == "complete_history"
        and coverage_accounting is not None
        and accounting_summary is not None
        and coverage_payload["fully_covered"]
        and not coverage_payload["legacy_gap"]
        and not saturated
        and aggregation_basis == "event_instance"
        and unresolved_match_or_unknown > 0
        and accepted_relation_unknown == 0
        and all_blocking_unresolved_finite
    )
    answer_kind = "exact" if exact else "range" if range_answer else "at_least"
    result: JsonObject = {
        "kind": OCCURRENCE_AGGREGATION_KIND,
        "answer_kind": answer_kind,
        "exact": exact,
        "lower_bound": lower_bound,
        "upper_bound": (lower_bound if exact else lower_bound + unresolved_finite_upper if range_answer else None),
        "unit": OCCURRENCE_AGGREGATION_UNITS[aggregation_basis],
        "aggregation_basis": aggregation_basis,
        "counted_member_keys": counted_member_keys,
        "occurrence_unit_ids": unit_ids,
        "provenance": provenance,
        "coverage": coverage_payload,
        "accepted_units": {
            "matching": accepted_matching,
            "disjoint_proven": accepted_disjoint_proven,
            "relation_unknown": accepted_relation_unknown,
        },
        "unresolved_claims": {
            "count": len(unresolved_claims),
            "disjoint_proven": unresolved_disjoint,
            "matching_or_unknown": unresolved_match_or_unknown,
            "saturated": bool(unresolved_saturated),
        },
        "saturated": saturated,
        "answer_sufficient": exact,
    }
    if exact:
        result["count"] = lower_bound
    return result


__all__ = [
    "OCCURRENCE_AGGREGATION_KIND",
    "OCCURRENCE_AGGREGATION_UNIT",
    "OCCURRENCE_AGGREGATION_UNITS",
    "OCCURRENCE_OBJECT_AGGREGATION_UNIT",
    "build_occurrence_aggregation",
    "build_occurrence_proposal",
    "normalize_count_key",
]
