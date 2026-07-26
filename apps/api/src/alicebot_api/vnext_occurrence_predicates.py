"""Canonical, bounded predicates and review receipts for occurrence counting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
import re
from typing import cast
from uuid import UUID

from alicebot_api.vnext_repositories import JsonObject


OCCURRENCE_PREDICATE_SCHEMA = "occurrence_predicate_v1"
OCCURRENCE_PREDICATE_TAXONOMY = "alice-occurrence-exact-v1"
OCCURRENCE_AGGREGATION_SCHEMA = "occurrence_aggregation_v1"
OCCURRENCE_AGGREGATION_BASES = frozenset({"event_instance", "object_member"})
OCCURRENCE_AGGREGATION_IDENTITY_BASES = frozenset(
    {"occurrence_key", "reviewed_stable_object_v1"}
)
MAX_OCCURRENCE_PREDICATE_ALTERNATIVES = 8
MAX_OCCURRENCE_PREDICATE_ANCESTORS = 8
MAX_OCCURRENCE_PREDICATE_QUALIFIERS = 8
MAX_OCCURRENCE_PREDICATE_SELECTOR_KEYS = 128
MAX_OCCURRENCE_PREDICATE_COMPONENT_LENGTH = 80
MAX_OCCURRENCE_AGGREGATION_MEMBERS = 32
MAX_OCCURRENCE_MEMBER_IDENTITY_LENGTH = 500
MAX_OCCURRENCE_MEMBER_IDENTITY_BASIS_LENGTH = 200

_COMPONENT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$")
_SELECTOR_RE = re.compile(
    r"^v1\|a=exact:(?P<action>[^|]+)"
    r"\|o=(?:(?P<wildcard>\*)|exact:(?P<object>[^|]+))$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVIEWED_OBJECT_MEMBER_RE = re.compile(r"^object:v1:[0-9a-f]{64}$")


def _component(value: object, *, field: str) -> str:
    text = str(value)
    if not 1 <= len(text) <= MAX_OCCURRENCE_PREDICATE_COMPONENT_LENGTH:
        raise ValueError(f"{field} must be 1..{MAX_OCCURRENCE_PREDICATE_COMPONENT_LENGTH} characters")
    if text != text.casefold() or text != text.strip() or _COMPONENT_RE.fullmatch(text) is None:
        raise ValueError(f"{field} must be a canonical lowercase predicate component")
    return text


def _bounded_components(
    value: object,
    *,
    field: str,
    limit: int,
) -> list[str]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be an array")
    values = [_component(item, field=field) for item in value]
    if len(values) > limit:
        raise ValueError(f"{field} exceeds its bounded size")
    canonical = sorted(set(values))
    if values != canonical:
        raise ValueError(f"{field} must be sorted and unique")
    return canonical


def _require_exact_keys(value: Mapping[str, object], expected: set[str], *, field: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{field} has invalid keys (missing={missing}, extra={extra})")


def _atom_selector_keys(atom: Mapping[str, object]) -> list[str]:
    action = cast(Mapping[str, object], atom["action"])
    object_value = cast(Mapping[str, object], atom["object"])
    action_leaf = str(action["leaf"])
    object_leaf = str(object_value["leaf"])
    keys = [
        f"v1|a=exact:{action_leaf}|o=exact:{object_leaf}",
        f"v1|a=exact:{action_leaf}|o=*",
    ]
    if bool(atom["closure_complete"]):
        action_ancestors = cast(list[str], action["ancestors"])
        object_ancestors = cast(list[str], object_value["ancestors"])
        keys.extend(f"v1|a=category:{ancestor}|o=exact:{object_leaf}" for ancestor in action_ancestors)
        keys.extend(f"v1|a=exact:{action_leaf}|o=category:{ancestor}" for ancestor in object_ancestors)
        keys.extend(
            f"v1|a=category:{action_ancestor}|o=category:{object_ancestor}"
            for action_ancestor in action_ancestors
            for object_ancestor in object_ancestors
        )
    if len(keys) > MAX_OCCURRENCE_PREDICATE_SELECTOR_KEYS:
        raise ValueError("predicate selector_keys exceeds its bounded size")
    return keys


def _canonical_atom(value: Mapping[str, object]) -> JsonObject:
    expected_keys = {
        "schema",
        "taxonomy",
        "op",
        "subject",
        "polarity",
        "action",
        "object",
        "selector_keys",
        "closure_complete",
    }
    _require_exact_keys(value, expected_keys, field="occurrence predicate atom")
    if value["schema"] != OCCURRENCE_PREDICATE_SCHEMA:
        raise ValueError("unsupported occurrence predicate schema")
    if value["taxonomy"] != OCCURRENCE_PREDICATE_TAXONOMY:
        raise ValueError("unsupported occurrence predicate taxonomy")
    if value["op"] != "atom" or value["subject"] != "self" or value["polarity"] != "completed":
        raise ValueError("occurrence predicate atom must represent a completed self action")
    if not isinstance(value["closure_complete"], bool):
        raise ValueError("occurrence predicate closure_complete must be boolean")
    action = value["action"]
    object_value = value["object"]
    if not isinstance(action, Mapping) or not isinstance(object_value, Mapping):
        raise ValueError("occurrence predicate action and object must be objects")
    _require_exact_keys(action, {"leaf", "ancestors"}, field="occurrence predicate action")
    _require_exact_keys(
        object_value,
        {"leaf", "qualifiers", "ancestors"},
        field="occurrence predicate object",
    )
    canonical: JsonObject = {
        "schema": OCCURRENCE_PREDICATE_SCHEMA,
        "taxonomy": OCCURRENCE_PREDICATE_TAXONOMY,
        "op": "atom",
        "subject": "self",
        "polarity": "completed",
        "action": {
            "leaf": _component(action["leaf"], field="predicate action leaf"),
            "ancestors": _bounded_components(
                action["ancestors"],
                field="predicate action ancestors",
                limit=MAX_OCCURRENCE_PREDICATE_ANCESTORS,
            ),
        },
        "object": {
            "leaf": _component(object_value["leaf"], field="predicate object leaf"),
            "qualifiers": _bounded_components(
                object_value["qualifiers"],
                field="predicate object qualifiers",
                limit=MAX_OCCURRENCE_PREDICATE_QUALIFIERS,
            ),
            "ancestors": _bounded_components(
                object_value["ancestors"],
                field="predicate object ancestors",
                limit=MAX_OCCURRENCE_PREDICATE_ANCESTORS,
            ),
        },
        "selector_keys": [],
        "closure_complete": value["closure_complete"],
    }
    if (
        cast(Mapping[str, object], canonical["action"])["ancestors"]
        or cast(Mapping[str, object], canonical["object"])["ancestors"]
    ):
        raise ValueError("exact occurrence taxonomy forbids semantic ancestors")
    selector_keys = _atom_selector_keys(canonical)
    supplied = value["selector_keys"]
    if isinstance(supplied, (str, bytes)) or not isinstance(supplied, Sequence):
        raise ValueError("occurrence predicate selector_keys must be an array")
    supplied_keys = [canonical_occurrence_selector_key(item) for item in supplied]
    if supplied_keys != selector_keys:
        raise ValueError("occurrence predicate selector_keys do not match the signed atom closure")
    canonical["selector_keys"] = selector_keys
    return canonical


def canonicalize_occurrence_predicate(
    value: object,
    *,
    allow_claim_ops: bool,
) -> JsonObject:
    """Validate and return the unique JSON representation of one predicate."""

    if not isinstance(value, Mapping):
        raise ValueError("occurrence predicate must be an object")
    op = value.get("op")
    if op == "atom":
        return _canonical_atom(value)
    if not allow_claim_ops:
        raise ValueError("occurrence units require one atomic predicate")
    if op == "unknown":
        _require_exact_keys(
            value,
            {
                "schema",
                "taxonomy",
                "op",
                "subject",
                "polarity",
                "selector_keys",
                "closure_complete",
            },
            field="unknown occurrence predicate",
        )
        if (
            value["schema"] != OCCURRENCE_PREDICATE_SCHEMA
            or value["taxonomy"] != OCCURRENCE_PREDICATE_TAXONOMY
            or value["subject"] != "self"
            or value["polarity"] != "completed"
            or value["selector_keys"] != []
            or value["closure_complete"] is not False
        ):
            raise ValueError("unknown occurrence predicate must be unsigned for matching")
        return {
            "schema": OCCURRENCE_PREDICATE_SCHEMA,
            "taxonomy": OCCURRENCE_PREDICATE_TAXONOMY,
            "op": "unknown",
            "subject": "self",
            "polarity": "completed",
            "selector_keys": [],
            "closure_complete": False,
        }
    if op != "or":
        raise ValueError("unsupported occurrence predicate operation")
    _require_exact_keys(
        value,
        {
            "schema",
            "taxonomy",
            "op",
            "subject",
            "polarity",
            "alternatives",
            "selector_keys",
            "closure_complete",
        },
        field="occurrence predicate union",
    )
    if (
        value["schema"] != OCCURRENCE_PREDICATE_SCHEMA
        or value["taxonomy"] != OCCURRENCE_PREDICATE_TAXONOMY
        or value["subject"] != "self"
        or value["polarity"] != "completed"
    ):
        raise ValueError("occurrence predicate union has incompatible common facts")
    raw_alternatives = value["alternatives"]
    if isinstance(raw_alternatives, (str, bytes)) or not isinstance(raw_alternatives, Sequence):
        raise ValueError("occurrence predicate alternatives must be an array")
    if not 2 <= len(raw_alternatives) <= MAX_OCCURRENCE_PREDICATE_ALTERNATIVES:
        raise ValueError("occurrence predicate union must contain 2..8 alternatives")
    alternatives = [_canonical_atom(cast(Mapping[str, object], item)) for item in raw_alternatives]
    alternatives = sorted(alternatives, key=_canonical_json)
    if len({_canonical_json(item) for item in alternatives}) != len(alternatives):
        raise ValueError("occurrence predicate alternatives must be unique")
    selector_keys = list(
        dict.fromkeys(
            selector
            for alternative in alternatives
            for selector in cast(list[str], alternative["selector_keys"])
        )
    )
    if len(selector_keys) > MAX_OCCURRENCE_PREDICATE_SELECTOR_KEYS:
        raise ValueError("predicate selector_keys exceeds its bounded size")
    supplied = value["selector_keys"]
    if not isinstance(supplied, Sequence) or isinstance(supplied, (str, bytes)):
        raise ValueError("occurrence predicate selector_keys must be an array")
    supplied_keys = [canonical_occurrence_selector_key(item) for item in supplied]
    if supplied_keys != selector_keys:
        raise ValueError("occurrence predicate selector_keys do not match the signed union closure")
    closure_complete = all(bool(item["closure_complete"]) for item in alternatives)
    if value["closure_complete"] is not closure_complete:
        raise ValueError("occurrence predicate union closure completeness is inconsistent")
    return {
        "schema": OCCURRENCE_PREDICATE_SCHEMA,
        "taxonomy": OCCURRENCE_PREDICATE_TAXONOMY,
        "op": "or",
        "subject": "self",
        "polarity": "completed",
        "alternatives": alternatives,
        "selector_keys": selector_keys,
        "closure_complete": closure_complete,
    }


def canonical_occurrence_selector_key(value: object) -> str:
    """Validate one exact, indexable selector key."""

    text = str(value)
    if len(text) > 240:
        raise ValueError("occurrence selector key exceeds its bounded size")
    match = _SELECTOR_RE.fullmatch(text)
    if match is None:
        raise ValueError("invalid occurrence selector key")
    _component(match.group("action"), field="selector action")
    if match.group("wildcard") is None:
        _component(match.group("object"), field="selector object")
    return text


def occurrence_predicate_digest(
    value: object,
    *,
    allow_claim_ops: bool,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            canonicalize_occurrence_predicate(
                value,
                allow_claim_ops=allow_claim_ops,
            )
        ).encode("utf-8")
    ).hexdigest()


def _canonical_occurrence_aggregation_basis(value: object) -> str:
    basis = str(value)
    if basis not in OCCURRENCE_AGGREGATION_BASES:
        raise ValueError("occurrence aggregation_basis must be event_instance or object_member")
    return basis


def _canonical_occurrence_member_identity(value: object) -> str:
    identity = str(value)
    if (
        not 1 <= len(identity) <= MAX_OCCURRENCE_MEMBER_IDENTITY_LENGTH
        or identity != identity.strip()
    ):
        raise ValueError("occurrence member_identity must be a bounded canonical value")
    return identity


def _canonical_occurrence_member_identity_basis(value: object) -> str:
    basis = str(value)
    if basis not in OCCURRENCE_AGGREGATION_IDENTITY_BASES:
        raise ValueError("unsupported occurrence aggregation identity_basis")
    return basis


def canonicalize_occurrence_claim_aggregation(value: object) -> JsonObject:
    """Canonical allowed count projections for one occurrence claim."""

    if not isinstance(value, Mapping):
        raise ValueError("claim aggregation_json must be an object")
    _require_exact_keys(
        value,
        {"schema", "bases"},
        field="claim aggregation_json",
    )
    if value["schema"] != OCCURRENCE_AGGREGATION_SCHEMA:
        raise ValueError("unsupported occurrence aggregation schema")
    raw_bases = value["bases"]
    if isinstance(raw_bases, (str, bytes)) or not isinstance(raw_bases, Sequence):
        raise ValueError("claim aggregation bases must be an array")
    if not 1 <= len(raw_bases) <= len(OCCURRENCE_AGGREGATION_BASES):
        raise ValueError("claim aggregation bases exceed their bounded size")
    bases: list[JsonObject] = []
    for raw in raw_bases:
        if not isinstance(raw, Mapping):
            raise ValueError("claim aggregation basis must be an object")
        _require_exact_keys(
            raw,
            {"basis", "identity_basis"},
            field="claim aggregation basis",
        )
        bases.append(
            {
                "basis": _canonical_occurrence_aggregation_basis(raw["basis"]),
                "identity_basis": _canonical_occurrence_member_identity_basis(
                    raw["identity_basis"]
                ),
            }
        )
    bases = sorted(bases, key=lambda item: str(item["basis"]))
    if len({str(item["basis"]) for item in bases}) != len(bases):
        raise ValueError("claim aggregation bases must be unique by basis")
    event_bases = [item for item in bases if item["basis"] == "event_instance"]
    if len(event_bases) != 1 or event_bases[0]["identity_basis"] != "occurrence_key":
        raise ValueError("claim aggregation requires event_instance with occurrence_key identity")
    object_bases = [item for item in bases if item["basis"] == "object_member"]
    if object_bases and object_bases[0]["identity_basis"] != "reviewed_stable_object_v1":
        raise ValueError(
            "object_member aggregation requires reviewed_stable_object_v1 identity"
        )
    return {
        "schema": OCCURRENCE_AGGREGATION_SCHEMA,
        "bases": bases,
    }


def canonicalize_occurrence_unit_aggregation(
    value: object,
    *,
    occurrence_key: str,
    claim_aggregation: object | None = None,
) -> JsonObject:
    """Canonical reviewed member projections for one real-world event."""

    if not isinstance(value, Mapping):
        raise ValueError("unit aggregation_json must be an object")
    _require_exact_keys(
        value,
        {"schema", "members"},
        field="unit aggregation_json",
    )
    if value["schema"] != OCCURRENCE_AGGREGATION_SCHEMA:
        raise ValueError("unsupported occurrence aggregation schema")
    raw_members = value["members"]
    if isinstance(raw_members, (str, bytes)) or not isinstance(raw_members, Sequence):
        raise ValueError("unit aggregation members must be an array")
    if not 1 <= len(raw_members) <= MAX_OCCURRENCE_AGGREGATION_MEMBERS:
        raise ValueError("unit aggregation members exceed their bounded size")
    members: list[JsonObject] = []
    for raw in raw_members:
        if not isinstance(raw, Mapping):
            raise ValueError("unit aggregation member must be an object")
        _require_exact_keys(
            raw,
            {"basis", "identity_basis", "member_identity"},
            field="unit aggregation member",
        )
        members.append(
            {
                "basis": _canonical_occurrence_aggregation_basis(raw["basis"]),
                "identity_basis": _canonical_occurrence_member_identity_basis(
                    raw["identity_basis"]
                ),
                "member_identity": _canonical_occurrence_member_identity(
                    raw["member_identity"]
                ),
            }
        )
    members = sorted(
        members,
        key=lambda item: (
            str(item["basis"]),
            str(item["identity_basis"]),
            str(item["member_identity"]),
        ),
    )
    member_identities = {
        (
            str(item["basis"]),
            str(item["identity_basis"]),
            str(item["member_identity"]),
        )
        for item in members
    }
    if len(member_identities) != len(members):
        raise ValueError("unit aggregation members must have unique identities")
    event_members = [item for item in members if item["basis"] == "event_instance"]
    if (
        len(event_members) != 1
        or event_members[0]["identity_basis"] != "occurrence_key"
        or event_members[0]["member_identity"] != occurrence_key
    ):
        raise ValueError("unit aggregation event member must equal occurrence_key")
    object_members = [item for item in members if item["basis"] == "object_member"]
    if any(
        item["identity_basis"] != "reviewed_stable_object_v1"
        or _REVIEWED_OBJECT_MEMBER_RE.fullmatch(
            str(item["member_identity"])
        )
        is None
        for item in object_members
    ):
        raise ValueError(
            "object_member requires a reviewed object:v1:<sha256> stable key"
        )
    if claim_aggregation is not None:
        allowed = canonicalize_occurrence_claim_aggregation(claim_aggregation)
        allowed_pairs = {
            (str(item["basis"]), str(item["identity_basis"]))
            for item in cast(list[JsonObject], allowed["bases"])
        }
        member_pairs = {
            (str(item["basis"]), str(item["identity_basis"]))
            for item in members
        }
        if not member_pairs.issubset(allowed_pairs):
            raise ValueError("unit aggregation members are not allowed by the owning claim")
    return {
        "schema": OCCURRENCE_AGGREGATION_SCHEMA,
        "members": members,
    }


def occurrence_aggregation_digest(
    value: object,
    *,
    occurrence_key: str | None,
) -> str:
    canonical = (
        canonicalize_occurrence_claim_aggregation(value)
        if occurrence_key is None
        else canonicalize_occurrence_unit_aggregation(
            value,
            occurrence_key=occurrence_key,
        )
    )
    return hashlib.sha256(_canonical_json(canonical).encode("utf-8")).hexdigest()


def canonicalize_occurrence_accounting_metadata(value: object) -> JsonObject:
    """Validate the exact corpus anchor used by a complete-history review."""

    if not isinstance(value, Mapping):
        raise ValueError("complete-history coverage requires occurrence accounting metadata")
    _require_exact_keys(
        value,
        {
            "accounting_schema",
            "extractor_version",
            "source_ids",
            "source_chunk_ids",
            "snapshot_digest",
            "disposition_digest",
        },
        field="occurrence accounting metadata",
    )
    if value["accounting_schema"] != "occurrence_accounting_v1":
        raise ValueError("unsupported occurrence accounting schema")
    extractor_version = str(value["extractor_version"])
    if not 1 <= len(extractor_version) <= 200 or extractor_version != extractor_version.strip():
        raise ValueError("occurrence accounting extractor_version must be bounded")

    def canonical_ids(raw: object, *, field: str) -> list[str]:
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            raise ValueError(f"{field} must be an array")
        try:
            ids = [str(UUID(str(item))) for item in raw]
        except ValueError as exc:
            raise ValueError(f"{field} must contain UUID values") from exc
        canonical = sorted(set(ids))
        if ids != canonical:
            raise ValueError(f"{field} must be sorted and unique")
        return canonical

    source_ids = canonical_ids(value["source_ids"], field="occurrence accounting source_ids")
    source_chunk_ids = canonical_ids(
        value["source_chunk_ids"],
        field="occurrence accounting source_chunk_ids",
    )
    if not source_ids or not source_chunk_ids:
        raise ValueError("complete-history accounting must bind a non-empty source set")
    snapshot_digest = str(value["snapshot_digest"])
    disposition_digest = str(value["disposition_digest"])
    if _SHA256_RE.fullmatch(snapshot_digest) is None or _SHA256_RE.fullmatch(disposition_digest) is None:
        raise ValueError("occurrence accounting digests must be lowercase SHA-256")
    return {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": extractor_version,
        "source_ids": source_ids,
        "source_chunk_ids": source_chunk_ids,
        "snapshot_digest": snapshot_digest,
        "disposition_digest": disposition_digest,
    }


def occurrence_claim_review_receipt_digest(
    claim: Mapping[str, object],
    *,
    resolution_status: str,
    resolution_decision: str,
    identity_basis: str,
    resolved_occurrence_id: str | None,
    reviewer_id: str,
    reason: str,
    review_version: int,
) -> str:
    """Bind every claim fact that can affect counting or resolution."""

    signed_claim = dict(claim)
    signed_claim.update(
        {
            "resolution_status": resolution_status,
            "resolution_decision": resolution_decision,
            "identity_basis": identity_basis,
            "resolved_occurrence_id": resolved_occurrence_id,
            "review_status": (
                "accepted"
                if resolution_status == "resolved"
                else "rejected"
                if resolution_status == "rejected"
                else "candidate"
            ),
        }
    )
    payload = {
        "schema": "occurrence_claim_review_receipt_v1",
        "claim_facts_digest": occurrence_claim_facts_digest(signed_claim),
        "reviewer_id": reviewer_id,
        "reason": reason,
        "review_version": review_version,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def occurrence_memory_carrier_facts_digest(
    memory: Mapping[str, object],
) -> str:
    """Bind live memory content and envelope facts covered by chunk accounting."""

    payload = {
        "schema": "occurrence_memory_carrier_facts_v1",
        "id": str(memory["id"]),
        "user_id": str(memory["user_id"]),
        "memory_key": str(memory["memory_key"]),
        "value": memory.get("value"),
        "status": str(memory["status"]),
        "source_event_ids": memory.get("source_event_ids"),
        "memory_type": str(memory["memory_type"]),
        "valid_from": _receipt_scalar(memory.get("valid_from")),
        "valid_to": _receipt_scalar(memory.get("valid_to")),
        "title": memory.get("title"),
        "canonical_text": str(memory.get("canonical_text") or ""),
        "summary": memory.get("summary"),
        "domain": str(memory["domain"]),
        "sensitivity": str(memory["sensitivity"]),
        "first_seen_at": _receipt_scalar(memory.get("first_seen_at")),
        "last_seen_at": _receipt_scalar(memory.get("last_seen_at")),
        "metadata_json": memory.get("metadata_json"),
        "project_id": (
            str(memory["project_id"])
            if memory.get("project_id") is not None
            else None
        ),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def occurrence_claim_facts_digest(claim: Mapping[str, object]) -> str:
    """Digest every claim fact that can affect selection or count semantics."""

    payload = {
        "schema": "occurrence_claim_facts_v1",
        "id": str(claim["id"]),
        "user_id": str(claim["user_id"]),
        "claim_key": str(claim["claim_key"]),
        "count_key": str(claim["count_key"]),
        "canonical_text": str(claim["canonical_text"]),
        "predicate_digest": occurrence_predicate_digest(
            claim["predicate_json"],
            allow_claim_ops=True,
        ),
        "aggregation_digest": occurrence_aggregation_digest(
            claim["aggregation_json"],
            occurrence_key=None,
        ),
        "quantity_min": int(cast(int, claim["quantity_min"])),
        "quantity_max": claim.get("quantity_max"),
        "range_kind": str(claim["range_kind"]),
        "resolution_decision": str(claim["resolution_decision"]),
        "resolution_status": str(claim["resolution_status"]),
        "identity_basis": str(claim["identity_basis"]),
        "resolved_occurrence_id": (
            str(claim["resolved_occurrence_id"])
            if claim.get("resolved_occurrence_id") is not None
            else None
        ),
        "review_status": str(claim["review_status"]),
        "occurred_at_start": _receipt_scalar(claim.get("occurred_at_start")),
        "occurred_at_end": _receipt_scalar(claim.get("occurred_at_end")),
        "domain": str(claim["domain"]),
        "sensitivity": str(claim["sensitivity"]),
        "project_scope": claim["project_scope"],
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def occurrence_extraction_disposition_review_receipt_digest(
    disposition: Mapping[str, object],
    *,
    action: str,
    reviewer_id: str,
    reason: str,
    review_version: int,
) -> str:
    """Bind an extraction decision to its exact current chunk and fact set."""

    payload = {
        "action": action,
        "claim_ids": list(cast(Sequence[object], disposition["claim_ids"])),
        "disposition": str(disposition["disposition"]),
        "disposition_id": str(disposition["id"]),
        "extractor_version": str(disposition["extractor_version"]),
        "metadata_json": dict(
            cast(Mapping[str, object], disposition["metadata_json"])
        ),
        "occurrence_ids": list(
            cast(Sequence[object], disposition["occurrence_ids"])
        ),
        "predicate_keys": list(
            cast(Sequence[object], disposition["predicate_keys"])
        ),
        "reason": reason,
        "review_version": review_version,
        "reviewer_id": reviewer_id,
        "snapshot_sha256": str(disposition["snapshot_sha256"]),
        "source_chunk_id": str(disposition["source_chunk_id"]),
        "source_id": str(disposition["source_id"]),
        "user_id": str(disposition["user_id"]),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def occurrence_coverage_review_receipt_digest(
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
    """Bind a coverage decision to its principal, boundary, and corpus proof."""

    payload = {
        "complete_through": _receipt_scalar(complete_through),
        "coverage_id": str(coverage_id),
        "coverage_mode": coverage_mode,
        "coverage_started_at": _receipt_scalar(coverage_started_at),
        "historical_review_status": historical_review_status,
        "accounting_metadata": (
            dict(accounting_metadata) if accounting_metadata is not None else None
        ),
        "reason": reason,
        "review_version": review_version,
        "reviewer_id": reviewer_id,
        "user_id": str(user_id),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def occurrence_unit_review_receipt_digest(
    unit: Mapping[str, object],
    *,
    action: str,
    reviewer_id: str,
    reason: str,
    review_version: int,
    evidence_digest: str,
) -> str:
    """Bind predicate, cardinality identity, evidence, and review facts."""

    superseded_by: str | None = None
    if action == "superseded":
        raw_superseded_by = unit.get("superseded_by")
        if raw_superseded_by is None:
            raise ValueError("superseded review receipt requires superseded_by")
        try:
            superseded_by = str(UUID(str(raw_superseded_by)))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "superseded review receipt requires a UUID superseded_by"
            ) from exc

    canonical = "occurrence_unit_review_receipt_v2;" + "".join(
        _framed_receipt_value(value)
        for value in (
            unit["id"],
            review_version,
            action,
            reviewer_id,
            reason,
            occurrence_unit_facts_digest(unit),
            superseded_by,
            evidence_digest,
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def occurrence_unit_facts_digest(unit: Mapping[str, object]) -> str:
    """Digest every immutable unit fact used by selection or counting."""

    occurrence_key = str(unit["occurrence_key"])
    payload = {
        "schema": "occurrence_unit_facts_v1",
        "id": str(unit["id"]),
        "user_id": str(unit["user_id"]),
        "claim_id": str(unit["claim_id"]),
        "claim_ordinal": int(cast(int, unit["claim_ordinal"])),
        "occurrence_key": occurrence_key,
        "count_key": str(unit["count_key"]),
        "canonical_text": str(unit["canonical_text"]),
        "unit_value": int(cast(int, unit["unit_value"])),
        "identity_status": str(unit["identity_status"]),
        "ambiguity_group_key": unit.get("ambiguity_group_key"),
        "predicate_digest": occurrence_predicate_digest(
            unit["predicate_json"],
            allow_claim_ops=False,
        ),
        "aggregation_digest": occurrence_aggregation_digest(
            unit["aggregation_json"],
            occurrence_key=occurrence_key,
        ),
        "occurred_at_start": _receipt_scalar(unit.get("occurred_at_start")),
        "occurred_at_end": _receipt_scalar(unit.get("occurred_at_end")),
        "domain": str(unit["domain"]),
        "sensitivity": str(unit["sensitivity"]),
        "project_scope": unit["project_scope"],
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _framed_receipt_value(value: object | None) -> str:
    if value is None:
        return "N;"
    text = str(value)
    return f"S{len(text.encode('utf-8'))}:{text};"


def occurrence_evidence_facts_digest(evidence: Mapping[str, object]) -> str:
    """Digest immutable evidence identity and provenance with unambiguous framing."""

    validate_occurrence_evidence_quote_digest(evidence)
    canonical = "occurrence_evidence_facts_v1;" + "".join(
        _framed_receipt_value(evidence.get(field))
        for field in (
            "id",
            "user_id",
            "claim_id",
            "occurrence_id",
            "evidence_key",
            "evidence_role",
            "memory_id",
            "source_id",
            "source_chunk_id",
            "quote_sha256",
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_occurrence_evidence_quote_digest(
    evidence: Mapping[str, object],
) -> None:
    """Reject a non-null quote whose persisted digest does not match its bytes."""

    quote = evidence.get("quote")
    if quote is None:
        return
    expected = hashlib.sha256(str(quote).encode("utf-8")).hexdigest()
    if evidence.get("quote_sha256") != expected:
        raise ValueError("occurrence evidence quote_sha256 does not match quote")


def occurrence_evidence_review_receipt_digest(
    evidence: Mapping[str, object],
    *,
    action: str,
    reviewer_id: str,
    reason: str,
    unit_review_receipt_digest: str | None,
) -> str:
    """Bind one evidence fact set to the exact unit review that accepted it."""

    canonical = "occurrence_evidence_review_receipt_v1;" + "".join(
        _framed_receipt_value(value)
        for value in (
            occurrence_evidence_facts_digest(evidence),
            action,
            reviewer_id,
            reason,
            unit_review_receipt_digest,
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _receipt_scalar(value: object) -> object:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    else:
        return str(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00",
        "Z",
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
