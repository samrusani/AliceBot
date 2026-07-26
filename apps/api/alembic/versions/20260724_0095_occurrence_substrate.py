"""Add the review-gated occurrence-counting substrate.

This migration is intentionally forward-only.  It creates empty occurrence
tables and does not inspect, infer from, or backfill any existing memory,
source, or event row.  Existing rows are not assumed to represent one
real-world occurrence.  Coverage therefore remains unknown until runtime
creates an explicit ``occurrence_coverage`` row; historical qualification is
a separate review-gated operation.

The substrate separates captured claims from countable units:

* ``occurrence_claims`` preserve exact, bounded, at-least, and ambiguous
  assertions without treating a claimed quantity as an answer.
* ``occurrence_units`` contribute exactly one only after review resolves
  their identity and signs the supporting evidence set.
* ``occurrence_evidence`` is many-to-many provenance.  Source/chunk/memory
  identifiers are durable historical annotations rather than foreign keys,
  matching the append-oriented precedent in migration 0078: destructive
  lifecycle coupling must not silently erase why a unit was reviewed.

Downgrade removes only the newly created occurrence data.

Revision ID: 20260724_0095
Revises: 20260721_0094
"""

from __future__ import annotations

from alembic import op


revision = "20260724_0095"
down_revision = "20260721_0094"
branch_labels = None
depends_on = None


DOMAINS = (
    "professional",
    "personal",
    "family",
    "health",
    "spiritual",
    "financial",
    "legal",
    "learning",
    "relationship",
    "project",
    "agent_run",
    "system",
    "unknown",
)

SENSITIVITY_LEVELS = (
    "public",
    "internal",
    "private",
    "confidential",
    "highly_sensitive",
    "sacred",
    "regulated",
    "unknown",
)

COVERAGE_MODES = ("forward_only", "partial_history", "complete_history")
HISTORICAL_REVIEW_STATUSES = ("not_reviewed", "needs_review", "reviewed")
RANGE_KINDS = ("exact", "at_least", "bounded", "unknown")
RESOLUTION_DECISIONS = ("new", "link_existing", "ambiguous")
RESOLUTION_STATUSES = ("pending", "resolved", "rejected")
IDENTITY_BASES = (
    "external_event_id",
    "exact_time",
    "date_and_ordinal",
    "session_and_ordinal",
    "reviewed_manual",
    "ambiguous",
)
CLAIM_REVIEW_STATUSES = ("candidate", "accepted", "rejected")
UNIT_REVIEW_STATUSES = (
    "candidate",
    "accepted",
    "rejected",
    "superseded",
    "retired",
)
IDENTITY_STATUSES = ("resolved", "ambiguous")
REVIEW_RECEIPT_ACTIONS = (
    "accepted",
    "refresh_evidence",
    "reestablished",
    "rejected",
    "ambiguous",
    "superseded",
    "retired",
)
EVIDENCE_REVIEW_RECEIPT_ACTIONS = (
    "accepted",
    "refresh_evidence",
    "reestablished",
    "rejected",
)
OCCURRENCE_EVIDENCE_ROLES = (
    "supports",
    "contradicts",
    "same_event_hint",
    "distinct_event_hint",
)
OCCURRENCE_EVIDENCE_REVIEW_STATUSES = ("candidate", "accepted", "rejected")
EXTRACTION_DISPOSITIONS = (
    "accepted_occurrences",
    "unresolved_claims",
    "no_occurrence",
)
EXTRACTION_REVIEW_STATUSES = ("candidate", "accepted", "rejected")
MAX_OCCURRENCE_AGGREGATION_MEMBERS = 32

# CPython 3.12's fixed Unicode whitespace table used by ``str.strip()``.
# PostgreSQL's default ``btrim`` character set does not include controls such
# as U+001C or Unicode spaces such as NBSP, so evidence DDL must use the same
# explicit policy as migration 0090 and the runtime writer.
_PYTHON_312_STRIP_CODEPOINTS = (
    0x0009,
    0x000A,
    0x000B,
    0x000C,
    0x000D,
    0x001C,
    0x001D,
    0x001E,
    0x001F,
    0x0020,
    0x0085,
    0x00A0,
    0x1680,
    0x2000,
    0x2001,
    0x2002,
    0x2003,
    0x2004,
    0x2005,
    0x2006,
    0x2007,
    0x2008,
    0x2009,
    0x200A,
    0x2028,
    0x2029,
    0x202F,
    0x205F,
    0x3000,
)
_PYTHON_312_STRIP_CHARS_SQL = " || ".join(f"chr({codepoint})" for codepoint in _PYTHON_312_STRIP_CODEPOINTS)


