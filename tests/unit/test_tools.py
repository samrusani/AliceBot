from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import (
    ToolAllowlistEvaluationRequestInput,
    ToolCreateInput,
    ToolRoutingRequestInput,
)
from alicebot_api.tools import (
    ToolAllowlistValidationError,
    create_tool_record,
    evaluate_tool_allowlist,
    get_tool_record,
    list_tool_records,
    route_tool_invocation,
    ToolRoutingValidationError,
)


class ToolStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.user_id = uuid4()
        self.thread_id = uuid4()
        self.consents: dict[str, dict[str, object]] = {}
        self.policies: list[dict[str, object]] = []
        self.tools: list[dict[str, object]] = []
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

    def list_consents(self) -> list[dict[str, object]]:
        return sorted(
            self.consents.values(),
            key=lambda consent: (consent["consent_key"], consent["created_at"], consent["id"]),
        )

    def create_policy(
        self,
        *,
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

    def list_active_policies(self) -> list[dict[str, object]]:
        return sorted(
            [policy for policy in self.policies if policy["active"] is True],
            key=lambda policy: (policy["priority"], policy["created_at"], policy["id"]),
        )

    def create_tool(
        self,
        *,
        tool_key: str,
        name: str,
        description: str,
        version: str,
        metadata_version: str,
        active: bool,
        tags: list[str],
        action_hints: list[str],
        scope_hints: list[str],
        domain_hints: list[str],
        risk_hints: list[str],
        metadata: dict[str, object],
    ) -> dict[str, object]:
        tool = {
            "id": uuid4(),
            "user_id": self.user_id,
            "tool_key": tool_key,
            "name": name,
            "description": description,
            "version": version,
            "metadata_version": metadata_version,
            "active": active,
            "tags": tags,
            "action_hints": action_hints,
            "scope_hints": scope_hints,
            "domain_hints": domain_hints,
            "risk_hints": risk_hints,
            "metadata": metadata,
            "created_at": self.base_time + timedelta(minutes=len(self.tools)),
        }
        self.tools.append(tool)
        return tool

    def get_tool_optional(self, tool_id: UUID) -> dict[str, object] | None:
        return next((tool for tool in self.tools if tool["id"] == tool_id), None)

    def list_tools(self) -> list[dict[str, object]]:
        return sorted(
            self.tools,
            key=lambda tool: (tool["tool_key"], tool["version"], tool["created_at"], tool["id"]),
        )

    def list_active_tools(self) -> list[dict[str, object]]:
        return [tool for tool in self.list_tools() if tool["active"] is True]

    def get_thread_optional(self, thread_id: UUID) -> dict[str, object] | None:
        if thread_id != self.thread_id:
            return None
        return {
            "id": self.thread_id,
            "user_id": self.user_id,
            "title": "Tool thread",
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


def test_create_list_and_get_tool_records_preserve_deterministic_order() -> None:
    store = ToolStoreStub()
    later = create_tool_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        tool=ToolCreateInput(
            tool_key="zeta.fetch",
            name="Zeta Fetch",
            description="Fetch zeta records.",
            version="2.0.0",
            action_hints=("tool.run",),
            scope_hints=("workspace",),
        ),
    )
    earlier = store.create_tool(
        tool_key="alpha.open",
        name="Alpha Open",
        description="Open alpha pages.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["browser"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=["docs"],
        risk_hints=[],
        metadata={"transport": "proxy"},
    )

    listed = list_tool_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
    )
    detail = get_tool_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        tool_id=UUID(later["tool"]["id"]),
    )

    assert [item["tool_key"] for item in listed["items"]] == ["alpha.open", "zeta.fetch"]
    assert listed["summary"] == {
        "total_count": 2,
        "order": ["tool_key_asc", "version_asc", "created_at_asc", "id_asc"],
    }
    assert detail == {"tool": later["tool"]}
    assert listed["items"][0]["id"] == str(earlier["id"])


