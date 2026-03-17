import { PageHeader } from "../../components/page-header";
import { RequestComposer } from "../../components/request-composer";
import { SectionCard } from "../../components/section-card";
import { getApiConfig, hasLiveApiConfig } from "../../lib/api";
import { requestHistoryFixtures } from "../../lib/fixtures";

export default function ChatPage() {
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Governed request path"
        title="Operator request surface"
        description="Submit governed requests through the shipped approval-request seam, keep the resulting approval and task linkage visible, and avoid inventing backend behavior in the UI."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{liveModeReady ? "Live submission enabled" : "Fixture preview mode"}</span>
            <span className="subtle-chip">Approval-request seam only</span>
          </div>
        }
      />

      <div className="content-grid content-grid--wide">
        <RequestComposer initialEntries={requestHistoryFixtures} {...apiConfig} />

        <div className="stack">
          <SectionCard
            eyebrow="Framing"
            title="Governed request rules"
            description="The request surface keeps operational intent explicit and bounded."
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
            description="The form stays narrow on purpose so the governed request path remains reviewable and deterministic."
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
        </div>
      </div>
    </div>
  );
}
