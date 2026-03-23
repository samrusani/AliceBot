#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Iterator
import contextlib
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any, Callable, Literal
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import UUID, uuid4

ROOT_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"


def _maybe_reexec_into_venv() -> None:
    if not VENV_PYTHON.exists():
        return
    venv_root = ROOT_DIR / ".venv"
    try:
        active_prefix = Path(sys.prefix).resolve()
        expected_prefix = venv_root.resolve()
    except OSError:
        active_prefix = Path(sys.prefix)
        expected_prefix = venv_root
    if active_prefix == expected_prefix:
        return
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])


_maybe_reexec_into_venv()

from alembic import command
import anyio
import psycopg
from psycopg import sql

API_SRC_DIR = ROOT_DIR / "apps" / "api" / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

import apps.api.src.alicebot_api.main as main_module
import alicebot_api.response_generation as response_generation_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.contracts import ModelInvocationResponse, ModelUsagePayload
from alicebot_api.db import user_connection
from alicebot_api.migrations import make_alembic_config
from alicebot_api.store import ContinuityStore

DEFAULT_ADMIN_URL = "postgresql://alicebot_admin:alicebot_admin@localhost:5432/alicebot"
DEFAULT_APP_URL = "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"

ACCEPTANCE_GATE_NAME = "acceptance_suite"
LATENCY_GATE_NAME = "latency_p95"
CACHE_GATE_NAME = "cache_reuse"
MEMORY_GATE_NAME = "memory_quality"

LATENCY_P95_THRESHOLD_SECONDS = 5.0
CACHE_REUSE_THRESHOLD = 0.70
MEMORY_PRECISION_THRESHOLD = 0.80
MEMORY_MIN_ADJUDICATED_SAMPLE = 20
PROBE_CALL_COUNT = 8

GateStatus = Literal["PASS", "FAIL", "BLOCKED"]
InducedScenario = Literal[
    "acceptance_fail",
    "latency_fail",
    "cache_fail",
    "cache_blocked",
    "memory_needs_review",
    "memory_insufficient",
]
CacheTelemetryMode = Literal["present", "low_reuse", "missing"]
MemoryProfile = Literal["on_track", "needs_review", "insufficient_evidence"]
INDUCED_SCENARIOS: tuple[InducedScenario, ...] = (
    "acceptance_fail",
    "latency_fail",
    "cache_fail",
    "cache_blocked",
    "memory_needs_review",
    "memory_insufficient",
)


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    status: GateStatus
    measured: str
    threshold: str
    detail: str


@dataclass(frozen=True, slots=True)
class ProbeRun:
    durations_seconds: list[float]
    usages: list[ModelUsagePayload]


@contextlib.contextmanager
def _temporary_database_urls() -> Iterator[dict[str, str]]:
    admin_root_url = os.getenv("DATABASE_ADMIN_URL", DEFAULT_ADMIN_URL)
    app_root_url = os.getenv("DATABASE_URL", DEFAULT_APP_URL)
    database_name = f"alicebot_readiness_{uuid4().hex[:12]}"
    admin_database_url = _swap_database_name(admin_root_url, database_name)
    app_database_url = _swap_database_name(app_root_url, database_name)

    with psycopg.connect(admin_root_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
            cur.execute(
                sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO alicebot_app").format(
                    sql.Identifier(database_name)
                )
            )

    try:
        yield {"admin": admin_database_url, "app": app_database_url}
    finally:
        with psycopg.connect(admin_root_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                        sql.Identifier(database_name)
                    )
                )


@contextlib.contextmanager
def _patched_api_runtime(
    *,
    settings: Settings,
    invoke_model: Callable[..., ModelInvocationResponse],
) -> Iterator[None]:
    original_get_settings = main_module.get_settings
    original_invoke_model = response_generation_module.invoke_model

    main_module.get_settings = lambda: settings  # type: ignore[assignment]
    response_generation_module.invoke_model = invoke_model  # type: ignore[assignment]
    try:
        yield
    finally:
        main_module.get_settings = original_get_settings  # type: ignore[assignment]
        response_generation_module.invoke_model = original_invoke_model  # type: ignore[assignment]