def test_evaluate_tool_allowlist_splits_allowed_denied_and_approval_required() -> None:
    store = ToolStoreStub()
    store.create_consent(consent_key="web_access", status="granted", metadata={"source": "settings"})
    allowed_tool = store.create_tool(
        tool_key="browser.open",
        name="Browser Open",
        description="Open documentation pages.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["browser"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=["docs"],
        risk_hints=[],
        metadata={"transport": "proxy"},
    )
    denied_tool = store.create_tool(
        tool_key="calendar.read",
        name="Calendar Read",
        description="Read a calendar.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["calendar"],
        action_hints=["calendar.read"],
        scope_hints=["calendar"],
        domain_hints=[],
        risk_hints=[],
        metadata={},
    )
    approval_tool = store.create_tool(
        tool_key="shell.exec",
        name="Shell Exec",
        description="Run shell commands.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["shell"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=[],
        risk_hints=[],
        metadata={"transport": "local"},
    )

    store.create_policy(
        name="Allow docs browser",
        action="tool.run",
        scope="workspace",
        effect="allow",
        priority=10,
        active=True,
        conditions={"tool_key": "browser.open", "domain_hint": "docs"},
        required_consents=["web_access"],
    )
    store.create_policy(
        name="Require shell approval",
        action="tool.run",
        scope="workspace",
        effect="require_approval",
        priority=20,
        active=True,
        conditions={"tool_key": "shell.exec"},
        required_consents=[],
    )

    payload = evaluate_tool_allowlist(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ToolAllowlistEvaluationRequestInput(
            thread_id=store.thread_id,
            action="tool.run",
            scope="workspace",
            domain_hint="docs",
            attributes={},
        ),
    )

    assert payload["allowed"] == [
        {
            "decision": "allowed",
            "tool": {
                "id": str(allowed_tool["id"]),
                "tool_key": "browser.open",
                "name": "Browser Open",
                "description": "Open documentation pages.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["browser"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": ["docs"],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
                "created_at": allowed_tool["created_at"].isoformat(),
            },
            "reasons": [
                {
                    "code": "tool_metadata_matched",
                    "source": "tool",
                    "message": "Tool metadata matched the requested action, scope, and optional hints.",
                    "tool_id": str(allowed_tool["id"]),
                    "policy_id": None,
                    "consent_key": None,
                },
                {
                    "code": "matched_policy",
                    "source": "policy",
                    "message": "Matched policy 'Allow docs browser' at priority 10.",
                    "tool_id": str(allowed_tool["id"]),
                    "policy_id": str(store.policies[0]["id"]),
                    "consent_key": None,
                },
                {
                    "code": "policy_effect_allow",
                    "source": "policy",
                    "message": "Policy effect resolved the decision to 'allow'.",
                    "tool_id": str(allowed_tool["id"]),
                    "policy_id": str(store.policies[0]["id"]),
                    "consent_key": None,
                },
            ],
        }
    ]
    assert [item["tool"]["id"] for item in payload["approval_required"]] == [str(approval_tool["id"])]
    assert payload["approval_required"][0]["reasons"][-1]["code"] == "policy_effect_require_approval"
    assert [item["tool"]["id"] for item in payload["denied"]] == [str(denied_tool["id"])]
    assert [reason["code"] for reason in payload["denied"][0]["reasons"]] == [
        "tool_action_unsupported",
        "tool_scope_unsupported",
    ]
    assert payload["summary"] == {
        "action": "tool.run",
        "scope": "workspace",
        "domain_hint": "docs",
        "risk_hint": None,
        "evaluated_tool_count": 3,
        "allowed_count": 1,
        "denied_count": 1,
        "approval_required_count": 1,
        "order": ["tool_key_asc", "version_asc", "created_at_asc", "id_asc"],
    }
    assert payload["trace"]["trace_event_count"] == 6
    assert [event["kind"] for event in store.trace_events] == [
        "tool.allowlist.request",
        "tool.allowlist.order",
        "tool.allowlist.decision",
        "tool.allowlist.decision",
        "tool.allowlist.decision",
        "tool.allowlist.summary",
    ]


def test_evaluate_tool_allowlist_validates_thread_scope() -> None:
    with pytest.raises(
        ToolAllowlistValidationError,
        match="thread_id must reference an existing thread owned by the user",
    ):
        evaluate_tool_allowlist(
            ToolStoreStub(),  # type: ignore[arg-type]
            user_id=uuid4(),
            request=ToolAllowlistEvaluationRequestInput(
                thread_id=uuid4(),
                action="tool.run",
                scope="workspace",
                attributes={},
            ),
        )


