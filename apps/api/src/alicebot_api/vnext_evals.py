"""vNext eval harness.

Unlike the previous revision of this module -- which scored a synthetic
fixture generator against itself and could never fail -- every suite here
either executes real production code or reports ``status: "skipped"`` with a
reason. Nothing in this module fabricates a pass.

Suites:

- ``retrieval_quality``: seeds a deterministic paraphrase corpus through the
  real ``PostgresVNextStore`` write path and runs every query through the
  production hybrid retrieval pipeline (``VNextRetrievalService`` --
  Postgres FTS + pgvector KNN fused with reciprocal-rank fusion). Reports
  recall@1 / recall@5 / MRR, per-query latency (p50/p95), and whether the
  vector stage was active or the run degraded to FTS-only. Requires a live
  Postgres (``ALICEBOT_EVAL_DATABASE_URL`` or an injected store handle);
  without one the suite is skipped, never passed.

All seeded rows are written inside a forced-rollback transaction, so a live
run leaves no data behind.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
from time import perf_counter
from typing import cast
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from alicebot_api.db import set_current_user
from alicebot_api.vnext_embeddings import (
    MAX_EMBEDDINGS_BATCH_SIZE,
    VNextEmbeddingConfigurationError,
    VNextEmbeddingProviderError,
    get_embedding_provider,
    memory_embedding_text,
)
from alicebot_api.vnext_retrieval import (
    VECTOR_STAGE_ENABLED,
    VNextRetrievalRequest,
    VNextRetrievalService,
    VNextRetrievalStore,
)
from alicebot_api.vnext_store import PostgresVNextStore

JsonObject = dict[str, object]
RetrievalFn = Callable[..., JsonObject]

VNEXT_EVAL_CORPUS_SCHEMA_VERSION = "vnext_eval_corpus_v1"
VNEXT_EVAL_REPORT_SCHEMA_VERSION = "vnext_eval_report_v1"
VNEXT_EVAL_CORPUS_SOURCE_PATH = "eval/fixtures/vnext_benchmark_corpus.json"
VNEXT_EVAL_REPORT_PATH = "eval/reports/vnext_eval_latest.json"
VNEXT_EVAL_DATABASE_URL_ENV = "ALICEBOT_EVAL_DATABASE_URL"
VNEXT_EVAL_USER_ID_ENV = "ALICEBOT_AUTH_USER_ID"
VNEXT_EVAL_DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
VNEXT_EVAL_MEMORY_KEY_PREFIX = "vnext-eval/retrieval/"

VNEXT_EVAL_SUITE_ORDER = ("retrieval_quality",)

RETRIEVAL_QUALITY_SUITE_KEY = "retrieval_quality"
RETRIEVAL_QUALITY_RECALL_LIMIT = 10
RETRIEVAL_QUALITY_SKIP_REASON = (
    "requires live store: pass a store handle or set "
    f"{VNEXT_EVAL_DATABASE_URL_ENV} to a migrated Postgres URL"
)

SUBSET_LEXICAL_OVERLAP = "lexical_overlap"
SUBSET_PARAPHRASE = "paraphrase"

RETRIEVAL_QUALITY_TARGETS: JsonObject = {
    "lexical_overlap_recall_at_5": {"minimum": 0.80},
    "lexical_overlap_mrr": {"minimum": 0.60},
    "paraphrase_recall_at_5": {
        "minimum": 0.70,
        "enforced_only_when_vector_stage_enabled": True,
    },
}

VNEXT_ACCEPTANCE_TARGETS: JsonObject = {
    RETRIEVAL_QUALITY_SUITE_KEY: deepcopy(RETRIEVAL_QUALITY_TARGETS),
}


# --------------------------------------------------------------------------
# Deterministic paraphrase corpus
#
# All content is derived from index arithmetic over hand-authored template
# pairs; there is no randomness at runtime. Every eval query is phrased
# differently from its target memory. The lexical-overlap subset rewords the
# fact while keeping most content vocabulary (FTS should handle it); the
# paraphrase subset restates the fact with near-zero shared vocabulary
# (FTS alone should struggle; the vector stage should recover it).
# --------------------------------------------------------------------------

_PROJECTS = (
    "Aurora",
    "Basilisk",
    "Cascade",
    "Dorado",
    "Ember",
    "Foxtrot",
    "Granite",
    "Harbor",
    "Icarus",
    "Juniper",
    "Kestrel",
    "Lumen",
)
_PEOPLE = (
    "Priya Nair",
    "Marcus Webb",
    "Elena Vasquez",
    "Tomas Lindqvist",
    "Ingrid Bauer",
    "Jamal Carter",
    "Sofia Marchetti",
    "Devon Blake",
    "Anaya Iyer",
    "Viktor Petrov",
    "Maren Holt",
    "Osei Mensah",
)
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

# Each lexical-overlap template is expanded for several projects. The query
# rewords the memory (word order, inflection, dropped words) but introduces
# no new content lexeme, so Postgres FTS with stemming can still match while
# exact-token overlap stays in roughly the 0.6-0.85 band.
_LEXICAL_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    (
        "{first_name} {last_name} approved the {project} launch budget of {amount}k for {month}.",
        "what launch budget did {first_name} approve for {project}",
        "{project} launch budget",
    ),
    (
        "The {project} weekly sync moved to {weekday} mornings at 9am.",
        "when did the {project} weekly sync move to mornings",
        "{project} weekly sync",
    ),
    (
        "The {project} beta rollout is blocked on the payments integration review.",
        "what is blocking the {project} beta rollout",
        "{project} beta rollout",
    ),
    (
        "{first_name} {last_name} owns the {project} incident postmortem due on {weekday}.",
        "who owns the incident postmortems for {project}",
        "{project} incident postmortem",
    ),
    (
        "The {project} contract renewal with {first_name} {last_name} closes at {amount}k annual value.",
        "what annual value does the {project} contract renewal close at",
        "{project} contract renewal",
    ),
    (
        "The {project} error budget burned sixty percent after the deploy freeze lifted.",
        "how did the {project} error budget burn after the deploy freeze lift",
        "{project} error budget",
    ),
    (
        "{first_name} {last_name} scheduled the {project} architecture review for {month} 12.",
        "when did {first_name} schedule the {project} architecture review",
        "{project} architecture review",
    ),
    (
        "The {project} data migration finished with zero rows lost in {month}.",
        "did the {project} data migration finish with zero rows",
        "{project} data migration",
    ),
)
_LEXICAL_VARIANTS_PER_TEMPLATE = 4

# Hand-authored pure-paraphrase pairs: the query restates the fact with
# synonyms and reworded intent, sharing (near) zero content tokens with the
# memory. Each pair is a unique topic so the expected answer is unambiguous.
_PARAPHRASE_PAIRS: tuple[tuple[str, str, str], ...] = (
    (
        "Q3 board pack is due Thursday, September 24.",
        "when is the quarterly board deck deadline",
        "Board pack due date",
    ),
    (
        "Sales offsite moved to the Lisbon office in early November.",
        "where will the revenue team gathering happen this fall",
        "Sales offsite location",
    ),
    (
        "New hires must complete security training within two weeks of their start date.",
        "how long do recent joiners have to finish the infosec course",
        "Security training window",
    ),
    (
        "The postgres upgrade to version 17 is planned for the first weekend of October.",
        "when are we bumping the database to the next major release",
        "Postgres upgrade timing",
    ),
    (
        "Customer churn dropped to four percent after the onboarding revamp.",
        "how did retention numbers change once the signup flow was redone",
        "Churn after onboarding revamp",
    ),
    (
        "Legal approved the updated data processing agreement for European customers.",
        "did counsel sign off on the new DPA for EU clients",
        "DPA approval",
    ),
    (
        "The mobile team froze feature work until the crash rate falls below one percent.",
        "why did app development pause new functionality",
        "Mobile feature freeze",
    ),
    (
        "The investor update goes out every Friday at noon.",
        "what day do backers receive the recurring status email",
        "Investor update cadence",
    ),
    (
        "Server costs doubled after the analytics pipeline moved to real-time processing.",
        "what happened to infrastructure spend when streaming was enabled",
        "Analytics cost increase",
    ),
    (
        "The design system migration finishes at the end of March.",
        "when does the UI component library switchover wrap up",
        "Design system migration",
    ),
    (
        "Support tickets about billing spiked after the pricing page redesign.",
        "which customer complaints increased following the new price layout",
        "Billing ticket spike",
    ),
    (
        "The hiring freeze exempts backend engineers and security roles.",
        "which positions can still be recruited during the headcount pause",
        "Hiring freeze exemptions",
    ),
    (
        "Beta invites are limited to fifty users weekly during the pilot.",
        "how many people can join the early access program each week",
        "Beta invite cap",
    ),
    (
        "The annual compliance audit starts on the second Monday of January.",
        "when do the yearly regulatory reviewers begin their inspection",
        "Compliance audit start",
    ),
    (
        "Marketing shifted the campaign budget from paid search to podcast sponsorships.",
        "where did the advertising money move away from adwords",
        "Campaign budget shift",
    ),
    (
        "The on-call rotation now includes the data platform engineers.",
        "who was recently added to the pager schedule",
        "On-call rotation change",
    ),
)

# Distractor memories share entities and business vocabulary with the query
# set but answer none of the queries.
_DISTRACTOR_TEMPLATES: tuple[str, ...] = (
    "{first_name} {last_name} joined the {project} steering committee in {month}.",
    "{project} standup notes are archived in the shared drive every Friday.",
    "Expense reports for {project} travel must be filed within thirty days.",
    "{first_name} {last_name} presented the {project} quarterly metrics at the all-hands.",
    "The {project} staging environment refreshes nightly at 2am.",
    "{first_name} {last_name} rotated onto {project} on-call for the {month} cycle.",
    "{project} documentation moved to the new wiki space.",
    "Vendor invoices for {project} route through {first_name} {last_name} for signoff.",
    "The {project} test suite runs on every merge to main.",
    "{first_name} {last_name} drafted the {project} hiring plan for two senior roles.",
    "{project} customer feedback is triaged every Tuesday afternoon.",
    "The {project} demo environment password rotates monthly.",
    "{first_name} {last_name} flagged a licensing question on the {project} dependency audit.",
    "{project} release notes are published the first Monday of each month.",
)
_DISTRACTOR_VARIANTS_PER_TEMPLATE = 12

VNEXT_BENCHMARK_EXPECTED_COUNTS: JsonObject = {
    "memories": len(_LEXICAL_TEMPLATES) * _LEXICAL_VARIANTS_PER_TEMPLATE
    + len(_PARAPHRASE_PAIRS)
    + len(_DISTRACTOR_TEMPLATES) * _DISTRACTOR_VARIANTS_PER_TEMPLATE,
    "queries": len(_LEXICAL_TEMPLATES) * _LEXICAL_VARIANTS_PER_TEMPLATE + len(_PARAPHRASE_PAIRS),
    "lexical_overlap_queries": len(_LEXICAL_TEMPLATES) * _LEXICAL_VARIANTS_PER_TEMPLATE,
    "paraphrase_queries": len(_PARAPHRASE_PAIRS),
    "distractor_memories": len(_DISTRACTOR_TEMPLATES) * _DISTRACTOR_VARIANTS_PER_TEMPLATE,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_corpus_path() -> Path:
    return _repo_root() / VNEXT_EVAL_CORPUS_SOURCE_PATH


def _default_report_path() -> Path:
    return _repo_root() / VNEXT_EVAL_REPORT_PATH


def _hash_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _memory_key(kind: str, index: int) -> str:
    return f"{VNEXT_EVAL_MEMORY_KEY_PREFIX}{kind}-{index:03d}"


def _template_fields(template_index: int, variant_index: int) -> dict[str, str]:
    project = _PROJECTS[(template_index * _LEXICAL_VARIANTS_PER_TEMPLATE + variant_index * 5) % len(_PROJECTS)]
    person = _PEOPLE[(template_index * 5 + variant_index * 3 + 1) % len(_PEOPLE)]
    first_name, last_name = person.split(" ", 1)
    return {
        "project": project,
        "first_name": first_name,
        "last_name": last_name,
        "month": _MONTHS[(template_index * 3 + variant_index) % len(_MONTHS)],
        "weekday": _WEEKDAYS[(template_index + variant_index) % len(_WEEKDAYS)],
        "amount": str(40 + ((template_index * 7 + variant_index * 11) % 50) * 5),
    }


def _corpus_memory(*, memory_key: str, title: str, canonical_text: str, role: str) -> JsonObject:
    return {
        "memory_key": memory_key,
        "title": title,
        "canonical_text": canonical_text,
        "domain": "professional",
        "sensitivity": "internal",
        "memory_type": "semantic",
        "status": "active",
        "role": role,
    }


def generate_vnext_benchmark_corpus() -> JsonObject:
    """Build the deterministic retrieval-quality corpus (no runtime random)."""
    memories: list[JsonObject] = []
    queries: list[JsonObject] = []

    lexical_index = 0
    for template_index, (memory_template, query_template, title_template) in enumerate(_LEXICAL_TEMPLATES):
        for variant_index in range(_LEXICAL_VARIANTS_PER_TEMPLATE):
            lexical_index += 1
            fields = _template_fields(template_index, variant_index)
            memory_key = _memory_key("lexical", lexical_index)
            memories.append(
                _corpus_memory(
                    memory_key=memory_key,
                    title=title_template.format(**fields),
                    canonical_text=memory_template.format(**fields),
                    role="target",
                )
            )
            queries.append(
                {
                    "query_key": f"lexical-{lexical_index:03d}",
                    "query": query_template.format(**fields),
                    "expected_memory_key": memory_key,
                    "subset": SUBSET_LEXICAL_OVERLAP,
                }
            )

    for pair_index, (memory_text, query_text, title) in enumerate(_PARAPHRASE_PAIRS, start=1):
        memory_key = _memory_key("paraphrase", pair_index)
        memories.append(
            _corpus_memory(
                memory_key=memory_key,
                title=title,
                canonical_text=memory_text,
                role="target",
            )
        )
        queries.append(
            {
                "query_key": f"paraphrase-{pair_index:03d}",
                "query": query_text,
                "expected_memory_key": memory_key,
                "subset": SUBSET_PARAPHRASE,
            }
        )

    distractor_index = 0
    for template_index, template in enumerate(_DISTRACTOR_TEMPLATES):
        for variant_index in range(_DISTRACTOR_VARIANTS_PER_TEMPLATE):
            distractor_index += 1
            project = _PROJECTS[variant_index % len(_PROJECTS)]
            person = _PEOPLE[(variant_index + template_index) % len(_PEOPLE)]
            first_name, last_name = person.split(" ", 1)
            fields = {
                "project": project,
                "first_name": first_name,
                "last_name": last_name,
                "month": _MONTHS[(template_index + variant_index * 2) % len(_MONTHS)],
            }
            memories.append(
                _corpus_memory(
                    memory_key=_memory_key("distractor", distractor_index),
                    title=f"{project} operational note {distractor_index:03d}",
                    canonical_text=template.format(**fields),
                    role="distractor",
                )
            )

    corpus: JsonObject = {
        "schema_version": VNEXT_EVAL_CORPUS_SCHEMA_VERSION,
        "kind": RETRIEVAL_QUALITY_SUITE_KEY,
        "counts": {
            "memories": len(memories),
            "queries": len(queries),
            "lexical_overlap_queries": sum(1 for query in queries if query["subset"] == SUBSET_LEXICAL_OVERLAP),
            "paraphrase_queries": sum(1 for query in queries if query["subset"] == SUBSET_PARAPHRASE),
            "distractor_memories": sum(1 for memory in memories if memory["role"] == "distractor"),
        },
        "memories": memories,
        "queries": queries,
    }
    corpus["corpus_digest"] = _hash_payload({"memories": memories, "queries": queries})
    return corpus


def load_vnext_benchmark_corpus(corpus_path: str | Path | None = None) -> JsonObject:
    path = Path(corpus_path) if corpus_path is not None else _default_corpus_path()
    if not path.exists():
        return generate_vnext_benchmark_corpus()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("vNext eval corpus must be a JSON object")
    if payload.get("schema_version") != VNEXT_EVAL_CORPUS_SCHEMA_VERSION:
        raise ValueError("unexpected vNext eval corpus schema version")
    return cast(JsonObject, payload)


def write_vnext_benchmark_corpus(corpus_path: str | Path | None = None) -> Path:
    path = Path(corpus_path) if corpus_path is not None else _default_corpus_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    corpus = generate_vnext_benchmark_corpus()
    path.write_text(json.dumps(corpus, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path.resolve()


# --------------------------------------------------------------------------
# Metric math (pure functions, unit-tested against known rankings)
# --------------------------------------------------------------------------

_EVAL_TOKEN_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "after",
        "all",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "been",
        "before",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "during",
        "each",
        "for",
        "from",
        "had",
        "has",
        "have",
        "here",
        "how",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "many",
        "much",
        "next",
        "no",
        "not",
        "now",
        "of",
        "on",
        "or",
        "our",
        "out",
        "over",
        "per",
        "should",
        "so",
        "some",
        "than",
        "that",
        "the",
        "their",
        "then",
        "there",
        "these",
        "this",
        "those",
        "to",
        "too",
        "under",
        "up",
        "us",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
    }
)


def eval_content_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.casefold())
        if len(token) > 1 and token not in _EVAL_TOKEN_STOPWORDS
    }


def eval_token_overlap(query: str, memory_text: str) -> float:
    """Fraction of the query's content tokens that appear verbatim in the memory."""
    query_tokens = eval_content_tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & eval_content_tokens(memory_text)) / len(query_tokens)


