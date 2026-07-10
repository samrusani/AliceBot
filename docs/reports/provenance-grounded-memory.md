# Provenance-grounded memory: what we learned measuring an agent memory system until the numbers stopped moving

Sami Rusani and the Alice project · 2026-07-11

**Abstract.** Alice is a local-first, review-gated memory service for AI agents: every memory carries provenance back to source evidence, and nothing an agent writes becomes durable truth without passing a review gate. We measured it on LongMemEval_s under the benchmark's own protocol — official reading templates, official judge model and prompts, byte-frozen — and scored 79.4% (397/500) while reading roughly 6,000 tokens of retrieved context per answer, with every per-question row committed to this repository. We then tried to buy a higher score: we drove evidence coverage in retrieval packs from 86.6% to 95.3% and ran eight paired configuration arms across three reader model classes, and nothing beat the baseline — the only arms that moved measurably moved down, both regressions traced to specific defects and rejected, and every remaining configuration landed within ±4 net flips. Along the way we collected negative results we consider as valuable as the headline: LLM listwise reranking is recency-blind, single-threshold semantic clustering produces grab-bag consolidation cards (all 1,376 of which the product's review gate rejected), and reasoning readers erode abstention. Replaying our 500 cached answers through three grading regimes moved the score only 2.6 points, which is the second finding of this report: honest answers are protocol-robust, and benchmark numbers published without the official protocol and per-question receipts are not comparable to numbers published with them — in either direction. Everything here replays from committed evidence files, most of it without an API key.

## 1. The claim

Agent memory is becoming infrastructure, and infrastructure gets trusted. Our position, after measuring one system until the numbers stopped moving, is twofold:

1. **Memory for agents needs provenance-grounded, review-gated architecture.** Not because it wins benchmarks — we will show it saturates one — but because a memory an agent writes to is a write path into everything the agent does later, and the only defenses that hold are gating what gets in and being able to trace where every stored claim came from.
2. **Benchmark numbers without protocol receipts are noise.** We measured our own answers under three grading regimes and our own retrieval under eight paired configurations. Grading choices alone moved the score by 2.6 points on identical answers; tens of points of separation between published systems can live inside undisclosed protocol differences. A number is comparable only when the judge, the prompts, the dataset revision, and the per-question rows ship with it.

What Alice is, in two sentences: a local-first memory service that agents use over MCP, HTTP, or CLI to store typed, revisioned memories — facts, decisions, open loops, resumption briefs — each with provenance links to the source evidence that produced it. Agent writes land as policy-checked commits or reviewable proposals; correction and supersession are first-class; nothing auto-promotes into durable truth.

## 2. How we measured

The full protocol is documented in the [benchmark README](../benchmarks/longmemeval/README.md) and the [honesty kit](../benchmarks/longmemeval/HONESTY-KIT.md); the short version:

- **The benchmark's protocol, verbatim.** LongMemEval_s: 500 questions, each with a ~50-session haystack. Answers are generated with the benchmark's official reading templates and judged by `gpt-4o-2024-08-06` with the benchmark's per-question-type judge prompts, ported verbatim. Every official template is sha256-pinned in CI ([`test_harness.py`](../../eval/longmemeval/test_harness.py)); we control pack content, never instruction text. No code path conditions on question type. Dataset: the cleaned 2025-09 release, hash-verified on fetch.
- **Fingerprints on everything.** Every checkpoint row carries a digest of the run configuration (models, budgets, reading style, pack format, dataset hash). Evidence files are append-only; retries stay in the file; aggregation dedupes by question id keeping the last row.
- **A cost ladder.** Free offline probes first (evidence-coverage replays, the judge-free stale-pick metric), then a fixed 172-question paired slice (~$2–3 per arm, exact McNemar via [`compare_runs.py`](../../eval/longmemeval/compare_runs.py)), and a full 500-question run only for release candidates.

The headline history: the first published run scored **64.6%** (323/500) ([evidence](../benchmarks/longmemeval/per-question-results.jsonl)). Failure analysis of all 177 misses found one dominant cause — a real bug. The source-search stage was content-blind: it matched only titles and metadata, through a broken stopword list, so it effectively returned the most recently ingested sessions regardless of the query. Fixing it (RRF fusion over chunk-level full-text hits, the provenance of winning memories, and title/recency signals), plus a disclosed configuration change (16 items / 24k-char packs, up from 8 / 12k; the official chain-of-thought reading template instead of the official standard one), produced the published **79.4%** (397/500): paired on the same 500 questions, +96 gained, −22 lost, McNemar p = 3.26e-12 ([per-question rows](../benchmarks/longmemeval/per-question-results-2026-07-07.jsonl), [report](../benchmarks/longmemeval/report-2026-07-07.json), [flip analysis](../benchmarks/longmemeval/paired-comparison-2026-07-07.txt)). One regression came with it and is disclosed rather than netted away: the chain-of-thought template costs abstention, 25/30 → 22/30.

