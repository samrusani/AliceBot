import { ModeToggle, type ChatMode } from "../../components/mode-toggle";
import { PageHeader } from "../../components/page-header";
import { RequestComposer } from "../../components/request-composer";
import { ResponseComposer } from "../../components/response-composer";
import { SectionCard } from "../../components/section-card";
import { getApiConfig, hasLiveApiConfig } from "../../lib/api";
import { requestHistoryFixtures, responseHistoryFixtures } from "../../lib/fixtures";

type ChatPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function normalizeMode(value: string | string[] | undefined): ChatMode {
  if (Array.isArray(value)) {
    return normalizeMode(value[0]);
  }

  return value === "request" ? "request" : "assistant";
}

export default async function ChatPage({ searchParams }: ChatPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const mode = normalizeMode(resolvedSearchParams?.mode);
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);
  const initialResponseEntries = liveModeReady ? [] : responseHistoryFixtures;
  const initialRequestEntries = liveModeReady ? [] : requestHistoryFixtures;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operator conversation surface"
        title="Chat with the assistant or route a governed request"
        description="Normal conversation and approval-gated actions now share one calm shell, but the two behaviors stay visibly separate so consequential work never hides inside a chat transcript."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{liveModeReady ? "Live submission enabled" : "Fixture preview mode"}</span>
            <span className="subtle-chip">Responses and approvals stay explicit</span>
          </div>
        }
      />

      <ModeToggle currentMode={mode} />

      <div className="content-grid content-grid--wide">
        {mode === "assistant" ? (
          <ResponseComposer
            initialEntries={initialResponseEntries}
            apiBaseUrl={apiConfig.apiBaseUrl}
            userId={apiConfig.userId}
            defaultThreadId={apiConfig.defaultThreadId}
          />
        ) : (
          <RequestComposer initialEntries={initialRequestEntries} {...apiConfig} />
        )}

        <div className="stack">
          {mode === "assistant" ? (
            <>
              <SectionCard
                eyebrow="Assistant mode"
                title="Normal conversation first"
                description="This mode stays for analysis, summaries, and question answering without implying approval-gated execution."
              >
                <ul className="bullet-list">
                  <li>Questions are submitted directly to `POST /v0/responses` with only the shipped user, thread, and message fields.</li>
                  <li>The operator still provides thread identity explicitly instead of relying on hidden routing or auto-selected context.</li>
                  <li>Each reply keeps compile and response trace summaries attached so explainability remains one click away.</li>
                </ul>
              </SectionCard>

              <SectionCard
                eyebrow="Mode boundary"
                title="What stays out of assistant mode"
                description="Consequential work remains visibly separated from normal conversation to preserve trust and reviewability."
              >
                <dl className="key-value-grid">
                  <div>
                    <dt>Assistant mode</dt>
                    <dd>Answer questions, summarize state, and explain prior work without submitting an approval request.</dd>
                  </div>
                  <div>
                    <dt>Governed mode</dt>
                    <dd>Submit action-oriented payloads that can create approval and task records through the shipped request seam.</dd>
                  </div>
                  <div>
                    <dt>Fallback</dt>
                    <dd>Fixture previews stay explicit when live API configuration is absent instead of failing silently.</dd>
                  </div>
                  <div>
                    <dt>Trace review</dt>
                    <dd>Compile and response trace IDs remain linked from each reply so the operator can inspect why the answer was produced.</dd>
                  </div>
                </dl>
              </SectionCard>
            </>
          ) : (
            <>
              <SectionCard
                eyebrow="Governed mode"
                title="Consequential actions remain reviewable"
                description="The request surface keeps operational intent explicit and bounded instead of blurring it into casual conversation."
              >
                <ul className="bullet-list">
                  <li>Requests are submitted directly to `POST /v0/approvals/requests` using shipped payload fields only.</li>
                  <li>The operator supplies thread and tool identifiers explicitly instead of relying on hidden web-side routing.</li>
                  <li>Every resulting summary keeps decision, approval linkage, task status, and trace references visible.</li>
                </ul>
              </SectionCard>

              <SectionCard
                eyebrow="Request schema"
                title="Submission fields"
                description="The governed path stays narrow on purpose so approvals and downstream task state remain deterministic."
              >
                <dl className="key-value-grid">
                  <div>
                    <dt>Required</dt>
                    <dd>Thread ID, tool ID, action, scope</dd>
                  </div>
                  <div>
                    <dt>Optional</dt>
                    <dd>Domain hint, risk hint</dd>
                  </div>
                  <div>
                    <dt>Attributes</dt>
                    <dd>JSON object sent unchanged to the backend</dd>
                  </div>
                  <div>
                    <dt>Fallback</dt>
                    <dd>Fixture preview instead of broken live submission</dd>
                  </div>
                </dl>
              </SectionCard>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
