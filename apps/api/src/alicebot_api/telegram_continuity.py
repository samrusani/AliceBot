from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import re
from typing import Any, Literal, TypedDict
from uuid import UUID

from psycopg.types.json import Jsonb

from alicebot_api.approvals import (
    ApprovalNotFoundError,
    ApprovalResolutionConflictError,
    approve_approval_record,
    list_approval_records,
    reject_approval_record,
)
from alicebot_api.continuity_capture import capture_continuity_input
from alicebot_api.continuity_objects import ContinuityObjectValidationError
from alicebot_api.continuity_open_loops import (
    ContinuityOpenLoopNotFoundError,
    ContinuityOpenLoopValidationError,
    apply_continuity_open_loop_review_action,
    compile_continuity_open_loop_dashboard,
)
from alicebot_api.continuity_recall import ContinuityRecallValidationError, query_continuity_recall
from alicebot_api.continuity_resumption import (
    ContinuityResumptionValidationError,
    compile_continuity_resumption_brief,
)
from alicebot_api.continuity_review import (
    ContinuityReviewNotFoundError,
    ContinuityReviewValidationError,
    apply_continuity_correction,
)
from alicebot_api.contracts import (
    ApprovalApproveInput,
    ApprovalRejectInput,
    ContinuityCaptureCreateInput,
    ContinuityCorrectionInput,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityOpenLoopReviewActionInput,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
)
from alicebot_api.db import set_current_user
from alicebot_api.store import ContinuityStore, JsonObject
from alicebot_api.tasks import TaskStepApprovalLinkageError, TaskStepLifecycleBoundaryError
from alicebot_api.telegram_channels import (
    TELEGRAM_CHANNEL_TYPE,
    TelegramMessageNotFoundError,
    TelegramRoutingError,
    dispatch_telegram_message,
    serialize_channel_message,
    serialize_delivery_receipt,
)


TelegramChatIntentKind = Literal[
    "capture",
    "recall",
    "resume",
    "correction",
    "open_loops",
    "open_loop_review",
    "approvals",
    "approval_approve",
    "approval_reject",
    "unknown",
]
TelegramChatIntentStatus = Literal["pending", "recorded", "handled", "failed"]

_SUPPORTED_INTENT_HINTS: set[str] = {
    "capture",
    "recall",
    "resume",
    "correction",
    "open_loops",
    "open_loop_review",
    "approvals",
    "approval_approve",
    "approval_reject",
    "unknown",
}
_RECALL_PATTERN = re.compile(r"^\s*/?recall\b(?:\s+(?P<query>.+))?$", flags=re.IGNORECASE)
_RESUME_PATTERN = re.compile(r"^\s*/?resume\b(?:\s+(?P<query>.+))?$", flags=re.IGNORECASE)
_OPEN_LOOPS_PATTERN = re.compile(r"^\s*(?:/?open-loops\b|open loops\b)(?:\s+.*)?$", flags=re.IGNORECASE)
_APPROVALS_PATTERN = re.compile(r"^\s*(?:/?approvals\b|pending approvals\b)(?:\s+.*)?$", flags=re.IGNORECASE)
_CORRECTION_PATTERN = re.compile(
    (
        r"^\s*/?(?:correct|correction)\b\s+"
        r"(?P<object_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
        r"\s+(?P<title>.+)$"
    ),
    flags=re.IGNORECASE,
)
_OPEN_LOOP_REVIEW_PATTERN = re.compile(
    (
        r"^\s*/?open-loop\b\s+"
        r"(?P<object_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
        r"\s+(?P<action>done|deferred|still_blocked)"
        r"(?:\s+(?P<note>.+))?$"
    ),
    flags=re.IGNORECASE,
)
_APPROVE_PATTERN = re.compile(r"^\s*/?approve\b(?:\s+(?P<approval_id>\S+))?.*$", flags=re.IGNORECASE)
_REJECT_PATTERN = re.compile(r"^\s*/?reject\b(?:\s+(?P<approval_id>\S+))?(?:\s+(?P<note>.+))?$", flags=re.IGNORECASE)


class HostedUserAccountNotFoundError(LookupError):
    """Raised when a hosted account is not available for continuity projection."""