def recall_at_k(ranked_ids: Sequence[str], expected_id: str, k: int) -> float:
    if k < 1:
        raise ValueError("recall@k requires k >= 1")
    return 1.0 if expected_id in list(ranked_ids)[:k] else 0.0


def reciprocal_rank(ranked_ids: Sequence[str], expected_id: str) -> float:
    for rank, ranked_id in enumerate(ranked_ids, start=1):
        if ranked_id == expected_id:
            return 1.0 / rank
    return 0.0


def latency_percentile(values: Sequence[float], percentile: float) -> float:
    """Nearest-rank percentile; deterministic and dependency-free."""
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be in (0, 100]")
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile / 100.0) * len(ordered)))
    return ordered[rank - 1]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# --------------------------------------------------------------------------
# Retrieval-quality suite: production pipeline execution
# --------------------------------------------------------------------------


def seed_retrieval_corpus(store: object, corpus: JsonObject) -> JsonObject:
    """Write the corpus memories through the real store write path.

    Embeds through the configured embedding provider when one is available so
    the vector stage participates; embedding failure degrades to FTS-only and
    is reported, never hidden.
    """
    create_memory = getattr(store, "create_memory", None)
    if not callable(create_memory):
        raise ValueError("retrieval-quality eval store must expose create_memory")
    memories = [cast(JsonObject, item) for item in cast(list[object], corpus.get("memories", [])) if isinstance(item, dict)]
    created_rows: list[JsonObject] = []
    for memory in memories:
        created_rows.append(
            cast(
                JsonObject,
                create_memory(
                    {
                        "memory_key": memory["memory_key"],
                        "value": {"text": memory["canonical_text"]},
                        "status": memory.get("status", "active"),
                        "memory_type": memory.get("memory_type", "semantic"),
                        "title": memory.get("title"),
                        "canonical_text": memory["canonical_text"],
                        "domain": memory.get("domain", "professional"),
                        "sensitivity": memory.get("sensitivity", "internal"),
                    }
                ),
            )
        )

    embedded_count = 0
    embedding_note = "no embedding provider configured; vector stage inactive"
    provider = get_embedding_provider()
    update_memory_embedding = getattr(store, "update_memory_embedding", None)
    if provider is not None and callable(update_memory_embedding):
        try:
            for batch_start in range(0, len(created_rows), MAX_EMBEDDINGS_BATCH_SIZE):
                batch = created_rows[batch_start : batch_start + MAX_EMBEDDINGS_BATCH_SIZE]
                vectors = provider.embed_batch([memory_embedding_text(row) for row in batch])
                for row, vector in zip(batch, vectors):
                    update_memory_embedding(memory_id=str(row["id"]), vector=vector)
                    embedded_count += 1
            embedding_note = f"embedded via {provider.provider}/{provider.model}"
        except (VNextEmbeddingConfigurationError, VNextEmbeddingProviderError) as exc:
            embedding_note = f"embedding failed, continuing FTS-only: {exc}"
    elif provider is not None:
        embedding_note = "store does not support update_memory_embedding; vector stage inactive"

    return {
        "seeded_memory_count": len(created_rows),
        "embedded_memory_count": embedded_count,
        "embedding_note": embedding_note,
    }


