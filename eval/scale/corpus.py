"""Deterministic synthetic corpus for the scale benchmark.

Everything derives from one seed, so a given (seed, scale) pair always
produces byte-identical memories, sources, entities, and edges on every
backend. Shape targets:

- titles 5-10 words, canonical_text 30-120 words, drawn from a realistic
  working vocabulary (projects, meetings, health, finance, ...)
- domains cycle through the FULL schema vocabulary (13 domains -- the
  ``memories.domain`` CHECK constraint in ``sqlite_schema.DOMAINS`` and the
  Postgres migrations allows exactly these, so "20 domains" is not
  representable without schema changes)
- a weighted memory_type mix over the schema's allowed types
- 10% of memories carry ``valid_to`` (mostly future; ~0.4% already expired
  so the first staleness sweep has real work but steady-state passes scan
  without marking)
- entity mentions sprinkled into text plus explicit memory->entity
  ``mentions`` edges so the graph substrate populates; entity[0]
  ("Meridian Labs") is deliberately hot (~1% of memories point at it)
- one source per 5 memories, each memory provenance-linked to its source
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import blake2b
import random
from typing import Iterator

SEED_DEFAULT = 42
MEMORIES_PER_SOURCE = 5

# All values below stay inside the schema CHECK vocabularies
# (sqlite_schema.DOMAINS / MEMORY_TYPES / SENSITIVITY_LEVELS and their
# Postgres migration mirrors).
DOMAINS = (
    "professional", "personal", "family", "health", "spiritual",
    "financial", "legal", "learning", "relationship", "project",
    "agent_run", "system", "unknown",
)
SENSITIVITY_MIX = (
    ("internal", 45), ("private", 25), ("unknown", 20), ("public", 10),
)
MEMORY_TYPE_MIX = (
    ("semantic", 28), ("episode", 15), ("preference", 10), ("decision", 10),
    ("project_fact", 8), ("commitment", 6), ("identity_fact", 5),
    ("routine", 5), ("relationship_fact", 5), ("project_state", 4),
    ("constraint", 3), ("open_loop", 3), ("procedure", 2),
)
STATUS_MIX = (("active", 93), ("candidate", 5), ("accepted", 2))
# Types the staleness sweep's confirmation-age rule inspects
# (vnext_scheduler.STALENESS_REVIEW_MEMORY_TYPES).
STALENESS_REVIEW_MEMORY_TYPES = frozenset({"open_loop", "commitment", "project_state"})

_NOUNS = (
    "migration", "deadline", "budget", "forecast", "quarter", "audit",
    "vendor", "contract", "renewal", "meeting", "planning", "roadmap",
    "rollout", "timeline", "checkup", "routine", "sleep", "schedule",
    "security", "onboarding", "review", "report", "invoice", "proposal",
    "sprint", "backlog", "release", "database", "pipeline", "workshop",
    "training", "insurance", "mortgage", "vacation", "birthday", "recipe",
    "garden", "commute", "subscription", "warranty", "estimate", "design",
    "prototype", "interview", "offer", "salary", "portfolio", "checklist",
)
_VERBS = (
    "decided", "reviewed", "scheduled", "postponed", "approved", "drafted",
    "confirmed", "cancelled", "escalated", "finished", "started", "paused",
    "renewed", "negotiated", "estimated", "measured", "documented",
    "shipped", "tested", "archived", "prioritized", "compared", "planned",
)
_MODIFIERS = (
    "quarterly", "weekly", "urgent", "tentative", "final", "preliminary",
    "annual", "internal", "external", "shared", "personal", "critical",
    "upcoming", "overdue", "revised", "approved", "draft", "monthly",
)
_CONNECTORS = (
    "before the", "after the", "because of the", "instead of the",
    "together with the", "pending the", "despite the", "ahead of the",
)

_PERSON_FIRST = ("Sara", "Jonas", "Priya", "Mateo", "Aiko", "Lena", "Omar", "Nadia", "Felix", "Ingrid")
_PERSON_LAST = ("Lindqvist", "Okafor", "Tanaka", "Marchetti", "Haugen", "Petrov", "Alvarez", "Bergman")
_ORG_FIRST = ("Meridian", "Northwind", "Quantia", "Bluepeak", "Solstice", "Verdant", "Halcyon", "Kestrel")
_ORG_SUFFIX = ("Labs", "Systems", "Capital", "Health", "Analytics", "Partners", "Logistics", "Studio")
_PROJECT_FIRST = ("Atlas", "Beacon", "Cascade", "Drift", "Ember", "Fathom", "Glacier", "Harbor")
_PROJECT_SUFFIX = ("Onboarding", "Migration", "Redesign", "Rollout", "Cleanup", "Expansion", "Pilot", "Upgrade")

HOT_ENTITY_NAME = "Meridian Labs"       # entity index 0, ~1% of memories edge to it
MID_ENTITY_NAME = "Atlas Onboarding"    # entity index 1, moderate fan-in

# Alice-recall-shaped queries: generic lexical, domain-inflected, and two
# that resolve entities so the graph stage participates.
RECALL_QUERIES = (
    "what did we decide about the database migration deadline",
    "vendor contract renewal terms and invoice schedule",
    "latest updates from Meridian Labs on the rollout timeline",
    "current status of Atlas Onboarding milestones",
    "health checkup routine and sleep schedule notes",
    "budget forecast for the upcoming quarter review",
    "who approved the security audit checklist",
    "preferences for weekly planning meeting agenda",
)


@dataclass(frozen=True, slots=True)
class EntitySpec:
    index: int
    name: str
    entity_type: str


@dataclass(frozen=True, slots=True)
class SourceSpec:
    index: int
    title: str
    content_hash: str
    domain: str
    sensitivity: str


@dataclass(frozen=True, slots=True)
class MemorySpec:
    index: int
    memory_key: str
    title: str
    canonical_text: str
    memory_type: str
    status: str
    domain: str
    sensitivity: str
    confidence: float
    salience: float
    valid_to: str | None
    last_confirmed_at: str | None
    source_index: int
    entity_indices: tuple[int, ...] = field(default=())


def _weighted(rng: random.Random, mix: tuple[tuple[str, int], ...]) -> str:
    return rng.choices([value for value, _ in mix], weights=[weight for _, weight in mix], k=1)[0]


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def entity_pool_size(scale: int) -> int:
    return max(40, scale // 50)


def build_entities(scale: int, *, seed: int = SEED_DEFAULT) -> list[EntitySpec]:
    rng = random.Random(f"entities-{seed}")
    specs = [
        EntitySpec(0, HOT_ENTITY_NAME, "organization"),
        EntitySpec(1, MID_ENTITY_NAME, "project"),
    ]
    seen = {HOT_ENTITY_NAME, MID_ENTITY_NAME}
    builders = (
        ("person", lambda: f"{rng.choice(_PERSON_FIRST)} {rng.choice(_PERSON_LAST)}"),
        ("organization", lambda: f"{rng.choice(_ORG_FIRST)} {rng.choice(_ORG_SUFFIX)}"),
        ("project", lambda: f"{rng.choice(_PROJECT_FIRST)} {rng.choice(_PROJECT_SUFFIX)}"),
        ("technology", lambda: f"{rng.choice(_ORG_FIRST)}{rng.choice(('DB', 'Flow', 'Kit', 'Sync'))}"),
    )
    index = 2
    while index < entity_pool_size(scale):
        entity_type, make_name = builders[index % len(builders)]
        name = make_name()
        if name in seen:
            name = f"{name} {index}"  # deterministic de-duplication
        seen.add(name)
        specs.append(EntitySpec(index, name, entity_type))
        index += 1
    return specs


def _entity_indices_for(index: int, pool: int) -> tuple[int, ...]:
    """Deterministic edge fan-out; ~26% of memories carry 1-2 edges."""
    indices: list[int] = []
    if index % 100 == 0:
        indices.append(0)  # hot entity: 1% of the corpus
    elif index % 200 == 5:
        indices.append(1)  # mid entity: 0.5%
    elif index % 10 in (3, 7):
        indices.append(2 + (index * 7) % (pool - 2))
    if index % 25 == 13:
        indices.append(2 + (index * 13) % (pool - 2))
    return tuple(dict.fromkeys(indices))


def _sentence(rng: random.Random, *, mention: str | None = None) -> str:
    words = [
        rng.choice(_VERBS), "the", rng.choice(_MODIFIERS), rng.choice(_NOUNS),
        rng.choice(_CONNECTORS), rng.choice(_NOUNS),
    ]
    sentence = " ".join(words)
    if mention is not None:
        sentence += f" with {mention}"
    return sentence[0].upper() + sentence[1:] + "."


def _title(rng: random.Random, mention: str | None) -> str:
    words = [rng.choice(_MODIFIERS), rng.choice(_NOUNS), rng.choice(_VERBS), rng.choice(_CONNECTORS).split()[0], rng.choice(_NOUNS)]
    if mention is not None and rng.random() < 0.5:
        words = words[:3] + [mention]  # keep 5-10 word budget
    title = " ".join(words)
    return (title[0].upper() + title[1:])[:118]


def _canonical_text(rng: random.Random, mentions: tuple[str, ...]) -> str:
    target_words = rng.randint(30, 120)
    sentences: list[str] = []
    remaining_mentions = list(mentions)
    word_count = 0
    while word_count < target_words:
        mention = remaining_mentions.pop(0) if remaining_mentions else None
        sentence = _sentence(rng, mention=mention)
        sentences.append(sentence)
        word_count += len(sentence.split())
    return " ".join(sentences)


def iter_memories(
    scale: int,
    *,
    seed: int = SEED_DEFAULT,
    entities: list[EntitySpec],
    now: datetime | None = None,
) -> Iterator[MemorySpec]:
    rng = random.Random(f"memories-{seed}-{scale}")
    reference = now or datetime.now(UTC)
    pool = len(entities)
    for index in range(scale):
        entity_indices = _entity_indices_for(index, pool)
        mentions = tuple(entities[i].name for i in entity_indices)
        memory_type = _weighted(rng, MEMORY_TYPE_MIX)
        status = _weighted(rng, STATUS_MIX)

        # 10% carry valid_to; 4% of those (0.4% of the corpus) are already
        # expired, which stays under the sweep's default 500-row mark limit
        # at every benchmarked scale.
        valid_to: str | None = None
        roll = rng.random()
        if roll < 0.004:
            valid_to = _iso(reference - timedelta(days=rng.randint(1, 90)))
        elif roll < 0.10:
            valid_to = _iso(reference + timedelta(days=rng.randint(30, 365)))

        # Working-state types stay inside the sweep's 180-day confirmation
        # window so steady-state sweep passes scan without marking.
        last_confirmed_at: str | None = None
        if memory_type in STALENESS_REVIEW_MEMORY_TYPES:
            last_confirmed_at = _iso(reference - timedelta(days=rng.randint(0, 90)))

        yield MemorySpec(
            index=index,
            memory_key=f"scale.bench.{seed}.{index:06d}",
            title=_title(rng, mentions[0] if mentions else None),
            canonical_text=_canonical_text(rng, mentions),
            memory_type=memory_type,
            status=status,
            domain=DOMAINS[index % len(DOMAINS)],
            sensitivity=_weighted(rng, SENSITIVITY_MIX),
            confidence=round(rng.uniform(0.6, 0.98), 3),
            salience=round(rng.uniform(0.1, 0.9), 3),
            valid_to=valid_to,
            last_confirmed_at=last_confirmed_at,
            source_index=index // MEMORIES_PER_SOURCE,
            entity_indices=entity_indices,
        )


def build_sources(scale: int, *, seed: int = SEED_DEFAULT) -> list[SourceSpec]:
    rng = random.Random(f"sources-{seed}-{scale}")
    sources: list[SourceSpec] = []
    for index in range((scale + MEMORIES_PER_SOURCE - 1) // MEMORIES_PER_SOURCE):
        digest = blake2b(f"scale-source-{seed}-{scale}-{index}".encode(), digest_size=16).hexdigest()
        sources.append(
            SourceSpec(
                index=index,
                title=_title(rng, None),
                content_hash=f"scalebench:{digest}",
                domain=DOMAINS[index % len(DOMAINS)],
                sensitivity=_weighted(rng, SENSITIVITY_MIX),
            )
        )
    return sources


def capture_text_for_iteration(iteration: int, *, seed: int = SEED_DEFAULT) -> tuple[str, str]:
    """(title, raw_text) for one measured capture; unique to defeat dedupe."""
    rng = random.Random(f"capture-{seed}-{iteration}")
    mention = HOT_ENTITY_NAME if iteration % 5 == 0 else f"{rng.choice(_PERSON_FIRST)} {rng.choice(_PERSON_LAST)}"
    paragraphs = [
        f"Capture note {iteration}: " + _sentence(rng, mention=mention),
        _sentence(rng) + " " + _sentence(rng),
        _sentence(rng, mention=rng.choice(_ORG_FIRST) + " " + rng.choice(_ORG_SUFFIX)),
    ]
    return (f"Scale bench capture {iteration}", "\n\n".join(paragraphs))


def commit_payload_for_iteration(iteration: int, *, seed: int = SEED_DEFAULT) -> dict[str, str]:
    rng = random.Random(f"commit-{seed}-{iteration}")
    return {
        "title": f"Bench decision {iteration}: {rng.choice(_MODIFIERS)} {rng.choice(_NOUNS)} {rng.choice(_VERBS)}",
        "canonical_text": _canonical_text(rng, ()),
        "memory_type": "decision",
        "domain": DOMAINS[iteration % len(DOMAINS)],
        "sensitivity": "internal",
        "idempotency_key": f"scale-bench-{seed}-commit-{iteration}",
    }


__all__ = [
    "DOMAINS",
    "EntitySpec",
    "HOT_ENTITY_NAME",
    "MEMORIES_PER_SOURCE",
    "MID_ENTITY_NAME",
    "MemorySpec",
    "RECALL_QUERIES",
    "SEED_DEFAULT",
    "SourceSpec",
    "build_entities",
    "build_sources",
    "capture_text_for_iteration",
    "commit_payload_for_iteration",
    "entity_pool_size",
    "iter_memories",
]
