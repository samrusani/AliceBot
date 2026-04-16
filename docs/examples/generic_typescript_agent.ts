type AgentView = {
  brief_type: string | null;
  summary: string | null;
  next_suggested_action: string | null;
  open_loop_count: number | null;
  source_kinds: string[];
  open_conflict_count: number | null;
};

function envOrDefault(name: string, fallback: string): string {
  const value = process.env[name];
  return value && value.trim() !== "" ? value : fallback;
}

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value || value.trim() === "") {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function compactAgentView(payload: Record<string, any>): AgentView {
  const brief = (payload.brief ?? {}) as Record<string, any>;
  const nextAction = (brief.next_suggested_action ?? {}) as Record<string, any>;
  const openLoops = (brief.open_loops ?? {}) as Record<string, any>;
  const openLoopSummary = (openLoops.summary ?? {}) as Record<string, any>;
  const trustPosture = (brief.trust_posture ?? {}) as Record<string, any>;
  const sourceKinds = Array.isArray(brief.sources)
    ? brief.sources.filter((value): value is string => typeof value === "string")
    : [];

  return {
    brief_type: typeof brief.brief_type === "string" ? brief.brief_type : null,
    summary: typeof brief.summary === "string" ? brief.summary : null,
    next_suggested_action:
      typeof nextAction.title === "string" ? nextAction.title : null,
    open_loop_count:
      typeof openLoopSummary.total_count === "number" ? openLoopSummary.total_count : null,
    source_kinds: sourceKinds,
    open_conflict_count:
      typeof trustPosture.open_conflict_count === "number"
        ? trustPosture.open_conflict_count
        : null,
  };
}

async function main(): Promise<number> {
  const apiBaseUrl = envOrDefault("ALICE_API_BASE_URL", "http://127.0.0.1:8000");
  const sessionToken = requiredEnv("ALICE_SESSION_TOKEN");
  const briefType = envOrDefault("ALICE_BRIEF_TYPE", "agent_handoff");
  const threadId = process.env.ALICE_THREAD_ID;
  const query = envOrDefault("ALICE_QUERY", "release handoff");

  const body: Record<string, unknown> = {
    brief_type: briefType,
    query,
    max_relevant_facts: 6,
    max_recent_changes: 5,
    max_open_loops: 5,
    max_conflicts: 3,
    max_timeline_highlights: 5,
  };
  if (threadId && threadId.trim() !== "") {
    body.thread_id = threadId;
  }

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/v1/continuity/brief`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${sessionToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Alice returned HTTP ${response.status}: ${detail}`);
  }

  const payload = (await response.json()) as Record<string, any>;
  const result = compactAgentView(payload);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  return 0;
}

main()
  .then((exitCode) => {
    process.exitCode = exitCode;
  })
  .catch((error: unknown) => {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`${message}\n`);
    process.exitCode = 1;
  });
