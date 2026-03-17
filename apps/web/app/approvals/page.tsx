import { ApprovalDetail } from "../../components/approval-detail";
import { ApprovalList } from "../../components/approval-list";
import { PageHeader } from "../../components/page-header";
import {
  combinePageModes,
  getApiConfig,
  getApprovalDetail,
  hasLiveApiConfig,
  listApprovals,
  pageModeLabel,
  type ApiSource,
} from "../../lib/api";
import { approvalFixtures, getFixtureApproval } from "../../lib/fixtures";

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

  const pageMode = combinePageModes(listSource, detail ? detailSource : null);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Approvals"
        title="Approval inbox and review"
        description="Review consequential actions with one stable split layout: queue on the left, rationale and request detail on the right, with explicit approve and reject controls."
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
          apiBaseUrl={apiConfig.apiBaseUrl}
          userId={apiConfig.userId}
        />
      </div>
    </div>
  );
}
