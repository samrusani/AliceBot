import { CalendarAccountConnectForm } from "../../components/calendar-account-connect-form";
import { CalendarAccountDetail } from "../../components/calendar-account-detail";
import { CalendarAccountList } from "../../components/calendar-account-list";
import { CalendarEventIngestForm } from "../../components/calendar-event-ingest-form";
import { CalendarEventList } from "../../components/calendar-event-list";
import { PageHeader } from "../../components/page-header";
import type {
  ApiSource,
  CalendarAccountListSummary,
  CalendarAccountRecord,
  CalendarEventListSummary,
  CalendarEventSummaryRecord,
} from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getCalendarAccountDetail,
  hasLiveApiConfig,
  listCalendarEvents,
  listCalendarAccounts,
  listTaskWorkspaces,
  pageModeLabel,
} from "../../lib/api";
import {
  calendarAccountFixtures,
  calendarAccountListSummaryFixture,
  getFixtureCalendarAccount,
  getFixtureCalendarEventList,
  taskWorkspaceFixtures,
  taskWorkspaceListSummaryFixture,
} from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const DEFAULT_CALENDAR_EVENT_LIMIT = 20;
const MAX_CALENDAR_EVENT_LIMIT = 50;

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

function resolveSelectedEventId(requestedEventId: string, items: CalendarEventSummaryRecord[]) {
  if (!items.length) {
    return "";
  }

  const availableIds = new Set(items.map((item) => item.provider_event_id));
  if (requestedEventId && availableIds.has(requestedEventId)) {
    return requestedEventId;
  }

  return "";
}

function resolveDiscoveryLimit(rawLimit: string) {
  const parsed = Number.parseInt(rawLimit, 10);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_CALENDAR_EVENT_LIMIT;
  }

  return Math.max(1, Math.min(MAX_CALENDAR_EVENT_LIMIT, parsed));
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
  const requestedEventId = normalizeParam(params.event);
  const requestedEventLimit = resolveDiscoveryLimit(normalizeParam(params.limit));
  const requestedTimeMin = normalizeParam(params.time_min);
  const requestedTimeMax = normalizeParam(params.time_max);
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

  let discoveredEvents: CalendarEventSummaryRecord[] = [];
  let discoveredEventSummary: CalendarEventListSummary | null = null;
  let discoveredEventSource: ApiSource | "unavailable" | null = null;
  let discoveredEventUnavailableReason: string | undefined;

  if (selectedAccount) {
    const fixturePayload = getFixtureCalendarEventList(selectedAccount.id, {
      limit: requestedEventLimit,
      timeMin: requestedTimeMin,
      timeMax: requestedTimeMax,
    });
    discoveredEvents = fixturePayload.items;
    discoveredEventSummary = fixturePayload.summary;
    discoveredEventSource = "fixture";
  }

  if (selectedAccount && liveModeReady && selectedAccountSource === "live") {
    try {
      const payload = await listCalendarEvents(
        apiConfig.apiBaseUrl,
        selectedAccount.id,
        apiConfig.userId,
        {
          limit: requestedEventLimit,
          timeMin: requestedTimeMin || undefined,
          timeMax: requestedTimeMax || undefined,
        },
      );
      discoveredEvents = payload.items;
      discoveredEventSummary = payload.summary;
      discoveredEventSource = "live";
    } catch (error) {
      discoveredEventUnavailableReason =
        error instanceof Error ? error.message : "Calendar event discovery could not be loaded.";

      if (!discoveredEventSummary && discoveredEvents.length === 0) {
        discoveredEventSource = "unavailable";
      }
    }
  }

  const selectedEventId = resolveSelectedEventId(requestedEventId, discoveredEvents);

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
    discoveredEventSource === "unavailable" ? null : discoveredEventSource,
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
            <span className="subtle-chip">{discoveredEventSummary?.total_count ?? 0} discovered events</span>
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
        <CalendarEventList
          account={selectedAccount}
          source={discoveredEventSource}
          events={discoveredEvents}
          summary={discoveredEventSummary}
          selectedEventId={selectedEventId}
          unavailableReason={discoveredEventUnavailableReason}
          limit={requestedEventLimit}
          timeMin={requestedTimeMin}
          timeMax={requestedTimeMax}
        />
      </div>

      <CalendarEventIngestForm
        account={selectedAccount}
        accountSource={selectedAccountSource}
        selectedProviderEventId={selectedEventId}
        selectedEventSource={discoveredEventSource}
        taskWorkspaces={taskWorkspaces}
        taskWorkspaceSource={taskWorkspaceSource}
        apiBaseUrl={apiConfig.apiBaseUrl}
        userId={apiConfig.userId}
      />

      {taskWorkspaceUnavailableReason ? (
        <p className="responsive-note">Live task workspace list read failed: {taskWorkspaceUnavailableReason}</p>
      ) : null}
    </div>
  );
}
