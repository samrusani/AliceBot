from __future__ import annotations

import json
from typing import Mapping, Sequence

from alicebot_api.contracts import (
    ContinuityArtifactDetailResponse,
    ContinuityCaptureCreateResponse,
    ContinuityCorrectionApplyResponse,
    ContinuityExplainResponse,
    ContinuityLifecycleDetailResponse,
    ContinuityLifecycleListResponse,
    ContinuityOpenLoopDashboardResponse,
    ContinuityRecallResultRecord,
    ContinuityRecallResponse,
    ContinuityResumptionBriefResponse,
    ContinuityReviewDetailResponse,
    ContinuityReviewQueueResponse,
    TemporalExplainResponse,
    TemporalStateAtResponse,
    TemporalTimelineResponse,
    TrustedFactPatternExplainResponse,
    TrustedFactPatternListResponse,
    TrustedFactPlaybookExplainResponse,
    TrustedFactPlaybookListResponse,
)


_SCOPE_KEY_ORDER = ("thread_id", "task_id", "project", "person", "since", "until")
_RECALL_ITEM_PREFIX = "  "


def _format_float(value: float) -> str:
    return f"{value:.3f}"


def _format_scope(scope: Mapping[str, object]) -> str:
    rendered: list[str] = []
    for key in _SCOPE_KEY_ORDER:
        if key not in scope:
            continue
        value = scope[key]
        if value is None:
            continue
        rendered.append(f"{key}={value}")
    if not rendered:
        return "(none)"
    return ", ".join(rendered)


def _format_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _format_provenance_refs(item: ContinuityRecallResultRecord) -> str:
    refs = item["provenance_references"]
    if len(refs) == 0:
        return "(none)"
    return "; ".join(f"{ref['source_kind']}:{ref['source_id']}" for ref in refs)


def _format_provenance_source(item: ContinuityRecallResultRecord) -> str:
    provenance = item.get("provenance", {})
    if not isinstance(provenance, dict):
        return "(unknown)"

    label = provenance.get("source_label")
    source_kind = provenance.get("source_kind")

    label_text = label.strip() if isinstance(label, str) else None
    source_kind_text = source_kind.strip() if isinstance(source_kind, str) else None

    if label_text and source_kind_text:
        return f"{label_text} ({source_kind_text})"
    if label_text:
        return label_text
    if source_kind_text:
        return source_kind_text
    return "(unknown)"


def _format_explanation_source_facts(item: ContinuityRecallResultRecord) -> str:
    explanation = item.get("explanation")
    if not isinstance(explanation, dict):
        return "(none)"
    source_facts = explanation.get("source_facts")
    if not isinstance(source_facts, list) or len(source_facts) == 0:
        return "(none)"
    rendered: list[str] = []
    for fact in source_facts:
        if not isinstance(fact, dict):
            continue
        label = fact.get("label")
        value = fact.get("value")
        if isinstance(label, str) and isinstance(value, str):
            rendered.append(f"{label}={value}")
    return " | ".join(rendered) if rendered else "(none)"


def _format_explanation_evidence(item: ContinuityRecallResultRecord) -> str:
    explanation = item.get("explanation")
    if not isinstance(explanation, dict):
        return "(none)"
    evidence_segments = explanation.get("evidence_segments")
    if not isinstance(evidence_segments, list) or len(evidence_segments) == 0:
        return "(none)"
    rendered: list[str] = []
    for segment in evidence_segments:
        if not isinstance(segment, dict):
            continue
        source_kind = segment.get("source_kind")
        source_id = segment.get("source_id")
        snippet = segment.get("snippet")
        if isinstance(source_kind, str) and isinstance(source_id, str) and isinstance(snippet, str):
            rendered.append(f"{source_kind}:{source_id} \"{snippet}\"")
    return " | ".join(rendered) if rendered else "(none)"


def _format_explanation_supersession(item: ContinuityRecallResultRecord) -> str:
    explanation = item.get("explanation")
    if not isinstance(explanation, dict):
        return "(none)"
    supersession_notes = explanation.get("supersession_notes")
    if not isinstance(supersession_notes, list) or len(supersession_notes) == 0:
        return "(none)"
    rendered: list[str] = []
    for note in supersession_notes:
        if not isinstance(note, dict):
            continue
        text = note.get("note")
        if isinstance(text, str):
            rendered.append(text)
    return " | ".join(rendered) if rendered else "(none)"


