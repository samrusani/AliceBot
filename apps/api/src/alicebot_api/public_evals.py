from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from alicebot_api.continuity_contradictions import sync_contradiction_state_for_objects
from alicebot_api.continuity_open_loops import compile_continuity_open_loop_dashboard
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.continuity_review import apply_continuity_correction
from alicebot_api.contracts import (
    ContinuityCorrectionInput,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityResumptionBriefRequestInput,
    PublicEvalResultRecord,
    PublicEvalRunDetailResponse,
    PublicEvalRunListResponse,
    PublicEvalRunRecord,
    PublicEvalSuiteDefinitionListResponse,
    PublicEvalSuiteDefinitionRecord,
)
from alicebot_api.retrieval_evaluation import get_retrieval_evaluation_summary
from alicebot_api.store import (
    ContinuityRecallCandidateRow,
    ContinuityStore,
    EvalCaseRow,
    EvalResultRow,
    EvalRunRow,
    EvalSuiteRow,
    JsonObject,
)

PUBLIC_EVAL_FIXTURE_SCHEMA_VERSION = "public_eval_fixture_v1"
PUBLIC_EVAL_REPORT_SCHEMA_VERSION = "public_eval_report_v1"
PUBLIC_EVAL_FIXTURE_SOURCE_PATH = "eval/fixtures/public_eval_suites.json"
PUBLIC_EVAL_RUN_ORDER = ["created_at_desc", "id_desc"]
PUBLIC_EVAL_SUITE_ORDER = ["suite_order_asc", "suite_key_asc"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _fixture_catalog_path() -> Path:
    return _repo_root() / PUBLIC_EVAL_FIXTURE_SOURCE_PATH


def _load_fixture_catalog() -> JsonObject:
    payload = json.loads(_fixture_catalog_path().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("public eval fixture catalog must be a JSON object")
    return cast(JsonObject, payload)


def _stable_uuid(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"alicebot-public-eval:{kind}:{value}")


def _parse_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _json_object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        return {}
    return cast(JsonObject, value)


def _json_objects(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [_json_object(item) for item in value if isinstance(item, dict)]


def _validate_fixture_catalog(catalog: JsonObject) -> list[JsonObject]:
    if str(catalog.get("schema_version")) != PUBLIC_EVAL_FIXTURE_SCHEMA_VERSION:
        raise ValueError("unexpected public eval fixture schema version")
    return _json_objects(catalog.get("suites"))


def _case_title(case: EvalCaseRow) -> str:
    return case["title"]


def _build_candidate_row(
    *,
    case_key: str,
    payload: JsonObject,
) -> ContinuityRecallCandidateRow:
    object_key = str(payload["object_key"])
    capture_key = f"{case_key}:{object_key}:capture"
    created_at = _parse_datetime(str(payload["created_at"]))
    last_confirmed_raw = payload.get("last_confirmed_at")
    supersedes_raw = payload.get("supersedes_object_key")
    superseded_by_raw = payload.get("superseded_by_object_key")
    return {
        "id": _stable_uuid("continuity_object", f"{case_key}:{object_key}"),
        "user_id": _stable_uuid("user", "public-eval"),
        "capture_event_id": _stable_uuid("capture_event", capture_key),
        "object_type": str(payload.get("object_type", "Decision")),
        "status": str(payload.get("status", "active")),
        "is_preserved": bool(payload.get("is_preserved", True)),
        "is_searchable": bool(payload.get("is_searchable", True)),
        "is_promotable": bool(payload.get("is_promotable", True)),
        "title": str(payload["title"]),
        "body": _json_object(payload.get("body")),
        "provenance": _json_object(payload.get("provenance")),
        "confidence": float(payload.get("confidence", 1.0)),
        "last_confirmed_at": (
            None if not isinstance(last_confirmed_raw, str) else _parse_datetime(last_confirmed_raw)
        ),
        "supersedes_object_id": (
            None
            if not isinstance(supersedes_raw, str)
            else _stable_uuid("continuity_object", f"{case_key}:{supersedes_raw}")
        ),
        "superseded_by_object_id": (
            None
            if not isinstance(superseded_by_raw, str)
            else _stable_uuid("continuity_object", f"{case_key}:{superseded_by_raw}")
        ),
        "object_created_at": created_at,
        "object_updated_at": created_at,
        "admission_posture": str(payload.get("admission_posture", "DERIVED")),
        "admission_reason": str(payload.get("admission_reason", "public_eval_fixture")),
        "explicit_signal": cast(str | None, payload.get("explicit_signal")),
        "capture_created_at": created_at,
    }


class _RecallOnlyStore:
    def __init__(self, rows: list[ContinuityRecallCandidateRow]) -> None:
        self._rows = [dict(row) for row in rows]

    def list_continuity_recall_candidates(self) -> list[ContinuityRecallCandidateRow]:
        return [cast(ContinuityRecallCandidateRow, dict(row)) for row in self._rows]

    def list_continuity_correction_events(self, *, continuity_object_id: UUID, limit: int) -> list[JsonObject]:
        del continuity_object_id, limit
        return []


class _CorrectionStore:
    def __init__(self, rows: list[ContinuityRecallCandidateRow]) -> None:
        self.base_time = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
        self.objects: dict[UUID, dict[str, object]] = {}
        self.events_by_object: dict[UUID, list[dict[str, object]]] = {}
        for row in rows:
            self.objects[row["id"]] = {
                "id": row["id"],
                "user_id": row["user_id"],
                "capture_event_id": row["capture_event_id"],
                "object_type": row["object_type"],
                "status": row["status"],
                "is_preserved": row["is_preserved"],
                "is_searchable": row["is_searchable"],
                "is_promotable": row["is_promotable"],
                "title": row["title"],
                "body": row["body"],
                "provenance": row["provenance"],
                "confidence": row["confidence"],
                "last_confirmed_at": row["last_confirmed_at"],
                "supersedes_object_id": row["supersedes_object_id"],
                "superseded_by_object_id": row["superseded_by_object_id"],
                "created_at": row["object_created_at"],
                "updated_at": row["object_updated_at"],
            }
            self.events_by_object[row["id"]] = []

    def get_continuity_object_optional(self, continuity_object_id: UUID) -> dict[str, object] | None:
        record = self.objects.get(continuity_object_id)
        return None if record is None else dict(record)

    def list_continuity_correction_events(
        self,
        *,
        continuity_object_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        rows = [dict(row) for row in self.events_by_object.get(continuity_object_id, [])]
        rows.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
        return rows[:limit]

    def create_continuity_correction_event(self, **kwargs: object) -> dict[str, object]:
        event = {
            "id": uuid4(),
            "user_id": _stable_uuid("user", "public-eval"),
            "created_at": self.base_time + timedelta(minutes=sum(len(items) for items in self.events_by_object.values()) + 1),
            **kwargs,
        }
        continuity_object_id = cast(UUID, kwargs["continuity_object_id"])
        self.events_by_object.setdefault(continuity_object_id, []).append(event)
        return dict(event)

    def update_continuity_object_optional(self, *, continuity_object_id: UUID, **kwargs: object) -> dict[str, object] | None:
        record = self.objects.get(continuity_object_id)
        if record is None:
            return None
        updated = {
            **record,
            **kwargs,
            "updated_at": self.base_time + timedelta(minutes=sum(len(items) for items in self.events_by_object.values()) + 1),
        }
        self.objects[continuity_object_id] = updated
        return dict(updated)

    def create_continuity_capture_event(
        self,
        *,
        raw_content: str,
        explicit_signal: str | None,
        admission_posture: str,
        admission_reason: str,
    ) -> dict[str, object]:
        return {
            "id": uuid4(),
            "user_id": _stable_uuid("user", "public-eval"),
            "raw_content": raw_content,
            "explicit_signal": explicit_signal,
            "admission_posture": admission_posture,
            "admission_reason": admission_reason,
            "created_at": self.base_time,
        }

    def create_continuity_object(self, **kwargs: object) -> dict[str, object]:
        object_id = uuid4()
        row = {
            "id": object_id,
            "user_id": _stable_uuid("user", "public-eval"),
            "created_at": self.base_time,
            "updated_at": self.base_time,
            **kwargs,
        }
        self.objects[object_id] = row
        self.events_by_object.setdefault(object_id, [])
        return dict(row)


class _ContradictionStore:
    def __init__(self, rows: list[ContinuityRecallCandidateRow]) -> None:
        self._rows = [dict(row) for row in rows]
        self._objects = {
            row["id"]: {
                "id": row["id"],
                "capture_event_id": row["capture_event_id"],
                "object_type": row["object_type"],
                "status": row["status"],
                "is_preserved": row["is_preserved"],
                "is_searchable": row["is_searchable"],
                "is_promotable": row["is_promotable"],
                "title": row["title"],
                "body": row["body"],
                "provenance": row["provenance"],
                "confidence": row["confidence"],
                "last_confirmed_at": row["last_confirmed_at"],
                "supersedes_object_id": row["supersedes_object_id"],
                "superseded_by_object_id": row["superseded_by_object_id"],
                "created_at": row["object_created_at"],
                "updated_at": row["object_updated_at"],
            }
            for row in rows
        }
        self._cases: dict[UUID, dict[str, object]] = {}
        self._signals: dict[tuple[UUID, str], dict[str, object]] = {}
        self._clock = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)

    def _tick(self) -> datetime:
        self._clock = self._clock + timedelta(seconds=1)
        return self._clock

    def list_continuity_recall_candidates(self) -> list[dict[str, object]]:
        return [dict(row) for row in self._rows]

    def list_continuity_correction_events(self, *, continuity_object_id: UUID, limit: int) -> list[dict[str, object]]:
        del continuity_object_id, limit
        return []

    def list_continuity_object_evidence(self, continuity_object_id: UUID) -> list[dict[str, object]]:
        del continuity_object_id
        return []

    def get_continuity_object_optional(self, continuity_object_id: UUID) -> dict[str, object] | None:
        record = self._objects.get(continuity_object_id)
        return None if record is None else dict(record)

    def create_contradiction_case(self, **kwargs: object) -> dict[str, object]:
        now = self._tick()
        row = {
            "id": uuid4(),
            "user_id": _stable_uuid("user", "public-eval"),
            "created_at": now,
            "updated_at": now,
            **kwargs,
        }
        self._cases[row["id"]] = row
        return dict(row)

    def update_contradiction_case_optional(self, *, contradiction_case_id: UUID, **kwargs: object) -> dict[str, object] | None:
        existing = self._cases.get(contradiction_case_id)
        if existing is None:
            return None
        updated = {**existing, **kwargs, "updated_at": self._tick()}
        self._cases[contradiction_case_id] = updated
        return dict(updated)

    def get_contradiction_case_optional(self, contradiction_case_id: UUID) -> dict[str, object] | None:
        record = self._cases.get(contradiction_case_id)
        return None if record is None else dict(record)

    def list_contradiction_cases(
        self,
        *,
        statuses: list[str],
        limit: int,
        continuity_object_id: UUID | None,
    ) -> list[dict[str, object]]:
        rows = [
            dict(row)
            for row in self._cases.values()
            if row["status"] in statuses
            and (
                continuity_object_id is None
                or row["continuity_object_id"] == continuity_object_id
                or row["counterpart_object_id"] == continuity_object_id
            )
        ]
        rows.sort(key=lambda row: (row["updated_at"], str(row["id"])), reverse=True)
        return rows[:limit]

    def list_contradiction_cases_for_objects(
        self,
        *,
        continuity_object_ids: list[UUID],
        statuses: list[str],
    ) -> list[dict[str, object]]:
        requested = set(continuity_object_ids)
        rows = [
            dict(row)
            for row in self._cases.values()
            if row["status"] in statuses
            and (
                row["continuity_object_id"] in requested
                or row["counterpart_object_id"] in requested
            )
        ]
        rows.sort(key=lambda row: (row["updated_at"], str(row["id"])), reverse=True)
        return rows

    def upsert_trust_signal(
        self,
        *,
        continuity_object_id: UUID,
        signal_key: str,
        signal_type: str,
        signal_state: str,
        direction: str,
        magnitude: float,
        reason: str,
        contradiction_case_id: UUID | None,
        related_continuity_object_id: UUID | None,
        payload: dict[str, object],
    ) -> dict[str, object]:
        now = self._tick()
        key = (continuity_object_id, signal_key)
        existing = self._signals.get(key)
        row = {
            "id": existing["id"] if existing is not None else uuid4(),
            "user_id": _stable_uuid("user", "public-eval"),
            "continuity_object_id": continuity_object_id,
            "signal_key": signal_key,
            "signal_type": signal_type,
            "signal_state": signal_state,
            "direction": direction,
            "magnitude": magnitude,
            "reason": reason,
            "contradiction_case_id": contradiction_case_id,
            "related_continuity_object_id": related_continuity_object_id,
            "payload": dict(payload),
            "created_at": existing["created_at"] if existing is not None else now,
            "updated_at": now,
        }
        self._signals[key] = row
        return dict(row)

    def list_trust_signals(
        self,
        *,
        limit: int,
        continuity_object_id: UUID | None,
        signal_state: str | None,
        signal_type: str | None,
    ) -> list[dict[str, object]]:
        rows = [
            dict(row)
            for row in self._signals.values()
            if (continuity_object_id is None or row["continuity_object_id"] == continuity_object_id)
            and (signal_state is None or row["signal_state"] == signal_state)
            and (signal_type is None or row["signal_type"] == signal_type)
        ]
        rows.sort(key=lambda row: (row["updated_at"], str(row["id"])), reverse=True)
        return rows[:limit]


def _suite_status(passed_case_count: int, case_count: int) -> str:
    if case_count <= 0:
        return "fail"
    return "pass" if passed_case_count == case_count else "fail"


def _serialize_case_result(
    *,
    suite_key: str,
    case_key: str,
    title: str,
    status: str,
    score: float,
    summary: JsonObject,
    details: JsonObject,
) -> JsonObject:
    return {
        "suite_key": suite_key,
        "case_key": case_key,
        "title": title,
        "status": status,
        "score": score,
        "summary": summary,
        "details": details,
    }


def _evaluate_recall_suite(
    store: ContinuityStore,
    *,
    user_id: UUID,
    suite_key: str,
    cases: list[EvalCaseRow],
) -> list[JsonObject]:
    payload = get_retrieval_evaluation_summary(store, user_id=user_id)
    results_by_fixture_id = {result["fixture_id"]: result for result in payload["fixtures"]}
    suite_results: list[JsonObject] = []
    for case in cases:
        fixture = case["fixture"]
        fixture_id = str(fixture["fixture_id"])
        expected = case["expectations"]
        result = results_by_fixture_id[fixture_id]
        minimum_precision = float(expected.get("minimum_precision_at_k", 1.0))
        minimum_lift = float(expected.get("minimum_precision_lift_at_k", 0.0))
        require_expected_top_result = bool(expected.get("require_expected_top_result", True))
        expected_top_result_id = (
            result["expected_relevant_ids"][0] if result["expected_relevant_ids"] else None
        )
        passed = (
            result["precision_at_k"] >= minimum_precision
            and result["precision_lift_at_k"] >= minimum_lift
            and (
                not require_expected_top_result
                or result["top_result_id"] == expected_top_result_id
            )
        )
        summary: JsonObject = {
            "expected_top_result_id": expected_top_result_id,
            "top_result_id": result["top_result_id"],
            "precision_at_k": result["precision_at_k"],
            "baseline_precision_at_k": result["baseline_precision_at_k"],
            "precision_lift_at_k": result["precision_lift_at_k"],
            "hit_count": result["hit_count"],
            "top_k": result["top_k"],
            "require_expected_top_result": require_expected_top_result,
        }
        details: JsonObject = {
            "query": result["query"],
            "expected_relevant_ids": result["expected_relevant_ids"],
            "returned_ids": result["returned_ids"],
            "baseline_returned_ids": result["baseline_returned_ids"],
        }
        suite_results.append(
            _serialize_case_result(
                suite_key=suite_key,
                case_key=case["case_key"],
                title=_case_title(case),
                status="pass" if passed else "fail",
                score=float(result["precision_at_k"]),
                summary=summary,
                details=details,
            )
        )
    return suite_results


def _evaluate_resumption_case(*, suite_key: str, case: EvalCaseRow) -> JsonObject:
    rows = [_build_candidate_row(case_key=case["case_key"], payload=item) for item in _json_objects(case["fixture"].get("rows"))]
    request_payload = case["fixture"].get("request")
    request = ContinuityResumptionBriefRequestInput(**_json_object(request_payload))
    payload = compile_continuity_resumption_brief(
        _RecallOnlyStore(rows),  # type: ignore[arg-type]
        user_id=_stable_uuid("user", "public-eval"),
        request=request,
    )
    brief = payload["brief"]
    expected = case["expectations"]
    last_decision_title = None if brief["last_decision"]["item"] is None else brief["last_decision"]["item"]["title"]
    next_action_title = None if brief["next_action"]["item"] is None else brief["next_action"]["item"]["title"]
    open_loop_titles = [item["title"] for item in brief["open_loops"]["items"]]
    recent_change_titles = [item["title"] for item in brief["recent_changes"]["items"]]
    expected_last_decision = cast(str | None, expected.get("last_decision_title"))
    expected_next_action = cast(str | None, expected.get("next_action_title"))
    expected_open_loop_titles = _string_list(expected.get("open_loop_titles"))
    expected_recent_change_titles = _string_list(expected.get("recent_change_titles"))
    passed = (
        last_decision_title == expected_last_decision
        and next_action_title == expected_next_action
        and open_loop_titles == expected_open_loop_titles
        and recent_change_titles == expected_recent_change_titles
    )
    score = 1.0 if passed else 0.0
    return _serialize_case_result(
        suite_key=suite_key,
        case_key=case["case_key"],
        title=_case_title(case),
        status="pass" if passed else "fail",
        score=score,
        summary={
            "last_decision_title": last_decision_title,
            "next_action_title": next_action_title,
            "open_loop_count": len(open_loop_titles),
            "recent_change_count": len(recent_change_titles),
        },
        details={
            "open_loop_titles": open_loop_titles,
            "recent_change_titles": recent_change_titles,
        },
    )


def _evaluate_correction_case(*, suite_key: str, case: EvalCaseRow) -> JsonObject:
    rows = [_build_candidate_row(case_key=case["case_key"], payload=item) for item in _json_objects(case["fixture"].get("rows"))]
    target_object_key = str(case["fixture"]["target_object_key"])
    store = _CorrectionStore(rows)
    payload = apply_continuity_correction(
        store,  # type: ignore[arg-type]
        user_id=_stable_uuid("user", "public-eval"),
        continuity_object_id=_stable_uuid("continuity_object", f"{case['case_key']}:{target_object_key}"),
        request=ContinuityCorrectionInput(**_json_object(case["fixture"].get("request"))),
    )
    continuity_object = payload["continuity_object"]
    replacement_object = payload["replacement_object"]
    expected = case["expectations"]
    replacement_status = None if replacement_object is None else replacement_object["status"]
    replacement_title = None if replacement_object is None else replacement_object["title"]
    passed = (
        continuity_object["status"] == expected.get("updated_status")
        and bool(replacement_object is not None) is bool(expected.get("replacement_created", False))
        and replacement_status == expected.get("replacement_status")
        and replacement_title == expected.get("replacement_title")
    )
    return _serialize_case_result(
        suite_key=suite_key,
        case_key=case["case_key"],
        title=_case_title(case),
        status="pass" if passed else "fail",
        score=1.0 if passed else 0.0,
        summary={
            "updated_status": continuity_object["status"],
            "replacement_created": replacement_object is not None,
            "replacement_status": replacement_status,
        },
        details={
            "updated_title": continuity_object["title"],
            "replacement_title": replacement_title,
            "correction_action": payload["correction_event"]["action"],
        },
    )


def _evaluate_contradiction_case(*, suite_key: str, case: EvalCaseRow) -> JsonObject:
    rows = [_build_candidate_row(case_key=case["case_key"], payload=item) for item in _json_objects(case["fixture"].get("rows"))]
    store = _ContradictionStore(rows)
    sync = sync_contradiction_state_for_objects(
        store,  # type: ignore[arg-type]
        continuity_object_ids=[row["id"] for row in rows],
    )
    open_cases = store.list_contradiction_cases(statuses=["open"], limit=100, continuity_object_id=None)
    open_case_kinds = sorted(str(case_row["kind"]) for case_row in open_cases)
    active_signal_types = sorted(
        {
            str(signal["signal_type"])
            for signal in store.list_trust_signals(
                limit=100,
                continuity_object_id=None,
                signal_state="active",
                signal_type=None,
            )
        }
    )
    expected = case["expectations"]
    passed = (
        len(open_cases) == int(expected.get("open_case_count", 0))
        and open_case_kinds == _string_list(expected.get("open_case_kinds"))
        and active_signal_types == _string_list(expected.get("active_signal_types"))
    )
    return _serialize_case_result(
        suite_key=suite_key,
        case_key=case["case_key"],
        title=_case_title(case),
        status="pass" if passed else "fail",
        score=1.0 if passed else 0.0,
        summary={
            "open_case_count": len(open_cases),
            "open_case_kinds": open_case_kinds,
            "active_signal_types": active_signal_types,
            "scanned_object_count": sync.scanned_object_count,
        },
        details={
            "updated_case_count": sync.updated_case_count,
            "resolved_case_count": sync.resolved_case_count,
        },
    )


def _evaluate_open_loop_case(*, suite_key: str, case: EvalCaseRow) -> JsonObject:
    rows = [_build_candidate_row(case_key=case["case_key"], payload=item) for item in _json_objects(case["fixture"].get("rows"))]
    payload = compile_continuity_open_loop_dashboard(
        _RecallOnlyStore(rows),  # type: ignore[arg-type]
        user_id=_stable_uuid("user", "public-eval"),
        request=ContinuityOpenLoopDashboardQueryInput(**_json_object(case["fixture"].get("request"))),
    )
    dashboard = payload["dashboard"]
    actual_titles: JsonObject = {
        posture: [item["title"] for item in dashboard[posture]["items"]]
        for posture in ("waiting_for", "blocker", "stale", "next_action")
    }
    expected_titles = {
        posture: _string_list(case["expectations"].get(f"{posture}_titles"))
        for posture in ("waiting_for", "blocker", "stale", "next_action")
    }
    passed = all(actual_titles[posture] == expected_titles[posture] for posture in expected_titles)
    total_count = int(dashboard["summary"]["total_count"])
    return _serialize_case_result(
        suite_key=suite_key,
        case_key=case["case_key"],
        title=_case_title(case),
        status="pass" if passed else "fail",
        score=1.0 if passed else 0.0,
        summary={
            "total_count": total_count,
            "waiting_for_count": len(cast(list[str], actual_titles["waiting_for"])),
            "blocker_count": len(cast(list[str], actual_titles["blocker"])),
            "stale_count": len(cast(list[str], actual_titles["stale"])),
            "next_action_count": len(cast(list[str], actual_titles["next_action"])),
        },
        details=cast(JsonObject, actual_titles),
    )


def _evaluate_case(*, suite_key: str, case: EvalCaseRow) -> JsonObject:
    evaluator_kind = case["evaluator_kind"]
    if evaluator_kind == "resumption_brief":
        return _evaluate_resumption_case(suite_key=suite_key, case=case)
    if evaluator_kind == "continuity_correction":
        return _evaluate_correction_case(suite_key=suite_key, case=case)
    if evaluator_kind == "contradiction_sync":
        return _evaluate_contradiction_case(suite_key=suite_key, case=case)
    if evaluator_kind == "open_loop_dashboard":
        return _evaluate_open_loop_case(suite_key=suite_key, case=case)
    raise ValueError(f"unsupported public eval evaluator kind: {evaluator_kind}")


def _sync_fixture_catalog(
    store: ContinuityStore,
    *,
    catalog: JsonObject,
) -> list[EvalSuiteRow]:
    raw_suites = _validate_fixture_catalog(catalog)
    synced_suites: list[EvalSuiteRow] = []
    synced_suite_keys: list[str] = []
    for suite_order, raw_suite in enumerate(raw_suites, start=1):
        suite_cases = _json_objects(raw_suite.get("cases"))
        suite_key = str(raw_suite["suite_key"])
        suite = store.upsert_eval_suite(
            suite_key=suite_key,
            title=str(raw_suite["title"]),
            description=str(raw_suite["description"]),
            evaluator_kind=str(raw_suite["evaluator_kind"]),
            fixture_schema_version=PUBLIC_EVAL_FIXTURE_SCHEMA_VERSION,
            fixture_source_path=PUBLIC_EVAL_FIXTURE_SOURCE_PATH,
            case_count=len(suite_cases),
            suite_order=suite_order,
            metadata={
                "metric_key": str(raw_suite.get("metric_key", "pass_rate")),
            },
        )
        synced_suites.append(suite)
        synced_suite_keys.append(suite_key)
        synced_case_keys: list[str] = []
        for case_order, raw_case in enumerate(suite_cases, start=1):
            case_key = str(raw_case["case_key"])
            store.upsert_eval_case(
                suite_id=suite["id"],
                case_key=case_key,
                title=str(raw_case["title"]),
                evaluator_kind=str(raw_case["evaluator_kind"]),
                case_order=case_order,
                fixture=_json_object(raw_case.get("fixture")),
                expectations=_json_object(raw_case.get("expectations")),
            )
            synced_case_keys.append(case_key)
        store.delete_eval_cases_for_suite_not_in(
            suite_id=suite["id"],
            case_keys=synced_case_keys,
        )
    store.delete_eval_suites_not_in(synced_suite_keys)
    return synced_suites


def _catalog_suite_definition_records(catalog: JsonObject) -> list[PublicEvalSuiteDefinitionRecord]:
    raw_suites = _validate_fixture_catalog(catalog)
    items: list[PublicEvalSuiteDefinitionRecord] = []
    for raw_suite in raw_suites:
        suite_cases = _json_objects(raw_suite.get("cases"))
        items.append(
            {
                "suite_key": str(raw_suite["suite_key"]),
                "title": str(raw_suite["title"]),
                "description": str(raw_suite["description"]),
                "evaluator_kind": str(raw_suite["evaluator_kind"]),
                "case_count": len(suite_cases),
                "fixture_schema_version": PUBLIC_EVAL_FIXTURE_SCHEMA_VERSION,
                "fixture_source_path": PUBLIC_EVAL_FIXTURE_SOURCE_PATH,
                "case_keys": [str(raw_case["case_key"]) for raw_case in suite_cases],
            }
        )
    return items


def _build_suite_report(
    suite: EvalSuiteRow,
    *,
    results: list[JsonObject],
) -> JsonObject:
    case_count = len(results)
    passed_case_count = sum(1 for result in results if result["status"] == "pass")
    failed_case_count = case_count - passed_case_count
    average_score = 0.0 if case_count == 0 else sum(float(result["score"]) for result in results) / case_count
    return {
        "suite_key": suite["suite_key"],
        "title": suite["title"],
        "description": suite["description"],
        "evaluator_kind": suite["evaluator_kind"],
        "case_count": case_count,
        "passed_case_count": passed_case_count,
        "failed_case_count": failed_case_count,
        "pass_rate": 0.0 if case_count == 0 else passed_case_count / case_count,
        "average_score": average_score,
        "status": _suite_status(passed_case_count, case_count),
        "cases": results,
    }


def _report_digest(report: JsonObject) -> str:
    serialized = json.dumps(report, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def write_public_eval_report(*, report: JsonObject, report_path: str | Path) -> Path:
    output_path = Path(report_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def list_public_eval_suites(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> PublicEvalSuiteDefinitionListResponse:
    del store, user_id
    catalog = _load_fixture_catalog()
    items = _catalog_suite_definition_records(catalog)
    return {
        "items": items,
        "summary": {
            "suite_count": len(items),
            "case_count": sum(item["case_count"] for item in items),
            "order": list(PUBLIC_EVAL_SUITE_ORDER),
        },
    }


def run_public_evals(
    store: ContinuityStore,
    *,
    user_id: UUID,
    suite_keys: list[str] | None = None,
) -> PublicEvalRunDetailResponse:
    catalog = _load_fixture_catalog()
    synced_suites = _sync_fixture_catalog(store, catalog=catalog)
    available_suite_keys = [suite["suite_key"] for suite in synced_suites]
    requested_suite_keys = list(dict.fromkeys(suite_keys or available_suite_keys))
    unknown_suite_keys = sorted(set(requested_suite_keys) - set(available_suite_keys))
    if unknown_suite_keys:
        raise ValueError(f"unknown suite_key values: {', '.join(unknown_suite_keys)}")
    selected_suites = [
        suite for suite in synced_suites if suite["suite_key"] in set(requested_suite_keys)
    ]

    suite_reports: list[JsonObject] = []
    persisted_results: list[JsonObject] = []
    for suite in selected_suites:
        cases = store.list_eval_cases_for_suite(suite["id"])
        if suite["evaluator_kind"] == "retrieval_evaluation":
            results = _evaluate_recall_suite(
                store,
                user_id=user_id,
                suite_key=suite["suite_key"],
                cases=cases,
            )
        else:
            results = [_evaluate_case(suite_key=suite["suite_key"], case=case) for case in cases]
        suite_reports.append(_build_suite_report(suite, results=results))
        persisted_results.extend(results)

    suite_count = len(suite_reports)
    case_count = len(persisted_results)
    passed_case_count = sum(1 for result in persisted_results if result["status"] == "pass")
    failed_case_count = case_count - passed_case_count
    report: JsonObject = {
        "schema_version": PUBLIC_EVAL_REPORT_SCHEMA_VERSION,
        "fixture_schema_version": PUBLIC_EVAL_FIXTURE_SCHEMA_VERSION,
        "fixture_source_path": PUBLIC_EVAL_FIXTURE_SOURCE_PATH,
        "summary": {
            "status": _suite_status(passed_case_count, case_count),
            "suite_count": suite_count,
            "case_count": case_count,
            "passed_case_count": passed_case_count,
            "failed_case_count": failed_case_count,
            "pass_rate": 0.0 if case_count == 0 else passed_case_count / case_count,
        },
        "suites": suite_reports,
    }
    digest = _report_digest(report)
    run_row = store.create_eval_run(
        fixture_schema_version=PUBLIC_EVAL_FIXTURE_SCHEMA_VERSION,
        fixture_source_path=PUBLIC_EVAL_FIXTURE_SOURCE_PATH,
        requested_suite_keys=requested_suite_keys,
        status=str(report["summary"]["status"]),
        summary=_json_object(report["summary"]),
        report=report,
        report_digest=digest,
    )
    result_rows: list[PublicEvalResultRecord] = []
    for result in persisted_results:
        row = store.create_eval_result(
            eval_run_id=run_row["id"],
            suite_key=str(result["suite_key"]),
            case_key=str(result["case_key"]),
            status=str(result["status"]),
            score=float(result["score"]),
            summary=_json_object(result["summary"]),
            details=_json_object(result["details"]),
        )
        result_rows.append(_serialize_eval_result_row(row))
    return {
        "run": _serialize_eval_run_row(run_row),
        "report": report,
        "results": result_rows,
    }


def _serialize_eval_run_row(row: EvalRunRow) -> PublicEvalRunRecord:
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "report_digest": row["report_digest"],
        "summary": row["summary"],
        "created_at": row["created_at"].isoformat(),
    }


def _serialize_eval_result_row(row: EvalResultRow) -> PublicEvalResultRecord:
    return {
        "id": str(row["id"]),
        "suite_key": row["suite_key"],
        "case_key": row["case_key"],
        "status": row["status"],
        "score": float(row["score"]),
        "summary": row["summary"],
        "details": row["details"],
        "created_at": row["created_at"].isoformat(),
    }


def list_public_eval_runs(
    store: ContinuityStore,
    *,
    user_id: UUID,
    limit: int,
) -> PublicEvalRunListResponse:
    del user_id
    rows = store.list_eval_runs(limit=limit)
    return {
        "items": [_serialize_eval_run_row(row) for row in rows],
        "summary": {
            "limit": limit,
            "returned_count": len(rows),
            "order": list(PUBLIC_EVAL_RUN_ORDER),
        },
    }


def get_public_eval_run(
    store: ContinuityStore,
    *,
    user_id: UUID,
    eval_run_id: UUID,
) -> PublicEvalRunDetailResponse:
    del user_id
    run_row = store.get_eval_run_optional(eval_run_id)
    if run_row is None:
        raise LookupError(f"eval run {eval_run_id} was not found")
    result_rows = store.list_eval_results_for_run(eval_run_id)
    return {
        "run": _serialize_eval_run_row(run_row),
        "report": run_row["report"],
        "results": [_serialize_eval_result_row(row) for row in result_rows],
    }


__all__ = [
    "PUBLIC_EVAL_FIXTURE_SCHEMA_VERSION",
    "PUBLIC_EVAL_FIXTURE_SOURCE_PATH",
    "PUBLIC_EVAL_REPORT_SCHEMA_VERSION",
    "get_public_eval_run",
    "list_public_eval_runs",
    "list_public_eval_suites",
    "run_public_evals",
    "write_public_eval_report",
]