| Question type | n | 2026-07-05 | 2026-07-07 (published) |
|---|---|---|---|
| single-session-user | 70 | 90.0% | 97.1% |
| single-session-assistant | 56 | 75.0% | 92.9% |
| knowledge-update | 78 | 74.4% | 89.7% |
| temporal-reasoning | 133 | 61.7% | 81.2% |
| single-session-preference | 30 | 60.0% | 70.0% |
| multi-session | 133 | 45.1% | 58.6% |
| **Overall** | **500** | **64.6%** | **79.4%** |

That was the uplift story: a bug fix and a disclosed config, not a clever prompt. The rest of this report is about what happened when we kept going.

## 3. The saturation experiment

The obvious hypothesis after 79.4% was that the remaining 20.6% hides in retrieval — evidence sessions the pack never surfaces. We measured that directly instead of assuming it.

**Coverage.** [`coverage_probe.py`](../../eval/longmemeval/coverage_probe.py) replays retrieval offline (no reader, no judge) and checks whether every dataset-labeled evidence session for a question is present among the pack's retrieved sources. On the fixed 172-question slice:

| Retrieval configuration | All-evidence coverage | Evidence |
|---|---|---|
| FTS + graph, no vectors | 86.6% | [coverage-keyless.jsonl](../benchmarks/longmemeval/saturation-evidence/coverage-keyless.jsonl) |
| + vector stage (`text-embedding-3-small`) | 95.3% | [coverage-vectors.jsonl](../benchmarks/longmemeval/saturation-evidence/coverage-vectors.jsonl) |
| + LLM reranker | 95.3% | [coverage-vectors-reranker.jsonl](../benchmarks/longmemeval/saturation-evidence/coverage-vectors-reranker.jsonl) |

Per-type at the vectors configuration: multi-session 93.3%, temporal-reasoning 90.5%, and 100% on the other four categories. Retrieval, by the strictest definition the dataset supports — every labeled evidence session in the pack — is close to saturated.

**Then the answers refused to improve.** We ran eight paired arms against the published run on the same 172 questions — a slice deliberately over-weighted toward the hardest categories (60 multi-session, 42 temporal-reasoning, 25 knowledge-update), on which the published run scores 73.8% (127/172). Paired exact McNemar throughout:

| Arm | Net flips | p | Note | Evidence |
|---|---|---|---|---|
| vectors + LLM reranker + accepted roll-up cards | **−14** | 0.054 | knowledge-update −9; grab-bag cards in losing packs (§4.2) | [compare](../benchmarks/longmemeval/saturation-evidence/vectors-reranker-rollups-compare.txt) |
| vectors + LLM reranker (cards rejected) | **−11** | 0.144 | knowledge-update −8; isolates the reranker (§4.1) | [compare](../benchmarks/longmemeval/saturation-evidence/vectors-reranker-compare.txt) |
| vectors only | **0** | 1.000 | multi-session +5, the campaign's best | [compare](../benchmarks/longmemeval/saturation-evidence/vectors-only-compare.txt) |
| vectors + gpt-4.1 reader | **+3** | 0.690 | multi-session +7, knowledge-update −4 | [compare](../benchmarks/longmemeval/saturation-evidence/vectors-gpt41-reader-compare.txt) |
| round-6 prose packs (currency chains + date precompute) | **−3** | 0.690 | multi-session +4, preference −2 | [compare](../benchmarks/longmemeval/saturation-evidence/round6-prose-compare.txt) |
| round-6 JSON packs | **0** | 1.000 | abstention 25/30, matching the best we have measured; temporal +3 | [compare](../benchmarks/longmemeval/saturation-evidence/round6-json-compare.txt) |
| o4-mini reasoning reader, frozen packs | **+2** | 0.845 | preference 86.7%, best of any arm; abstention 22→17 (§4.3) | [compare](../benchmarks/longmemeval/saturation-evidence/vectors-o4mini-reader-compare.txt) |
| round-2 integrated branch (earlier, from repo history) | **+1** | 1.000 | parity; features shipped for product value, no new claim | [CHANGELOG](../../CHANGELOG.md), Unreleased |