def _format_explanation_timestamps(item: ContinuityRecallResultRecord) -> str:
    explanation = item.get("explanation")
    if not isinstance(explanation, dict):
        return (
            f"created_at={item['created_at']} updated_at={item['updated_at']} "
            f"last_confirmed_at={item['last_confirmed_at']}"
        )
    timestamps = explanation.get("timestamps")
    if not isinstance(timestamps, dict):
        return (
            f"created_at={item['created_at']} updated_at={item['updated_at']} "
            f"last_confirmed_at={item['last_confirmed_at']}"
        )
    return (
        f"capture_created_at={timestamps.get('capture_created_at')} "
        f"created_at={timestamps.get('created_at')} "
        f"updated_at={timestamps.get('updated_at')} "
        f"last_confirmed_at={timestamps.get('last_confirmed_at')}"
    )


def _format_explanation_trust(item: ContinuityRecallResultRecord) -> str:
    explanation = item.get("explanation")
    if not isinstance(explanation, dict):
        return "(none)"
    trust = explanation.get("trust")
    if not isinstance(trust, dict):
        return "(none)"
    return (
        f"{trust.get('trust_class')} "
        f"reason={trust.get('trust_reason')} "
        f"evidence_segments={trust.get('evidence_segment_count')} "
        f"corrections={trust.get('correction_count')}"
    )


def _render_recall_item(
    item: ContinuityRecallResultRecord,
    *,
    index: int | None = None,
    prefix: str = _RECALL_ITEM_PREFIX,
) -> list[str]:
    marker = "-" if index is None else f"{index}."
    lines = [
        f"{prefix}{marker} [{item['object_type']}|{item['status']}] {item['title']}",
        f"{prefix}  id={item['id']} capture_event_id={item['capture_event_id']}",
        (
            f"{prefix}  lifecycle=preserved:{item['lifecycle']['is_preserved']} "
            f"searchable:{item['lifecycle']['is_searchable']} "
            f"promotable:{item['lifecycle']['is_promotable']}"
        ),
        (
            f"{prefix}  confidence={_format_float(item['confidence'])} "
            f"relevance={_format_float(item['relevance'])} "
            f"confirmation={item['confirmation_status']}"
        ),
        (
            f"{prefix}  freshness={item['ordering']['freshness_posture']} "
            f"provenance={item['ordering']['provenance_posture']} "
            f"supersession={item['ordering']['supersession_posture']}"
        ),
        f"{prefix}  source={_format_provenance_source(item)}",
        f"{prefix}  provenance_refs={_format_provenance_refs(item)}",
        f"{prefix}  trust={_format_explanation_trust(item)}",
        f"{prefix}  timestamps={_format_explanation_timestamps(item)}",
        f"{prefix}  source_facts={_format_explanation_source_facts(item)}",
        f"{prefix}  evidence_segments={_format_explanation_evidence(item)}",
        f"{prefix}  supersession_notes={_format_explanation_supersession(item)}",
    ]
    return lines


def _render_recall_list_section(
    *,
    title: str,
    items: Sequence[ContinuityRecallResultRecord],
    limit: int,
    total_count: int,
    order: Sequence[str],
    empty_message: str,
) -> list[str]:
    lines = [
        f"{title} (returned={len(items)} total={total_count} limit={limit})",
        f"order: {', '.join(order)}",
    ]
    if len(items) == 0:
        lines.append(f"empty: {empty_message}")
        return lines

    for index, item in enumerate(items, start=1):
        lines.extend(_render_recall_item(item, index=index))
    return lines