class TelegramMessageResultNotFoundError(LookupError):
    """Raised when no Telegram handle result is available for the message."""


class _TelegramInboundMessageRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_thread_id: UUID | None
    channel_identity_id: UUID | None
    route_status: str
    message_text: str | None
    external_chat_id: str | None


class TelegramIntentClassification(TypedDict):
    intent_kind: TelegramChatIntentKind
    confidence: float
    intent_payload: JsonObject


class _ChatIntentRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_message_id: UUID
    channel_thread_id: UUID | None
    intent_kind: str
    status: str
    intent_payload: JsonObject
    result_payload: JsonObject
    handled_at: datetime | None
    created_at: datetime


class _ApprovalChallengeRow(TypedDict):
    id: UUID
    workspace_id: UUID
    approval_id: UUID
    channel_message_id: UUID | None
    status: str
    challenge_prompt: str
    challenge_payload: JsonObject
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    if normalized == "":
        return None
    return normalized


def _normalize_optional_payload_text(payload: JsonObject, *, field_name: str) -> str | None:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        raise ValueError(f"{field_name} must be a string")
    return _normalize_optional_text(raw_value)


def _parse_uuid(value: str, *, field_name: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid uuid") from exc


def _resolve_intent_hint(intent_hint: str | None) -> TelegramChatIntentKind | None:
    normalized = _normalize_optional_text(intent_hint)
    if normalized is None:
        return None
    lowered = normalized.casefold()
    if lowered not in _SUPPORTED_INTENT_HINTS:
        allowed = ", ".join(sorted(_SUPPORTED_INTENT_HINTS))
        raise ValueError(f"intent_hint must be one of: {allowed}")
    return lowered  # type: ignore[return-value]


def _serialize_chat_intent(row: _ChatIntentRow) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "channel_message_id": str(row["channel_message_id"]),
        "channel_thread_id": None if row["channel_thread_id"] is None else str(row["channel_thread_id"]),
        "intent_kind": row["intent_kind"],
        "status": row["status"],
        "intent_payload": row["intent_payload"],
        "result_payload": row["result_payload"],
        "handled_at": None if row["handled_at"] is None else row["handled_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
    }


def _serialize_approval_challenge(row: _ApprovalChallengeRow) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "approval_id": str(row["approval_id"]),
        "channel_message_id": None if row["channel_message_id"] is None else str(row["channel_message_id"]),
        "status": row["status"],
        "challenge_prompt": row["challenge_prompt"],
        "challenge_payload": row["challenge_payload"],
        "resolved_at": None if row["resolved_at"] is None else row["resolved_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def prepare_telegram_continuity_context(
    conn,
    *,
    user_account_id: UUID,
) -> None:
    set_current_user(conn, user_account_id)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, email, display_name
            FROM user_accounts
            WHERE id = %s
            LIMIT 1
            """,
            (user_account_id,),
        )
        account = cur.fetchone()

        if account is None:
            raise HostedUserAccountNotFoundError(f"hosted user account {user_account_id} was not found")

        cur.execute(
            """
            INSERT INTO users (id, email, display_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (account["id"], account["email"], account["display_name"]),
        )


def _load_workspace_inbound_message(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    message_id: UUID,
) -> _TelegramInboundMessageRow:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.id,
                   m.workspace_id,
                   m.channel_thread_id,
                   m.channel_identity_id,
                   m.route_status,
                   m.message_text,
                   m.external_chat_id
            FROM channel_messages AS m
            JOIN workspace_members AS wm
              ON wm.workspace_id = m.workspace_id
            WHERE m.id = %s
              AND m.workspace_id = %s
              AND wm.user_account_id = %s
              AND m.channel_type = %s
              AND m.direction = 'inbound'
            LIMIT 1
            """,
            (message_id, workspace_id, user_account_id, TELEGRAM_CHANNEL_TYPE),
        )
        row = cur.fetchone()

    if row is None:
        raise TelegramMessageNotFoundError(f"telegram source message {message_id} was not found")
    if row["route_status"] != "resolved":
        raise TelegramRoutingError("telegram source message does not have resolved routing")
    return row


def classify_telegram_message_intent(message_text: str) -> TelegramIntentClassification:
    normalized_text = _normalize_optional_text(message_text)
    if normalized_text is None:
        return {
            "intent_kind": "unknown",
            "confidence": 1.0,
            "intent_payload": {"reason": "empty_message"},
        }

    review_match = _OPEN_LOOP_REVIEW_PATTERN.match(normalized_text)
    if review_match is not None:
        note = _normalize_optional_text(review_match.group("note"))
        payload: JsonObject = {
            "continuity_object_id": review_match.group("object_id"),
            "action": review_match.group("action").casefold(),
        }
        payload["note"] = note
        return {
            "intent_kind": "open_loop_review",
            "confidence": 0.99,
            "intent_payload": payload,
        }

    correction_match = _CORRECTION_PATTERN.match(normalized_text)
    if correction_match is not None:
        return {
            "intent_kind": "correction",
            "confidence": 0.99,
            "intent_payload": {
                "continuity_object_id": correction_match.group("object_id"),
                "replacement_title": correction_match.group("title").strip(),
            },
        }

    approve_match = _APPROVE_PATTERN.match(normalized_text)
    if approve_match is not None:
        return {
            "intent_kind": "approval_approve",
            "confidence": 0.98,
            "intent_payload": {
                "approval_id": approve_match.group("approval_id"),
            },
        }

    reject_match = _REJECT_PATTERN.match(normalized_text)
    if reject_match is not None:
        return {
            "intent_kind": "approval_reject",
            "confidence": 0.98,
            "intent_payload": {
                "approval_id": reject_match.group("approval_id"),
                "note": _normalize_optional_text(reject_match.group("note")),
            },
        }

    recall_match = _RECALL_PATTERN.match(normalized_text)
    if recall_match is not None:
        return {
            "intent_kind": "recall",
            "confidence": 0.97,
            "intent_payload": {"query": _normalize_optional_text(recall_match.group("query"))},
        }

    if normalized_text.casefold().startswith("what do you remember"):
        suffix = _normalize_optional_text(normalized_text[len("what do you remember") :])
        return {
            "intent_kind": "recall",
            "confidence": 0.85,
            "intent_payload": {"query": suffix},
        }

    resume_match = _RESUME_PATTERN.match(normalized_text)
    if resume_match is not None:
        return {
            "intent_kind": "resume",
            "confidence": 0.97,
            "intent_payload": {"query": _normalize_optional_text(resume_match.group("query"))},
        }

    if normalized_text.casefold().startswith("where was i"):
        return {
            "intent_kind": "resume",
            "confidence": 0.85,
            "intent_payload": {"query": None},
        }

    if _OPEN_LOOPS_PATTERN.match(normalized_text) is not None:
        return {
            "intent_kind": "open_loops",
            "confidence": 0.98,
            "intent_payload": {"query": None},
        }

    if _APPROVALS_PATTERN.match(normalized_text) is not None:
        return {
            "intent_kind": "approvals",
            "confidence": 0.98,
            "intent_payload": {"status": "pending"},
        }

    return {
        "intent_kind": "capture",
        "confidence": 0.65,
        "intent_payload": {"raw_content": normalized_text},
    }


def _upsert_chat_intent_result(
    conn,
    *,
    workspace_id: UUID,
    channel_message_id: UUID,
    channel_thread_id: UUID | None,
    intent_kind: TelegramChatIntentKind,
    status: TelegramChatIntentStatus,
    intent_payload: JsonObject,
    result_payload: JsonObject,
    handled_at: datetime | None,
) -> _ChatIntentRow:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_intents (
              workspace_id,
              channel_message_id,
              channel_thread_id,
              intent_kind,
              status,
              intent_payload,
              result_payload,
              handled_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (channel_message_id, intent_kind) DO UPDATE
            SET status = EXCLUDED.status,
                intent_payload = EXCLUDED.intent_payload,
                result_payload = EXCLUDED.result_payload,
                handled_at = EXCLUDED.handled_at
            RETURNING id,
                      workspace_id,
                      channel_message_id,
                      channel_thread_id,
                      intent_kind,
                      status,
                      intent_payload,
                      result_payload,
                      handled_at,
                      created_at
            """,
            (
                workspace_id,
                channel_message_id,
                channel_thread_id,
                intent_kind,
                status,
                Jsonb(intent_payload),
                Jsonb(result_payload),
                handled_at,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to persist telegram chat intent result")
    return row


def _fetch_latest_chat_intent_result(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    message_id: UUID,
) -> _ChatIntentRow:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ci.id,
                   ci.workspace_id,
                   ci.channel_message_id,
                   ci.channel_thread_id,
                   ci.intent_kind,
                   ci.status,
                   ci.intent_payload,
                   ci.result_payload,
                   ci.handled_at,
                   ci.created_at
            FROM chat_intents AS ci
            JOIN workspace_members AS wm
              ON wm.workspace_id = ci.workspace_id
            WHERE ci.workspace_id = %s
              AND ci.channel_message_id = %s
              AND wm.user_account_id = %s
              AND ci.intent_kind <> 'inbound_message'
            ORDER BY COALESCE(ci.handled_at, ci.created_at) DESC, ci.created_at DESC, ci.id DESC
            LIMIT 1
            """,
            (workspace_id, message_id, user_account_id),
        )
        row = cur.fetchone()

    if row is None:
        raise TelegramMessageResultNotFoundError(
            f"telegram message {message_id} does not have a continuity handle result yet"
        )
    return row


def _format_provenance_reference_list(references: list[dict[str, object]], *, limit: int = 3) -> str:
    compact: list[str] = []
    for item in references[:limit]:
        source_kind = str(item.get("source_kind", "source"))
        source_id = str(item.get("source_id", "unknown"))
        compact.append(f"{source_kind}:{source_id}")
    return ", ".join(compact)


def _record_pending_approval_challenges(
    conn,
    *,
    workspace_id: UUID,
    approvals: list[dict[str, object]],
    channel_message_id: UUID | None,
) -> list[dict[str, object]]:
    recorded: list[dict[str, object]] = []
    if not approvals:
        return recorded

    with conn.cursor() as cur:
        for approval in approvals:
            approval_id = _parse_uuid(str(approval["id"]), field_name="approval_id")
            request_payload = approval.get("request")
            if isinstance(request_payload, dict):
                action_hint = _normalize_optional_text(str(request_payload.get("action")))
            else:
                action_hint = None

            challenge_prompt = (
                f"Approval {approval_id} is pending."
                if action_hint is None
                else f"Approval {approval_id} is pending for action '{action_hint}'."
            )
            challenge_payload: JsonObject = {
                "approval": approval,
                "source": "telegram",
            }
            cur.execute(
                """
                INSERT INTO approval_challenges (
                  workspace_id,
                  approval_id,
                  channel_message_id,
                  status,
                  challenge_prompt,
                  challenge_payload,
                  updated_at
                )
                VALUES (%s, %s, %s, 'pending', %s, %s, %s)
                ON CONFLICT (workspace_id, approval_id) WHERE status = 'pending'
                DO UPDATE
                SET channel_message_id = COALESCE(EXCLUDED.channel_message_id, approval_challenges.channel_message_id),
                    challenge_prompt = EXCLUDED.challenge_prompt,
                    challenge_payload = EXCLUDED.challenge_payload,
                    updated_at = EXCLUDED.updated_at
                RETURNING id,
                          workspace_id,
                          approval_id,
                          channel_message_id,
                          status,
                          challenge_prompt,
                          challenge_payload,
                          resolved_at,
                          created_at,
                          updated_at
                """,
                (
                    workspace_id,
                    approval_id,
                    channel_message_id,
                    challenge_prompt,
                    Jsonb(challenge_payload),
                    _utcnow(),
                ),
            )
            row = cur.fetchone()
            if row is not None:
                recorded.append(_serialize_approval_challenge(row))

    return recorded


def _resolve_pending_approval_challenges(
    conn,
    *,
    workspace_id: UUID,
    approval_id: UUID,
    resolution_status: Literal["approved", "rejected"],
) -> list[dict[str, object]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE approval_challenges
            SET status = %s,
                resolved_at = %s,
                updated_at = %s
            WHERE workspace_id = %s
              AND approval_id = %s
              AND status = 'pending'
            RETURNING id,
                      workspace_id,
                      approval_id,
                      channel_message_id,
                      status,
                      challenge_prompt,
                      challenge_payload,
                      resolved_at,
                      created_at,
                      updated_at
            """,
            (
                resolution_status,
                _utcnow(),
                _utcnow(),
                workspace_id,
                approval_id,
            ),
        )
        rows = cur.fetchall()

    return [_serialize_approval_challenge(row) for row in rows]


def list_telegram_approvals(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    status_filter: Literal["pending", "all"] = "pending",
    channel_message_id: UUID | None = None,
) -> dict[str, object]:
    payload = list_approval_records(
        ContinuityStore(conn),
        user_id=user_account_id,
    )
    raw_items = payload["items"]
    if status_filter == "pending":
        items = [item for item in raw_items if item["status"] == "pending"]
    else:
        items = raw_items

    pending_items = [item for item in raw_items if item["status"] == "pending"]
    challenges = _record_pending_approval_challenges(
        conn,
        workspace_id=workspace_id,
        approvals=pending_items,
        channel_message_id=channel_message_id,
    )

    return {
        "items": items,
        "summary": {
            "status": status_filter,
            "returned_count": len(items),
            "pending_count": len(pending_items),
            "order": payload["summary"]["order"],
        },
        "challenges": challenges,
    }


def approve_telegram_approval(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    approval_id: UUID,
) -> dict[str, object]:
    payload = approve_approval_record(
        ContinuityStore(conn),
        user_id=user_account_id,
        request=ApprovalApproveInput(approval_id=approval_id),
    )
    challenge_updates = _resolve_pending_approval_challenges(
        conn,
        workspace_id=workspace_id,
        approval_id=approval_id,
        resolution_status="approved",
    )
    return {
        **payload,
        "challenge_updates": challenge_updates,
    }


def reject_telegram_approval(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    approval_id: UUID,
) -> dict[str, object]:
    payload = reject_approval_record(
        ContinuityStore(conn),
        user_id=user_account_id,
        request=ApprovalRejectInput(approval_id=approval_id),
    )
    challenge_updates = _resolve_pending_approval_challenges(
        conn,
        workspace_id=workspace_id,
        approval_id=approval_id,
        resolution_status="rejected",
    )
    return {
        **payload,
        "challenge_updates": challenge_updates,
    }


def apply_telegram_open_loop_review_with_log(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    continuity_object_id: UUID,
    action: str,
    note: str | None,
    channel_message_id: UUID | None = None,
) -> dict[str, object]:
    response = apply_continuity_open_loop_review_action(
        ContinuityStore(conn),
        user_id=user_account_id,
        continuity_object_id=continuity_object_id,
        request=ContinuityOpenLoopReviewActionInput(
            action=action,  # type: ignore[arg-type]
            note=note,
        ),
    )

    correction_event_id = _parse_uuid(response["correction_event"]["id"], field_name="correction_event_id")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO open_loop_reviews (
              workspace_id,
              continuity_object_id,
              channel_message_id,
              correction_event_id,
              review_action,
              note
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id,
                      workspace_id,
                      continuity_object_id,
                      channel_message_id,
                      correction_event_id,
                      review_action,
                      note,
                      created_at
            """,
            (
                workspace_id,
                continuity_object_id,
                channel_message_id,
                correction_event_id,
                action,
                note,
            ),
        )
        review_row = cur.fetchone()

    if review_row is None:
        raise RuntimeError("failed to persist open-loop review action log")

    return {
        **response,
        "review_log": {
            "id": str(review_row["id"]),
            "workspace_id": str(review_row["workspace_id"]),
            "continuity_object_id": str(review_row["continuity_object_id"]),
            "channel_message_id": None
            if review_row["channel_message_id"] is None
            else str(review_row["channel_message_id"]),
            "correction_event_id": None
            if review_row["correction_event_id"] is None
            else str(review_row["correction_event_id"]),
            "review_action": review_row["review_action"],
            "note": review_row["note"],
            "created_at": review_row["created_at"].isoformat(),
        },
    }


def _execute_intent(
    conn,
    *,
    store: ContinuityStore,
    user_account_id: UUID,
    workspace_id: UUID,
    source_message_id: UUID,
    classification: TelegramIntentClassification,
    source_message_text: str,
) -> tuple[JsonObject, str]:
    intent_kind = classification["intent_kind"]
    intent_payload = classification["intent_payload"]

    if intent_kind == "capture":
        capture_payload = capture_continuity_input(
            store,
            user_id=user_account_id,
            request=ContinuityCaptureCreateInput(
                raw_content=source_message_text,
                explicit_signal=None,
            ),
        )
        capture = capture_payload["capture"]
        derived_object = capture.get("derived_object")
        if isinstance(derived_object, dict):
            object_type = str(derived_object.get("object_type", "Note"))
            title = str(derived_object.get("title", "captured object"))
            reply_text = f"Captured {object_type}: {title}"
        else:
            reply_text = "Captured and queued for continuity triage."
        return (
            {
                "mode": "capture",
                "capture": capture_payload["capture"],
                "provenance_references": [
                    {
                        "source_kind": "continuity_capture_event",
                        "source_id": capture["capture_event"]["id"],
                    }
                ],
            },
            reply_text,
        )

    if intent_kind == "recall":
        query = _normalize_optional_payload_text(intent_payload, field_name="query")
        if query is None:
            raise ValueError("recall intent requires a query")
        recall_payload = query_continuity_recall(
            store,
            user_id=user_account_id,
            request=ContinuityRecallQueryInput(query=query, limit=5),
        )
        if len(recall_payload["items"]) == 0:
            reply_text = f"No recall results for '{query}'."
        else:
            first = recall_payload["items"][0]
            provenance = _format_provenance_reference_list(first["provenance_references"])
            if provenance == "":
                reply_text = f"Recall: {first['title']} ({first['status']})."
            else:
                reply_text = f"Recall: {first['title']} ({first['status']}). Provenance {provenance}."
        return (
            {
                "mode": "recall",
                "query": query,
                "recall": recall_payload,
            },
            reply_text,
        )

    if intent_kind == "resume":
        query = _normalize_optional_payload_text(intent_payload, field_name="query")
        resume_payload = compile_continuity_resumption_brief(
            store,
            user_id=user_account_id,
            request=ContinuityResumptionBriefRequestInput(
                query=query,
            ),
        )
        brief = resume_payload["brief"]
        decision = brief["last_decision"]["item"]
        next_action = brief["next_action"]["item"]
        decision_title = "none" if decision is None else decision["title"]
        next_action_title = "none" if next_action is None else next_action["title"]
        open_loop_count = brief["open_loops"]["summary"]["returned_count"]
        reply_text = (
            f"Resume: decision={decision_title}; next_action={next_action_title}; "
            f"open_loops={open_loop_count}."
        )
        return (
            {
                "mode": "resume",
                "brief": brief,
            },
            reply_text,
        )

    if intent_kind == "correction":
        continuity_object_id_raw = _normalize_optional_payload_text(intent_payload, field_name="continuity_object_id")
        if continuity_object_id_raw is None:
            raise ValueError("correction intent requires continuity object id")
        continuity_object_id = _parse_uuid(continuity_object_id_raw, field_name="continuity_object_id")
        replacement_title = _normalize_optional_payload_text(intent_payload, field_name="replacement_title")
        if replacement_title is None:
            raise ValueError("correction intent requires replacement title text")
        correction_payload = apply_continuity_correction(
            store,
            user_id=user_account_id,
            continuity_object_id=continuity_object_id,
            request=ContinuityCorrectionInput(
                action="edit",
                reason="telegram_correction",
                title=replacement_title,
            ),
        )
        updated_object = correction_payload["continuity_object"]
        reply_text = f"Correction applied: {updated_object['id']} now titled '{updated_object['title']}'."
        return (
            {
                "mode": "correction",
                "correction": correction_payload,
                "provenance_references": [
                    {
                        "source_kind": "continuity_correction_event",
                        "source_id": correction_payload["correction_event"]["id"],
                    },
                    {
                        "source_kind": "continuity_object",
                        "source_id": updated_object["id"],
                    },
                ],
            },
            reply_text,
        )

    if intent_kind == "open_loops":
        dashboard_payload = compile_continuity_open_loop_dashboard(
            store,
            user_id=user_account_id,
            request=ContinuityOpenLoopDashboardQueryInput(limit=5),
        )
        dashboard = dashboard_payload["dashboard"]
        reply_text = (
            "Open loops: "
            f"waiting_for={dashboard['waiting_for']['summary']['total_count']}, "
            f"blocker={dashboard['blocker']['summary']['total_count']}, "
            f"stale={dashboard['stale']['summary']['total_count']}, "
            f"next_action={dashboard['next_action']['summary']['total_count']}."
        )
        return (
            {
                "mode": "open_loops",
                "dashboard": dashboard,
            },
            reply_text,
        )

    if intent_kind == "open_loop_review":
        continuity_object_id_raw = _normalize_optional_payload_text(intent_payload, field_name="continuity_object_id")
        if continuity_object_id_raw is None:
            raise ValueError("open-loop review intent requires continuity object id")
        continuity_object_id = _parse_uuid(continuity_object_id_raw, field_name="continuity_object_id")
        action = _normalize_optional_payload_text(intent_payload, field_name="action")
        if action is None:
            raise ValueError("open-loop review intent requires action")
        note = _normalize_optional_payload_text(intent_payload, field_name="note")
        review_payload = apply_telegram_open_loop_review_with_log(
            conn,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
            continuity_object_id=continuity_object_id,
            action=action,
            note=note,
            channel_message_id=source_message_id,
        )
        reply_text = (
            f"Open-loop review applied: action={review_payload['review_action']}, "
            f"outcome={review_payload['lifecycle_outcome']}."
        )
        return (
            {
                "mode": "open_loop_review",
                "review": review_payload,
            },
            reply_text,
        )

    if intent_kind == "approvals":
        approvals_payload = list_telegram_approvals(
            conn,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
            status_filter="pending",
            channel_message_id=source_message_id,
        )
        items = approvals_payload["items"]
        if len(items) == 0:
            reply_text = "No pending approvals."
        else:
            pending_ids = ", ".join(str(item["id"]) for item in items[:3])
            suffix = "" if len(items) <= 3 else f" (+{len(items) - 3} more)"
            reply_text = f"Pending approvals: {pending_ids}{suffix}."
        return (
            {
                "mode": "approvals",
                "approvals": approvals_payload,
            },
            reply_text,
        )

    if intent_kind == "approval_approve":
        approval_id_raw = _normalize_optional_payload_text(intent_payload, field_name="approval_id")
        if approval_id_raw is None:
            raise ValueError("approve intent requires approval id")
        approval_id = _parse_uuid(approval_id_raw, field_name="approval_id")
        approval_payload = approve_telegram_approval(
            conn,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
            approval_id=approval_id,
        )
        final_status = approval_payload["approval"]["status"]
        reply_text = f"Approval {approval_id} resolved as {final_status}."
        return (
            {
                "mode": "approval_approve",
                "resolution": approval_payload,
            },
            reply_text,
        )

    if intent_kind == "approval_reject":
        approval_id_raw = _normalize_optional_payload_text(intent_payload, field_name="approval_id")
        if approval_id_raw is None:
            raise ValueError("reject intent requires approval id")
        approval_id = _parse_uuid(approval_id_raw, field_name="approval_id")
        approval_payload = reject_telegram_approval(
            conn,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
            approval_id=approval_id,
        )
        final_status = approval_payload["approval"]["status"]
        reply_text = f"Approval {approval_id} resolved as {final_status}."
        return (
            {
                "mode": "approval_reject",
                "resolution": approval_payload,
            },
            reply_text,
        )

    if intent_kind == "unknown":
        return (
            {
                "mode": "unknown",
                "reason": intent_payload.get("reason", "unknown_intent"),
            },
            "I could not determine the requested action. Use /recall, /resume, /open-loops, /approvals, or send capture text.",
        )

    raise ValueError(f"unsupported telegram intent kind: {intent_kind}")


def handle_telegram_message(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    message_id: UUID,
    bot_token: str,
    intent_hint: str | None = None,
) -> dict[str, object]:
    source_message = _load_workspace_inbound_message(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
        message_id=message_id,
    )

    source_text = _normalize_optional_text(source_message["message_text"]) or ""
    classification = classify_telegram_message_intent(source_text)
    hinted_intent = _resolve_intent_hint(intent_hint)

    intent_kind: TelegramChatIntentKind = classification["intent_kind"]
    status: TelegramChatIntentStatus
    result_payload: JsonObject
    reply_text: str

    store = ContinuityStore(conn)
    execution_error_kinds = (
        ApprovalNotFoundError,
        ApprovalResolutionConflictError,
        ContinuityOpenLoopNotFoundError,
        ContinuityOpenLoopValidationError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
        ContinuityReviewNotFoundError,
        ContinuityReviewValidationError,
        ContinuityObjectValidationError,
        TaskStepApprovalLinkageError,
        TaskStepLifecycleBoundaryError,
        ValueError,
    )

    if hinted_intent is not None and hinted_intent != classification["intent_kind"]:
        intent_kind = hinted_intent
        status = "failed"
        result_payload = {
            "ok": False,
            "error": {
                "code": "intent_hint_mismatch",
                "detail": (
                    f"intent_hint '{hinted_intent}' does not match detected intent "
                    f"'{classification['intent_kind']}'"
                ),
            },
            "detected_intent_kind": classification["intent_kind"],
        }
        reply_text = (
            f"Intent hint '{hinted_intent}' did not match detected intent "
            f"'{classification['intent_kind']}'."
        )
    else:
        try:
            intent_result, reply_text = _execute_intent(
                conn,
                store=store,
                user_account_id=user_account_id,
                workspace_id=workspace_id,
                source_message_id=message_id,
                classification=classification,
                source_message_text=source_text,
            )
            status = "handled"
            result_payload = {
                "ok": True,
                "intent_result": intent_result,
            }
        except execution_error_kinds as exc:
            status = "failed"
            result_payload = {
                "ok": False,
                "error": {
                    "code": "intent_execution_failed",
                    "type": exc.__class__.__name__,
                    "detail": str(exc),
                },
            }
            reply_text = f"Unable to process {classification['intent_kind']}: {exc}"

    dispatch_idempotency_key = hashlib.sha256(
        f"telegram:handle:{message_id}:{intent_kind}".encode("utf-8")
    ).hexdigest()
    outbound_message, receipt = dispatch_telegram_message(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
        source_message_id=message_id,
        text=reply_text,
        dispatch_idempotency_key=dispatch_idempotency_key,
        bot_token=bot_token,
    )

    result_payload["reply"] = {
        "text": reply_text,
        "outbound_message_id": str(outbound_message["id"]),
        "delivery_receipt_id": str(receipt["id"]),
    }

    persisted_intent = _upsert_chat_intent_result(
        conn,
        workspace_id=workspace_id,
        channel_message_id=message_id,
        channel_thread_id=source_message["channel_thread_id"],
        intent_kind=intent_kind,
        status=status,
        intent_payload={
            **classification["intent_payload"],
            "detected_intent_kind": classification["intent_kind"],
            "intent_confidence": classification["confidence"],
            "intent_hint": hinted_intent,
        },
        result_payload=result_payload,
        handled_at=_utcnow(),
    )

    return {
        "message": {
            "id": str(source_message["id"]),
            "workspace_id": str(source_message["workspace_id"]),
            "channel_thread_id": None
            if source_message["channel_thread_id"] is None
            else str(source_message["channel_thread_id"]),
            "channel_identity_id": None
            if source_message["channel_identity_id"] is None
            else str(source_message["channel_identity_id"]),
            "route_status": source_message["route_status"],
            "message_text": source_message["message_text"],
            "external_chat_id": source_message["external_chat_id"],
        },
        "intent": _serialize_chat_intent(persisted_intent),
        "outbound_message": serialize_channel_message(outbound_message),
        "delivery_receipt": serialize_delivery_receipt(receipt),
    }


def get_telegram_message_result(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    message_id: UUID,
) -> dict[str, object]:
    intent = _fetch_latest_chat_intent_result(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
        message_id=message_id,
    )
    return {
        "message_id": str(message_id),
        "intent": _serialize_chat_intent(intent),
    }
