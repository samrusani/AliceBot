from __future__ import annotations

from alicebot_api.telegram_continuity import classify_telegram_message_intent


def test_classify_routes_capture_by_default() -> None:
    classified = classify_telegram_message_intent("Decision: ship P10-S3")

    assert classified["intent_kind"] == "capture"
    assert classified["intent_payload"]["raw_content"] == "Decision: ship P10-S3"


def test_classify_routes_recall_resume_open_loop_and_approvals_commands() -> None:
    recall = classify_telegram_message_intent("/recall sprint objective")
    resume = classify_telegram_message_intent("/resume")
    open_loops = classify_telegram_message_intent("/open-loops")
    approvals = classify_telegram_message_intent("/approvals")

    assert recall["intent_kind"] == "recall"
    assert recall["intent_payload"]["query"] == "sprint objective"
    assert resume["intent_kind"] == "resume"
    assert open_loops["intent_kind"] == "open_loops"
    assert approvals["intent_kind"] == "approvals"


def test_classify_routes_correction_and_open_loop_review_commands() -> None:
    object_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    correction = classify_telegram_message_intent(f"/correct {object_id} Decision: use deterministic routing")
    review = classify_telegram_message_intent(f"/open-loop {object_id} deferred needs new signal")

    assert correction["intent_kind"] == "correction"
    assert correction["intent_payload"]["continuity_object_id"] == object_id
    assert correction["intent_payload"]["replacement_title"] == "Decision: use deterministic routing"

    assert review["intent_kind"] == "open_loop_review"
    assert review["intent_payload"]["continuity_object_id"] == object_id
    assert review["intent_payload"]["action"] == "deferred"
    assert review["intent_payload"]["note"] == "needs new signal"


def test_classify_routes_approval_resolution_commands() -> None:
    approval_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    approve = classify_telegram_message_intent(f"/approve {approval_id}")
    reject = classify_telegram_message_intent(f"/reject {approval_id} no longer needed")

    assert approve["intent_kind"] == "approval_approve"
    assert approve["intent_payload"]["approval_id"] == approval_id

    assert reject["intent_kind"] == "approval_reject"
    assert reject["intent_payload"]["approval_id"] == approval_id
    assert reject["intent_payload"]["note"] == "no longer needed"


def test_classify_empty_message_is_unknown() -> None:
    classified = classify_telegram_message_intent("    ")

    assert classified["intent_kind"] == "unknown"
    assert classified["intent_payload"]["reason"] == "empty_message"