def _render_retrieval_debug(payload: Mapping[str, object]) -> list[str]:
    debug = payload.get("debug")
    if not isinstance(debug, dict):
        return []

    lines = [
        "debug:",
        f"  retrieval_run_id: {debug.get('retrieval_run_id')}",
        f"  source_surface: {debug.get('source_surface')}",
        f"  ranking_strategy: {debug.get('ranking_strategy')}",
        f"  query_terms: {', '.join(debug.get('query_terms', [])) if isinstance(debug.get('query_terms'), list) else '(none)'}",
        (
            "  entity_anchors: "
            + (
                ", ".join(debug.get("entity_anchor_names", []))
                if isinstance(debug.get("entity_anchor_names"), list) and debug.get("entity_anchor_names")
                else "(none)"
            )
        ),
        (
            "  entity_expansion: "
            + (
                ", ".join(debug.get("entity_expansion_names", []))
                if isinstance(debug.get("entity_expansion_names"), list) and debug.get("entity_expansion_names")
                else "(none)"
            )
        ),
        f"  candidates: {debug.get('candidate_count')} selected={debug.get('selected_count')}",
    ]

    candidates = debug.get("candidates")
    if not isinstance(candidates, list) or len(candidates) == 0:
        return lines

    lines.append("  trace:")
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            continue
        lines.append(
            "    "
            f"{index}. rank={candidate.get('rank')} selected={candidate.get('selected')} "
            f"relevance={_format_float(float(candidate.get('relevance', 0.0)))} "
            f"object_id={candidate.get('object_id')} title={candidate.get('title')}"
        )
        lines.append(f"       exclusion_reason={candidate.get('exclusion_reason')}")
        stage_scores = candidate.get("stage_scores")
        if not isinstance(stage_scores, dict):
            continue
        for stage_name in ("lexical", "semantic", "entity_edge", "temporal", "trust"):
            stage = stage_scores.get(stage_name)
            if not isinstance(stage, dict):
                continue
            raw_score = float(stage.get("raw_score", 0.0))
            normalized_score = float(stage.get("normalized_score", 0.0))
            lines.append(
                "       "
                f"{stage_name}: raw={_format_float(raw_score)} normalized={_format_float(normalized_score)} "
                f"matched={stage.get('matched')} reason={stage.get('reason')}"
            )
    return lines


def format_capture_output(payload: ContinuityCaptureCreateResponse) -> str:
    capture = payload["capture"]["capture_event"]
    derived = payload["capture"]["derived_object"]

    lines = [
        "capture result",
        f"capture_event_id: {capture['id']}",
        f"created_at: {capture['created_at']}",
        f"admission_posture: {capture['admission_posture']}",
        f"admission_reason: {capture['admission_reason']}",
        f"explicit_signal: {capture['explicit_signal']}",
    ]

    if derived is None:
        lines.append("derived_object: none")
    else:
        lines.extend(
            [
                f"derived_object_id: {derived['id']}",
                f"derived_object_type: {derived['object_type']}",
                f"derived_object_status: {derived['status']}",
                (
                    "derived_lifecycle: "
                    f"preserved={derived['lifecycle']['is_preserved']} "
                    f"searchable={derived['lifecycle']['is_searchable']} "
                    f"promotable={derived['lifecycle']['is_promotable']}"
                ),
                f"derived_confidence: {_format_float(derived['confidence'])}",
                f"derived_title: {derived['title']}",
            ]
        )

    return "\n".join(lines)


def format_recall_output(payload: ContinuityRecallResponse) -> str:
    summary = payload["summary"]
    lines = [
        "recall summary",
        f"query: {summary['query']}",
        f"filters: {_format_scope(summary['filters'])}",
        (
            f"returned: {summary['returned_count']}/{summary['total_count']} "
            f"(limit={summary['limit']})"
        ),
        f"order: {', '.join(summary['order'])}",
    ]

    items = payload["items"]
    if len(items) == 0:
        lines.append("empty: no continuity results in requested scope.")
        lines.extend(_render_retrieval_debug(payload))
        return "\n".join(lines)

    lines.append("items:")
    for index, item in enumerate(items, start=1):
        lines.extend(_render_recall_item(item, index=index))
    lines.extend(_render_retrieval_debug(payload))
    return "\n".join(lines)


def format_resume_output(payload: ContinuityResumptionBriefResponse) -> str:
    brief = payload["brief"]
    lines = [
        "resumption brief",
        f"assembly_version: {brief['assembly_version']}",
        f"scope: {_format_scope(brief['scope'])}",
        f"sources: {', '.join(brief['sources'])}",
    ]

    lines.append("last_decision:")
    last_decision = brief["last_decision"]
    if last_decision["item"] is None:
        lines.append(f"  empty: {last_decision['empty_state']['message']}")
    else:
        lines.extend(_render_recall_item(last_decision["item"]))

    lines.extend(
        _render_recall_list_section(
            title="open_loops",
            items=brief["open_loops"]["items"],
            limit=brief["open_loops"]["summary"]["limit"],
            total_count=brief["open_loops"]["summary"]["total_count"],
            order=brief["open_loops"]["summary"]["order"],
            empty_message=brief["open_loops"]["empty_state"]["message"],
        )
    )
    lines.extend(
        _render_recall_list_section(
            title="recent_changes",
            items=brief["recent_changes"]["items"],
            limit=brief["recent_changes"]["summary"]["limit"],
            total_count=brief["recent_changes"]["summary"]["total_count"],
            order=brief["recent_changes"]["summary"]["order"],
            empty_message=brief["recent_changes"]["empty_state"]["message"],
        )
    )

    lines.append("next_action:")
    next_action = brief["next_action"]
    if next_action["item"] is None:
        lines.append(f"  empty: {next_action['empty_state']['message']}")
    else:
        lines.extend(_render_recall_item(next_action["item"]))

    lines.extend(_render_retrieval_debug(payload))
    return "\n".join(lines)


