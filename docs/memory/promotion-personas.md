# Memory promotion personas

Alice's write gate historically had one setting: every agent memory proposal
went to human review. That is right for an enterprise deployment and wrong for
a personal second brain, whose owner never opens the review queue.

This document says plainly who each persona is for, what the tradeoff is, and
what an enterprise buyer should be told.

## Positioning

**Tiered promotion is a personal and team feature. Enterprise deployments
leave it off, and off is the default.**

`enterprise` is the default persona, and a deployment that configures nothing
at all behaves exactly as it did before this feature existed. An enterprise
buyer asking "can an agent write to memory without review" should get:

> Not in your configuration. `ALICE_MEMORY_PERSONA` is unset, which is the
> review-gated behaviour you already have, and auto-promotion additionally
> requires you to issue an agent API key. Leave both alone and nothing
> changes.

That is the honest answer. It is not a discussion of writer trust levels.

## The personas

| persona | who it is for | behaviour |
|---|---|---|
| unset | everyone, until they choose otherwise | identical to the pre-promotion write gate |
| `enterprise` | explicit review-gated posture | identical to unset, plus an audit record of the decision |
| `personal` | one owner, one second brain, no review queue | auto-promote when nothing escalates |
| `team` | a small team that wants the writes and a digest afterwards | auto-promote, plus a non-blocking `review.item_created` digest entry |

## What has to be true before anything is promoted

1. A persona is configured, by the owner's Brain Charter or by
   `ALICE_MEMORY_PERSONA`.
2. At least one active agent API key exists. Without a key nobody is
   distinguishable from anybody, so no writer is trusted.
3. The writer is either an agent whose identity resolved through an issued key
   (`authenticated_agent`), or the owner on a surface that actually
   authenticated this call (`owner`). A caller-asserted identity and an
   unidentifiable caller are never promotion-eligible.
4. The agent's permission profile permits the write in the first place.
   Promotion removes the human gate in front of an authorization; it never
   widens one. `read_only_agent` and `memory_proposal_agent` never promote.
5. No hard floor rule fires: credential material, agent-directed instructions,
   or re-ingestion of the agent's own output as fact.
6. No enabled escalation filter fires.

## What the content filters do and do not model

The three defences against content Alice pulled in are deliberately split.

`indirect_provenance` reads the declared `source_type` as an allowlist of
labels meaning "the writer composed this". Anything unrecognised, including
an invented label or an empty one, counts as external and escalates. Reading
it the other way round rewarded a relabel: an agent wanting to dodge the
filter only had to make a string up.

`unverified_authority_claim` does **not** consult the source type at all. It
is the one content backstop that does not rest on self-declaration, because
the ASI06 threat model is an agent manipulated by content it fetched, and a
defence that asks the possibly-compromised component to label its own fetch
honestly is not a defence. It models a specific shape: a claim that approval
has *already* been given, which asserts that scrutiny is unnecessary. A dated
report of an approval ("Legal approved the contract last Thursday") carries
no such marker and promotes.

`agent_control_vocabulary` stays scoped to external provenance, because its
members ("do not tell the user", a pasted `Assistant:` transcript, a note
opening "New instructions:") are ordinary things for an owner or an
authenticated agent to record and an attack surface only when they arrive
inside fetched material.

The hard floor carries only shapes with no ordinary declarative reading. The
test is grammatical rather than lexical: an imperative addressed to the agent
("ignore all previous instructions"), a second-person authority claim coupled
with an instruction to persist it, or control markup. The same words in a
declarative sentence are a note, which is why "we agreed to ignore the
previous guidelines" and "the style guide says to ignore prior rules" both
promote.

"Addressed to the agent" is decided by the subject of the clause, not by
whether it has one. A second-person subject leaves a clause a command, so
"could you ignore your previous instructions" and "if you ignore your prior
instructions" are on the floor along with the bare imperative. Any other
subject makes it a report. The one exception is the bare-infinitive
construction, where "our policy lets you ignore the previous guidelines" is a
report about a permission and promotes.

Everything the floor reads is read on every text-carrying field: title,
canonical text, conversation excerpt and `source_refs`, including refs nested
inside mappings and lists. Refs are persisted on the row and replayed into
context packs like body text, so a rule that skipped them would be optional.

### One credential rule, two guards