def test_route_tool_invocation_returns_ready_with_trace() -> None:
    store = ToolStoreStub()
    store.create_consent(consent_key="web_access", status="granted", metadata={"source": "settings"})
    tool = store.create_tool(
        tool_key="browser.open",
        name="Browser Open",
        description="Open documentation pages.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["browser"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=["docs"],
        risk_hints=[],
        metadata={"transport": "proxy"},
    )
    policy = store.create_policy(
        name="Allow docs browser",
        action="tool.run",
        scope="workspace",
        effect="allow",
        priority=10,
        active=True,
        conditions={"tool_key": "browser.open", "domain_hint": "docs"},
        required_consents=["web_access"],
    )

    payload = route_tool_invocation(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ToolRoutingRequestInput(
            thread_id=store.thread_id,
            tool_id=tool["id"],
            action="tool.run",
            scope="workspace",
            domain_hint="docs",
            attributes={"channel": "chat"},
        ),
    )

    assert payload == {
        "request": {
            "thread_id": str(store.thread_id),
            "tool_id": str(tool["id"]),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": "docs",
            "risk_hint": None,
            "attributes": {"channel": "chat"},
        },
        "decision": "ready",
        "tool": {
            "id": str(tool["id"]),
            "tool_key": "browser.open",
            "name": "Browser Open",
            "description": "Open documentation pages.",
            "version": "1.0.0",
            "metadata_version": "tool_metadata_v0",
            "active": True,
            "tags": ["browser"],
            "action_hints": ["tool.run"],
            "scope_hints": ["workspace"],
            "domain_hints": ["docs"],
            "risk_hints": [],
            "metadata": {"transport": "proxy"},
            "created_at": tool["created_at"].isoformat(),
        },
        "reasons": [
            {
                "code": "tool_metadata_matched",
                "source": "tool",
                "message": "Tool metadata matched the requested action, scope, and optional hints.",
                "tool_id": str(tool["id"]),
                "policy_id": None,
                "consent_key": None,
            },
            {
                "code": "matched_policy",
                "source": "policy",
                "message": "Matched policy 'Allow docs browser' at priority 10.",
                "tool_id": str(tool["id"]),
                "policy_id": str(policy["id"]),
                "consent_key": None,
            },
            {
                "code": "policy_effect_allow",
                "source": "policy",
                "message": "Policy effect resolved the decision to 'allow'.",
                "tool_id": str(tool["id"]),
                "policy_id": str(policy["id"]),
                "consent_key": None,
            },
        ],
        "summary": {
            "thread_id": str(store.thread_id),
            "tool_id": str(tool["id"]),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": "docs",
            "risk_hint": None,
            "decision": "ready",
            "evaluated_tool_count": 1,
            "active_policy_count": 1,
            "consent_count": 1,
            "order": ["tool_key_asc", "version_asc", "created_at_asc", "id_asc"],
        },
        "trace": {
            "trace_id": str(store.traces[0]["id"]),
            "trace_event_count": 3,
        },
    }
    assert store.traces[0]["kind"] == "tool.route"
    assert store.traces[0]["compiler_version"] == "tool_routing_v0"
    assert [event["kind"] for event in store.trace_events] == [
        "tool.route.request",
        "tool.route.decision",
        "tool.route.summary",
    ]
    assert store.trace_events[1]["payload"]["allowlist_decision"] == "allowed"
    assert store.trace_events[1]["payload"]["routing_decision"] == "ready"


def test_route_tool_invocation_returns_denied_for_metadata_or_policy_denial() -> None:
    store = ToolStoreStub()
    tool = store.create_tool(
        tool_key="calendar.read",
        name="Calendar Read",
        description="Read calendars.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["calendar"],
        action_hints=["calendar.read"],
        scope_hints=["calendar"],
        domain_hints=[],
        risk_hints=[],
        metadata={},
    )

    payload = route_tool_invocation(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ToolRoutingRequestInput(
            thread_id=store.thread_id,
            tool_id=tool["id"],
            action="tool.run",
            scope="workspace",
            attributes={},
        ),
    )

    assert payload["decision"] == "denied"
    assert [reason["code"] for reason in payload["reasons"]] == [
        "tool_action_unsupported",
        "tool_scope_unsupported",
    ]
    assert payload["summary"]["decision"] == "denied"
    assert payload["trace"]["trace_event_count"] == 3


def test_route_tool_invocation_returns_approval_required() -> None:
    store = ToolStoreStub()
    tool = store.create_tool(
        tool_key="shell.exec",
        name="Shell Exec",
        description="Run shell commands.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["shell"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=[],
        risk_hints=[],
        metadata={"transport": "local"},
    )
    policy = store.create_policy(
        name="Require shell approval",
        action="tool.run",
        scope="workspace",
        effect="require_approval",
        priority=10,
        active=True,
        conditions={"tool_key": "shell.exec"},
        required_consents=[],
    )

    payload = route_tool_invocation(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ToolRoutingRequestInput(
            thread_id=store.thread_id,
            tool_id=tool["id"],
            action="tool.run",
            scope="workspace",
            attributes={},
        ),
    )

    assert payload["decision"] == "approval_required"
    assert payload["summary"]["decision"] == "approval_required"
    assert payload["reasons"][-1] == {
        "code": "policy_effect_require_approval",
        "source": "policy",
        "message": "Policy effect resolved the decision to 'require_approval'.",
        "tool_id": str(tool["id"]),
        "policy_id": str(policy["id"]),
        "consent_key": None,
    }


def test_route_tool_invocation_validates_thread_scope() -> None:
    store = ToolStoreStub()
    tool = store.create_tool(
        tool_key="browser.open",
        name="Browser Open",
        description="Open documentation pages.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["browser"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=[],
        risk_hints=[],
        metadata={},
    )

    with pytest.raises(
        ToolRoutingValidationError,
        match="thread_id must reference an existing thread owned by the user",
    ):
        route_tool_invocation(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ToolRoutingRequestInput(
                thread_id=uuid4(),
                tool_id=tool["id"],
                action="tool.run",
                scope="workspace",
                attributes={},
            ),
        )


def test_route_tool_invocation_validates_active_tool_scope() -> None:
    store = ToolStoreStub()
    inactive_tool = store.create_tool(
        tool_key="browser.open",
        name="Browser Open",
        description="Open documentation pages.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=False,
        tags=["browser"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=[],
        risk_hints=[],
        metadata={},
    )

    with pytest.raises(
        ToolRoutingValidationError,
        match="tool_id must reference an existing active tool owned by the user",
    ):
        route_tool_invocation(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ToolRoutingRequestInput(
                thread_id=store.thread_id,
                tool_id=inactive_tool["id"],
                action="tool.run",
                scope="workspace",
                attributes={},
            ),
        )
