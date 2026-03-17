import { PageHeader } from "../../components/page-header";
import { RequestComposer, type RequestHistoryEntry } from "../../components/request-composer";
import { SectionCard } from "../../components/section-card";

const initialEntries: RequestHistoryEntry[] = [
  {
    id: "req-001",
    request: "Summarize the open magnesium reorder task and tell me whether an approval is still required.",
    response:
      "The current task remains in a governed state. The latest task step is waiting on approval resolution before any execution can proceed, and the next operator action is to review the approval inbox rather than trigger another tool call.",
    submittedAt: "2026-03-17T08:45:00Z",
    source: "fixture",
    trace: {
      compileTraceId: "trace-ctx-401",
      compileTraceEventCount: 9,
      responseTraceId: "trace-resp-402",
      responseTraceEventCount: 4,
    },
  },
];

function getApiConfig() {
  return {
    apiBaseUrl:
      process.env.NEXT_PUBLIC_ALICEBOT_API_BASE_URL ?? process.env.ALICEBOT_API_BASE_URL ?? "",
    userId: process.env.NEXT_PUBLIC_ALICEBOT_USER_ID ?? process.env.ALICEBOT_USER_ID ?? "",
    threadId: process.env.NEXT_PUBLIC_ALICEBOT_THREAD_ID ?? process.env.ALICEBOT_THREAD_ID ?? "",
  };
}

export default function ChatPage() {
  const apiConfig = getApiConfig();
  const liveModeReady = Boolean(apiConfig.apiBaseUrl && apiConfig.userId && apiConfig.threadId);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Governed request path"
        title="Operator request surface"
        description="This is a review-oriented request composer, not a consumer chat skin. Compose bounded prompts, keep governance context visible, and inspect recent response traces."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{liveModeReady ? "Live API mode" : "Fixture mode"}</span>
            <span className="subtle-chip">Response traces visible</span>
          </div>
        }
      />

      <div className="content-grid content-grid--wide">
        <RequestComposer initialEntries={initialEntries} {...apiConfig} />

        <div className="stack">
          <SectionCard
            eyebrow="Framing"
            title="Governed request rules"
            description="The request surface keeps operational intent explicit and bounded."
          >
            <ul className="bullet-list">
              <li>Requests are framed as operator instructions against existing governed seams.</li>
              <li>Live mode posts to the shipped response endpoint only when API configuration is present.</li>
              <li>Trace references stay attached to each recent response so explainability remains first-class.</li>
            </ul>
          </SectionCard>

          <SectionCard
            eyebrow="Compile defaults"
            title="Context limits"
            description="The current UI reflects the backend’s bounded compilation model rather than inventing broader retrieval behavior."
          >
            <dl className="key-value-grid">
              <div>
                <dt>Sessions</dt>
                <dd>Up to 8 recent sessions</dd>
              </div>
              <div>
                <dt>Events</dt>
                <dd>Up to 80 continuity events</dd>
              </div>
              <div>
                <dt>Memories</dt>
                <dd>Up to 20 admitted memories</dd>
              </div>
              <div>
                <dt>Entities</dt>
                <dd>Up to 12 entities and 20 edges</dd>
              </div>
            </dl>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
