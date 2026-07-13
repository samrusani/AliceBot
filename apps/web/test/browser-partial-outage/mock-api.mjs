import { createServer } from "node:http";

const host = "127.0.0.1";
const port = 3199;
const objectId = "object-live-detail-outage";
const continuityObject = {
  id: objectId,
  capture_event_id: "capture-live-detail-outage",
  object_type: "Decision",
  status: "active",
  title: "Decision: Live queue target remains correction-ready",
  body: { decision_text: "Live queue target remains correction-ready" },
  provenance: { capture_event_id: "capture-live-detail-outage" },
  confidence: 0.9,
  last_confirmed_at: null,
  supersedes_object_id: null,
  superseded_by_object_id: null,
  created_at: "2026-07-13T10:00:00Z",
  updated_at: "2026-07-13T10:00:00Z",
};

function send(response, status, payload) {
  response.writeHead(status, {
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Origin": "*",
    "Content-Type": "application/json",
  });
  response.end(JSON.stringify(payload));
}

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", `http://${host}:${port}`);
  if (request.method === "OPTIONS") {
    send(response, 204, {});
    return;
  }
  if (request.method === "GET" && url.pathname === "/health") {
    send(response, 200, { status: "ok" });
    return;
  }
  if (request.method === "GET" && url.pathname === "/v0/continuity/review-queue") {
    send(response, 200, {
      items: [continuityObject],
      summary: {
        status: "correction_ready",
        limit: 20,
        returned_count: 1,
        total_count: 1,
        order: ["updated_at_desc", "created_at_desc", "id_desc"],
      },
    });
    return;
  }
  if (
    request.method === "GET" &&
    url.pathname === `/v0/continuity/review-queue/${objectId}`
  ) {
    send(response, 503, { detail: "detail history intentionally unavailable" });
    return;
  }
  if (
    request.method === "POST" &&
    url.pathname === `/v0/continuity/review-queue/${objectId}/corrections`
  ) {
    send(response, 200, {
      continuity_object: { ...continuityObject, last_confirmed_at: "2026-07-13T10:01:00Z" },
      correction_event: {
        id: "correction-live-detail-outage",
        continuity_object_id: objectId,
        action: "confirm",
        reason: "Queue-proven target",
        before_snapshot: {},
        after_snapshot: {},
        payload: {},
        created_at: "2026-07-13T10:01:00Z",
      },
      replacement_object: null,
    });
    return;
  }
  send(response, 503, { detail: "unrelated continuity read intentionally unavailable" });
});

server.listen(port, host);
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
