from __future__ import annotations

import json

from apps.api.src.alicebot_api.config import Settings
from alicebot_api.contracts import (
    ModelInvocationRequest,
    ModelInvocationResponse,
    PROMPT_ASSEMBLY_VERSION_V0,
    PromptAssemblyInput,
)
from alicebot_api.response_generation import (
    assemble_prompt,
    build_assistant_response_payload,
    invoke_model,
)


def make_context_pack() -> dict[str, object]:
    return {
        "compiler_version": "continuity_v0",
        "scope": {
            "user_id": "11111111-1111-1111-8111-111111111111",
            "thread_id": "22222222-2222-2222-8222-222222222222",
        },
        "limits": {
            "max_sessions": 3,
            "max_events": 8,
            "max_memories": 5,
            "max_entities": 5,
            "max_entity_edges": 10,
        },
        "user": {
            "id": "11111111-1111-1111-8111-111111111111",
            "email": "owner@example.com",
            "display_name": "Owner",
            "created_at": "2026-03-12T09:00:00+00:00",
        },
        "thread": {
            "id": "22222222-2222-2222-8222-222222222222",
            "title": "Thread",
            "created_at": "2026-03-12T09:00:00+00:00",
            "updated_at": "2026-03-12T09:05:00+00:00",
        },
        "sessions": [],
        "events": [
            {
                "id": "33333333-3333-3333-8333-333333333333",
                "session_id": None,
                "sequence_no": 1,
                "kind": "message.user",
                "payload": {"text": "Hello"},
                "created_at": "2026-03-12T09:06:00+00:00",
            }
        ],
        "memories": [
            {
                "id": "44444444-4444-4444-8444-444444444444",
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["33333333-3333-3333-8333-333333333333"],
                "created_at": "2026-03-12T09:04:00+00:00",
                "updated_at": "2026-03-12T09:05:00+00:00",
                "source_provenance": {"sources": ["symbolic"], "semantic_score": None},
            }
        ],
        "memory_summary": {
            "candidate_count": 1,
            "included_count": 1,
            "excluded_deleted_count": 0,
            "excluded_limit_count": 0,
            "hybrid_retrieval": {
                "requested": False,
                "embedding_config_id": None,
                "query_vector_dimensions": 0,
                "semantic_limit": 0,
                "symbolic_selected_count": 1,
                "semantic_selected_count": 0,
                "merged_candidate_count": 1,
                "deduplicated_count": 0,
                "included_symbolic_only_count": 1,
                "included_semantic_only_count": 0,
                "included_dual_source_count": 0,
                "similarity_metric": None,
                "source_precedence": ["symbolic", "semantic"],
                "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
                "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
            },
        },
        "artifact_chunks": [],
        "artifact_chunk_summary": {
            "requested": False,
            "scope": None,
            "query": None,
            "query_terms": [],
            "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
            "limit": 0,
            "searched_artifact_count": 0,
            "candidate_count": 0,
            "included_count": 0,
            "excluded_uningested_artifact_count": 0,
            "excluded_limit_count": 0,
            "order": [
                "matched_query_term_count_desc",
                "first_match_char_start_asc",
                "relative_path_asc",
                "sequence_no_asc",
                "id_asc",
            ],
        },
        "semantic_artifact_chunks": [],
        "semantic_artifact_chunk_summary": {
            "requested": False,
            "scope": None,
            "embedding_config_id": None,
            "query_vector_dimensions": 0,
            "limit": 0,
            "searched_artifact_count": 0,
            "candidate_count": 0,
            "included_count": 0,
            "excluded_uningested_artifact_count": 0,
            "excluded_limit_count": 0,
            "similarity_metric": None,
            "order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
        },
        "entities": [],
        "entity_summary": {
            "candidate_count": 0,
            "included_count": 0,
            "excluded_limit_count": 0,
        },
        "entity_edges": [],
        "entity_edge_summary": {
            "anchor_entity_count": 0,
            "candidate_count": 0,
            "included_count": 0,
            "excluded_limit_count": 0,
        },
    }


