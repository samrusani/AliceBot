from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import ConsentUpsertInput, PolicyCreateInput, PolicyEvaluationRequestInput
from alicebot_api.policy import (
    PolicyEvaluationValidationError,
    PolicyNotFoundError,
    create_policy_record,
    evaluate_policy_request,
    get_policy_record,
    list_consent_records,
    list_policy_records,
    upsert_consent_record,
)


class PolicyStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.user_id = uuid4()
        self.thread_id = uuid4()
        self.thread_agent_profile_id = "assistant_default"
        self.consents: dict[str, dict[str, object]] = {}
        self.policies: list[dict[str, object]] = []
        self.traces: list[dict[str, object]] = []
        self.trace_events: list[dict[str, object]] = []

    def create_consent(self, *, consent_key: str, status: str, metadata: dict[str, object]) -> dict[str, object]:
        consent = {
            "id": uuid4(),
            "user_id": self.user_id,
            "consent_key": consent_key,
            "status": status,
            "metadata": metadata,
            "created_at": self.base_time + timedelta(minutes=len(self.consents)),
            "updated_at": self.base_time + timedelta(minutes=len(self.consents)),
        }
        self.consents[consent_key] = consent
        return consent

    def get_consent_by_key_optional(self, consent_key: str) -> dict[str, object] | None:
        return self.consents.get(consent_key)

    def list_consents(self) -> list[dict[str, object]]:
        return sorted(
            self.consents.values(),
            key=lambda consent: (consent["consent_key"], consent["created_at"], consent["id"]),
        )

    def update_consent(self, *, consent_id: UUID, status: str, metadata: dict[str, object]) -> dict[str, object]:
        for consent in self.consents.values():
            if consent["id"] != consent_id:
                continue
            consent["status"] = status
            consent["metadata"] = metadata
            consent["updated_at"] = consent["updated_at"] + timedelta(minutes=5)
            return consent
        raise AssertionError("missing consent")

    def create_policy(
        self,
        *,
        agent_profile_id: str | None = None,
        name: str,
        action: str,
        scope: str,
        effect: str,
        priority: int,
        active: bool,
        conditions: dict[str, object],
        required_consents: list[str],
    ) -> dict[str, object]:
        policy = {
            "id": uuid4(),
            "user_id": self.user_id,
            "agent_profile_id": agent_profile_id,
            "name": name,
            "action": action,
            "scope": scope,
            "effect": effect,
            "priority": priority,
            "active": active,
            "conditions": conditions,
            "required_consents": required_consents,
            "created_at": self.base_time + timedelta(minutes=len(self.policies)),
            "updated_at": self.base_time + timedelta(minutes=len(self.policies)),
        }
        self.policies.append(policy)
        return policy

    def list_policies(self) -> list[dict[str, object]]:
        return sorted(
            self.policies,
            key=lambda policy: (policy["priority"], policy["created_at"], policy["id"]),
        )

    def get_policy_optional(self, policy_id: UUID) -> dict[str, object] | None:
        return next((policy for policy in self.policies if policy["id"] == policy_id), None)

    def list_active_policies(self, *, agent_profile_id: str | None = None) -> list[dict[str, object]]:
        active = [policy for policy in self.list_policies() if policy["active"] is True]
        if agent_profile_id is None:
            return active
        return [
            policy
            for policy in active
            if policy["agent_profile_id"] is None or policy["agent_profile_id"] == agent_profile_id
        ]

    def get_thread_optional(self, thread_id: UUID) -> dict[str, object] | None:
        if thread_id != self.thread_id:
            return None
        return {
            "id": self.thread_id,
            "user_id": self.user_id,
            "title": "Policy thread",
            "agent_profile_id": self.thread_agent_profile_id,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }

    def create_trace(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        kind: str,
        compiler_version: str,
        status: str,
        limits: dict[str, object],
    ) -> dict[str, object]:
        trace = {
            "id": uuid4(),
            "user_id": user_id,
            "thread_id": thread_id,
            "kind": kind,
            "compiler_version": compiler_version,
            "status": status,
            "limits": limits,
            "created_at": self.base_time,
        }
        self.traces.append(trace)
        return trace

    def append_trace_event(
        self,
        *,
        trace_id: UUID,
        sequence_no: int,
        kind: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        event = {
            "id": uuid4(),
            "trace_id": trace_id,
            "sequence_no": sequence_no,
            "kind": kind,
            "payload": payload,
            "created_at": self.base_time,
        }
        self.trace_events.append(event)
        return event


def test_upsert_consent_record_creates_and_updates_in_place() -> None:
    store = PolicyStoreStub()

    created = upsert_consent_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        consent=ConsentUpsertInput(
            consent_key="email_marketing",
            status="granted",
            metadata={"source": "settings"},
        ),
    )
    updated = upsert_consent_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        consent=ConsentUpsertInput(
            consent_key="email_marketing",
            status="revoked",
            metadata={"source": "banner"},
        ),
    )

    assert created["write_mode"] == "created"
    assert updated["write_mode"] == "updated"
    assert updated["consent"]["id"] == created["consent"]["id"]
    assert updated["consent"]["status"] == "revoked"
    assert updated["consent"]["metadata"] == {"source": "banner"}


