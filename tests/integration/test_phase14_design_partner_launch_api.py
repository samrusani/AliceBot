from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlencode

import anyio
import psycopg
from psycopg.rows import dict_row

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings


def invoke_request(
    method: str,
    path: str,
    *,
    query_params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, object]] = []
    encoded_body = b"" if payload is None else json.dumps(payload).encode()
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}

        request_received = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    query_string = urlencode(query_params or {}).encode()
    request_headers = [(b"content-type", b"application/json")]
    for key, value in (headers or {}).items():
        request_headers.append((key.lower().encode(), value.encode()))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": request_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    anyio.run(main_module.app, scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start_message["status"], json.loads(body)


def auth_header(session_token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {session_token}"}


def _configure_settings(migrated_database_urls, monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            app_env="test",
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
            hosted_chat_rate_limit_window_seconds=60,
            hosted_chat_rate_limit_max_requests=20,
            hosted_scheduler_rate_limit_window_seconds=300,
            hosted_scheduler_rate_limit_max_requests=20,
            hosted_abuse_window_seconds=600,
            hosted_abuse_block_threshold=5,
            hosted_rate_limits_enabled_by_default=True,
            hosted_abuse_controls_enabled_by_default=True,
        ),
    )


def _create_workspace(session_token: str, *, name: str) -> str:
    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": name},
        headers=auth_header(session_token),
    )
    assert create_workspace_status == 201
    workspace_id = create_workspace_payload["workspace"]["id"]

    bootstrap_status, bootstrap_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert bootstrap_status == 200
    assert bootstrap_payload["workspace"]["bootstrap_status"] == "ready"
    return workspace_id


def _bootstrap_workspace_session(email: str, *, workspace_name: str) -> tuple[str, str, str]:
    start_status, start_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/start",
        payload={"email": email},
    )
    assert start_status == 200

    verify_status, verify_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/verify",
        payload={
            "challenge_token": start_payload["challenge"]["challenge_token"],
            "device_label": "P14-S5 Device",
            "device_key": f"device-{email}",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]
    user_account_id = verify_payload["user_account"]["id"]
    workspace_id = _create_workspace(session_token, name=workspace_name)
    return session_token, workspace_id, user_account_id


