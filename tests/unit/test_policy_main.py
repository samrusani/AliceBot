from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.policy import PolicyEvaluationValidationError, PolicyNotFoundError


def test_upsert_consent_endpoint_translates_request_and_returns_created_status(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_upsert_consent_record(store, *, user_id, consent):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["consent"] = consent
        return {
            "consent": {
                "id": "consent-123",
                "consent_key": "email_marketing",
                "status": "granted",
                "metadata": {"source": "settings"},
                "created_at": "2026-03-12T09:00:00+00:00",
                "updated_at": "2026-03-12T09:00:00+00:00",
            },
            "write_mode": "created",
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "upsert_consent_record", fake_upsert_consent_record)

    response = main_module.upsert_consent(
        main_module.UpsertConsentRequest(
            user_id=user_id,
            consent_key="email_marketing",
            status="granted",
            metadata={"source": "settings"},
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "consent": {
            "id": "consent-123",
            "consent_key": "email_marketing",
            "status": "granted",
            "metadata": {"source": "settings"},
            "created_at": "2026-03-12T09:00:00+00:00",
            "updated_at": "2026-03-12T09:00:00+00:00",
        },
        "write_mode": "created",
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["consent"].consent_key == "email_marketing"
    assert captured["consent"].status == "granted"
    assert captured["consent"].metadata == {"source": "settings"}


def test_get_policy_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    policy_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_policy_record(*_args, **_kwargs):
        raise PolicyNotFoundError(f"policy {policy_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_policy_record", fake_get_policy_record)

    response = main_module.get_policy(policy_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"policy {policy_id} was not found"}


def test_evaluate_policy_endpoint_translates_request_and_returns_trace_payload(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_evaluate_policy_request(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "decision": "allow",
            "matched_policy": {
                "id": "policy-123",
                "name": "Allow export",
                "action": "memory.export",
                "scope": "profile",
                "effect": "allow",
                "priority": 10,
                "active": True,
                "conditions": {"channel": "email"},
                "required_consents": ["email_marketing"],
                "created_at": "2026-03-12T09:00:00+00:00",
                "updated_at": "2026-03-12T09:00:00+00:00",
            },
            "reasons": [
                {
                    "code": "matched_policy",
                    "source": "policy",
                    "message": "Matched policy 'Allow export' at priority 10.",
                    "policy_id": "policy-123",
                    "consent_key": None,
                },
                {
                    "code": "policy_effect_allow",
                    "source": "policy",
                    "message": "Policy effect resolved the decision to 'allow'.",
                    "policy_id": "policy-123",
                    "consent_key": None,
                },
            ],
            "evaluation": {
                "action": "memory.export",
                "scope": "profile",
                "evaluated_policy_count": 1,
                "matched_policy_id": "policy-123",
                "order": ["priority_asc", "created_at_asc", "id_asc"],
            },
            "trace": {"trace_id": "trace-123", "trace_event_count": 3},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "evaluate_policy_request", fake_evaluate_policy_request)

    response = main_module.evaluate_policy(
        main_module.EvaluatePolicyRequest(
            user_id=user_id,
            thread_id=thread_id,
            action="memory.export",
            scope="profile",
            attributes={"channel": "email"},
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["trace"] == {"trace_id": "trace-123", "trace_event_count": 3}
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].thread_id == thread_id
    assert captured["request"].action == "memory.export"
    assert captured["request"].scope == "profile"
    assert captured["request"].attributes == {"channel": "email"}


def test_evaluate_policy_endpoint_maps_validation_errors_to_400(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_evaluate_policy_request(*_args, **_kwargs):
        raise PolicyEvaluationValidationError("thread_id must reference an existing thread owned by the user")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "evaluate_policy_request", fake_evaluate_policy_request)

    response = main_module.evaluate_policy(
        main_module.EvaluatePolicyRequest(
            user_id=user_id,
            thread_id=uuid4(),
            action="memory.export",
            scope="profile",
            attributes={},
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "thread_id must reference an existing thread owned by the user"
    }