def _sql_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


_DOMAINS_SQL = _sql_list(DOMAINS)
_SENSITIVITY_SQL = _sql_list(SENSITIVITY_LEVELS)
_COVERAGE_MODES_SQL = _sql_list(COVERAGE_MODES)
_HISTORICAL_REVIEW_STATUSES_SQL = _sql_list(HISTORICAL_REVIEW_STATUSES)
_RANGE_KINDS_SQL = _sql_list(RANGE_KINDS)
_RESOLUTION_DECISIONS_SQL = _sql_list(RESOLUTION_DECISIONS)
_RESOLUTION_STATUSES_SQL = _sql_list(RESOLUTION_STATUSES)
_IDENTITY_BASES_SQL = _sql_list(IDENTITY_BASES)
_CLAIM_REVIEW_STATUSES_SQL = _sql_list(CLAIM_REVIEW_STATUSES)
_UNIT_REVIEW_STATUSES_SQL = _sql_list(UNIT_REVIEW_STATUSES)
_IDENTITY_STATUSES_SQL = _sql_list(IDENTITY_STATUSES)
_REVIEW_RECEIPT_ACTIONS_SQL = _sql_list(REVIEW_RECEIPT_ACTIONS)
_EVIDENCE_REVIEW_RECEIPT_ACTIONS_SQL = _sql_list(EVIDENCE_REVIEW_RECEIPT_ACTIONS)
_OCCURRENCE_EVIDENCE_ROLES_SQL = _sql_list(OCCURRENCE_EVIDENCE_ROLES)
_OCCURRENCE_EVIDENCE_REVIEW_STATUSES_SQL = _sql_list(OCCURRENCE_EVIDENCE_REVIEW_STATUSES)
_EXTRACTION_DISPOSITIONS_SQL = _sql_list(EXTRACTION_DISPOSITIONS)
_EXTRACTION_REVIEW_STATUSES_SQL = _sql_list(EXTRACTION_REVIEW_STATUSES)


def _postgres_occurrence_object_member_checks() -> str:
    checks: list[str] = []
    for index in range(1, MAX_OCCURRENCE_AGGREGATION_MEMBERS):
        identity = f"aggregation_json #>> '{{members,{index},member_identity}}'"
        member_checks = [
            f"jsonb_typeof(aggregation_json #> '{{members,{index}}}') = 'object'",
            f"aggregation_json #>> '{{members,{index},basis}}' = 'object_member'",
            (f"aggregation_json #>> '{{members,{index},identity_basis}}' = 'reviewed_stable_object_v1'"),
            f"char_length({identity}) BETWEEN 1 AND 500",
            f"{identity} ~ '^object:v1:[0-9a-f]{{64}}$'",
        ]
        if index > 1:
            previous = f"aggregation_json #>> '{{members,{index - 1},member_identity}}'"
            member_checks.append(f'({previous}) COLLATE "C" < ({identity}) COLLATE "C"')
        checks.append(
            f"(jsonb_array_length(aggregation_json -> 'members') <= {index} OR (" + " AND ".join(member_checks) + "))"
        )
    return "\n              AND ".join(checks)


_OCCURRENCE_OBJECT_MEMBER_CHECKS_SQL = _postgres_occurrence_object_member_checks()

_RLS_TABLES = (
    "occurrence_coverage",
    "occurrence_claims",
    "occurrence_units",
    "occurrence_evidence",
    "occurrence_extraction_dispositions",
)