def format_open_loops_output(payload: ContinuityOpenLoopDashboardResponse) -> str:
    dashboard = payload["dashboard"]
    summary = dashboard["summary"]
    lines = [
        "open loops dashboard",
        f"scope: {_format_scope(dashboard['scope'])}",
        f"sources: {', '.join(dashboard['sources'])}",
        (
            f"summary: total={summary['total_count']} "
            f"limit={summary['limit']} "
            f"posture_order={','.join(summary['posture_order'])}"
        ),
    ]

    for posture in ("waiting_for", "blocker", "stale", "next_action"):
        section = dashboard[posture]
        lines.extend(
            _render_recall_list_section(
                title=posture,
                items=section["items"],
                limit=section["summary"]["limit"],
                total_count=section["summary"]["total_count"],
                order=section["summary"]["order"],
                empty_message=section["empty_state"]["message"],
            )
        )

    return "\n".join(lines)


def format_review_queue_output(payload: ContinuityReviewQueueResponse) -> str:
    summary = payload["summary"]
    lines = [
        "review queue",
        (
            f"status={summary['status']} "
            f"returned={summary['returned_count']}/{summary['total_count']} "
            f"limit={summary['limit']}"
        ),
        f"order: {', '.join(summary['order'])}",
    ]

    items = payload["items"]
    if len(items) == 0:
        lines.append("empty: no review items in requested status.")
        return "\n".join(lines)

    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. [{item['object_type']}|{item['status']}] {item['title']}",
                f"   id={item['id']} capture_event_id={item['capture_event_id']}",
                (
                    "   lifecycle="
                    f"preserved:{item['lifecycle']['is_preserved']} "
                    f"searchable:{item['lifecycle']['is_searchable']} "
                    f"promotable:{item['lifecycle']['is_promotable']}"
                ),
                f"   confidence={_format_float(item['confidence'])} last_confirmed_at={item['last_confirmed_at']}",
                f"   provenance={_format_json(item['provenance'])}",
            ]
        )

    return "\n".join(lines)


def format_review_detail_output(payload: ContinuityReviewDetailResponse) -> str:
    review = payload["review"]
    continuity_object = review["continuity_object"]
    supersession = review["supersession_chain"]

    lines = [
        "review detail",
        f"continuity_object_id: {continuity_object['id']}",
        f"type: {continuity_object['object_type']}",
        f"status: {continuity_object['status']}",
        (
            "lifecycle: "
            f"preserved={continuity_object['lifecycle']['is_preserved']} "
            f"searchable={continuity_object['lifecycle']['is_searchable']} "
            f"promotable={continuity_object['lifecycle']['is_promotable']}"
        ),
        f"title: {continuity_object['title']}",
        f"confidence: {_format_float(continuity_object['confidence'])}",
        f"last_confirmed_at: {continuity_object['last_confirmed_at']}",
        f"body: {_format_json(continuity_object['body'])}",
        f"provenance: {_format_json(continuity_object['provenance'])}",
        (
            "supersession_chain: "
            f"supersedes={None if supersession['supersedes'] is None else supersession['supersedes']['id']} "
            f"superseded_by={None if supersession['superseded_by'] is None else supersession['superseded_by']['id']}"
        ),
        f"correction_event_count: {len(review['correction_events'])}",
    ]

    for index, event in enumerate(review["correction_events"], start=1):
        lines.append(
            f"event {index}: id={event['id']} action={event['action']} "
            f"reason={event['reason']} created_at={event['created_at']}"
        )

    return "\n".join(lines)


