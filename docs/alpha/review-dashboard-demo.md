# Review Dashboard Demo

This is the bounded enterprise demo for the shipped review surfaces. It uses only
existing public HTTP operations and the existing web dashboard; it does not add a
demo-only route or mutation.

## Prerequisites

- Start Alice with PostgreSQL and the web app by following the [quickstart](quickstart.md).
- Keep the API on a loopback interface unless agent-key authentication and a TLS reverse proxy are configured.
- Set `ALICE_USER_ID` to the local Alice user UUID.
- Use one of exactly two authentication postures for this full sequence:
  - a fresh local-keyless user with **zero active agent keys**, leaving `ALICE_AGENT_API_KEY` unset; or
  - an active, **unbound `admin_agent`** key for that same user, exported as `ALICE_AGENT_API_KEY`.
    Create one without `--project-scope`, for example:
    `alicebot agent keys create --agent-id review-dashboard-operator --profile admin_agent --label "Review dashboard demo"`.
  Lower-privilege or project-bound keys cannot perform every review and redaction action below. Once any
  active key exists, omitting the Bearer header also fails closed.
- Set `ALICE_API_URL` to the API origin, normally `http://127.0.0.1:8000`.

The examples below use `jq`. Build the optional Authorization header once in an
owner-only temporary curl config. Curl receives only the config path in its
process arguments, never the raw key:

```bash
auth_config="$(mktemp "${TMPDIR:-/tmp}/alice-review-demo.XXXXXX")"
chmod 600 "$auth_config"
trap 'rm -f "$auth_config"' EXIT
: >"$auth_config"
if [ -n "${ALICE_AGENT_API_KEY:-}" ]; then
  printf 'header = "Authorization: Bearer %s"\n' "$ALICE_AGENT_API_KEY" >"$auth_config"
fi
auth_args=(--config "$auth_config")
```

Use synthetic text. Do not paste customer or production secrets into a demo.

## 1. Capture a source

```bash
sentinel="DASHBOARD-DEMO-$(date +%s)"
source_json="$({
  printf '{"user_id":"%s","raw_text":"Decision: %s is accepted only after operator review.","title":"Review dashboard demo","domain":"professional","sensitivity":"private"}' \
    "$ALICE_USER_ID" "$sentinel"
} | curl --fail-with-body --silent --show-error \
  "${auth_args[@]}" \
  -H 'Content-Type: application/json' \
  --data-binary @- \
  "$ALICE_API_URL/v0/vnext/sources")"
source_id="$(jq -er '.source_id' <<<"$source_json")"
```

Expected: HTTP 201, one source ID, and at least one candidate memory. Open
`/vnext` to show the review inbox; the source is captured, not accepted.

## 2. Review the source and identify its candidate

```bash
trace_json="$(curl --fail-with-body --silent --show-error \
  "${auth_args[@]}" \
  -H 'Content-Type: application/json' \
  --data "$(jq -cn --arg user_id "$ALICE_USER_ID" \
    '{user_id:$user_id,action:"review",review_note:"Reviewed in the enterprise demo."}')" \
  "$ALICE_API_URL/v0/vnext/sources/$source_id/review")"
memory_id="$(jq -er '.trace.candidate_memories[0].id' <<<"$trace_json")"
jq '{trace_kind:.trace.trace_kind, summary:.trace.summary, sampling:.trace.sampling}' <<<"$trace_json"
```

Expected: `capture_to_brief`, the same source ID, a non-zero candidate-memory
count, and `trace_complete: true` for this one-row demo. This is the trace embedded
in the mutating source-review response.

## 3. Accept the candidate

```bash
accept_json="$(curl --fail-with-body --silent --show-error \
  "${auth_args[@]}" \
  -H 'Content-Type: application/json' \
  --data "$(jq -cn --arg user_id "$ALICE_USER_ID" '{user_id:$user_id,action:"accept"}')" \
  "$ALICE_API_URL/v0/vnext/memories/$memory_id/review")"
jq '{id:.memory.id,status:.memory.status}' <<<"$accept_json"
```

Expected: the same memory ID with `status: active`.

- With an active key, open `/vnext`, enter the same unbound `admin_agent` key in
  **Unbound admin_agent API key**, and inspect the accepted row in **Memory Review**.
- Only in the zero-key local/demo posture may `/memories` and `/traces` be used as
  separate review surfaces. Those pages are server-rendered and cannot forward
  the `/vnext` browser-memory Bearer, so they must not be presented as live keyed
  evidence. Do not invent a `/traces` record linkage from this source trace.

## 4. Read the bounded source trace without another mutation

```bash
trace_json="$(curl --fail-with-body --silent --show-error \
  "${auth_args[@]}" \
  "$ALICE_API_URL/v0/vnext/traces/sources/$source_id?user_id=$ALICE_USER_ID")"
jq '{trace_kind,summary,sampling,events}' <<<"$trace_json"
```

Expected: the same `capture_to_brief` trace now includes the accepted memory and
its `review.item_accepted` event. This GET does not update source review metadata
or append another source-review event. Do not claim that this bounded source trace
is linked to one of the independently persisted records on `/traces` unless the
response supplies that UUID linkage.

## 5. Redact through the public API

The web dashboard deliberately has no redaction button. Redaction is a
human/admin-only lifecycle action and remains on the governed public API:

```bash
redact_json="$(curl --fail-with-body --silent --show-error \
  "${auth_args[@]}" \
  -H 'Content-Type: application/json' \
  --data "$(jq -cn --arg user_id "$ALICE_USER_ID" --arg memory_id "$memory_id" \
    '{user_id:$user_id,memory_id:$memory_id,reason:"Scripted enterprise demo cleanup."}')" \
  "$ALICE_API_URL/v0/vnext/memories/redact")"
jq '{status,forgotten_first,idempotent_replay,redaction_marker}' <<<"$redact_json"
```

Expected: `status: redacted` and `forgotten_first: true`. The automated
role-separated test below verifies the surviving audit skeleton and proves that
its governed memory, revision, and event content no longer contains the raw
sentinel. Memory redaction intentionally does not erase the separately governed
source or source chunks; archive/delete that source under the source retention
policy if source-evidence removal is also required.

## Automated proof

- `tests/integration/test_review_dashboard_demo.py` runs capture, source review,
  accept, read-only bounded-trace GET, and redaction in both zero-key and unbound
  `admin_agent` modes against a role-separated migrated PostgreSQL database. It
  proves the trace GET does not mutate source metadata/events, the audit skeleton
  survives, and the sentinel is absent from the governed memory graph.
- `apps/web/test/browser/review-dashboard-demo.spec.ts` proves fixture navigation
  is explicit, selected rows use `aria-current`, the dashboard does not advertise
  a linked trace it cannot prove, no web redaction control exists, and desktop and
  mobile layouts stay bounded.