def _promote_session_to_operator(migrated_database_urls, *, session_token: str) -> str:
    token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
    with psycopg.connect(migrated_database_urls["app"], row_factory=dict_row) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_account_id
                    FROM auth_sessions
                    WHERE session_token_hash = %s
                    LIMIT 1
                    """,
                    (token_hash,),
                )
                session = cur.fetchone()
                assert session is not None
                user_account_id = session["user_account_id"]

                cur.execute(
                    """
                    INSERT INTO beta_cohorts (cohort_key, description)
                    VALUES ('p10-ops', 'Phase 10 hosted beta operator cohort')
                    ON CONFLICT (cohort_key) DO NOTHING
                    """,
                )
                cur.execute(
                    """
                    UPDATE user_accounts
                    SET beta_cohort_key = 'p10-ops'
                    WHERE id = %s
                    """,
                    (user_account_id,),
                )
    return str(user_account_id)


def _seed_provider_invocation_telemetry(
    admin_db_url: str,
    *,
    workspace_id: str,
    user_account_id: str,
    display_name: str,
) -> None:
    with psycopg.connect(admin_db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_providers (
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  default_model,
                  status,
                  metadata
                )
                VALUES (
                  %s,
                  %s,
                  'openai_compatible',
                  'openai_responses',
                  %s,
                  'https://provider.example',
                  'test-key',
                  'gpt-oss-20b',
                  'active',
                  '{}'::jsonb
                )
                RETURNING id
                """,
                (workspace_id, user_account_id, display_name),
            )
            provider_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO provider_invocation_telemetry (
                  workspace_id,
                  provider_id,
                  thread_id,
                  invoked_by_user_account_id,
                  invocation_kind,
                  adapter_key,
                  runtime_provider,
                  requested_model,
                  response_model,
                  response_id,
                  status,
                  latency_ms,
                  usage,
                  error_detail
                )
                VALUES (
                  %s,
                  %s,
                  NULL,
                  %s,
                  'runtime_invoke',
                  'openai_compatible',
                  'openai_responses',
                  'gpt-oss-20b',
                  'gpt-oss-20b',
                  %s,
                  'succeeded',
                  120,
                  '{"input_tokens": 15, "output_tokens": 6, "total_tokens": 21}'::jsonb,
                  NULL
                )
                """,
                (workspace_id, provider_id, user_account_id, f"resp-{display_name}"),
            )
        conn.commit()


def test_design_partner_launch_admin_endpoints_require_operator_access(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, _, _ = _bootstrap_workspace_session(
        "design-partner-reader@example.com",
        workspace_name="Design Partner Reader Workspace",
    )

    status, payload = invoke_request(
        "GET",
        "/v1/admin/hosted/design-partners/dashboard",
        headers=auth_header(session_token),
    )

    assert status == 403
    assert "hosted_admin_operator" in payload["detail"]


def test_design_partner_launch_tracks_linkage_feedback_and_usage_summary(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_alpha, operator_user_account_id = _bootstrap_workspace_session(
        "design-partner-ops@example.com",
        workspace_name="Partner Alpha Workspace",
    )
    _promote_session_to_operator(migrated_database_urls, session_token=session_token)
    workspace_beta = _create_workspace(session_token, name="Partner Beta Workspace")
    workspace_gamma = _create_workspace(session_token, name="Partner Gamma Workspace")

    partner_specs = [
        {
            "name": "Partner Alpha",
            "lifecycle_stage": "active",
            "instrumentation_status": "ready",
            "case_study_status": "candidate",
            "workspace_id": workspace_alpha,
        },
        {
            "name": "Partner Beta",
            "lifecycle_stage": "pilot",
            "instrumentation_status": "ready",
            "case_study_status": "not_started",
            "workspace_id": workspace_beta,
        },
        {
            "name": "Partner Gamma",
            "lifecycle_stage": "pilot",
            "instrumentation_status": "partial",
            "case_study_status": "not_started",
            "workspace_id": workspace_gamma,
        },
    ]

    design_partner_ids: list[str] = []
    for spec in partner_specs:
        create_status, create_payload = invoke_request(
            "POST",
            "/v1/admin/hosted/design-partners",
            headers=auth_header(session_token),
            payload={
                "name": spec["name"],
                "lifecycle_stage": spec["lifecycle_stage"],
                "instrumentation_status": spec["instrumentation_status"],
                "case_study_status": spec["case_study_status"],
                "support_status": "green",
                "onboarding_status": "in_progress",
                "target_outcome": "Ship a production-like pilot with tracked usage.",
            },
        )
        assert create_status == 201
        design_partner_ids.append(create_payload["design_partner"]["id"])

    for design_partner_id, spec in zip(design_partner_ids, partner_specs, strict=True):
        link_status, link_payload = invoke_request(
            "POST",
            f"/v1/admin/hosted/design-partners/{design_partner_id}/workspaces",
            headers=auth_header(session_token),
            payload={
                "workspace_id": spec["workspace_id"],
                "linkage_status": spec["lifecycle_stage"] if spec["lifecycle_stage"] != "active" else "active",
                "environment_label": "pilot",
                "instrumentation_ready": spec["instrumentation_status"] == "ready",
                "notes": "Tracked pilot workspace.",
            },
        )
        assert link_status == 201
        assert len(link_payload["design_partner"]["linked_workspaces"]) == 1

        _seed_provider_invocation_telemetry(
            migrated_database_urls["admin"],
            workspace_id=spec["workspace_id"],
            user_account_id=operator_user_account_id,
            display_name=f"{spec['name']} Provider",
        )

    feedback_status, feedback_payload = invoke_request(
        "POST",
        f"/v1/admin/hosted/design-partners/{design_partner_ids[0]}/feedback",
        headers=auth_header(session_token),
        payload={
            "workspace_id": workspace_alpha,
            "source_kind": "partner_call",
            "category": "win",
            "sentiment": "positive",
            "urgency": "medium",
            "feedback_status": "new",
            "case_study_signal": True,
            "summary": "Pilot team wants to use this rollout as a case-study candidate.",
            "detail": "They reported clear improvement in provider switching confidence.",
            "metadata": {"meeting_type": "weekly_review"},
        },
    )
    assert feedback_status == 201
    assert feedback_payload["feedback"]["case_study_signal"] is True

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/design-partners",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    assert list_payload["summary"]["total_count"] == 3
    assert list_payload["summary"]["active_or_pilot_count"] == 3
    assert list_payload["summary"]["usage_visible_count"] == 3
    assert list_payload["summary"]["candidate_case_study_count"] == 1
    assert list_payload["summary"]["open_feedback_count"] == 1
    assert all(item["usage_summary"]["runtime_invocation_count"] == 1 for item in list_payload["items"])

    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v1/admin/hosted/design-partners/{design_partner_ids[0]}",
        headers=auth_header(session_token),
    )
    assert detail_status == 200
    assert detail_payload["design_partner"]["name"] == "Partner Alpha"
    assert detail_payload["design_partner"]["feedback_summary"]["case_study_signal_count"] == 1
    assert detail_payload["design_partner"]["onboarding_checklist"]["summary"]["completed_count"] >= 1
    assert detail_payload["feedback"][0]["workspace_id"] == workspace_alpha

    dashboard_status, dashboard_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/design-partners/dashboard",
        headers=auth_header(session_token),
    )
    assert dashboard_status == 200
    assert dashboard_payload["dashboard"]["summary"]["active_or_pilot_count"] == 3
    assert dashboard_payload["dashboard"]["launch_readiness"]["status"] == "on_track"
    assert dashboard_payload["dashboard"]["launch_readiness"]["acceptance_snapshot"] == {
        "three_partners_active_or_pilot": True,
        "usage_summaries_visible": True,
        "structured_feedback_present": True,
        "candidate_case_study_underway": True,
    }
    assert dashboard_payload["dashboard"]["usage"]["runtime_invocation_count"] == 3


def test_design_partner_feedback_rejects_unlinked_workspace(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id, _ = _bootstrap_workspace_session(
        "design-partner-feedback@example.com",
        workspace_name="Feedback Validation Workspace",
    )
    _promote_session_to_operator(migrated_database_urls, session_token=session_token)

    create_status, create_payload = invoke_request(
        "POST",
        "/v1/admin/hosted/design-partners",
        headers=auth_header(session_token),
        payload={
            "name": "Partner Delta",
            "lifecycle_stage": "onboarding",
            "support_status": "green",
            "instrumentation_status": "not_ready",
            "case_study_status": "not_started",
        },
    )
    assert create_status == 201
    design_partner_id = create_payload["design_partner"]["id"]

    feedback_status, feedback_payload = invoke_request(
        "POST",
        f"/v1/admin/hosted/design-partners/{design_partner_id}/feedback",
        headers=auth_header(session_token),
        payload={
            "workspace_id": workspace_id,
            "source_kind": "operator_note",
            "category": "onboarding",
            "sentiment": "neutral",
            "urgency": "low",
            "summary": "Workspace is not linked yet.",
        },
    )

    assert feedback_status == 400
    assert "is not linked to design partner" in feedback_payload["detail"]


def test_design_partner_dashboard_requires_real_usage_and_feedback_evidence(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_alpha, _ = _bootstrap_workspace_session(
        "design-partner-readiness@example.com",
        workspace_name="Readiness Alpha Workspace",
    )
    _promote_session_to_operator(migrated_database_urls, session_token=session_token)
    workspace_beta = _create_workspace(session_token, name="Readiness Beta Workspace")
    workspace_gamma = _create_workspace(session_token, name="Readiness Gamma Workspace")

    workspaces = [workspace_alpha, workspace_beta, workspace_gamma]
    for index, workspace_id in enumerate(workspaces, start=1):
        create_status, create_payload = invoke_request(
            "POST",
            "/v1/admin/hosted/design-partners",
            headers=auth_header(session_token),
            payload={
                "name": f"Readiness Partner {index}",
                "lifecycle_stage": "pilot",
                "onboarding_status": "in_progress",
                "support_status": "green",
                "instrumentation_status": "partial",
                "case_study_status": "not_started",
                "target_outcome": "Validate launch readiness tracking only when evidence exists.",
            },
        )
        assert create_status == 201
        design_partner_id = create_payload["design_partner"]["id"]

        link_status, _ = invoke_request(
            "POST",
            f"/v1/admin/hosted/design-partners/{design_partner_id}/workspaces",
            headers=auth_header(session_token),
            payload={
                "workspace_id": workspace_id,
                "linkage_status": "pilot",
                "environment_label": "pilot",
                "instrumentation_ready": False,
                "notes": "Linked but not yet producing runtime evidence.",
            },
        )
        assert link_status == 201

    dashboard_status, dashboard_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/design-partners/dashboard",
        headers=auth_header(session_token),
    )

    assert dashboard_status == 200
    assert dashboard_payload["dashboard"]["summary"]["active_or_pilot_count"] == 3
    assert dashboard_payload["dashboard"]["summary"]["usage_visible_count"] == 0
    assert dashboard_payload["dashboard"]["summary"]["feedback_captured_count"] == 0
    assert dashboard_payload["dashboard"]["launch_readiness"]["status"] == "needs_attention"
    assert dashboard_payload["dashboard"]["launch_readiness"]["acceptance_snapshot"] == {
        "three_partners_active_or_pilot": True,
        "usage_summaries_visible": False,
        "structured_feedback_present": False,
        "candidate_case_study_underway": False,
    }


def test_design_partner_dashboard_counts_closed_feedback_as_captured_evidence(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_alpha, operator_user_account_id = _bootstrap_workspace_session(
        "design-partner-closed-feedback@example.com",
        workspace_name="Closed Feedback Alpha Workspace",
    )
    _promote_session_to_operator(migrated_database_urls, session_token=session_token)
    workspace_beta = _create_workspace(session_token, name="Closed Feedback Beta Workspace")
    workspace_gamma = _create_workspace(session_token, name="Closed Feedback Gamma Workspace")

    partner_specs = [
        ("Closed Feedback Partner Alpha", workspace_alpha, "candidate"),
        ("Closed Feedback Partner Beta", workspace_beta, "not_started"),
        ("Closed Feedback Partner Gamma", workspace_gamma, "not_started"),
    ]

    design_partner_ids: list[str] = []
    for name, workspace_id, case_study_status in partner_specs:
        create_status, create_payload = invoke_request(
            "POST",
            "/v1/admin/hosted/design-partners",
            headers=auth_header(session_token),
            payload={
                "name": name,
                "lifecycle_stage": "pilot",
                "onboarding_status": "completed",
                "support_status": "green",
                "instrumentation_status": "ready",
                "case_study_status": case_study_status,
                "target_outcome": "Verify launch readiness against persisted pilot evidence.",
            },
        )
        assert create_status == 201
        design_partner_id = create_payload["design_partner"]["id"]
        design_partner_ids.append(design_partner_id)

        link_status, _ = invoke_request(
            "POST",
            f"/v1/admin/hosted/design-partners/{design_partner_id}/workspaces",
            headers=auth_header(session_token),
            payload={
                "workspace_id": workspace_id,
                "linkage_status": "pilot",
                "environment_label": "pilot",
                "instrumentation_ready": True,
                "notes": "Tracked pilot workspace with runtime evidence.",
            },
        )
        assert link_status == 201

        _seed_provider_invocation_telemetry(
            migrated_database_urls["admin"],
            workspace_id=workspace_id,
            user_account_id=operator_user_account_id,
            display_name=f"{name} Provider",
        )

    feedback_status, feedback_payload = invoke_request(
        "POST",
        f"/v1/admin/hosted/design-partners/{design_partner_ids[0]}/feedback",
        headers=auth_header(session_token),
        payload={
            "workspace_id": workspace_alpha,
            "source_kind": "support_review",
            "category": "win",
            "sentiment": "positive",
            "urgency": "low",
            "feedback_status": "closed",
            "case_study_signal": True,
            "summary": "The launch review confirmed this pilot as a case-study candidate.",
            "detail": "The team approved next-step drafting after the first successful usage window.",
        },
    )
    assert feedback_status == 201
    assert feedback_payload["feedback"]["feedback_status"] == "closed"

    dashboard_status, dashboard_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/design-partners/dashboard",
        headers=auth_header(session_token),
    )

    assert dashboard_status == 200
    assert dashboard_payload["dashboard"]["summary"]["usage_visible_count"] == 3
    assert dashboard_payload["dashboard"]["summary"]["feedback_captured_count"] == 1
    assert dashboard_payload["dashboard"]["summary"]["open_feedback_count"] == 0
    assert dashboard_payload["dashboard"]["launch_readiness"]["status"] == "on_track"
    assert dashboard_payload["dashboard"]["launch_readiness"]["acceptance_snapshot"] == {
        "three_partners_active_or_pilot": True,
        "usage_summaries_visible": True,
        "structured_feedback_present": True,
        "candidate_case_study_underway": True,
    }