def test_list_consent_records_returns_deterministic_shape() -> None:
    store = PolicyStoreStub()
    zeta = store.create_consent(consent_key="zeta", status="granted", metadata={})
    alpha = store.create_consent(consent_key="alpha", status="revoked", metadata={"reason": "user"})

    payload = list_consent_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
    )

    assert payload == {
        "items": [
            {
                "id": str(alpha["id"]),
                "consent_key": "alpha",
                "status": "revoked",
                "metadata": {"reason": "user"},
                "created_at": alpha["created_at"].isoformat(),
                "updated_at": alpha["updated_at"].isoformat(),
            },
            {
                "id": str(zeta["id"]),
                "consent_key": "zeta",
                "status": "granted",
                "metadata": {},
                "created_at": zeta["created_at"].isoformat(),
                "updated_at": zeta["updated_at"].isoformat(),
            },
        ],
        "summary": {
            "total_count": 2,
            "order": ["consent_key_asc", "created_at_asc", "id_asc"],
        },
    }


def test_create_and_list_policy_records_preserve_priority_order_and_shape() -> None:
    store = PolicyStoreStub()
    first = create_policy_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        policy=PolicyCreateInput(
            name="Require approval for exports",
            action="memory.export",
            scope="profile",
            effect="require_approval",
            priority=20,
            active=True,
            conditions={"channel": "email"},
            required_consents=("email_marketing", "email_marketing"),
            agent_profile_id="assistant_default",
        ),
    )
    second_policy = store.create_policy(
        name="Allow low risk read",
        action="memory.read",
        scope="profile",
        effect="allow",
        priority=10,
        active=True,
        conditions={},
        required_consents=[],
    )

    list_payload = list_policy_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
    )
    detail_payload = get_policy_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        policy_id=UUID(first["policy"]["id"]),
    )

    assert first["policy"]["required_consents"] == ["email_marketing"]
    assert first["policy"]["agent_profile_id"] == "assistant_default"
    assert [item["id"] for item in list_payload["items"]] == [
        str(second_policy["id"]),
        first["policy"]["id"],
    ]
    assert list_payload["summary"] == {
        "total_count": 2,
        "order": ["priority_asc", "created_at_asc", "id_asc"],
    }
    assert detail_payload == {"policy": first["policy"]}


def test_get_policy_record_raises_not_found_for_inaccessible_policy() -> None:
    with pytest.raises(PolicyNotFoundError, match="policy .* was not found"):
        get_policy_record(
            PolicyStoreStub(),  # type: ignore[arg-type]
            user_id=uuid4(),
            policy_id=uuid4(),
        )


def test_evaluate_policy_request_uses_first_matching_policy_and_emits_trace() -> None:
    store = PolicyStoreStub()
    store.create_consent(consent_key="email_marketing", status="granted", metadata={"source": "settings"})
    higher_priority_match = store.create_policy(
        name="Allow email export",
        action="memory.export",
        scope="profile",
        effect="allow",
        priority=10,
        active=True,
        conditions={"channel": "email"},
        required_consents=["email_marketing"],
    )
    store.create_policy(
        name="Deny fallback export",
        action="memory.export",
        scope="profile",
        effect="deny",
        priority=20,
        active=True,
        conditions={"channel": "email"},
        required_consents=[],
    )

    payload = evaluate_policy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=PolicyEvaluationRequestInput(
            thread_id=store.thread_id,
            action="memory.export",
            scope="profile",
            attributes={"channel": "email"},
        ),
    )

    assert payload["decision"] == "allow"
    assert payload["matched_policy"]["id"] == str(higher_priority_match["id"])
    assert [reason["code"] for reason in payload["reasons"]] == [
        "matched_policy",
        "policy_effect_allow",
    ]
    assert payload["evaluation"] == {
        "action": "memory.export",
        "scope": "profile",
        "evaluated_policy_count": 2,
        "matched_policy_id": str(higher_priority_match["id"]),
        "order": ["priority_asc", "created_at_asc", "id_asc"],
    }
    assert payload["trace"]["trace_event_count"] == 3
    assert [event["kind"] for event in store.trace_events] == [
        "policy.evaluate.request",
        "policy.evaluate.order",
        "policy.evaluate.decision",
    ]


