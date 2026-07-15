from __future__ import annotations

import importlib

from alicebot_api.vnext_capture import capture_dedupe_key_for_text


MODULE_NAME = "apps.api.alembic.versions.20260714_0090_project_scope_identity"


def test_revision_repairs_presence_aware_conservative_source_identity(monkeypatch) -> None:
    module = importlib.import_module(MODULE_NAME)
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert module.revision == "20260714_0090"
    assert module.down_revision == "20260713_0089"
    assert executed[0] == "DROP INDEX IF EXISTS sources_user_dedupe_key_unique_idx"
    joined = "\n".join(executed)
    assert "resource ? 'project_scope'" in joined
    assert "metadata_container ? 'project_scope'" in joined
    assert "scope_container ? 'project_scope'" in joined
    assert "metadata_container #> '{agentic_memory,project_scope}'" in joined
    assert "metadata_container #> '{agent_identity,project_scope}'" in joined
    assert "scope_container #> '{agentic_memory,project_scope}'" in joined
    assert "scope_container #> '{agent_identity,project_scope}'" in joined
    for nested_container in (
        "metadata_container -> 'agentic_memory'",
        "metadata_container -> 'agent_identity'",
        "scope_container -> 'agentic_memory'",
        "scope_container -> 'agent_identity'",
    ):
        assert f"jsonb_typeof({nested_container}) = 'object'" in joined
        assert f"({nested_container}) ? 'project_scope'" in joined
    nested_presence = joined.index("jsonb_typeof(metadata_container -> 'agentic_memory') = 'object'")
    root_alias = joined.index("resource -> 'project_id'")
    assert nested_presence < root_alias
    nested_block = joined[joined.index("-- Historical nested project_scope") : joined.index("-- Root aliases")]
    assert "IF cardinality(resolved) > 0" not in nested_block
    assert "resource -> 'project_id'" in joined
    assert "resource -> 'project'" in joined
    assert "resource -> 'projects'" in joined
    assert "metadata_container -> 'project_id'" in joined
    assert "scope_container -> 'projects'" in joined
    assert "metadata_container #> '{agentic_memory,project_id}'" in joined
    assert "scope_container #> '{agentic_memory,projects}'" in joined
    assert "alice_source_scope_resource(source.metadata_json)" in joined
    assert "ARRAY['agentic_memory', 'agent_identity']" in joined
    assert "direct_nested || stored_nested" in joined
    assert "agent_identity,project_id" not in joined
    assert "octet_length(normalized_scope.value) = char_length(normalized_scope.value)" in joined
    assert "translate(" in joined
    assert "chr(9) || chr(10) || chr(11) || chr(12) || chr(13)" in joined
    assert 'COLLATE "C"' in joined
    assert "SELECT DISTINCT lower" not in joined
    assert "::numeric = trunc(" in joined
    assert "THEN '0'" in joined
    assert "^-?(0|[1-9][0-9]*)$" not in joined
    assert "domain:" in joined
    assert "sensitivity:" in joined
    assert "row_number() OVER" in joined
    assert "duplicate_rank = 1" in joined
    assert "CREATE UNIQUE INDEX sources_user_dedupe_key_unique_idx" in joined
    assert joined.index("DROP FUNCTION IF EXISTS pg_temp.alice_resolve_project_scope") < joined.index(
        "CREATE UNIQUE INDEX sources_user_dedupe_key_unique_idx"
    )


def test_downgrade_retains_repaired_values_and_rebuilds_uniqueness(monkeypatch) -> None:
    module = importlib.import_module(MODULE_NAME)
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert len(executed) == 2
    assert executed[0] == "DROP INDEX IF EXISTS sources_user_dedupe_key_unique_idx"
    assert "CREATE UNIQUE INDEX" in executed[1]
    assert all("UPDATE sources" not in statement for statement in executed)


def test_capture_text_normalizer_mirrors_python_312_strip_without_widening_project_ids() -> None:
    module = importlib.import_module(MODULE_NAME)
    expected_codepoints = (
        *range(0x0009, 0x000E),
        *range(0x001C, 0x0021),
        0x0085,
        0x00A0,
        0x1680,
        *range(0x2000, 0x200B),
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
    )
    assert module._PYTHON_312_STRIP_CODEPOINTS == expected_codepoints

    raw_text_normalizer = module._INSTALL_CAPTURE_TEXT_NORMALIZER_HELPER
    assert "[[:space:]]" not in raw_text_normalizer
    assert "regexp_replace" not in raw_text_normalizer
    assert "replace(replace(raw_text, E'\\r\\n', E'\\n'), E'\\r', E'\\n')" in raw_text_normalizer
    assert all(f"chr({codepoint})" in raw_text_normalizer for codepoint in expected_codepoints)
    assert "alice_normalize_capture_text(" in module._RECOMPUTE_LIVE_SOURCE_IDENTITIES

    # Project identifiers intentionally retain the narrower six-ASCII rule.
    project_identifier_normalizer = module._INSTALL_NORMALIZED_SCOPE_HELPER
    assert "chr(133)" not in project_identifier_normalizer
    assert "chr(160)" not in project_identifier_normalizer
    assert "chr(8195)" not in project_identifier_normalizer

    golden_keys = {
        "\u00a0Fact: NBSP boundary\u00a0": "capture-md5:989339e5b12bc37696a4ab7953caab6d",
        "\u0085Fact: NEL boundary\u0085": "capture-md5:4586e4b25d3a6d59410354f874227481",
        "\u2003Fact: EM SPACE boundary\u2003": "capture-md5:6384e336106457a8c146e9c8c8463bbc",
        "\u00a0\r\nFact: newline normalization\r\u0085": "capture-md5:a26f83e20eeaba800b8454b10d70c630",
    }
    for raw_text, expected_key in golden_keys.items():
        assert (
            capture_dedupe_key_for_text(
                raw_text,
                ("Legacy Project",),
                domain="project",
                sensitivity="private",
            )
            == expected_key
        )