def format_explain_output(payload: ContinuityExplainResponse) -> str:
    explain = payload["explain"]
    continuity_object = explain["continuity_object"]
    explanation = explain.get("explanation")
    lines = [
        "explain",
        f"continuity_object_id: {continuity_object['id']}",
        f"title: {continuity_object['title']}",
        f"type: {continuity_object['object_type']}",
        f"status: {continuity_object['status']}",
    ]
    if isinstance(explanation, dict):
        trust = explanation.get("trust", {})
        timestamps = explanation.get("timestamps", {})
        source_facts = explanation.get("source_facts", [])
        supersession_notes = explanation.get("supersession_notes", [])
        evidence_segments = explanation.get("evidence_segments", [])
        lines.extend(
            [
                f"trust: {_format_json(trust)}",
                f"timestamps: {_format_json(timestamps)}",
                f"source_facts: {_format_json(source_facts)}",
                f"evidence_segments: {_format_json(evidence_segments)}",
                f"supersession_notes: {_format_json(supersession_notes)}",
            ]
        )
    lines.extend(
        [
        f"evidence_links: {len(explain['evidence_chain'])}",
        ]
    )
    if len(explain["evidence_chain"]) == 0:
        lines.append("evidence: none")
        return "\n".join(lines)

    for index, link in enumerate(explain["evidence_chain"], start=1):
        lines.extend(
            [
                f"{index}. relationship={link['relationship']}",
                (
                    "   artifact="
                    f"{link['artifact']['display_name']} "
                    f"({link['artifact']['relative_path']}, {link['artifact']['source_kind']})"
                ),
                f"   artifact_copy_checksum={link['artifact_copy']['checksum_sha256']}",
            ]
        )
        segment = link["artifact_segment"]
        if segment is not None:
            lines.extend(
                [
                    (
                        "   segment="
                        f"{segment['segment_kind']} "
                        f"source_item_id={segment['source_item_id']} "
                        f"locator={_format_json(segment['locator'])}"
                    ),
                    f"   raw_evidence={segment['raw_content']}",
                ]
            )
    return "\n".join(lines)


def format_temporal_state_output(payload: TemporalStateAtResponse) -> str:
    state_at = payload["state_at"]
    summary = state_at["summary"]
    lines = [
        "state_at",
        f"entity_id: {summary['entity_id']}",
        f"entity_name: {summary['entity_name']}",
        f"entity_type: {summary['entity_type']}",
        f"as_of: {summary['as_of']}",
        f"facts: {summary['fact_count']}",
        f"edges: {summary['edge_count']}",
    ]
    if len(state_at["facts"]) == 0:
        lines.append("facts_detail: none")
    else:
        lines.append("facts_detail:")
        for index, fact in enumerate(state_at["facts"], start=1):
            lines.extend(
                [
                    f"  {index}. {fact['memory_key']}",
                    f"    memory_id={fact['memory_id']} status={fact['status']}",
                    f"    value={_format_json(fact['value'])}",
                    (
                        "    validity="
                        f"{fact['validity']['valid_from']}..{fact['validity']['valid_to']} "
                        f"effective_at={fact['validity']['effective_at']}"
                    ),
                ]
            )
    if len(state_at["edges"]) == 0:
        lines.append("edges_detail: none")
    else:
        lines.append("edges_detail:")
        for index, edge in enumerate(state_at["edges"], start=1):
            lines.extend(
                [
                    f"  {index}. {edge['relationship_type']}",
                    (
                        f"    from={edge['from_entity_id']} "
                        f"to={edge['to_entity_id']}"
                    ),
                    (
                        "    validity="
                        f"{edge['validity']['valid_from']}..{edge['validity']['valid_to']} "
                        f"effective_at={edge['validity']['effective_at']}"
                    ),
                    f"    source_memory_ids={','.join(edge['source_memory_ids'])}",
                ]
            )
    return "\n".join(lines)


def format_temporal_timeline_output(payload: TemporalTimelineResponse) -> str:
    timeline = payload["timeline"]
    summary = timeline["summary"]
    lines = [
        "timeline",
        f"entity_id: {summary['entity_id']}",
        f"entity_name: {summary['entity_name']}",
        f"entity_type: {summary['entity_type']}",
        f"filters: entity_id={summary['entity_id']}, since={summary['since']}, until={summary['until']}",
        f"returned: {summary['returned_count']}/{summary['total_count']} (limit={summary['limit']})",
        f"order: {', '.join(summary['order'])}",
    ]
    if len(timeline["events"]) == 0:
        lines.append("empty: no temporal events in requested scope.")
        return "\n".join(lines)

    lines.append("events:")
    for index, event in enumerate(timeline["events"], start=1):
        lines.extend(
            [
                f"  {index}. [{event['event_type']}] {event['summary']}",
                (
                    f"    occurred_at={event['occurred_at']} "
                    f"object_kind={event['object_kind']} object_id={event['object_id']}"
                ),
                f"    payload={_format_json(event['payload'])}",
            ]
        )
    return "\n".join(lines)


