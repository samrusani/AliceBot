# Friction-first roadmap

Written 2026-07-29. Supersedes the feature-ordered plan for the next phase.

## The thesis, and the evidence for it

`thedotmack/claude-mem` has **90,631 stars**. Alice has **2**. Verified against
the GitHub API on 2026-07-29, not from a screenshot.

claude-mem is a year old, carries 429 open issues, and is on any reasonable
engineering measure less rigorous than Alice: no published benchmark receipt,
no adversarial review record, no release attestation chain. Alice has hybrid
retrieval with reciprocal rank fusion, a LongMemEval receipt with disclosed
trade-offs, eight adversarial rounds on the promotion policy alone, and a
release gate that caught four real defects in a single day.

None of that produced adoption. The difference is that claude-mem starts in
about thirty seconds and Alice needs PostgreSQL.

**So the next phase is ordered by friction removed, not features added.** A
better memory layer nobody can start is worth less than a rougher one they can.

## Licensing constraint, read this before opening their source

claude-mem is **Apache-2.0**. Alice is **MIT**. Apache-2.0 code cannot be
copied into Alice and kept MIT: the patent grant and NOTICE obligations travel
with the code, and including it would make Alice mixed-license, which
undercuts the clean-MIT position.

Ideas are not copyrightable. Read it, understand the pattern, reimplement.
Do not paste. If a specific file is ever genuinely worth vendoring, that is a
deliberate licensing decision to take explicitly, not a shortcut.

---

## Track 1: a first run that needs nothing

**Problem.** Getting to a first memory today requires provisioning PostgreSQL,
installing pgvector, running migrations, configuring an embeddings provider,
minting an agent key, and wiring MCP. The dogfooding guide for this is twenty
minutes long.

**Target.** One command, no services, a working memory in under a minute.

The SQLite on-ramp already exists (`alice-memory mcp`) but is documented as the
trial path and carries real limits: no agent keys, no web console, no
scheduler. Those limits are exactly what makes it unsuitable as the front door
today, because tiered promotion needs a key to be useful.

Work:

1. Make the SQLite path support agent keys, so tiered promotion works there.
   Without this the easiest way in is the one where the headline feature does
   not apply.
2. Ship a single-command installer. `uvx alice-memory init` or equivalent that
   creates the store, writes the MCP config, and prints the next step.
3. Decide and document the upgrade path from SQLite to PostgreSQL, because the
   embedding fingerprint makes the vector store close to permanent once loaded.
4. Measure the result honestly: time from `pip install` to first successful
   recall, on a clean machine, written down.

**Acceptance.** A person who has never seen Alice gets a memory stored and
recalled without reading past the first screen of the README.

---

## Track 2: capture that does not need to be chosen

**Problem.** Alice records a memory when an agent decides to call a memory
tool. Tiered promotion removed the approval step, which was the right fix, but
the agent still has to initiate. If it does not think to remember, nothing is
remembered.

**Pattern to reimplement.** claude-mem hooks the session lifecycle:
SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd. Capture becomes
ambient rather than deliberate.

Work:

1. A Claude Code plugin exposing the same lifecycle points, writing through the
   existing commit path so the promotion policy, the hard floor and the
   credential guard all still apply. Ambient capture must not become a way
   around the write gate.
2. A capture policy for what is worth keeping, since hooking everything is how
   a memory store fills with noise. This is where Alice's existing capture
   rules and staleness handling should earn their keep.
3. Provenance on ambient writes, so a memory captured by a hook is
   distinguishable from one the user asked for. `write_provenance` already
   exists; extend rather than duplicate it.

**Acceptance.** A session produces useful memories without the user or the
agent explicitly asking, and every ambient write is refusable by the same
floor that governs deliberate ones.

---

## Track 3: progressive disclosure and token accounting

**Problem.** Context packs return content. There is no cheap layer to filter
against before paying for detail.

**Pattern to reimplement.** A three-layer read: a search index, then a
timeline or summary layer, then full detail. claude-mem claims roughly a ten
times token saving from filtering before fetching. Treat that number as their
claim rather than as measured fact until Alice has its own.

Work:

1. Add a cheap discovery layer over the existing retrieval, returning
   identifiers and one-line summaries rather than full memories.
2. Report token cost as a first-class field on retrieval responses, so a caller
   can see what a pack costs before and after.
3. Measure the saving on Alice's own corpus and publish the number with its
   method, the way the LongMemEval receipt is published. If it is 3x rather
   than 10x, publish 3x.

**Acceptance.** A measured, reproducible token saving on Alice's own eval
corpus, with the harness committed.

---

## Track 4: dogfooding, running in parallel throughout

Not sequenced after the others, because none of them depend on it and it is the
only source of first-run truth Alice does not currently have.

Load the wiki, use it for a week, keep the journal line:

    date | what I asked or captured | hit/miss/partial | latency feel | correction needed?

Misses and corrections are the valuable rows. Two weeks of honest lines decides
what track 1 and track 2 actually need, as opposed to what seems obvious now.

---

## Deliberately not in this phase

**Enterprise readiness.** God modules, contract drift, multi-user, SSO, audit
export. All real, all large, none of them convert until an enterprise
conversation exists. Building for a buyer who has not appeared is the expensive
form of guessing.

**Phase 6 counting.** Still parked. It needs typed rows and SQL aggregation,
not better extraction.

**Another benchmark run.** 79.4% with a disclosed trade-off is already a better
artifact than a bigger number without a receipt. A higher score does not fix
2 stars.

---

## The writing, which is not optional

Two pieces, independent of all four tracks, aimed at the actual bottleneck:

1. **The governance design point.** Held-out corpora with thresholds fixed
   before the work exists. A membership diff requiring every moved rule to be
   listed. A tag that could not be deleted to cover a mistake, and the version
   number burned instead. This is the differentiator, and nobody knows it
   exists.
2. **Benchmark comparability.** Why a single-run receipt with disclosed
   trade-offs and a committed reproduction script is worth more than a headline
   number, and how to read the memory-benchmark claims currently in circulation.

These are what a prospective client reads. The engineering is not the
constraint.