_UPGRADE_SCHEMA = f"""
        CREATE TABLE occurrence_coverage (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          coverage_mode text NOT NULL,
          coverage_started_at timestamptz NOT NULL,
          historical_review_status text NOT NULL DEFAULT 'not_reviewed',
          complete_through timestamptz NULL,
          reviewed_at timestamptz NULL,
          reviewer_id text NULL,
          review_reason text NULL,
          review_version integer NOT NULL DEFAULT 0,
          review_receipt_digest text NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (user_id),
          CONSTRAINT occurrence_coverage_mode_check
            CHECK (coverage_mode IN ({_COVERAGE_MODES_SQL})),
          CONSTRAINT occurrence_coverage_historical_review_status_check
            CHECK (historical_review_status IN ({_HISTORICAL_REVIEW_STATUSES_SQL})),
          CONSTRAINT occurrence_coverage_complete_history_check
            CHECK (
              coverage_mode <> 'complete_history'
              OR historical_review_status = 'reviewed'
            ),
          CONSTRAINT occurrence_coverage_complete_through_check
            CHECK (
              complete_through IS NULL
              OR complete_through >= coverage_started_at
            ),
          CONSTRAINT occurrence_coverage_review_version_check
            CHECK (review_version >= 0),
          CONSTRAINT occurrence_coverage_review_receipt_digest_check
            CHECK (
              review_receipt_digest IS NULL
              OR review_receipt_digest ~ '^[0-9a-f]{{64}}$'
            ),
          CONSTRAINT occurrence_coverage_reviewed_state_check
            CHECK (
              historical_review_status <> 'reviewed'
              OR (
                reviewed_at IS NOT NULL
                AND reviewer_id IS NOT NULL
                AND char_length(btrim(reviewer_id)) > 0
                AND review_reason IS NOT NULL
                AND char_length(btrim(review_reason)) > 0
                AND review_receipt_digest IS NOT NULL
              )
            ),
          CONSTRAINT occurrence_coverage_historical_mode_check
            CHECK (
              coverage_mode = 'forward_only'
              OR (
                historical_review_status = 'reviewed'
                AND complete_through IS NOT NULL
              )
            ),
          CONSTRAINT occurrence_coverage_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE occurrence_claims (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          claim_key text NOT NULL,
          count_key text NOT NULL,
          predicate_json jsonb NOT NULL,
          canonical_text text NOT NULL,
          quantity_min integer NOT NULL,
          quantity_max integer NULL,
          range_kind text NOT NULL,
          resolution_decision text NOT NULL,
          resolution_status text NOT NULL DEFAULT 'pending',
          identity_basis text NOT NULL,
          aggregation_json jsonb NOT NULL,
          review_status text NOT NULL DEFAULT 'candidate',
          occurred_at_start timestamptz NULL,
          occurred_at_end timestamptz NULL,
          domain text NOT NULL DEFAULT 'unknown',
          sensitivity text NOT NULL DEFAULT 'unknown',
          project_scope jsonb NOT NULL DEFAULT '[]'::jsonb,
          resolved_occurrence_id uuid NULL,
          reviewed_at timestamptz NULL,
          reviewer_id text NULL,
          review_reason text NULL,
          review_version integer NOT NULL DEFAULT 0,
          review_receipt_digest text NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (id, user_id, count_key),
          UNIQUE (user_id, claim_key),
          CONSTRAINT occurrence_claims_claim_key_length_check
            CHECK (char_length(claim_key) BETWEEN 1 AND 200),
          CONSTRAINT occurrence_claims_count_key_length_check
            CHECK (char_length(count_key) BETWEEN 1 AND 500),
          CONSTRAINT occurrence_claims_predicate_json_object_check
            CHECK (
              jsonb_typeof(predicate_json) = 'object'
              AND predicate_json ->> 'schema' = 'occurrence_predicate_v1'
              AND predicate_json ->> 'taxonomy' = 'alice-occurrence-exact-v1'
              AND predicate_json ->> 'op' IN ('atom', 'or', 'unknown')
            ),
          CONSTRAINT occurrence_claims_canonical_text_length_check
            CHECK (char_length(canonical_text) BETWEEN 1 AND 10000),
          CONSTRAINT occurrence_claims_quantity_min_check
            CHECK (quantity_min >= 0),
          CONSTRAINT occurrence_claims_quantity_range_check
            CHECK (quantity_max IS NULL OR quantity_max >= quantity_min),
          CONSTRAINT occurrence_claims_range_kind_check
            CHECK (range_kind IN ({_RANGE_KINDS_SQL})),
          CONSTRAINT occurrence_claims_exact_range_check
            CHECK (
              range_kind <> 'exact'
              OR (quantity_max IS NOT NULL AND quantity_min = quantity_max)
            ),
          CONSTRAINT occurrence_claims_bounded_range_check
            CHECK (range_kind <> 'bounded' OR quantity_max IS NOT NULL),
          CONSTRAINT occurrence_claims_resolution_decision_check
            CHECK (resolution_decision IN ({_RESOLUTION_DECISIONS_SQL})),
          CONSTRAINT occurrence_claims_resolution_status_check
            CHECK (resolution_status IN ({_RESOLUTION_STATUSES_SQL})),
          CONSTRAINT occurrence_claims_identity_basis_check
            CHECK (identity_basis IN ({_IDENTITY_BASES_SQL})),
          CONSTRAINT occurrence_claims_aggregation_json_check
            CHECK (
              jsonb_typeof(aggregation_json) = 'object'
              AND aggregation_json ->> 'schema' = 'occurrence_aggregation_v1'
              AND jsonb_typeof(aggregation_json -> 'bases') = 'array'
              AND jsonb_array_length(aggregation_json -> 'bases') BETWEEN 1 AND 2
              AND aggregation_json #>> '{{bases,0,basis}}' = 'event_instance'
              AND aggregation_json #>> '{{bases,0,identity_basis}}' = 'occurrence_key'
              AND (
                jsonb_array_length(aggregation_json -> 'bases') = 1
                OR (
                  aggregation_json #>> '{{bases,1,basis}}' = 'object_member'
                  AND aggregation_json #>> '{{bases,1,identity_basis}}'
                    = 'reviewed_stable_object_v1'
                )
              )
            ),
          CONSTRAINT occurrence_claims_object_projection_quantity_check
            CHECK (
              jsonb_array_length(aggregation_json -> 'bases') = 1
              OR (
                range_kind = 'exact'
                AND quantity_min = 1
                AND quantity_max = 1
              )
            ),
          CONSTRAINT occurrence_claims_review_status_check
            CHECK (review_status IN ({_CLAIM_REVIEW_STATUSES_SQL})),
          CONSTRAINT occurrence_claims_review_version_check
            CHECK (review_version >= 0),
          CONSTRAINT occurrence_claims_event_range_check
            CHECK (
              occurred_at_start IS NULL
              OR occurred_at_end IS NULL
              OR occurred_at_end >= occurred_at_start
            ),
          CONSTRAINT occurrence_claims_domain_check
            CHECK (domain IN ({_DOMAINS_SQL})),
          CONSTRAINT occurrence_claims_sensitivity_check
            CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
          CONSTRAINT occurrence_claims_project_scope_array_check
            CHECK (jsonb_typeof(project_scope) = 'array'),
          CONSTRAINT occurrence_claims_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object'),
          CONSTRAINT occurrence_claims_review_receipt_check
            CHECK (
              (
                review_status = 'candidate'
                AND review_receipt_digest IS NULL
              )
              OR (
                reviewed_at IS NOT NULL
                AND reviewer_id IS NOT NULL
                AND char_length(btrim(reviewer_id)) > 0
                AND review_reason IS NOT NULL
                AND char_length(btrim(review_reason)) > 0
                AND review_receipt_digest ~ '^[0-9a-f]{{64}}$'
              )
            ),
          CONSTRAINT occurrence_claims_resolved_state_check
            CHECK (
              resolution_status <> 'resolved'
              OR (
                review_status = 'accepted'
                AND identity_basis <> 'ambiguous'
                AND (
                  (
                    resolution_decision = 'new'
                    AND resolved_occurrence_id IS NULL
                  )
                  OR (
                    resolution_decision = 'link_existing'
                    AND resolved_occurrence_id IS NOT NULL
                  )
                )
              )
            ),
          CONSTRAINT occurrence_claims_ambiguous_state_check
            CHECK (
              resolution_decision <> 'ambiguous'
              OR (
                (
                  resolution_status = 'pending'
                  AND review_status = 'candidate'
                )
                OR (
                  resolution_status = 'rejected'
                  AND review_status = 'rejected'
                )
              )
            )
        );

        CREATE TABLE occurrence_units (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          claim_id uuid NOT NULL,
          claim_ordinal integer NOT NULL,
          occurrence_key text NOT NULL,
          count_key text NOT NULL,
          predicate_json jsonb NOT NULL,
          canonical_text text NOT NULL,
          aggregation_json jsonb NOT NULL,
          unit_value smallint NOT NULL DEFAULT 1,
          review_status text NOT NULL DEFAULT 'candidate',
          identity_status text NOT NULL,
          ambiguity_group_key text NULL,
          occurred_at_start timestamptz NULL,
          occurred_at_end timestamptz NULL,
          domain text NOT NULL DEFAULT 'unknown',
          sensitivity text NOT NULL DEFAULT 'unknown',
          project_scope jsonb NOT NULL DEFAULT '[]'::jsonb,
          reviewed_at timestamptz NULL,
          reviewer_id text NULL,
          review_reason text NULL,
          review_version integer NOT NULL DEFAULT 0,
          reviewed_evidence_count integer NOT NULL DEFAULT 0,
          reviewed_evidence_digest text NULL,
          review_receipt_digest text NULL,
          review_receipt_action text NULL,
          superseded_by uuid NULL,
          retired_at timestamptz NULL,
          retired_by text NULL,
          retirement_reason text NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (id, user_id, count_key),
          UNIQUE (id, claim_id, user_id),
          UNIQUE (user_id, occurrence_key),
          UNIQUE (user_id, claim_id, claim_ordinal),
          CONSTRAINT occurrence_units_claim_fkey
            FOREIGN KEY (claim_id, user_id, count_key)
            REFERENCES occurrence_claims(id, user_id, count_key)
            ON DELETE CASCADE,
          CONSTRAINT occurrence_units_superseded_by_fkey
            FOREIGN KEY (superseded_by, user_id, count_key)
            REFERENCES occurrence_units(id, user_id, count_key),
          CONSTRAINT occurrence_units_claim_ordinal_check
            CHECK (claim_ordinal >= 1),
          CONSTRAINT occurrence_units_occurrence_key_length_check
            CHECK (char_length(occurrence_key) BETWEEN 1 AND 200),
          CONSTRAINT occurrence_units_count_key_length_check
            CHECK (char_length(count_key) BETWEEN 1 AND 500),
          CONSTRAINT occurrence_units_predicate_json_atom_check
            CHECK (
              jsonb_typeof(predicate_json) = 'object'
              AND predicate_json ->> 'schema' = 'occurrence_predicate_v1'
              AND predicate_json ->> 'taxonomy' = 'alice-occurrence-exact-v1'
              AND predicate_json ->> 'op' = 'atom'
            ),
          CONSTRAINT occurrence_units_canonical_text_length_check
            CHECK (char_length(canonical_text) BETWEEN 1 AND 10000),
          CONSTRAINT occurrence_units_aggregation_json_check
            CHECK (
              jsonb_typeof(aggregation_json) = 'object'
              AND aggregation_json ->> 'schema' = 'occurrence_aggregation_v1'
              AND jsonb_typeof(aggregation_json -> 'members') = 'array'
              AND jsonb_array_length(aggregation_json -> 'members')
                BETWEEN 1 AND {MAX_OCCURRENCE_AGGREGATION_MEMBERS}
              AND jsonb_typeof(aggregation_json #> '{{members,0}}') = 'object'
              AND aggregation_json #>> '{{members,0,basis}}' = 'event_instance'
              AND aggregation_json #>> '{{members,0,identity_basis}}' = 'occurrence_key'
              AND aggregation_json #>> '{{members,0,member_identity}}'
                = occurrence_key
              AND char_length(
                aggregation_json #>> '{{members,0,member_identity}}'
              ) BETWEEN 1 AND 500
              AND {_OCCURRENCE_OBJECT_MEMBER_CHECKS_SQL}
            ),
          CONSTRAINT occurrence_units_unit_value_check
            CHECK (unit_value = 1),
          CONSTRAINT occurrence_units_review_status_check
            CHECK (review_status IN ({_UNIT_REVIEW_STATUSES_SQL})),
          CONSTRAINT occurrence_units_identity_status_check
            CHECK (identity_status IN ({_IDENTITY_STATUSES_SQL})),
          CONSTRAINT occurrence_units_review_version_check
            CHECK (review_version >= 0),
          CONSTRAINT occurrence_units_reviewed_evidence_count_check
            CHECK (reviewed_evidence_count >= 0),
          CONSTRAINT occurrence_units_event_range_check
            CHECK (
              occurred_at_start IS NULL
              OR occurred_at_end IS NULL
              OR occurred_at_end >= occurred_at_start
            ),
          CONSTRAINT occurrence_units_domain_check
            CHECK (domain IN ({_DOMAINS_SQL})),
          CONSTRAINT occurrence_units_sensitivity_check
            CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
          CONSTRAINT occurrence_units_project_scope_array_check
            CHECK (jsonb_typeof(project_scope) = 'array'),
          CONSTRAINT occurrence_units_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object'),
          CONSTRAINT occurrence_units_reviewed_evidence_digest_check
            CHECK (
              reviewed_evidence_digest IS NULL
              OR reviewed_evidence_digest ~ '^[0-9a-f]{{64}}$'
            ),
          CONSTRAINT occurrence_units_review_receipt_digest_check
            CHECK (
              review_receipt_digest IS NULL
              OR review_receipt_digest ~ '^[0-9a-f]{{64}}$'
            ),
          CONSTRAINT occurrence_units_review_receipt_action_check
            CHECK (
              review_receipt_action IS NULL
              OR review_receipt_action IN ({_REVIEW_RECEIPT_ACTIONS_SQL})
            ),
          CONSTRAINT occurrence_units_accepted_state_check
            CHECK (
              review_status <> 'accepted'
              OR (
                identity_status = 'resolved'
                AND reviewed_at IS NOT NULL
                AND reviewer_id IS NOT NULL
                AND char_length(btrim(reviewer_id)) > 0
                AND reviewed_evidence_count >= 1
                AND reviewed_evidence_digest IS NOT NULL
                AND review_receipt_digest IS NOT NULL
                AND review_receipt_action IS NOT NULL
              )
            ),
          CONSTRAINT occurrence_units_superseded_state_check
            CHECK (review_status <> 'superseded' OR superseded_by IS NOT NULL),
          CONSTRAINT occurrence_units_retired_state_check
            CHECK (
              review_status <> 'retired'
              OR (
                retired_at IS NOT NULL
                AND retired_by IS NOT NULL
                AND char_length(btrim(retired_by)) > 0
                AND retirement_reason IS NOT NULL
                AND char_length(btrim(retirement_reason)) > 0
              )
            ),
          CONSTRAINT occurrence_units_superseded_not_self_check
            CHECK (superseded_by IS NULL OR superseded_by <> id)
        );

        ALTER TABLE occurrence_claims
          ADD CONSTRAINT occurrence_claims_resolved_occurrence_fkey
          FOREIGN KEY (resolved_occurrence_id, user_id, count_key)
          REFERENCES occurrence_units(id, user_id, count_key);

        CREATE TABLE occurrence_evidence (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          claim_id uuid NOT NULL,
          occurrence_id uuid NULL,
          source_id uuid NULL,
          source_chunk_id uuid NULL,
          memory_id uuid NULL,
          evidence_key text NOT NULL,
          evidence_role text NOT NULL,
          quote text NULL,
          quote_sha256 text NOT NULL,
          confidence double precision NOT NULL DEFAULT 0.5,
          review_status text NOT NULL DEFAULT 'candidate',
          reviewed_at timestamptz NULL,
          reviewer_id text NULL,
          review_reason text NULL,
          review_receipt_digest text NULL,
          review_receipt_action text NULL,
          unit_review_receipt_digest text NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, evidence_key),
          CONSTRAINT occurrence_evidence_claim_fkey
            FOREIGN KEY (claim_id, user_id)
            REFERENCES occurrence_claims(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT occurrence_evidence_unit_fkey
            FOREIGN KEY (occurrence_id, user_id)
            REFERENCES occurrence_units(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT occurrence_evidence_key_length_check
            CHECK (char_length(evidence_key) BETWEEN 1 AND 200),
          CONSTRAINT occurrence_evidence_role_check
            CHECK (evidence_role IN ({_OCCURRENCE_EVIDENCE_ROLES_SQL})),
          CONSTRAINT occurrence_evidence_quote_check
            CHECK (
              quote IS NOT NULL
              AND char_length(
                btrim(quote, {_PYTHON_312_STRIP_CHARS_SQL})
              ) > 0
            ),
          CONSTRAINT occurrence_evidence_quote_sha256_check
            CHECK (quote_sha256 ~ '^[0-9a-f]{{64}}$'),
          CONSTRAINT occurrence_evidence_confidence_range_check
            CHECK (confidence >= 0.0 AND confidence <= 1.0),
          CONSTRAINT occurrence_evidence_review_status_check
            CHECK (
              review_status IN ({_OCCURRENCE_EVIDENCE_REVIEW_STATUSES_SQL})
            ),
          CONSTRAINT occurrence_evidence_review_receipt_digest_check
            CHECK (
              review_receipt_digest IS NULL
              OR review_receipt_digest ~ '^[0-9a-f]{{64}}$'
            ),
          CONSTRAINT occurrence_evidence_unit_review_receipt_digest_check
            CHECK (
              unit_review_receipt_digest IS NULL
              OR unit_review_receipt_digest ~ '^[0-9a-f]{{64}}$'
            ),
          CONSTRAINT occurrence_evidence_review_receipt_action_check
            CHECK (
              review_receipt_action IS NULL
              OR review_receipt_action IN ({_EVIDENCE_REVIEW_RECEIPT_ACTIONS_SQL})
            ),
          CONSTRAINT occurrence_evidence_reviewed_state_check
            CHECK (
              review_status = 'candidate'
              OR (
                reviewed_at IS NOT NULL
                AND reviewer_id IS NOT NULL
                AND char_length(btrim(reviewer_id)) > 0
                AND review_receipt_digest IS NOT NULL
                AND review_receipt_action IS NOT NULL
              )
            ),
          CONSTRAINT occurrence_evidence_unit_receipt_state_check
            CHECK (
              unit_review_receipt_digest IS NULL
              OR (
                review_status = 'accepted'
                AND occurrence_id IS NOT NULL
              )
            ),
          CONSTRAINT occurrence_evidence_authorization_carrier_check
            CHECK (memory_id IS NOT NULL OR source_id IS NOT NULL),
          CONSTRAINT occurrence_evidence_source_chunk_parent_check
            CHECK (source_chunk_id IS NULL OR source_id IS NOT NULL),
          CONSTRAINT occurrence_evidence_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE TABLE occurrence_extraction_dispositions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source_id uuid NOT NULL,
          source_chunk_id uuid NOT NULL,
          snapshot_sha256 text NOT NULL,
          extractor_version text NOT NULL,
          disposition text NOT NULL,
          predicate_keys jsonb NOT NULL DEFAULT '[]'::jsonb,
          claim_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
          occurrence_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
          review_status text NOT NULL DEFAULT 'candidate',
          reviewed_at timestamptz NULL,
          reviewer_id text NULL,
          review_reason text NULL,
          review_version integer NOT NULL DEFAULT 0,
          review_receipt_digest text NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (
            user_id,
            source_chunk_id,
            snapshot_sha256,
            extractor_version
          ),
          CONSTRAINT occurrence_extraction_dispositions_source_fkey
            FOREIGN KEY (source_id, user_id)
            REFERENCES sources(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT occurrence_extraction_dispositions_chunk_fkey
            FOREIGN KEY (source_chunk_id, user_id)
            REFERENCES source_chunks(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT occurrence_extraction_dispositions_snapshot_check
            CHECK (snapshot_sha256 ~ '^[0-9a-f]{{64}}$'),
          CONSTRAINT occurrence_extraction_dispositions_extractor_length_check
            CHECK (char_length(extractor_version) BETWEEN 1 AND 120),
          CONSTRAINT occurrence_extraction_dispositions_disposition_check
            CHECK (disposition IN ({_EXTRACTION_DISPOSITIONS_SQL})),
          CONSTRAINT occurrence_extraction_dispositions_predicates_array_check
            CHECK (jsonb_typeof(predicate_keys) = 'array'),
          CONSTRAINT occurrence_extraction_dispositions_claims_array_check
            CHECK (jsonb_typeof(claim_ids) = 'array'),
          CONSTRAINT occurrence_extraction_dispositions_occurrences_array_check
            CHECK (jsonb_typeof(occurrence_ids) = 'array'),
          CONSTRAINT occurrence_extraction_dispositions_review_status_check
            CHECK (review_status IN ({_EXTRACTION_REVIEW_STATUSES_SQL})),
          CONSTRAINT occurrence_extraction_dispositions_review_version_check
            CHECK (review_version >= 0),
          CONSTRAINT occurrence_extraction_dispositions_review_receipt_check
            CHECK (
              review_receipt_digest IS NULL
              OR review_receipt_digest ~ '^[0-9a-f]{{64}}$'
            ),
          CONSTRAINT occurrence_extraction_dispositions_reviewed_state_check
            CHECK (
              review_status = 'candidate'
              OR (
                reviewed_at IS NOT NULL
                AND reviewer_id IS NOT NULL
                AND char_length(btrim(reviewer_id)) > 0
                AND review_reason IS NOT NULL
                AND char_length(btrim(review_reason)) > 0
                AND review_receipt_digest IS NOT NULL
              )
            ),
          CONSTRAINT occurrence_extraction_dispositions_shape_check
            CHECK (
              (
                disposition = 'accepted_occurrences'
                AND jsonb_array_length(occurrence_ids) > 0
              )
              OR (
                disposition = 'unresolved_claims'
                AND jsonb_array_length(claim_ids) > 0
              )
              OR (
                disposition = 'no_occurrence'
                AND predicate_keys = '[]'::jsonb
                AND claim_ids = '[]'::jsonb
                AND occurrence_ids = '[]'::jsonb
              )
            ),
          CONSTRAINT occurrence_extraction_dispositions_metadata_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE INDEX memories_occurrence_source_chunk_idx
          ON memories (
            user_id,
            (metadata_json ->> 'source_chunk_id'),
            (metadata_json #>> '{{occurrence_proposal,source_chunk_id}}'),
            id
          )
          WHERE deleted_at IS NULL
            AND metadata_json ->> 'source_chunk_id' IS NOT NULL
            AND metadata_json #>> '{{occurrence_proposal,source_chunk_id}}' IS NOT NULL;
        CREATE INDEX occurrence_claims_resolution_created_idx
          ON occurrence_claims (user_id, resolution_status, created_at DESC, id DESC);
        CREATE INDEX occurrence_claims_count_resolution_created_idx
          ON occurrence_claims (user_id, count_key, resolution_status, created_at DESC, id DESC);
        CREATE INDEX occurrence_units_accepted_count_time_idx
          ON occurrence_units (
            user_id,
            count_key,
            occurred_at_start DESC,
            id DESC
          )
          WHERE review_status = 'accepted' AND identity_status = 'resolved';
        CREATE INDEX occurrence_units_ambiguity_group_idx
          ON occurrence_units (user_id, ambiguity_group_key)
          WHERE ambiguity_group_key IS NOT NULL;
        CREATE INDEX occurrence_units_search_tsv_idx
          ON occurrence_units
          USING gin (
            to_tsvector(
              'english',
              COALESCE(count_key, '') || ' ' || COALESCE(canonical_text, '')
            )
          )
          WHERE review_status = 'accepted' AND identity_status = 'resolved';
        CREATE INDEX occurrence_units_selector_keys_idx
          ON occurrence_units
          USING gin ((predicate_json -> 'selector_keys') jsonb_path_ops)
          WHERE review_status = 'accepted' AND identity_status = 'resolved';
        CREATE INDEX occurrence_evidence_unit_created_idx
          ON occurrence_evidence (user_id, occurrence_id, created_at ASC, id ASC);
        CREATE INDEX occurrence_evidence_claim_created_idx
          ON occurrence_evidence (user_id, claim_id, created_at ASC, id ASC);
        CREATE INDEX occurrence_evidence_source_chunk_idx
          ON occurrence_evidence (user_id, source_chunk_id)
          WHERE source_chunk_id IS NOT NULL;
        CREATE INDEX occurrence_evidence_memory_idx
          ON occurrence_evidence (user_id, memory_id)
          WHERE memory_id IS NOT NULL;
        CREATE INDEX occurrence_extraction_dispositions_summary_idx
          ON occurrence_extraction_dispositions (
            user_id,
            extractor_version,
            source_chunk_id,
            snapshot_sha256,
            review_status
          );
        """