def format_temporal_explain_output(payload: TemporalExplainResponse) -> str:
    explain = payload["explain"]
    summary = explain["summary"]
    lines = [
        "temporal explain",
        f"entity_id: {summary['entity_id']}",
        f"entity_name: {summary['entity_name']}",
        f"entity_type: {summary['entity_type']}",
        f"as_of: {summary['as_of']}",
        f"facts: {summary['fact_count']}",
        f"edges: {summary['edge_count']}",
    ]
    if len(explain["facts"]) == 0:
        lines.append("fact_explanations: none")
    else:
        lines.append("fact_explanations:")
        for index, fact in enumerate(explain["facts"], start=1):
            lines.extend(
                [
                    f"  {index}. {fact['memory_key']}",
                    f"    memory_id={fact['memory_id']} status={fact['status']}",
                    f"    trust={_format_json(fact['trust'])}",
                    f"    provenance={_format_json(fact['provenance'])}",
                    f"    supersession_chain={_format_json(fact['supersession_chain'])}",
                ]
            )
    if len(explain["edges"]) == 0:
        lines.append("edge_explanations: none")
    else:
        lines.append("edge_explanations:")
        for index, edge in enumerate(explain["edges"], start=1):
            lines.extend(
                [
                    f"  {index}. {edge['relationship_type']}",
                    (
                        f"    from={edge['from_entity_id']} "
                        f"to={edge['to_entity_id']}"
                    ),
                    f"    trust={_format_json(edge['trust'])}",
                    f"    provenance={_format_json(edge['provenance'])}",
                    f"    supersession_chain={_format_json(edge['supersession_chain'])}",
                ]
            )
    return "\n".join(lines)


def format_trusted_fact_pattern_list_output(payload: TrustedFactPatternListResponse) -> str:
    summary = payload["summary"]
    lines = [
        "patterns",
        f"returned: {summary['returned_count']}/{summary['total_count']} (limit={summary['limit']})",
        f"order: {', '.join(summary['order'])}",
    ]
    if len(payload["items"]) == 0:
        lines.append("empty: no trusted fact patterns.")
        return "\n".join(lines)

    for index, item in enumerate(payload["items"], start=1):
        lines.extend(
            [
                f"{index}. {item['title']}",
                f"   id={item['id']} pattern_key={item['pattern_key']}",
                (
                    f"   memory_type={item['memory_type']} "
                    f"namespace_key={item['namespace_key']} fact_count={item['fact_count']}"
                ),
                f"   source_fact_ids={','.join(item['source_fact_ids'])}",
            ]
        )
    return "\n".join(lines)


def format_trusted_fact_pattern_explain_output(payload: TrustedFactPatternExplainResponse) -> str:
    pattern = payload["pattern"]
    lines = [
        "pattern",
        f"id: {pattern['id']}",
        f"pattern_key: {pattern['pattern_key']}",
        f"title: {pattern['title']}",
        f"memory_type: {pattern['memory_type']}",
        f"namespace_key: {pattern['namespace_key']}",
        f"fact_count: {pattern['fact_count']}",
        f"source_fact_ids: {','.join(pattern['source_fact_ids'])}",
        f"explanation: {pattern['explanation']}",
    ]
    if len(pattern["evidence_chain"]) == 0:
        lines.append("evidence_chain: none")
        return "\n".join(lines)

    lines.append("evidence_chain:")
    for index, link in enumerate(pattern["evidence_chain"], start=1):
        lines.extend(
            [
                f"  {index}. fact_id={link['fact_id']} memory_key={link['memory_key']}",
                (
                    f"    trust_class={link['trust']['trust_class']} "
                    f"promotion={link['promotion_eligibility']} "
                    f"evidence_count={link['evidence_count']} "
                    f"independent_source_count={link['independent_source_count']}"
                ),
                f"    source_event_ids={','.join(link['source_event_ids'])}",
                f"    revision={_format_json({'sequence_no': link['revision_sequence_no'], 'action': link['revision_action'], 'created_at': link['revision_created_at']})}",
            ]
        )
    return "\n".join(lines)