A credential is a secret-shaped **name** assigned an actual **value**, which
is what separates "her password= convention in the wiki is outdated" from
`DB_PASSWORD=hunter2abc`. That rule lives in `vnext_promotion_policy` and the
memory-commit reject path imports it, so there is one implementation rather
than two that agree today. Two copies is how the two guards drifted apart
before: measured against each other they disagreed on twelve shapes.

The guards are still complementary and both still run. The floor normalises
and decodes, which is what catches unicode, zero-width and fullwidth defeats
and character-spaced runs. The reject path's prefix patterns accept a shorter
AWS-style id than the floor's exact-shape rule. Neither is a superset of the
other, so the reject path consults both.

### Known residuals

1. The floor is a grammatical model of English. It has residual false
   negatives on unusual constructions and residual false positives on notes
   genuinely phrased as instructions. The measured rate on adversarial
   ordinary material is roughly 95%, not 100%.
2. The prose fields are matched as one joined surface, which is what holds an
   injection split across a title and a body. The same join means a field
   ending on a bare floor verb and a field beginning with that verb's object
   can spell a command neither field contains, and that pair gates. Narrowing
   it by matching fields separately would reopen the split-injection bypass,
   so it stands as a disclosed false positive rather than a traded-away
   defence. It is pinned in the unit tests in both directions.
3. `agent_control_vocabulary` is provenance-scoped by choice, so a pasted
   transcript shape relayed under an internal `source_type` promotes.
4. A claim about a person referred to by first name alone is not caught by
   `third_party_person`.

## The tradeoff, stated plainly

On a deployment that opts in, an authenticated agent at `trusted_local_agent`
or above can write durable memory without a human gate. **A compromised agent
key can therefore poison memory.** That is the cost of trusting an out-of-band
credential instead of trying to read intent out of the sentence, and the
alternative was measured: inspecting content to decide whether an agent could
be believed refused every agent write, because an agent authors both its claim
and any evidence it offers for the claim.

What stands against it:

- it is opt-in per deployment and additionally requires a key to exist;
- every write records which agent made it, under what source type, at what
  writer trust, and the read path surfaces that on the row so a poisoned
  memory is visibly agent-authored rather than anonymous;
- the row stays undoable and expirable through the ordinary lifecycle;
- the hard floor still catches credentials and agent-directed instructions
  whatever the writer;
- `alicebot vnext memories quarantine` expires everything a named key
  auto-promoted in a window, so a compromised key's blast radius is bounded
  and recoverable rather than unbounded in count and time.

## Recovering from a compromised key

```
alicebot agent keys revoke <key>                       # stop the next write
alicebot vnext memories quarantine \
    --target-agent-id <id> --reason "incident" --dry-run
alicebot vnext memories quarantine \
    --target-agent-id <id> --reason "incident"
```

**Quarantine is deliberately CLI-only. This is a decision, not unfinished
work, and it should not be reopened without revisiting the reasoning.**

Two reasons. The first is security: quarantine exists precisely for the case
where an agent key has been compromised, and it is reachable by the human
operator and by an `admin_agent` key. An HTTP route would widen who can reach
the incident control to anything able to present an admin key over the
network. Requiring shell access on the host is a posture, not a scheduling
compromise.

The second is that adding the route moves receipts in seven test files beyond
the two authorised for this work, and those seven are not all drift
detectors: the public error shapes and the vNext auth surface are behavioural
contracts with external consumers. Updating nineteen tests across that set to
add parity for a control that already has a working operator surface is the
kind of change where a guard gets updated because it was in the way rather
than because somebody understood what it pinned. This repository has already
lost two guards that way.

The sweep expires, it never deletes or redacts. Rows, revisions, provenance
and events all survive, the sweep records exactly which ids it acted on, and
`memory.unexpire` reverses it row by row. Who can run it: the human operator, and an `admin_agent` key **for its own
writes only**. No agent below `admin_agent` can run it at all, and an admin
key naming another agent is blocked with
`quarantine_limited_to_own_agent_id`, so the sweep cannot be used to bury
somebody else's memories. Sweeping an arbitrary key is the human operator's
to do.

It can only reach rows carrying a `memory.auto_promoted` event for the named
agent. A reviewed write, a human write, and another agent's write are not
addressable by it at all.

## Configuration

See `.env.example`. `ALICE_MEMORY_ESCALATION_FILTERS` is an enable-list: an
empty value keeps all filters on, and turning them all off requires the
explicit `DISABLE_ALL_ESCALATION_FILTERS` token.
