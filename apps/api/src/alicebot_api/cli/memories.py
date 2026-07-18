from __future__ import annotations

import argparse
from uuid import uuid4
from alicebot_api.cli_formatting import format_contradiction_sync_output
from alicebot_api.continuity_contradictions import sync_contradictions
from alicebot_api.contracts import ContradictionSyncInput
from alicebot_api.vnext_agent_control import agent_metadata, ensure_policy_allowed, summarize_agent_policy_telemetry
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_embeddings import (
    DeferredMemoryEmbedding,
    EMBEDDINGS_API_KEY_ENV,
    EMBEDDINGS_BASE_URL_ENV,
    EMBEDDINGS_MODEL_ENV,
    EMBEDDING_SIGNATURE_VERSION,
    MAX_EMBEDDINGS_BATCH_SIZE,
    endpoint_fingerprint,
    get_embedding_provider,
    memory_embedding_text,
    persist_deferred_memory_embeddings_best_effort,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.mcp_tools import redact_memory_flow
from alicebot_api.vnext_memory_commit import VNextMemoryCommitService, memory_commit_request_from_payload
from .errors import EmbeddingBackfillFailure, _emit_cli_error
from .models import CLIContext
from .shared import (
    _json_dumps,
    _persist_deferred_embedding_inputs,
    _store_context,
    _vnext_agent_identity_from_args,
    _vnext_policy_checked_for_args,
    _vnext_store_context,
)


def _run_vnext_agent_propose_memory(ctx: CLIContext, args: argparse.Namespace) -> str:
    if not getattr(args, "agent_id", None):
        raise ValueError("--agent-id is required")
    blocked_decision = None
    memory: JsonObject | None = None
    decision = None
    with _vnext_store_context(ctx) as store:
        identity, _actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="memory.propose",
            domains=(args.domain,),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            if identity is None:
                raise ValueError("--agent-id is required")
            memory = store.create_memory(
                {
                    "memory_type": args.memory_type,
                    "memory_key": f"agent_proposal.{args.proposal_type}.{uuid4()}",
                    "value": {
                        "proposal_type": args.proposal_type,
                        "text": args.canonical_text,
                        "rationale": args.rationale,
                    },
                    "status": "candidate",
                    "confidence": args.confidence,
                    "title": args.title,
                    "canonical_text": args.canonical_text,
                    "summary": args.canonical_text[:280],
                    "domain": args.domain,
                    "sensitivity": args.sensitivity,
                    "metadata_json": {
                        "proposal_type": args.proposal_type,
                        "review_required": True,
                        **agent_metadata(identity, decision),
                    },
                },
                actor_type="agent",
            )
            append_event(
                store,
                event_type="agent.memory_proposed",
                actor_type="agent",
                actor_id=identity.agent_id,
                target_type="memory",
                target_id=str(memory["id"]),
                trace_id=decision.trace_id,
                run_id=identity.agent_run_id,
                payload={"proposal_type": args.proposal_type, "agent_identity": identity.to_record()},
            )
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if memory is None or decision is None:
        raise RuntimeError("agent memory proposal did not complete")
    return _json_dumps({"proposal": memory, "policy_decision": decision.to_record(), "review_required": True})


def _run_vnext_memory_commit(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        identity = _vnext_agent_identity_from_args(args)
        request = memory_commit_request_from_payload(
            {
                "title": args.title,
                "canonical_text": args.text,
                "memory_type": args.memory_type,
                "domain": args.domain,
                "sensitivity": args.sensitivity,
                "confidence": args.confidence,
                "intent": args.intent,
                "source_type": args.source_type,
                "source_refs": args.source_ref,
                "conversation_excerpt": args.conversation_excerpt,
                "rationale": args.rationale,
                "idempotency_key": args.idempotency_key,
                "project_scope": getattr(args, "project_scope", None) or [],
                "contradiction_refs": args.contradiction_ref,
            },
            user_id=ctx.user_id,
        )
        service = VNextMemoryCommitService(store, defer_embeddings=True)
        payload = service.commit(identity=identity, request=request)
        deferred_embedding_inputs = service.deferred_embedding_inputs
    _persist_deferred_embedding_inputs(
        ctx,
        deferred_embedding_inputs,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
        trace_id=request.trace_id,
    )
    return _json_dumps(payload)


def _run_vnext_memory_confirm(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        identity, actor_type, actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="memory.confirm",
        )
        ensure_policy_allowed(decision)
        service = VNextMemoryCommitService(store, defer_embeddings=True)
        payload = service.confirm(
            identity=identity,
            confirmation_id=args.confirmation_id,
            action=args.action,
            canonical_text=args.text,
            rationale=args.rationale,
        )
        deferred_embedding_inputs = service.deferred_embedding_inputs
    _persist_deferred_embedding_inputs(
        ctx,
        deferred_embedding_inputs,
        actor_type=actor_type,
        actor_id=actor_id,
        trace_id=getattr(args, "trace_id", None),
    )
    return _json_dumps(payload)


def _run_vnext_memory_undo(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        identity, _actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="memory.undo",
        )
        ensure_policy_allowed(decision)
        payload = VNextMemoryCommitService(store).undo(
            identity=identity,
            memory_id=args.memory_id,
            reason=args.reason,
        )
    return _json_dumps(payload)


def _run_vnext_memory_correct(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        identity, actor_type, actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="memory.correct",
        )
        ensure_policy_allowed(decision)
        service = VNextMemoryCommitService(store, defer_embeddings=True)
        payload = service.correct(
            identity=identity,
            memory_id=args.memory_id,
            canonical_text=args.text,
            reason=args.reason,
        )
        deferred_embedding_inputs = service.deferred_embedding_inputs
    _persist_deferred_embedding_inputs(
        ctx,
        deferred_embedding_inputs,
        actor_type=actor_type,
        actor_id=actor_id,
        trace_id=getattr(args, "trace_id", None),
    )
    return _json_dumps(payload)


def _run_vnext_memory_forget(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        identity, _actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="memory.forget",
        )
        ensure_policy_allowed(decision)
        payload = VNextMemoryCommitService(store).forget(
            identity=identity, memory_id=args.memory_id, reason=args.reason
        )
    return _json_dumps(payload)


def _run_vnext_memory_expire(ctx: CLIContext, args: argparse.Namespace) -> str:
    # The commit service policy-checks memory.expire itself (and appends the
    # policy events), so no CLI-side pre-check is needed; a blocked decision
    # raises AgentPolicyBlockedError exactly like ensure_policy_allowed.
    with _vnext_store_context(ctx) as store:
        identity = _vnext_agent_identity_from_args(args)
        payload = VNextMemoryCommitService(store).expire(
            args.memory_id,
            valid_to=args.valid_to,
            reason=args.reason,
            identity=identity,
        )
    return _json_dumps(payload)


def _run_vnext_memory_unexpire(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        identity = _vnext_agent_identity_from_args(args)
        payload = VNextMemoryCommitService(store).unexpire(
            args.memory_id,
            reason=args.reason,
            identity=identity,
        )
    return _json_dumps(payload)


def _run_vnext_memory_accept_consolidation(ctx: CLIContext, args: argparse.Namespace) -> str:
    # Acceptance is a review decision: the commit service policy-checks it
    # internally (human or admin agent only).
    with _vnext_store_context(ctx) as store:
        identity = _vnext_agent_identity_from_args(args)
        service = VNextMemoryCommitService(store, defer_embeddings=True)
        payload = service.accept_consolidation_candidate(
            args.memory_id,
            reason=args.reason,
            identity=identity,
        )
        deferred_embedding_inputs = service.deferred_embedding_inputs
    _persist_deferred_embedding_inputs(
        ctx,
        deferred_embedding_inputs,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
    )
    return _json_dumps(payload)


def _run_vnext_memory_redact(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        # The shared flow authorizes the destructive action against the locked
        # memory.  Keeping the policy seam there also makes an exact replay a
        # strict no-write operation on every surface.
        identity = _vnext_agent_identity_from_args(args)
        payload = redact_memory_flow(store, memory_id=args.memory_id, reason=args.reason, identity=identity)
    return _json_dumps(payload)


def _run_vnext_memory_recent(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        identity, _actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="memory.recent_commits",
        )
        ensure_policy_allowed(decision)
        payload = VNextMemoryCommitService(store).recent_commits(limit=args.limit)
    return _json_dumps(payload)


def _run_vnext_memory_audit(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        identity, _actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="memory.audit",
        )
        ensure_policy_allowed(decision)
        payload = VNextMemoryCommitService(store).audit(memory_id=args.memory_id)
    return _json_dumps(payload)


def _run_vnext_memories_backfill_embeddings(ctx: CLIContext, args: argparse.Namespace) -> str:
    provider = get_embedding_provider()
    if provider is None:
        raise ValueError(
            "embedding provider is not configured; set "
            f"{EMBEDDINGS_BASE_URL_ENV} and {EMBEDDINGS_MODEL_ENV} "
            f"(and {EMBEDDINGS_API_KEY_ENV} when the endpoint requires a key) "
            "to enable embedding backfill"
        )
    batch_size = args.batch_size
    if batch_size < 1 or batch_size > MAX_EMBEDDINGS_BATCH_SIZE:
        raise ValueError(f"--batch-size must be between 1 and {MAX_EMBEDDINGS_BATCH_SIZE}")
    embedded = 0
    reindexed_incompatible = 0
    skipped = 0
    failed = 0
    batches = 0
    after_id: str | None = None
    while True:
        # Snapshot one page in a short transaction. Provider I/O and vector
        # persistence both happen only after this read transaction closes.
        with _vnext_store_context(ctx) as store:
            rows = store.list_memories_missing_embeddings(
                limit=batch_size,
                after_id=after_id,
                embedding_provider=provider.provider,
                embedding_model=provider.model,
                embedding_endpoint=endpoint_fingerprint(getattr(provider, "base_url", "")),
                embedding_signature_version=EMBEDDING_SIGNATURE_VERSION,
            )
        if not rows:
            break
        batches += 1
        after_id = str(rows[-1]["id"])
        pending = [(row, memory_embedding_text(row)) for row in rows]
        embeddable = [(row, text) for row, text in pending if text != ""]
        skipped += len(pending) - len(embeddable)
        if not embeddable:
            continue
        deferred_inputs = tuple(DeferredMemoryEmbedding.from_memory(row) for row, _text in embeddable)
        attached = persist_deferred_memory_embeddings_best_effort(
            deferred_inputs,
            store_context=lambda: _vnext_store_context(ctx),
            provider=provider,
        )
        embedded += attached
        batch_failed = len(embeddable) - attached
        failed += batch_failed
        if batch_failed:
            _emit_cli_error(
                code="embedding_batch_failed",
                message="An embedding batch failed",
            )
        # Exact for a fully persisted batch. For partial persistence, report a
        # guaranteed lower bound instead of claiming an incompatible vector
        # was replaced when only fresh rows may have succeeded.
        fresh_count = sum(row.get("embedding_present") is not True for row, _text in embeddable)
        reindexed_incompatible += max(0, attached - fresh_count)
    output = _json_dumps(
        {
            "provider": provider.provider,
            "model": provider.model,
            "batches": batches,
            "embedded": embedded,
            "reindexed_incompatible": reindexed_incompatible,
            "skipped": skipped,
            "failed": failed,
        }
    )
    if failed:
        raise EmbeddingBackfillFailure(output)
    return output


def _run_maintenance_sync_contradictions(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = sync_contradictions(
            store,
            user_id=ctx.user_id,
            request=ContradictionSyncInput(
                continuity_object_id=args.continuity_object_id,
                limit=args.limit,
            ),
        )
    return format_contradiction_sync_output(payload)


def _run_vnext_agent_policy_telemetry(ctx: CLIContext, args: argparse.Namespace) -> str:
    bounded_limit = min(max(args.limit, 1), 200)
    with _vnext_store_context(ctx) as store:
        events = store.list_agent_events(agent_id=args.agent_id, limit=bounded_limit)
        artifacts = store.list_agent_policy_artifacts(
            agent_id=args.agent_id,
            limit=bounded_limit,
        )
        memories = store.list_agent_policy_memories(
            agent_id=args.agent_id,
            limit=bounded_limit,
        )
    return _json_dumps(
        {
            "summary": summarize_agent_policy_telemetry(
                agent_events=events,
                artifacts=artifacts,
                memories=memories,
            )
        }
    )
