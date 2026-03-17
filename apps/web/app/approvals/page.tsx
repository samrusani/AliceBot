import { ApprovalDetail } from "../../components/approval-detail";
import { ApprovalList } from "../../components/approval-list";
import { PageHeader } from "../../components/page-header";
import {
  combinePageModes,
  getToolExecution,
  getApiConfig,
  getApprovalDetail,
  hasLiveApiConfig,
  listToolExecutions,
  listApprovals,
  pageModeLabel,
  type ApiSource,
} from "../../lib/api";
import { approvalFixtures, getFixtureApproval, getFixtureExecutionByApprovalId } from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function ApprovalsPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const selectedId = typeof params.approval === "string" ? params.approval : undefined;
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let items = approvalFixtures;
  let listSource: ApiSource = "fixture";

  if (liveModeReady) {
    try {
      const payload = await listApprovals(apiConfig.apiBaseUrl, apiConfig.userId);
      items = payload.items;
      listSource = "live";
    } catch {
      items = approvalFixtures;
      listSource = "fixture";
    }
  }

  const selected = items.find((item) => item.id === selectedId) ?? items[0] ?? null;
  let detail = selected;
  let detailSource: ApiSource = selected ? listSource : "fixture";

  if (selected && liveModeReady && listSource === "live") {
    try {
      const payload = await getApprovalDetail(apiConfig.apiBaseUrl, selected.id, apiConfig.userId);
      detail = payload.approval;
      detailSource = "live";
    } catch {
      detail = getFixtureApproval(selected.id) ?? selected;
      detailSource = detail === selected ? "live" : "fixture";
    }
  }

  let execution = detail ? getFixtureExecutionByApprovalId(detail.id) : null;
  let executionSource: ApiSource | null = execution ? "fixture" : null;
  let executionUnavailableMessage: string | null = null;

  if (detail && liveModeReady && detailSource === "live") {
    try {
      const payload = await listToolExecutions(apiConfig.apiBaseUrl, apiConfig.userId);
      const linked = payload.items.find((item) => item.approval_id === detail.id) ?? null;

      if (linked) {
        try {
          const detailPayload = await getToolExecution(apiConfig.apiBaseUrl, linked.id, apiConfig.userId);
          execution = detailPayload.execution;
          executionSource = "live";
        } catch {
          execution = linked;
          executionSource = "live";
        }
      } else {
        execution = null;
        executionSource = null;
      }
    } catch {
      if (detail.status === "approved") {
        execution = null;
        executionSource = null;
        executionUnavailableMessage =
          "The linked execution review could not be loaded from the configured backend.";
      }
    }
  }

  const pageMode = combinePageModes(
    listSource,
    detail ? detailSource : null,
    execution ? executionSource : null,
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Approvals"
        title="Approval inbox and review"
        description="Review consequential actions in one calm split layout, then execute approved requests and inspect the resulting execution state without leaving the shell."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(pageMode)}</span>
            <span className="subtle-chip">{items.length} items</span>
          </div>
        }
      />

      <div className="split-layout">
        <ApprovalList items={items} selectedId={selected?.id} />
        <ApprovalDetail
          initialApproval={detail}
          detailSource={detailSource}
          initialExecution={execution}
          executionSource={executionSource}
          executionUnavailableMessage={executionUnavailableMessage}
          apiBaseUrl={apiConfig.apiBaseUrl}
          userId={apiConfig.userId}
        />
      </div>
    </div>
  );
}
