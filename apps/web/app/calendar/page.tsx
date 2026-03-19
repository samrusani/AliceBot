import { CalendarAccountConnectForm } from "../../components/calendar-account-connect-form";
import { CalendarAccountDetail } from "../../components/calendar-account-detail";
import { CalendarAccountList } from "../../components/calendar-account-list";
import { CalendarEventIngestForm } from "../../components/calendar-event-ingest-form";
import { PageHeader } from "../../components/page-header";
import type { ApiSource, CalendarAccountListSummary, CalendarAccountRecord } from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getCalendarAccountDetail,
  hasLiveApiConfig,
  listCalendarAccounts,
  listTaskWorkspaces,
  pageModeLabel,
} from "../../lib/api";
import {
  calendarAccountFixtures,
  calendarAccountListSummaryFixture,
  getFixtureCalendarAccount,
  taskWorkspaceFixtures,
  taskWorkspaceListSummaryFixture,
} from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }

  return value?.trim() ?? "";
}

function resolveSelectedAccountId(requestedAccountId: string, items: CalendarAccountRecord[]) {
  if (!items.length) {
    return "";
  }

  const availableIds = new Set(items.map((item) => item.id));
  if (requestedAccountId && availableIds.has(requestedAccountId)) {
    return requestedAccountId;
  }

  return items[0]?.id ?? "";
}

export default async function CalendarPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const requestedAccountId = normalizeParam(params.account);
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let accounts = calendarAccountFixtures;
  let accountListSummary: CalendarAccountListSummary | null = calendarAccountListSummaryFixture;
  let accountListSource: ApiSource | "unavailable" = "fixture";
  let accountListUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await listCalendarAccounts(apiConfig.apiBaseUrl, apiConfig.userId);
      accounts = payload.items;
      accountListSummary = payload.summary;
      accountListSource = "live";
    } catch (error) {
      accountListUnavailableReason =
        error instanceof Error ? error.message : "Calendar account list could not be loaded.";
      if (!calendarAccountFixtures.length) {
        accounts = [];
        accountListSummary = null;
        accountListSource = "unavailable";
      }
    }
  }

  const selectedAccountId = resolveSelectedAccountId(requestedAccountId, accounts);
  const selectedFromList = accounts.find((item) => item.id === selectedAccountId) ?? null;

  let selectedAccount = selectedFromList;
  let selectedAccountSource: ApiSource | "unavailable" | null =
    selectedAccount && accountListSource !== "unavailable" ? accountListSource : null;
  let selectedAccountUnavailableReason: string | undefined;

  if (selectedFromList && liveModeReady && accountListSource === "live") {
    try {
      const payload = await getCalendarAccountDetail(
        apiConfig.apiBaseUrl,
        selectedFromList.id,
        apiConfig.userId,
      );
      selectedAccount = payload.account;
      selectedAccountSource = "live";
    } catch (error) {
      const fixtureAccount = getFixtureCalendarAccount(selectedFromList.id);
      if (fixtureAccount) {
        selectedAccount = fixtureAccount;
        selectedAccountSource = "fixture";
      } else {
        selectedAccountSource = "unavailable";
      }
      selectedAccountUnavailableReason =
        error instanceof Error ? error.message : "Selected Calendar account detail could not be loaded.";
    }
  }

  let taskWorkspaces = taskWorkspaceFixtures;
  let taskWorkspaceSummary = taskWorkspaceListSummaryFixture;
  let taskWorkspaceSource: ApiSource | "unavailable" = "fixture";
  let taskWorkspaceUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await listTaskWorkspaces(apiConfig.apiBaseUrl, apiConfig.userId);
      taskWorkspaces = payload.items;
      taskWorkspaceSummary = payload.summary;
      taskWorkspaceSource = "live";
    } catch (error) {
      taskWorkspaceUnavailableReason =
        error instanceof Error ? error.message : "Task workspace list could not be loaded.";
      if (!taskWorkspaceFixtures.length) {
        taskWorkspaceSource = "unavailable";
      }
    }
  }

  const pageMode = combinePageModes(
    accountListSource === "unavailable" ? null : accountListSource,
    selectedAccountSource === "unavailable" ? null : selectedAccountSource,
    taskWorkspaceSource === "unavailable" ? null : taskWorkspaceSource,
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Calendar"
        title="Calendar account review workspace"
        description="Review connected accounts first, inspect one selected account second, then run explicit connect or single-event ingestion actions."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(pageMode)}</span>
            <span className="subtle-chip">{accounts.length} visible accounts</span>
            <span className="subtle-chip">{taskWorkspaceSummary.total_count} task workspaces</span>
            {selectedAccount ? (
              <span className="subtle-chip">Selected: {selectedAccount.email_address}</span>
            ) : null}
          </div>
        }
      />

      <div className="calendar-layout">
        <CalendarAccountList
          accounts={accounts}
          selectedAccountId={selectedAccount?.id}
          summary={accountListSummary}
          source={accountListSource}
          unavailableReason={accountListUnavailableReason}
        />
        <CalendarAccountDetail
          account={selectedAccount}
          source={selectedAccountSource}
          unavailableReason={selectedAccountUnavailableReason}
        />
      </div>

      <div className="calendar-action-grid">
        <CalendarAccountConnectForm
          apiBaseUrl={apiConfig.apiBaseUrl}
          userId={apiConfig.userId}
        />
        <CalendarEventIngestForm
          account={selectedAccount}
          accountSource={selectedAccountSource}
          taskWorkspaces={taskWorkspaces}
          taskWorkspaceSource={taskWorkspaceSource}
          apiBaseUrl={apiConfig.apiBaseUrl}
          userId={apiConfig.userId}
        />
      </div>

      {taskWorkspaceUnavailableReason ? (
        <p className="responsive-note">Live task workspace list read failed: {taskWorkspaceUnavailableReason}</p>
      ) : null}
    </div>
  );
}