def test_evaluate_policy_request_denies_when_required_consent_is_missing() -> None:
    store = PolicyStoreStub()
    matched_policy = store.create_policy(
        name="Allow export with consent",
        action="memory.export",
        scope="profile",
        effect="allow",
        priority=10,
        active=True,
        conditions={},
        required_consents=["email_marketing"],
    )

    payload = evaluate_policy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=PolicyEvaluationRequestInput(
            thread_id=store.thread_id,
            action="memory.export",
            scope="profile",
            attributes={},
        ),
    )

    assert payload["decision"] == "deny"
    assert payload["matched_policy"]["id"] == str(matched_policy["id"])
    assert [reason["code"] for reason in payload["reasons"]] == [
        "matched_policy",
        "consent_missing",
    ]


def test_evaluate_policy_request_denies_when_required_consent_is_revoked() -> None:
    store = PolicyStoreStub()
    matched_policy = store.create_policy(
        name="Allow export with consent",
        action="memory.export",
        scope="profile",
        effect="allow",
        priority=10,
        active=True,
        conditions={},
        required_consents=["email_marketing"],
    )
    store.create_consent(
        consent_key="email_marketing",
        status="revoked",
        metadata={"source": "settings"},
    )

    payload = evaluate_policy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=PolicyEvaluationRequestInput(
            thread_id=store.thread_id,
            action="memory.export",
            scope="profile",
            attributes={},
        ),
    )

    assert payload["decision"] == "deny"
    assert payload["matched_policy"]["id"] == str(matched_policy["id"])
    assert [reason["code"] for reason in payload["reasons"]] == [
        "matched_policy",
        "consent_revoked",
    ]


def test_evaluate_policy_request_returns_require_approval_and_validates_thread_scope() -> None:
    store = PolicyStoreStub()
    matched_policy = store.create_policy(
        name="Escalate export",
        action="memory.export",
        scope="profile",
        effect="require_approval",
        priority=10,
        active=True,
        conditions={},
        required_consents=[],
    )

    payload = evaluate_policy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=PolicyEvaluationRequestInput(
            thread_id=store.thread_id,
            action="memory.export",
            scope="profile",
            attributes={},
        ),
    )

    assert payload["decision"] == "require_approval"
    assert payload["matched_policy"]["id"] == str(matched_policy["id"])
    assert payload["reasons"][-1]["code"] == "policy_effect_require_approval"

    with pytest.raises(
        PolicyEvaluationValidationError,
        match="thread_id must reference an existing thread owned by the user",
    ):
        evaluate_policy_request(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=PolicyEvaluationRequestInput(
                thread_id=uuid4(),
                action="memory.export",
                scope="profile",
                attributes={},
            ),
        )


def test_evaluate_policy_request_filters_to_global_and_thread_profile_policies() -> None:
    store = PolicyStoreStub()
    store.thread_agent_profile_id = "coach_default"
    mismatched = store.create_policy(
        agent_profile_id="assistant_default",
        name="Mismatched deny",
        action="memory.export",
        scope="profile",
        effect="deny",
        priority=1,
        active=True,
        conditions={},
        required_consents=[],
    )
    global_policy = store.create_policy(
        agent_profile_id=None,
        name="Global approval",
        action="memory.export",
        scope="profile",
        effect="require_approval",
        priority=5,
        active=True,
        conditions={},
        required_consents=[],
    )
    matched = store.create_policy(
        agent_profile_id="coach_default",
        name="Matched allow",
        action="memory.export",
        scope="profile",
        effect="allow",
        priority=10,
        active=True,
        conditions={},
        required_consents=[],
    )

    payload = evaluate_policy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=PolicyEvaluationRequestInput(
            thread_id=store.thread_id,
            action="memory.export",
            scope="profile",
            attributes={},
        ),
    )

    assert payload["decision"] == "require_approval"
    assert payload["matched_policy"] is not None
    assert payload["matched_policy"]["id"] == str(global_policy["id"])
    assert payload["evaluation"]["evaluated_policy_count"] == 2

    order_event = store.trace_events[1]
    assert order_event["kind"] == "policy.evaluate.order"
    assert order_event["payload"]["policy_ids"] == [str(global_policy["id"]), str(matched["id"])]
    assert str(mismatched["id"]) not in order_event["payload"]["policy_ids"]
