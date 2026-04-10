"""Add archive-first continuity evidence tables for imported artifacts."""

from __future__ import annotations

from alembic import op


revision = "20260410_0050"
down_revision = "20260410_0049"
branch_labels = None
depends_on = None

_RLS_TABLES = (
    "continuity_artifacts",
    "continuity_artifact_copies",
    "continuity_artifact_segments",
    "continuity_object_evidence_links",
)

_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE continuity_artifacts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source_kind text NOT NULL,
          import_source_path text NOT NULL,
          relative_path text NOT NULL,
          display_name text NOT NULL,
          media_type text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, source_kind, import_source_path, relative_path),
          CONSTRAINT continuity_artifacts_source_kind_length_check
            CHECK (char_length(source_kind) >= 1 AND char_length(source_kind) <= 100),
          CONSTRAINT continuity_artifacts_import_source_path_length_check
            CHECK (char_length(import_source_path) >= 1 AND char_length(import_source_path) <= 2000),
          CONSTRAINT continuity_artifacts_relative_path_length_check
            CHECK (char_length(relative_path) >= 1 AND char_length(relative_path) <= 1000),
          CONSTRAINT continuity_artifacts_display_name_length_check
            CHECK (char_length(display_name) >= 1 AND char_length(display_name) <= 280),
          CONSTRAINT continuity_artifacts_media_type_length_check
            CHECK (char_length(media_type) >= 1 AND char_length(media_type) <= 120)
        );
        """,
    """
        CREATE TABLE continuity_artifact_copies (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          artifact_id uuid NOT NULL,
          checksum_sha256 text NOT NULL,
          content_text text NOT NULL,
          content_length_bytes integer NOT NULL,
          content_encoding text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, artifact_id, checksum_sha256),
          CONSTRAINT continuity_artifact_copies_artifact_fkey
            FOREIGN KEY (artifact_id, user_id)
            REFERENCES continuity_artifacts(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_artifact_copies_checksum_sha256_length_check
            CHECK (char_length(checksum_sha256) = 64),
          CONSTRAINT continuity_artifact_copies_content_length_bytes_check
            CHECK (content_length_bytes >= 0),
          CONSTRAINT continuity_artifact_copies_content_encoding_length_check
            CHECK (char_length(content_encoding) >= 1 AND char_length(content_encoding) <= 40)
        );
        """,
    """
        CREATE TABLE continuity_artifact_segments (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          artifact_id uuid NOT NULL,
          artifact_copy_id uuid NOT NULL,
          source_item_id text NOT NULL,
          sequence_no integer NOT NULL,
          segment_kind text NOT NULL,
          locator jsonb NOT NULL,
          raw_content text NOT NULL,
          checksum_sha256 text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, artifact_copy_id, source_item_id),
          CONSTRAINT continuity_artifact_segments_artifact_fkey
            FOREIGN KEY (artifact_id, user_id)
            REFERENCES continuity_artifacts(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_artifact_segments_artifact_copy_fkey
            FOREIGN KEY (artifact_copy_id, user_id)
            REFERENCES continuity_artifact_copies(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_artifact_segments_source_item_id_length_check
            CHECK (char_length(source_item_id) >= 1 AND char_length(source_item_id) <= 500),
          CONSTRAINT continuity_artifact_segments_sequence_no_check
            CHECK (sequence_no >= 1),
          CONSTRAINT continuity_artifact_segments_segment_kind_length_check
            CHECK (char_length(segment_kind) >= 1 AND char_length(segment_kind) <= 80),
          CONSTRAINT continuity_artifact_segments_checksum_sha256_length_check
            CHECK (char_length(checksum_sha256) = 64)
        );
        """,
    """
        CREATE TABLE continuity_object_evidence_links (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          continuity_object_id uuid NOT NULL,
          artifact_id uuid NOT NULL,
          artifact_copy_id uuid NOT NULL,
          artifact_segment_id uuid NULL,
          relationship text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT continuity_object_evidence_links_object_fkey
            FOREIGN KEY (continuity_object_id, user_id)
            REFERENCES continuity_objects(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_object_evidence_links_artifact_fkey
            FOREIGN KEY (artifact_id, user_id)
            REFERENCES continuity_artifacts(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_object_evidence_links_artifact_copy_fkey
            FOREIGN KEY (artifact_copy_id, user_id)
            REFERENCES continuity_artifact_copies(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_object_evidence_links_artifact_segment_fkey
            FOREIGN KEY (artifact_segment_id, user_id)
            REFERENCES continuity_artifact_segments(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_object_evidence_links_relationship_length_check
            CHECK (char_length(relationship) >= 1 AND char_length(relationship) <= 80)
        );
        """,
    """
        CREATE INDEX continuity_artifacts_user_kind_created_idx
          ON continuity_artifacts (user_id, source_kind, created_at DESC, id DESC);
        CREATE INDEX continuity_artifact_copies_artifact_created_idx
          ON continuity_artifact_copies (artifact_id, created_at ASC, id ASC);
        CREATE INDEX continuity_artifact_segments_artifact_sequence_idx
          ON continuity_artifact_segments (artifact_id, sequence_no ASC, id ASC);
        CREATE INDEX continuity_object_evidence_links_object_created_idx
          ON continuity_object_evidence_links (continuity_object_id, created_at ASC, id ASC);
        """,
    "GRANT SELECT, INSERT ON continuity_artifacts TO alicebot_app",
    "GRANT SELECT, INSERT ON continuity_artifact_copies TO alicebot_app",
    "GRANT SELECT, INSERT ON continuity_artifact_segments TO alicebot_app",
    "GRANT SELECT, INSERT ON continuity_object_evidence_links TO alicebot_app",
    "ALTER TABLE continuity_artifacts ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE continuity_artifacts FORCE ROW LEVEL SECURITY",
    "ALTER TABLE continuity_artifact_copies ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE continuity_artifact_copies FORCE ROW LEVEL SECURITY",
    "ALTER TABLE continuity_artifact_segments ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE continuity_artifact_segments FORCE ROW LEVEL SECURITY",
    "ALTER TABLE continuity_object_evidence_links ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE continuity_object_evidence_links FORCE ROW LEVEL SECURITY",
    """
        CREATE POLICY continuity_artifacts_read_own ON continuity_artifacts
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY continuity_artifacts_insert_own ON continuity_artifacts
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY continuity_artifact_copies_read_own ON continuity_artifact_copies
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY continuity_artifact_copies_insert_own ON continuity_artifact_copies
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY continuity_artifact_segments_read_own ON continuity_artifact_segments
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY continuity_artifact_segments_insert_own ON continuity_artifact_segments
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY continuity_object_evidence_links_read_own ON continuity_object_evidence_links
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY continuity_object_evidence_links_insert_own ON continuity_object_evidence_links
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS continuity_object_evidence_links",
    "DROP TABLE IF EXISTS continuity_artifact_segments",
    "DROP TABLE IF EXISTS continuity_artifact_copies",
    "DROP TABLE IF EXISTS continuity_artifacts",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