_GRANTS = (
    "GRANT SELECT, INSERT, UPDATE ON occurrence_coverage TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON occurrence_claims TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON occurrence_units TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON occurrence_evidence TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON occurrence_extraction_dispositions TO alicebot_app",
)

_POLICIES = """
        CREATE POLICY occurrence_coverage_is_owner ON occurrence_coverage
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY occurrence_claims_is_owner ON occurrence_claims
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY occurrence_units_is_owner ON occurrence_units
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY occurrence_evidence_is_owner ON occurrence_evidence
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY occurrence_extraction_dispositions_is_owner
          ON occurrence_extraction_dispositions
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE = (
    "DROP INDEX IF EXISTS memories_occurrence_source_chunk_idx",
    "DROP TABLE IF EXISTS occurrence_extraction_dispositions",
    "DROP TABLE IF EXISTS occurrence_evidence",
    "ALTER TABLE occurrence_units DROP CONSTRAINT IF EXISTS occurrence_units_claim_fkey",
    "DROP TABLE IF EXISTS occurrence_claims",
    "DROP TABLE IF EXISTS occurrence_units",
    "DROP TABLE IF EXISTS occurrence_coverage",
)


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA)
    for statement in _GRANTS:
        op.execute(statement)
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(_POLICIES)


def downgrade() -> None:
    for statement in _DOWNGRADE:
        op.execute(statement)