def production_retrieval_fn(store: object) -> RetrievalFn:
    """Per-query closure over the real hybrid retrieval pipeline."""
    service = VNextRetrievalService(cast(VNextRetrievalStore, store))

    def _retrieve(query: str, *, limit: int) -> JsonObject:
        pack = service.compile_context_pack(
            VNextRetrievalRequest(
                query=query,
                max_items=limit,
                include_sources=False,
                include_contradictions=False,
                actor_type="system",
            )
        )
        relevant = cast(list[JsonObject], pack.get("relevant_memories", []))
        trace = cast(JsonObject, pack.get("trace", {}))
        return {
            "ranked_memory_keys": [str(item["memory_key"]) for item in relevant if item.get("memory_key")],
            "vector_stage": trace.get("vector_stage", "unknown"),
        }

    return _retrieve


def _skipped_retrieval_suite(reason: str) -> JsonObject:
    return {
        "suite_key": RETRIEVAL_QUALITY_SUITE_KEY,
        "title": "Retrieval quality (production hybrid pipeline)",
        "status": "skipped",
        "reason": reason,
        "targets": deepcopy(RETRIEVAL_QUALITY_TARGETS),
        "metrics": {"query_count": 0},
        "cases": [],
    }


def run_retrieval_quality_eval(
    store: object | None,
    *,
    retrieval_fn: RetrievalFn | None = None,
    corpus: JsonObject | None = None,
    recall_limit: int = RETRIEVAL_QUALITY_RECALL_LIMIT,
) -> JsonObject:
    """Execute the retrieval-quality suite against the production pipeline.

    With a live ``store`` handle the corpus is seeded through the real write
    path and every query runs through ``VNextRetrievalService``. A
    ``retrieval_fn`` may be injected for metric-math testing. With neither,
    the suite reports ``status: "skipped"`` -- never a fabricated pass.
    """
    resolved_corpus = corpus if corpus is not None else generate_vnext_benchmark_corpus()
    queries = [
        cast(JsonObject, item)
        for item in cast(list[object], resolved_corpus.get("queries", []))
        if isinstance(item, dict)
    ]
    if not queries:
        raise ValueError("retrieval-quality corpus must include queries")

    seeding: JsonObject | None = None
    if retrieval_fn is None:
        if store is None:
            return _skipped_retrieval_suite(RETRIEVAL_QUALITY_SKIP_REASON)
        seeding = seed_retrieval_corpus(store, resolved_corpus)
        retrieval_fn = production_retrieval_fn(store)

    cases: list[JsonObject] = []
    latencies_ms: list[float] = []
    vector_stages: set[str] = set()
    for query in queries:
        query_text = str(query["query"])
        expected_key = str(query["expected_memory_key"])
        subset = str(query.get("subset", SUBSET_LEXICAL_OVERLAP))
        started = perf_counter()
        result = retrieval_fn(query_text, limit=recall_limit)
        latency_ms = (perf_counter() - started) * 1000.0
        latencies_ms.append(latency_ms)
        ranked_keys = [str(key) for key in cast(list[object], result.get("ranked_memory_keys", []))]
        vector_stages.add(str(result.get("vector_stage", "unknown")))
        case_recall_at_1 = recall_at_k(ranked_keys, expected_key, 1)
        case_recall_at_5 = recall_at_k(ranked_keys, expected_key, 5)
        case_reciprocal_rank = reciprocal_rank(ranked_keys, expected_key)
        cases.append(
            {
                "case_key": str(query["query_key"]),
                "subset": subset,
                "status": "pass" if case_recall_at_5 == 1.0 else "fail",
                "metrics": {
                    "recall_at_1": case_recall_at_1,
                    "recall_at_5": case_recall_at_5,
                    "reciprocal_rank": case_reciprocal_rank,
                    "latency_ms": round(latency_ms, 3),
                },
                "evidence": {
                    "query": query_text,
                    "expected_memory_key": expected_key,
                    "top_memory_keys": ranked_keys[:5],
                    "vector_stage": result.get("vector_stage", "unknown"),
                },
            }
        )

    vector_stage_active = vector_stages == {VECTOR_STAGE_ENABLED}
    if vector_stage_active:
        retrieval_mode = "hybrid"
    elif VECTOR_STAGE_ENABLED in vector_stages:
        retrieval_mode = "mixed"
    else:
        retrieval_mode = "fts_only"

    def _subset_metrics(subset: str) -> JsonObject:
        subset_cases = [case for case in cases if case["subset"] == subset]
        metrics = [cast(JsonObject, case["metrics"]) for case in subset_cases]
        return {
            "query_count": len(subset_cases),
            "recall_at_1": _mean([cast(float, metric["recall_at_1"]) for metric in metrics]),
            "recall_at_5": _mean([cast(float, metric["recall_at_5"]) for metric in metrics]),
            "mrr": _mean([cast(float, metric["reciprocal_rank"]) for metric in metrics]),
        }

    lexical_metrics = _subset_metrics(SUBSET_LEXICAL_OVERLAP)
    paraphrase_metrics = _subset_metrics(SUBSET_PARAPHRASE)
    all_metrics = [cast(JsonObject, case["metrics"]) for case in cases]

    lexical_recall_target = cast(dict[str, float], RETRIEVAL_QUALITY_TARGETS["lexical_overlap_recall_at_5"])["minimum"]
    lexical_mrr_target = cast(dict[str, float], RETRIEVAL_QUALITY_TARGETS["lexical_overlap_mrr"])["minimum"]
    paraphrase_recall_target = cast(dict[str, float], RETRIEVAL_QUALITY_TARGETS["paraphrase_recall_at_5"])["minimum"]

    checks: dict[str, bool] = {
        "lexical_overlap_recall_at_5": cast(float, lexical_metrics["recall_at_5"]) >= lexical_recall_target,
        "lexical_overlap_mrr": cast(float, lexical_metrics["mrr"]) >= lexical_mrr_target,
    }
    # The paraphrase subset is designed so FTS alone struggles; the target is
    # only enforced when the vector stage actually ran. In FTS-only mode the
    # paraphrase numbers are still reported, honestly, as degraded coverage.
    if vector_stage_active:
        checks["paraphrase_recall_at_5"] = cast(float, paraphrase_metrics["recall_at_5"]) >= paraphrase_recall_target

    metrics: JsonObject = {
        "query_count": len(cases),
        "recall_at_1": _mean([cast(float, metric["recall_at_1"]) for metric in all_metrics]),
        "recall_at_5": _mean([cast(float, metric["recall_at_5"]) for metric in all_metrics]),
        "mrr": _mean([cast(float, metric["reciprocal_rank"]) for metric in all_metrics]),
        "latency_ms": {
            "p50": round(latency_percentile(latencies_ms, 50), 3),
            "p95": round(latency_percentile(latencies_ms, 95), 3),
            "max": round(max(latencies_ms), 3),
        },
        "vector_stages": sorted(vector_stages),
        "retrieval_mode": retrieval_mode,
        "paraphrase_targets_enforced": vector_stage_active,
        "subsets": {
            SUBSET_LEXICAL_OVERLAP: lexical_metrics,
            SUBSET_PARAPHRASE: paraphrase_metrics,
        },
        "target_checks": {key: ("pass" if passed else "fail") for key, passed in sorted(checks.items())},
    }
    if seeding is not None:
        metrics["seeding"] = seeding

    return {
        "suite_key": RETRIEVAL_QUALITY_SUITE_KEY,
        "title": "Retrieval quality (production hybrid pipeline)",
        "status": "pass" if all(checks.values()) else "fail",
        "targets": deepcopy(RETRIEVAL_QUALITY_TARGETS),
        "metrics": metrics,
        "cases": cases,
    }