def format_trusted_fact_playbook_list_output(payload: TrustedFactPlaybookListResponse) -> str:
    summary = payload["summary"]
    lines = [
        "playbooks",
        f"returned: {summary['returned_count']}/{summary['total_count']} (limit={summary['limit']})",
        f"order: {', '.join(summary['order'])}",
    ]
    if len(payload["items"]) == 0:
        lines.append("empty: no trusted fact playbooks.")
        return "\n".join(lines)

    for index, item in enumerate(payload["items"], start=1):
        lines.extend(
            [
                f"{index}. {item['title']}",
                f"   id={item['id']} playbook_key={item['playbook_key']}",
                (
                    f"   memory_type={item['memory_type']} pattern_key={item['pattern_key']} "
                    f"step_count={len(item['steps'])}"
                ),
                f"   source_fact_ids={','.join(item['source_fact_ids'])}",
            ]
        )
    return "\n".join(lines)


def format_trusted_fact_playbook_explain_output(payload: TrustedFactPlaybookExplainResponse) -> str:
    playbook = payload["playbook"]
    lines = [
        "playbook",
        f"id: {playbook['id']}",
        f"playbook_key: {playbook['playbook_key']}",
        f"pattern_id: {playbook['pattern_id']}",
        f"pattern_key: {playbook['pattern_key']}",
        f"title: {playbook['title']}",
        f"memory_type: {playbook['memory_type']}",
        f"source_fact_ids: {','.join(playbook['source_fact_ids'])}",
        f"source_pattern_ids: {','.join(playbook['source_pattern_ids'])}",
        f"explanation: {playbook['explanation']}",
    ]
    if len(playbook["steps"]) == 0:
        lines.append("steps: none")
        return "\n".join(lines)

    lines.append("steps:")
    for step in playbook["steps"]:
        lines.extend(
            [
                f"  {step['step_no']}. [{step['action_type']}] {step['instruction']}",
                f"    fact_id={step['fact_id']} memory_key={step['memory_key']}",
                f"    trust={_format_json(step['trust'])}",
            ]
        )
    return "\n".join(lines)


def format_artifact_detail_output(payload: ContinuityArtifactDetailResponse) -> str:
    detail = payload["artifact_detail"]
    artifact = detail["artifact"]
    lines = [
        "artifact detail",
        f"artifact_id: {artifact['id']}",
        f"source_kind: {artifact['source_kind']}",
        f"import_source_path: {artifact['import_source_path']}",
        f"relative_path: {artifact['relative_path']}",
        f"media_type: {artifact['media_type']}",
        f"copies: {len(detail['copies'])}",
        f"segments: {len(detail['segments'])}",
    ]
    for index, artifact_copy in enumerate(detail["copies"], start=1):
        lines.extend(
            [
                f"copy {index}: checksum={artifact_copy['checksum_sha256']}",
                (
                    "  content="
                    f"{artifact_copy['content_encoding']} "
                    f"bytes={artifact_copy['content_length_bytes']}"
                ),
            ]
        )
    for index, segment in enumerate(detail["segments"], start=1):
        lines.extend(
            [
                (
                    f"segment {index}: {segment['segment_kind']} "
                    f"source_item_id={segment['source_item_id']}"
                ),
                f"  locator={_format_json(segment['locator'])}",
                f"  raw={segment['raw_content']}",
            ]
        )
    return "\n".join(lines)


def format_review_apply_output(payload: ContinuityCorrectionApplyResponse) -> str:
    continuity_object = payload["continuity_object"]
    correction_event = payload["correction_event"]
    replacement_object = payload["replacement_object"]

    lines = [
        "review apply result",
        f"continuity_object_id: {continuity_object['id']}",
        f"continuity_object_status: {continuity_object['status']}",
        (
            "continuity_object_lifecycle: "
            f"preserved={continuity_object['lifecycle']['is_preserved']} "
            f"searchable={continuity_object['lifecycle']['is_searchable']} "
            f"promotable={continuity_object['lifecycle']['is_promotable']}"
        ),
        f"continuity_object_title: {continuity_object['title']}",
        f"correction_event_id: {correction_event['id']}",
        f"correction_action: {correction_event['action']}",
        f"correction_reason: {correction_event['reason']}",
        f"correction_created_at: {correction_event['created_at']}",
    ]

    if replacement_object is None:
        lines.append("replacement_object_id: none")
    else:
        lines.extend(
            [
                f"replacement_object_id: {replacement_object['id']}",
                f"replacement_status: {replacement_object['status']}",
                f"replacement_title: {replacement_object['title']}",
            ]
        )

    return "\n".join(lines)