Full checkpoints for every arm sit next to the compare files in [saturation-evidence/](../benchmarks/longmemeval/saturation-evidence/). (The −14 arm judged 171 of 172; its compare file discloses this.)

Eight paired configurations spanning retrieval composition (FTS-only through vectors and reranking), pack presentation (prose, JSON records, explicit update chains, precomputed date arithmetic), and three reader classes (gpt-4o, gpt-4.1, o4-mini). Not one beat the baseline. The two arms that moved measurably moved *down*, and §4 traces both regressions to specific defects we then rejected; every configuration without a diagnosed defect landed within ±4 net flips, the best at +3 (p = 0.69). Coverage went from 86.6% to 95.3% and the score stayed put.

**What this means.** Under this frozen protocol, the reader is the binding constraint, not the memory system. Once the evidence is in the pack, the residue of errors belongs to the questions and the protocol: stale-value selection already at its floor (§5), date arithmetic the reader fumbles even when handed precomputed deltas, counting and aggregation slips, genuinely ambiguous gold answers, and judge strictness. Per-question forensics on the remaining knowledge-update misses showed the interfering stale values sitting outside any fact line a pack could carry. A coverage-saturated system gains nothing from further retrieval spend — that is now a measurement, not an assumption, and it is why we stopped paying for runs rather than continuing to tune toward the judge.

## 4. Negative results

Each of these cost real money and produced a mechanism, not just a delta. They are first-class findings in the [honesty kit](../benchmarks/longmemeval/HONESTY-KIT.md); we summarize and add what we shipped instead.

### 4.1 LLM listwise reranking is recency-blind

A disclosed reranker stage (provider-scored listwise precision over the fused candidate head, reorder-only, fail-open) measured **−11 net** on the slice, with knowledge-update taking −8 and the arm's stale-pick rate (§5) hitting 31.3% against 12.5% for the identical configuration without the reranker. The mechanism is plain in the per-question rows: a listwise relevance scorer ranks by topical match, and a superseded value matches the question exactly as well as its replacement — often better, since older statements tend to be phrased more declaratively. The reranker systematically promoted stale values over updated ones. Fusion with recency and supersession signals had already settled those battles; the reranker re-litigated and lost them. What we shipped instead: the stage remains in the product as a dormant, disclosed, fail-open seam, and the design guidance is that any reranker in a memory read path must be currency-aware and deterministic — topical relevance alone is disqualifying.

### 4.2 Single-threshold semantic clustering produces grab-bag cards — and the review gate caught all of it

Consolidation roll-up cards (pre-aggregated same-topic summaries with per-instance provenance) were clustered by single-linkage embedding similarity over one global threshold (a 0.60 cosine floor, validated only on keyless fixtures). On real embeddings at store scale, that threshold produced 22–40-instance grab-bag cards — "kitchen" cards absorbing unrelated errands. Force-accepting them through a disclosed harness step and rendering them into packs measured **−14 net**, the campaign's worst arm; forensics found grab-bag cards in 11 of the 16 losing packs examined. Two lessons. First, the engineering one: embedding-gated features must be validated at scale with real or mock vectors, not fixture trios, and cluster membership needs typed, slot-aware rules (latest-value, tally, timeline — cards whose counts are correct by construction), not one global similarity threshold. Second, the architectural one: when we ran the same proposals through the product's actual review path instead of force-accepting them, **the gate rejected all 1,376 junk cards through the ordinary review verb**. No migration, no manual surgery. The review boundary — the thing that looks like friction in a demo — is precisely what kept a bad consolidation pass from becoming durable truth.

### 4.3 Reasoning readers over-answer