def _swap_database_name(database_url: str, database_name: str) -> str:
    parsed = urlsplit(database_url)
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{database_name}", parsed.query, parsed.fragment))


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic Phase 2 readiness gates for quantitative evidence.",
    )
    parser.add_argument(
        "--induce-gate",
        choices=INDUCED_SCENARIOS,
        default=None,
        help="Intentionally induce one gate outcome to validate deterministic failure/blocked behavior.",
    )
    return parser.parse_args(argv)


def _seed_probe_state(database_url: str) -> dict[str, UUID]:
    user_id = uuid4()

    with user_connection(database_url, user_id) as conn:
        store = ContinuityStore(conn)
        store.create_user(user_id, "readiness@example.com", "Readiness Runner")
        thread = store.create_thread("Phase 2 readiness probe")
        session = store.create_session(thread["id"], status="active")
        source_event = store.append_event(
            thread["id"],
            session["id"],
            "message.user",
            {"text": "Probe baseline context."},
        )

    return {
        "user_id": user_id,
        "thread_id": thread["id"],
        "source_event_id": source_event["id"],
    }


def _seed_memory_quality_sample(
    *,
    database_url: str,
    user_id: UUID,
    source_event_id: UUID,
    profile: MemoryProfile,
) -> None:
    if profile == "on_track":
        correct_count = 17
        incorrect_count = 3
        total_count = 20
    elif profile == "needs_review":
        correct_count = 16
        incorrect_count = 4
        total_count = 20
    else:
        correct_count = 9
        incorrect_count = 1
        total_count = 10

    with user_connection(database_url, user_id) as conn:
        store = ContinuityStore(conn)
        for index in range(total_count):
            memory = store.create_memory(
                memory_key=f"user.readiness.sample.{index}",
                value={"value": index},
                status="active",
                source_event_ids=[str(source_event_id)],
            )
            if index < correct_count:
                store.create_memory_review_label(
                    memory_id=memory["id"],
                    label="correct",
                    note="Readiness seed: correct",
                )
            elif index < correct_count + incorrect_count:
                store.create_memory_review_label(
                    memory_id=memory["id"],
                    label="incorrect",
                    note="Readiness seed: incorrect",
                )