def format_status_output(status: Mapping[str, object]) -> str:
    lines = [
        "alice-core status",
        f"user_id: {status['user_id']}",
        f"database: {status['database_status']}",
        f"continuity_capture_events: {status['continuity_capture_events']}",
        f"continuity_objects_total: {status['continuity_objects_total']}",
        (
            "continuity_object_statuses: "
            f"active={status['continuity_objects_active']} "
            f"stale={status['continuity_objects_stale']} "
            f"superseded={status['continuity_objects_superseded']} "
            f"deleted={status['continuity_objects_deleted']}"
        ),
        (
            "continuity_object_lifecycle: "
            f"searchable={status['continuity_objects_searchable']} "
            f"non_searchable={status['continuity_objects_non_searchable']} "
            f"promotable={status['continuity_objects_promotable']} "
            f"non_promotable={status['continuity_objects_non_promotable']}"
        ),
        (
            "review_queue: "
            f"correction_ready={status['review_correction_ready']} "
            f"active={status['review_active']} "
            f"stale={status['review_stale']} "
            f"superseded={status['review_superseded']} "
            f"deleted={status['review_deleted']}"
        ),
        (
            "open_loops: "
            f"total={status['open_loops_total']} "
            f"waiting_for={status['open_loops_waiting_for']} "
            f"blocker={status['open_loops_blocker']} "
            f"stale={status['open_loops_stale']} "
            f"next_action={status['open_loops_next_action']}"
        ),
        (
            "maintenance: "
            f"status={status['maintenance_status']} "
            f"schedule={status['maintenance_schedule']} "
            f"last_run={status['maintenance_last_run_at']} "
            f"failures={status['maintenance_failure_count']} "
            f"warnings={status['maintenance_warning_count']} "
            f"stale_facts={status['maintenance_stale_fact_count']} "
            f"reembedded_segments={status['maintenance_reembedded_segment_count']} "
            f"pattern_candidates={status['maintenance_pattern_candidate_count']} "
            f"benchmark={status['maintenance_benchmark_status']}"
        ),
        (
            "retrieval_eval: "
            f"status={status['retrieval_eval_status']} "
            f"precision_at_k_mean={status['retrieval_precision_at_k_mean']} "
            f"precision_at_1_mean={status['retrieval_precision_at_1_mean']}"
        ),
    ]
    return "\n".join(lines)


def format_lifecycle_list_output(payload: ContinuityLifecycleListResponse) -> str:
    summary = payload["summary"]
    lines = [
        "continuity lifecycle",
        (
            f"returned: {summary['returned_count']}/{summary['total_count']} "
            f"(limit={summary['limit']})"
        ),
        (
            "counts: "
            f"preserved={summary['counts']['preserved_count']} "
            f"searchable={summary['counts']['searchable_count']} "
            f"promotable={summary['counts']['promotable_count']} "
            f"non_searchable={summary['counts']['not_searchable_count']} "
            f"non_promotable={summary['counts']['not_promotable_count']}"
        ),
        f"order: {', '.join(summary['order'])}",
    ]
    if len(payload["items"]) == 0:
        lines.append("empty: no continuity lifecycle records.")
        return "\n".join(lines)

    for index, item in enumerate(payload["items"], start=1):
        lines.extend(
            [
                f"{index}. [{item['object_type']}|{item['status']}] {item['title']}",
                f"   id={item['id']} capture_event_id={item['capture_event_id']}",
                (
                    "   lifecycle="
                    f"preserved:{item['lifecycle']['is_preserved']} "
                    f"searchable:{item['lifecycle']['is_searchable']} "
                    f"promotable:{item['lifecycle']['is_promotable']}"
                ),
            ]
        )
    return "\n".join(lines)


def format_lifecycle_detail_output(payload: ContinuityLifecycleDetailResponse) -> str:
    item = payload["continuity_object"]
    return "\n".join(
        [
            "continuity lifecycle detail",
            f"continuity_object_id: {item['id']}",
            f"type: {item['object_type']}",
            f"status: {item['status']}",
            (
                "lifecycle: "
                f"preserved={item['lifecycle']['is_preserved']} "
                f"searchable={item['lifecycle']['is_searchable']} "
                f"promotable={item['lifecycle']['is_promotable']}"
            ),
            f"title: {item['title']}",
            f"body: {_format_json(item['body'])}",
            f"provenance: {_format_json(item['provenance'])}",
        ]
    )