@contextmanager
def _ephemeral_eval_store(database_url: str) -> Iterator[PostgresVNextStore]:
    """Live store scoped to a forced-rollback transaction: no data persists."""
    user_id = UUID(os.environ.get(VNEXT_EVAL_USER_ID_ENV, "").strip() or VNEXT_EVAL_DEFAULT_USER_ID)
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.transaction(force_rollback=True):
            set_current_user(conn, user_id)
            with conn.cursor() as cur:
                # Seeded memories require an acting user row; it rolls back
                # with everything else.
                cur.execute(
                    "INSERT INTO users (id, email, display_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (user_id, f"vnext-eval+{user_id}@example.invalid", "vNext Eval"),
                )
            yield PostgresVNextStore(conn)


def _run_retrieval_quality_suite(
    *,
    corpus: JsonObject,
    store: object | None,
    retrieval_fn: RetrievalFn | None,
) -> JsonObject:
    if store is not None or retrieval_fn is not None:
        return run_retrieval_quality_eval(store, retrieval_fn=retrieval_fn, corpus=corpus)
    database_url = os.environ.get(VNEXT_EVAL_DATABASE_URL_ENV, "").strip()
    if database_url == "":
        return _skipped_retrieval_suite(RETRIEVAL_QUALITY_SKIP_REASON)
    try:
        with _ephemeral_eval_store(database_url) as live_store:
            return run_retrieval_quality_eval(live_store, corpus=corpus)
    except psycopg.Error as exc:
        return _skipped_retrieval_suite(f"live store unavailable ({type(exc).__name__}): {exc}")


