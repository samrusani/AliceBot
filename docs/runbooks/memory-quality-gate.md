# Memory Quality Gate Runbook

## Objective
Use `/memories` to read a deterministic ship-gate signal for memory quality before broader MVP testing.

## Source Of Truth
- Endpoint: `GET /v0/memories/evaluation-summary`
- Queue endpoint: `GET /v0/memories/review-queue`
- Label endpoint: `POST /v0/memories/{memory_id}/labels`
- Gate computes from summary counts only:
  - `correct = label_row_counts_by_value.correct`
  - `incorrect = label_row_counts_by_value.incorrect`
  - `unlabeled = unlabeled_memory_count`

## Gate Math
- `precision = correct / (correct + incorrect)` (undefined when denominator is `0`)
- `adjudicated_sample = correct + incorrect`
- `remaining_to_minimum_sample = max(0, 10 - adjudicated_sample)`
- Precision target: `>= 0.80`
- Minimum adjudicated sample: `>= 10`

## Gate States
- `on_track`: precision `>= 0.80` and adjudicated sample `>= 10`
- `needs_review`: precision `< 0.80` and adjudicated sample `>= 10`
- `insufficient_evidence`: adjudicated sample `< 10`
- `unavailable data`: evaluation summary not available for computation

## Posture Readouts
- Sample posture:
  - enough sample when adjudicated sample `>= 10`
  - insufficient sample when adjudicated sample `< 10`
- Queue posture:
  - queue clear when `unlabeled_memory_count = 0`
  - backlog present when `unlabeled_memory_count > 0`

## Manual Verification On `/memories`
1. Open `/memories`.
2. In `Memory summary`, locate `Memory-quality gate`.
3. Confirm the card shows:
   - precision percent
   - adjudicated sample count
   - remaining labels to minimum sample
   - unlabeled queue count
   - gate status badge
4. Confirm source badges (`Summary` and `Queue`) are explicit (`Live`, `Fixture`, or `Unavailable`).
5. Verify interpretation copy matches the displayed gate status and counts.

## Queue Adjudication Workflow
1. Open `/memories?filter=queue`.
2. Select the current queue item.
3. Choose one review label and optional note.
4. Use `Submit review label` to save and stay on the same memory.
5. Use `Submit and next in queue` to save and advance to the next visible queue item in current list order.
6. Continue until the queue clears or minimum sample is reached.

## Stop Conditions
- Stop when `remaining_to_minimum_sample = 0` and gate status is `on_track` or `needs_review`.
- Stop when queue is clear (`unlabeled_memory_count = 0`) and escalate if minimum sample is still not met.
- Stop and fix source/config first when summary or queue source is unavailable.

## Notes For MVP Testing
- Treat `on_track` as readiness signal for memory quality sampling.
- Treat `needs_review` and `insufficient_evidence` as stop-and-investigate states before ship decisions.
- If data is unavailable, fix source availability first; do not infer readiness from stale assumptions.