def _invoke_request(
    method: str,
    path: str,
    *,
    query_params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
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
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": [(b"content-type", b"application/json")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    anyio.run(main_module.app, scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    parsed_body = {} if not body else json.loads(body)
    return int(start_message["status"]), parsed_body


def calculate_p95_seconds(durations_seconds: list[float]) -> float:
    if not durations_seconds:
        raise ValueError("at least one probe duration is required")

    sorted_durations = sorted(durations_seconds)
    rank = math.ceil(0.95 * len(sorted_durations))
    return sorted_durations[max(rank - 1, 0)]


def _evaluate_latency_gate(durations_seconds: list[float]) -> GateResult:
    p95_seconds = calculate_p95_seconds(durations_seconds)
    status: GateStatus = "PASS" if p95_seconds < LATENCY_P95_THRESHOLD_SECONDS else "FAIL"
    return GateResult(
        gate=LATENCY_GATE_NAME,
        status=status,
        measured=(
            f"p95_seconds={p95_seconds:.6f}; "
            f"samples={','.join(f'{value:.6f}' for value in durations_seconds)}"
        ),
        threshold=f"p95_seconds < {LATENCY_P95_THRESHOLD_SECONDS:.1f}",
        detail=f"probe_count={len(durations_seconds)}",
    )


def calculate_cache_reuse_ratio(usages: list[ModelUsagePayload]) -> float | None:
    if not usages:
        return None

    total_input_tokens = 0
    total_cached_tokens = 0
    for usage in usages:
        input_tokens = usage.get("input_tokens")
        cached_input_tokens = usage.get("cached_input_tokens")
        if not isinstance(input_tokens, int) or input_tokens <= 0:
            return None
        if not isinstance(cached_input_tokens, int) or cached_input_tokens < 0:
            return None
        total_input_tokens += input_tokens
        total_cached_tokens += min(cached_input_tokens, input_tokens)

    if total_input_tokens <= 0:
        return None
    return total_cached_tokens / total_input_tokens


def _evaluate_cache_reuse_gate(usages: list[ModelUsagePayload]) -> GateResult:
    ratio = calculate_cache_reuse_ratio(usages)
    if ratio is None:
        return GateResult(
            gate=CACHE_GATE_NAME,
            status="BLOCKED",
            measured="cache_reuse_ratio=unavailable",
            threshold=f"cache_reuse_ratio >= {CACHE_REUSE_THRESHOLD:.2f}",
            detail="cached token telemetry was not available for all probe responses",
        )

    status: GateStatus = "PASS" if ratio >= CACHE_REUSE_THRESHOLD else "FAIL"
    return GateResult(
        gate=CACHE_GATE_NAME,
        status=status,
        measured=f"cache_reuse_ratio={ratio:.6f}",
        threshold=f"cache_reuse_ratio >= {CACHE_REUSE_THRESHOLD:.2f}",
        detail=f"probe_count={len(usages)}",
    )


def _evaluate_memory_quality_gate(summary: dict[str, Any]) -> GateResult:
    counts = summary.get("label_row_counts_by_value")
    if not isinstance(counts, dict):
        return GateResult(
            gate=MEMORY_GATE_NAME,
            status="BLOCKED",
            measured="precision=unavailable; adjudicated_sample=unavailable",
            threshold=(
                f"precision > {MEMORY_PRECISION_THRESHOLD:.2f} and "
                f"adjudicated_sample >= {MEMORY_MIN_ADJUDICATED_SAMPLE}"
            ),
            detail="evaluation summary payload was missing label counts",
        )

    correct = counts.get("correct")
    incorrect = counts.get("incorrect")
    unlabeled = summary.get("unlabeled_memory_count")
    if not isinstance(correct, int) or not isinstance(incorrect, int) or not isinstance(unlabeled, int):
        return GateResult(
            gate=MEMORY_GATE_NAME,
            status="BLOCKED",
            measured="precision=unavailable; adjudicated_sample=unavailable",
            threshold=(
                f"precision > {MEMORY_PRECISION_THRESHOLD:.2f} and "
                f"adjudicated_sample >= {MEMORY_MIN_ADJUDICATED_SAMPLE}"
            ),
            detail="evaluation summary payload had invalid value types",
        )

    adjudicated_sample = correct + incorrect
    precision = None if adjudicated_sample == 0 else correct / adjudicated_sample

    if adjudicated_sample < MEMORY_MIN_ADJUDICATED_SAMPLE:
        status: GateStatus = "BLOCKED"
        posture = "insufficient_evidence"
    elif precision is not None and precision > MEMORY_PRECISION_THRESHOLD:
        status = "PASS"
        posture = "on_track"
    else:
        status = "FAIL"
        posture = "needs_review"

    precision_text = "undefined" if precision is None else f"{precision:.6f}"
    return GateResult(
        gate=MEMORY_GATE_NAME,
        status=status,
        measured=(
            f"precision={precision_text}; adjudicated_sample={adjudicated_sample}; "
            f"unlabeled_memory_count={unlabeled}; posture={posture}"
        ),
        threshold=(
            f"precision > {MEMORY_PRECISION_THRESHOLD:.2f} and "
            f"adjudicated_sample >= {MEMORY_MIN_ADJUDICATED_SAMPLE}"
        ),
        detail=f"correct={correct}; incorrect={incorrect}",
    )


def _build_probe_invoke_model(
    *,
    cache_mode: CacheTelemetryMode,
    captured_usages: list[ModelUsagePayload],
) -> Callable[..., ModelInvocationResponse]:
    def fake_invoke_model(*, settings: Settings, request: Any) -> ModelInvocationResponse:
        del settings
        del request
        usage: ModelUsagePayload
        if cache_mode == "present":
            usage = {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "cached_input_tokens": 80,
            }
        elif cache_mode == "low_reuse":
            usage = {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "cached_input_tokens": 50,
            }
        else:
            usage = {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            }

        captured_usages.append(usage)
        return ModelInvocationResponse(
            provider="openai_responses",
            model="gpt-5-mini",
            response_id="resp_readiness_probe",
            finish_reason="completed",
            output_text="Readiness probe reply.",
            usage=usage,
        )

    return fake_invoke_model


def _run_response_probes(
    *,
    settings: Settings,
    user_id: UUID,
    thread_id: UUID,
    cache_mode: CacheTelemetryMode,
    forced_duration_seconds: float | None,
) -> ProbeRun:
    durations_seconds: list[float] = []
    captured_usages: list[ModelUsagePayload] = []
    invoke_model = _build_probe_invoke_model(cache_mode=cache_mode, captured_usages=captured_usages)

    with _patched_api_runtime(settings=settings, invoke_model=invoke_model):
        for index in range(PROBE_CALL_COUNT):
            started = time.perf_counter()
            status_code, payload = _invoke_request(
                "POST",
                "/v0/responses",
                payload={
                    "user_id": str(user_id),
                    "thread_id": str(thread_id),
                    "message": f"Readiness probe call {index + 1}",
                },
            )
            elapsed = time.perf_counter() - started
            duration = elapsed if forced_duration_seconds is None else forced_duration_seconds
            durations_seconds.append(duration)
            if status_code != 200:
                raise RuntimeError(
                    "response probe call failed: "
                    f"status={status_code} payload={json.dumps(payload, sort_keys=True)}"
                )

    return ProbeRun(durations_seconds=durations_seconds, usages=captured_usages)


def _fetch_memory_summary(*, settings: Settings, user_id: UUID) -> dict[str, Any]:
    def unused_invoke_model(*, settings: Settings, request: Any) -> ModelInvocationResponse:
        del settings
        del request
        raise AssertionError("invoke_model should not be called for memory summary gate")

    with _patched_api_runtime(settings=settings, invoke_model=unused_invoke_model):
        status_code, payload = _invoke_request(
            "GET",
            "/v0/memories/evaluation-summary",
            query_params={"user_id": str(user_id)},
        )
    if status_code != 200:
        raise RuntimeError(
            "memory summary request failed: "
            f"status={status_code} payload={json.dumps(payload, sort_keys=True)}"
        )

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("memory summary response did not include a summary object")
    return summary


def _run_acceptance_suite_gate(*, induce_failure: bool) -> GateResult:
    python_executable = _resolve_python_executable()
    command_parts = [python_executable, "scripts/run_phase2_acceptance.py"]
    if induce_failure:
        command_parts.extend(["--induce-failure", "response_memory"])

    completed = subprocess.run(
        command_parts,
        cwd=ROOT_DIR,
        check=False,
    )
    status: GateStatus = "PASS" if completed.returncode == 0 else "FAIL"
    return GateResult(
        gate=ACCEPTANCE_GATE_NAME,
        status=status,
        measured=f"exit_code={completed.returncode}",
        threshold="exit_code == 0",
        detail=f"command={shlex.join(command_parts)}",
    )


def run_readiness_gates(*, induce_gate: InducedScenario | None = None) -> list[GateResult]:
    gate_results: list[GateResult] = []

    acceptance_gate = _run_acceptance_suite_gate(induce_failure=induce_gate == "acceptance_fail")
    gate_results.append(acceptance_gate)

    cache_mode: CacheTelemetryMode = "present"
    if induce_gate == "cache_blocked":
        cache_mode = "missing"
    elif induce_gate == "cache_fail":
        cache_mode = "low_reuse"

    memory_profile: MemoryProfile = "on_track"
    if induce_gate == "memory_needs_review":
        memory_profile = "needs_review"
    elif induce_gate == "memory_insufficient":
        memory_profile = "insufficient_evidence"

    forced_duration_seconds = 5.2 if induce_gate == "latency_fail" else None

    try:
        with _temporary_database_urls() as database_urls:
            config = make_alembic_config(database_urls["admin"])
            command.upgrade(config, "head")

            seeded = _seed_probe_state(database_urls["app"])
            _seed_memory_quality_sample(
                database_url=database_urls["app"],
                user_id=seeded["user_id"],
                source_event_id=seeded["source_event_id"],
                profile=memory_profile,
            )

            settings = Settings(
                database_url=database_urls["app"],
                model_provider="openai_responses",
                model_name="gpt-5-mini",
                model_api_key="test-key",
            )
            probe_run = _run_response_probes(
                settings=settings,
                user_id=seeded["user_id"],
                thread_id=seeded["thread_id"],
                cache_mode=cache_mode,
                forced_duration_seconds=forced_duration_seconds,
            )
            gate_results.append(_evaluate_latency_gate(probe_run.durations_seconds))
            gate_results.append(_evaluate_cache_reuse_gate(probe_run.usages))

            summary = _fetch_memory_summary(settings=settings, user_id=seeded["user_id"])
            gate_results.append(_evaluate_memory_quality_gate(summary))
    except Exception as exc:
        blocked_detail = str(exc)
        existing_gates = {result.gate for result in gate_results}
        if LATENCY_GATE_NAME not in existing_gates:
            gate_results.append(
                GateResult(
                    gate=LATENCY_GATE_NAME,
                    status="BLOCKED",
                    measured="p95_seconds=unavailable",
                    threshold=f"p95_seconds < {LATENCY_P95_THRESHOLD_SECONDS:.1f}",
                    detail=blocked_detail,
                )
            )
        if CACHE_GATE_NAME not in existing_gates:
            gate_results.append(
                GateResult(
                    gate=CACHE_GATE_NAME,
                    status="BLOCKED",
                    measured="cache_reuse_ratio=unavailable",
                    threshold=f"cache_reuse_ratio >= {CACHE_REUSE_THRESHOLD:.2f}",
                    detail=blocked_detail,
                )
            )
        if MEMORY_GATE_NAME not in existing_gates:
            gate_results.append(
                GateResult(
                    gate=MEMORY_GATE_NAME,
                    status="BLOCKED",
                    measured="precision=unavailable; adjudicated_sample=unavailable",
                    threshold=(
                        f"precision > {MEMORY_PRECISION_THRESHOLD:.2f} and "
                        f"adjudicated_sample >= {MEMORY_MIN_ADJUDICATED_SAMPLE}"
                    ),
                    detail=blocked_detail,
                )
            )

    return gate_results


def exit_code_for_gate_results(gate_results: list[GateResult]) -> int:
    return 0 if all(result.status == "PASS" for result in gate_results) else 1


def _print_gate_results(gate_results: list[GateResult]) -> None:
    print("Phase 2 readiness gate results:")
    for result in gate_results:
        print(f" - {result.gate}: {result.status}")
        print(f"   measured: {result.measured}")
        print(f"   threshold: {result.threshold}")
        print(f"   detail: {result.detail}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    gate_results = run_readiness_gates(induce_gate=args.induce_gate)
    _print_gate_results(gate_results)

    exit_code = exit_code_for_gate_results(gate_results)
    if exit_code == 0:
        print("Phase 2 readiness gate result: PASS")
    else:
        print("Phase 2 readiness gate result: NO_GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