# --------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------


def _resolve_suite_keys(suite: str | None) -> tuple[str, ...]:
    requested = "all" if suite is None else suite.strip().lower()
    if requested == "all":
        return VNEXT_EVAL_SUITE_ORDER
    if requested not in VNEXT_EVAL_SUITE_ORDER:
        raise ValueError(f"unknown vNext eval suite: {suite}")
    return (requested,)


def _validate_corpus_counts(corpus: JsonObject) -> JsonObject:
    actual_counts = cast(JsonObject, corpus.get("counts", {}))
    mismatches = {
        key: {"expected": expected, "actual": actual_counts.get(key)}
        for key, expected in VNEXT_BENCHMARK_EXPECTED_COUNTS.items()
        if actual_counts.get(key) != expected
    }
    return {
        "expected": deepcopy(VNEXT_BENCHMARK_EXPECTED_COUNTS),
        "actual": actual_counts,
        "status": "pass" if not mismatches else "fail",
        "mismatches": mismatches,
    }


def _generated_at(now_fn: Callable[[], datetime] | None) -> str:
    now = now_fn() if now_fn is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def run_vnext_evals(
    *,
    suite: str | None = "all",
    corpus_path: str | Path | None = None,
    store: object | None = None,
    retrieval_fn: RetrievalFn | None = None,
    now_fn: Callable[[], datetime] | None = None,
) -> JsonObject:
    """Run the vNext eval suites and assemble an honest report.

    Overall ``status`` is ``"pass"`` only when every *executed* suite passed;
    skipped suites are listed separately and never counted as a pass. When no
    suite could execute at all the report status is ``"skipped"``.
    """
    corpus = load_vnext_benchmark_corpus(corpus_path)
    if corpus.get("schema_version") != VNEXT_EVAL_CORPUS_SCHEMA_VERSION:
        raise ValueError("unexpected vNext eval corpus schema version")
    corpus_validation = _validate_corpus_counts(corpus)
    requested_suite = "all" if suite is None else suite.strip().lower()
    suite_keys = _resolve_suite_keys(suite)

    suites: list[JsonObject] = []
    for suite_key in suite_keys:
        if suite_key == RETRIEVAL_QUALITY_SUITE_KEY:
            suites.append(_run_retrieval_quality_suite(corpus=corpus, store=store, retrieval_fn=retrieval_fn))

    executed_suites = [suite_report for suite_report in suites if suite_report["status"] != "skipped"]
    skipped_suites = [suite_report for suite_report in suites if suite_report["status"] == "skipped"]
    if corpus_validation["status"] != "pass":
        status = "fail"
    elif not executed_suites:
        status = "skipped"
    elif all(suite_report["status"] == "pass" for suite_report in executed_suites):
        status = "pass"
    else:
        status = "fail"

    case_count = sum(len(cast(list[JsonObject], suite_report["cases"])) for suite_report in executed_suites)
    passed_case_count = sum(
        1
        for suite_report in executed_suites
        for case in cast(list[JsonObject], suite_report["cases"])
        if case.get("status") == "pass"
    )
    report: JsonObject = {
        "schema_version": VNEXT_EVAL_REPORT_SCHEMA_VERSION,
        "generated_at": _generated_at(now_fn),
        "suite": requested_suite,
        "status": status,
        "targets": deepcopy(VNEXT_ACCEPTANCE_TARGETS),
        "corpus": {
            "schema_version": corpus.get("schema_version"),
            "corpus_digest": corpus.get("corpus_digest"),
            "counts": corpus_validation,
        },
        "skipped_suites": [
            {"suite_key": suite_report["suite_key"], "reason": suite_report.get("reason")}
            for suite_report in skipped_suites
        ],
        "summary": {
            "status": status,
            "suite_count": len(suites),
            "executed_suite_count": len(executed_suites),
            "skipped_suite_count": len(skipped_suites),
            "case_count": case_count,
            "passed_case_count": passed_case_count,
            "failed_case_count": case_count - passed_case_count,
            "pass_rate": passed_case_count / max(case_count, 1),
            "suite_order": list(suite_keys),
        },
        "suites": suites,
    }
    # The digest intentionally excludes generated_at so identical runs hash
    # identically regardless of wall-clock time.
    report["report_digest"] = _hash_payload(
        {
            "schema_version": report["schema_version"],
            "suite": report["suite"],
            "summary": report["summary"],
            "corpus_digest": report["corpus"]["corpus_digest"],
        }
    )
    return report