The o4-mini arm read the exact packs the published configuration produced (frozen, byte-identical) and landed at **+2 net** — parity, with the best preference score of any arm (86.7%) — but abstention fell from 22/30 to 17/30, and knowledge-update lost 5. The published run had already paid 25/30 → 22/30 for chain-of-thought reading; a dedicated reasoning model doubles down on the same failure. The pattern, visible in its transcripts: more reasoning over a rich history manufactures more justification for answering questions the memory does not actually support. The model talks itself into an answer. To our knowledge this behavior — reasoning capability trading directly against abstention honesty on memory tasks — is under-reported, and it matters for anyone planning to bolt a reasoning model onto a memory system. Abstention needs pack-side evidence signals (Alice's packs state "no stored memories mention X" when that is true) and disclosed verification gates; it does not come free with more thinking.

### 4.4 Retrieval spend past saturation buys nothing

Stated once more as its own result, because it is the expensive one: coverage 86.6% → 95.3%, eight arms, three reader classes, and the best any arm gained was +3 net flips (p = 0.69) — statistically nothing. If your evidence coverage is measured and high, the next benchmark point is not in retrieval. Measure coverage before buying more of it.

## 5. Protocol sensitivity, and a judge-free metric

### Three grading regimes, same 500 answers

We replayed the published run's cached answers — no new generation — through three grading regimes ([rejudge-gpt41.json](../benchmarks/longmemeval/saturation-evidence/rejudge-gpt41.json), [rejudge-generic.json](../benchmarks/longmemeval/saturation-evidence/rejudge-generic.json); the replay costs under a dollar):

| Grading protocol | Score | Flips vs official |
|---|---|---|
| Official: `gpt-4o-2024-08-06`, the benchmark's question-specific prompts | **79.4%** (397/500) | — |
| Grader-model swap: GPT-4.1, official prompts | 76.8% (384/500) | +1 / −14 |
| Generic lenient prompt ("conveys the right information"), GPT-4.1 | 79.2% (396/500) | +13 / −14 |

Two findings. First, these answers are protocol-robust: a 2.6-point band across graders and prompts. Answers grounded in retrieved evidence barely care who grades them. Second, the official prompts are not the lenient option — swapping in a newer grader under the official prompts moved the score *down*.

What "incomparable" means, precisely, and in both directions: a score produced under a different judge model, different prompts, a different dataset revision, or undisclosed answer selection cannot be ranked against a score produced under the official protocol — not above it, and not below it. Our own table shows grading choices alone are worth 2.6 points on fixed answers; nothing in our evidence licenses reading a higher or lower number produced under a different protocol as a better or worse memory system. This cuts against us exactly as it cuts for us: if you cannot replay a system's per-question rows under the official judge, the honest statement is "conditions differ," full stop. That is why every number in this report ships with its evidence file, and why we do not name or rank other systems anywhere in it.

### The stale-pick metric

Judges cost money and add a variable. For the dominant measured failure mode on knowledge-update questions — answering with a superseded value even when both values were retrieved — we built a metric that needs neither: [`stale_pick.py`](../../eval/longmemeval/stale_pick.py) extracts each question's update chain from the dataset's own labels and classifies any run checkpoint's answers as gold-value, stale-value, or other, deterministically, offline. Validation against the official judge: on the two full published runs its gold/not-gold split agrees with the judge on 94.9% and 96.6% of classified questions, and across all eight runs we replayed, **zero** answers classified stale-value were judged correct.

| Run | Stale-pick rate |
|---|---|
| 2026-07-05 baseline (64.6%) | 15.3% |
| 2026-07-07 published (79.4%) | **3.4%** |
| round-5 arms (−14 / −11 / 0 / +3) | 25.0% / 31.3% / 12.5% / 12.5% |

([Committed baseline table](../benchmarks/longmemeval/stale-pick-baseline-2026-07-10.json); the replay command is in the honesty kit and re-derives it byte-identically from in-repo files.) The published run sits at the metric's floor, which is the quantitative form of "currency and supersession are working"; and the metric flagged the reranker's stale-value promotion without any judge in the loop. We publish it as the free regression signal for any future currency work — ours or anyone's.

## 6. What this architecture is for

The saturation result reframes the architecture question. If retrieval quality past a threshold stops buying benchmark points, why build a review gate, provenance chains, typed supersession? Because the failure mode that matters in deployment is not a missed recall — it is a wrong write that gets trusted later.

The memory-poisoning literature converges on a small set of attack shapes: injection through ordinary queries that induce the agent to store attacker-chosen "facts"; sleeper entries that lie dormant until a trigger query activates them; and writes smuggled through summarization or compaction channels that no one inspects. The common structure is an unguarded write path into durable memory plus reads that cannot be traced. The defense the same literature converges on is exactly two things: **gate the writes, keep the provenance.**

Alice is that defense by construction rather than by add-on:

- **Nothing auto-promotes.** Agent writes are policy-checked commits or reviewable proposals; consolidation acceptance and redaction require human or admin policy; per-agent API keys carry scopes that may narrow but never widen.
- **Every memory can explain itself.** Provenance links run from a memory to source evidence, reviews, and corrections; a reader can ask why the system believes something and get a chain, not a shrug.
- **Correction is first-class.** Supersession stamps validity windows; packs label current versus superseded values; redaction truly expunges content while preserving the audit skeleton.
- The 1,376-card rejection in §4.2 is the gate demonstrated empirically — against a self-inflicted flood of machine-generated junk rather than an adversary, but the mechanism that contained it is the one the poisoning literature calls for.

For completeness, the substrate the benchmark numbers ride on: an MCP server exposing eleven core tools, SQLite as the on-ramp and Postgres (with row-level security) as the scale path; hybrid retrieval — full-text, vector, and entity-graph stages fused by reciprocal-rank fusion under content-stable deterministic tie-breaks; packs that carry temporal anchors with precomputed date arithmetic, same-slot currency chains labeling current versus superseded values, an aggregation coverage mode for count/list-shaped queries, and entity-grounding notes stating when the store holds nothing about a queried entity; and a fingerprint-disclosed benchmark configuration on every run.

The efficiency profile makes the trust properties affordable. The published run read a mean of ~6,000 tokens of context per answer (measured per-question in the [committed rows](../benchmarks/longmemeval/per-question-results-2026-07-07.jsonl)) against haystacks that run to roughly 115k tokens if read whole — the memory system's job is to make the reader cheap, and grounding it in fewer, provenance-bearing tokens is also what makes its answers auditable. Writes are flat: ~2.3ms per memory commit on SQLite from 1k through 100k stored memories ([scale envelope](../benchmarks/scale/README.md) — a benchmark that caught and fixed a 300× O(N) scan in the process). And retrieval is deterministic under re-ingest: content-stable tie-breaking took two-seed pack divergence from 7/40 to 0/40, so ingesting the same content twice produces byte-identical packs.

## 7. Reproduction

Everything in this report replays. The free parts need no API key: the stale-pick table, the coverage probes, and every paired comparison re-derive from committed files, byte-identically. The full run reproduces for roughly $15 of API spend and a few hours of wall clock:

```bash
python eval/longmemeval/fetch.py --variant s   # hash-verified dataset fetch
export ALICE_LME_MODEL_BASE_URL=https://api.openai.com/v1 \
       ALICE_LME_MODEL=gpt-4o \
       ALICE_LME_MODEL_API_KEY=... \
       ALICE_LME_JUDGE_MODEL=gpt-4o-2024-08-06 \
       ALICE_EMBEDDINGS_BASE_URL=https://api.openai.com/v1 \
       ALICE_EMBEDDINGS_MODEL=text-embedding-3-small \
       ALICE_EMBEDDINGS_API_KEY=...
python scripts/run_longmemeval.py --variant s --workers 3 --resume \
       --cot --max-items 16 --context-char-budget 24000
python eval/longmemeval/compare_runs.py BASELINE.jsonl CANDIDATE.jsonl
```

Slice arms cost ~$2–3 each; `--reuse-stores` reuses embedded stores across arms so iteration does not re-pay ingest; the grading-regime replay costs under $1. The standing commitments from the [honesty kit](../benchmarks/longmemeval/HONESTY-KIT.md) apply to this report: evidence files are append-only, judge and reading templates stay byte-frozen, config widenings are disclosed in run fingerprints, and negative results stay published. If a future run cannot honor those, it does not get published.

## 8. Limitations

- **The headline is a single run.** The prior configuration's three-run variance band was 63.0–64.6, so single-run deltas under ~2 points are noise. The paired +74 (p = 3.26e-12) is far outside that band, but 79.4% itself has not yet been replicated; a confirmation run is the one paid item still budgeted.
- **Multi-session synthesis is the weakest category: 58.6%** on the published run. The saturation arms moved it at most +5 net flips under the published reader (vectors-only) and +7 under a gpt-4.1 reader — suggestive of headroom, demonstrated nowhere near full scale. It remains the top roadmap item.
- **The benchmark measures QA-recall, not longitudinal behavior.** LongMemEval asks questions about synthetic histories. It does not exercise what Alice is mostly built for — resuming interrupted work, honoring past decisions, tracking open loops, surviving corrections — and it grants no credit for review governance or provenance. Behavioral, multi-week benchmarks are the gap; our scores here should be read as "the recall substrate works," not "the product is validated."
- **The ceiling analysis is protocol-specific.** With coverage at 95.3% and the stale-pick rate at its floor, the residual misses concentrate in reader arithmetic, counting, ambiguous golds, and judge strictness. We do not claim 79.4% is a hard ceiling for this architecture; we claim the marginal return on retrieval spend under this frozen protocol measured zero, and we stopped there rather than tune toward the judge.

The evidence directory for everything above is [docs/benchmarks/longmemeval/](../benchmarks/longmemeval/); the audit companion is the [honesty kit](../benchmarks/longmemeval/HONESTY-KIT.md). If a claim in this report cannot be traced to a committed file, treat it as unproven.