def test_assemble_prompt_is_deterministic_and_explicit() -> None:
    first = assemble_prompt(
        request=PromptAssemblyInput(
            context_pack=make_context_pack(),
            system_instruction="System instruction",
            developer_instruction="Developer instruction",
        ),
        compile_trace_id="compile-trace-123",
    )
    second = assemble_prompt(
        request=PromptAssemblyInput(
            context_pack=make_context_pack(),
            system_instruction="System instruction",
            developer_instruction="Developer instruction",
        ),
        compile_trace_id="compile-trace-123",
    )

    assert first.prompt_text == second.prompt_text
    assert first.prompt_sha256 == second.prompt_sha256
    assert first.trace_payload == second.trace_payload
    assert [section.name for section in first.sections] == [
        "system",
        "developer",
        "context",
        "conversation",
    ]
    assert "[SYSTEM]\nSystem instruction" in first.prompt_text
    assert "[DEVELOPER]\nDeveloper instruction" in first.prompt_text
    assert '"memory_key":"user.preference.coffee"' in first.prompt_text
    assert first.trace_payload["version"] == PROMPT_ASSEMBLY_VERSION_V0
    assert first.trace_payload["compile_trace_id"] == "compile-trace-123"
    assert first.trace_payload["included_event_count"] == 1
    assert first.trace_payload["included_memory_count"] == 1


class FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_invoke_model_sends_tools_disabled_request_and_parses_response(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            json.dumps(
                {
                    "id": "resp_123",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Assistant reply"}],
                        }
                    ],
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 4,
                        "total_tokens": 16,
                    },
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("alicebot_api.response_generation.urlopen", fake_urlopen)

    prompt = assemble_prompt(
        request=PromptAssemblyInput(
            context_pack=make_context_pack(),
            system_instruction="System instruction",
            developer_instruction="Developer instruction",
        ),
        compile_trace_id="compile-trace-123",
    )
    response = invoke_model(
        settings=Settings(
            model_provider="openai_responses",
            model_base_url="https://example.test/v1",
            model_name="gpt-5-mini",
            model_api_key="secret-key",
            model_timeout_seconds=17,
        ),
        request=ModelInvocationRequest(
            provider="openai_responses",
            model="gpt-5-mini",
            prompt=prompt,
        ),
    )

    assert captured["url"] == "https://example.test/v1/responses"
    assert captured["timeout"] == 17
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["body"]["tool_choice"] == "none"
    assert captured["body"]["tools"] == []
    assert captured["body"]["store"] is False
    assert [item["role"] for item in captured["body"]["input"]] == [
        "system",
        "developer",
        "user",
        "user",
    ]
    assert response == ModelInvocationResponse(
        provider="openai_responses",
        model="gpt-5-mini",
        response_id="resp_123",
        finish_reason="completed",
        output_text="Assistant reply",
        usage={"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
    )


def test_build_assistant_response_payload_captures_model_and_prompt_metadata() -> None:
    prompt = assemble_prompt(
        request=PromptAssemblyInput(
            context_pack=make_context_pack(),
            system_instruction="System instruction",
            developer_instruction="Developer instruction",
        ),
        compile_trace_id="compile-trace-123",
    )
    payload = build_assistant_response_payload(
        prompt=prompt,
        model_response=ModelInvocationResponse(
            provider="openai_responses",
            model="gpt-5-mini",
            response_id="resp_123",
            finish_reason="completed",
            output_text="Assistant reply",
            usage={"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
        ),
    )

    assert payload == {
        "text": "Assistant reply",
        "model": {
            "provider": "openai_responses",
            "model": "gpt-5-mini",
            "response_id": "resp_123",
            "finish_reason": "completed",
            "usage": {"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
        },
        "prompt": {
            "assembly_version": "prompt_assembly_v0",
            "prompt_sha256": prompt.prompt_sha256,
            "section_order": ["system", "developer", "context", "conversation"],
        },
    }