def write_vnext_eval_report(
    *,
    report: JsonObject,
    report_path: str | Path | None = None,
) -> Path:
    path = Path(report_path) if report_path is not None else _default_report_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path.resolve()


__all__ = [
    "RETRIEVAL_QUALITY_RECALL_LIMIT",
    "RETRIEVAL_QUALITY_SUITE_KEY",
    "RETRIEVAL_QUALITY_TARGETS",
    "SUBSET_LEXICAL_OVERLAP",
    "SUBSET_PARAPHRASE",
    "VNEXT_ACCEPTANCE_TARGETS",
    "VNEXT_BENCHMARK_EXPECTED_COUNTS",
    "VNEXT_EVAL_CORPUS_SCHEMA_VERSION",
    "VNEXT_EVAL_DATABASE_URL_ENV",
    "VNEXT_EVAL_MEMORY_KEY_PREFIX",
    "VNEXT_EVAL_REPORT_SCHEMA_VERSION",
    "VNEXT_EVAL_SUITE_ORDER",
    "eval_content_tokens",
    "eval_token_overlap",
    "generate_vnext_benchmark_corpus",
    "latency_percentile",
    "load_vnext_benchmark_corpus",
    "production_retrieval_fn",
    "recall_at_k",
    "reciprocal_rank",
    "run_retrieval_quality_eval",
    "run_vnext_evals",
    "seed_retrieval_corpus",
    "write_vnext_benchmark_corpus",
    "write_vnext_eval_report",
]
