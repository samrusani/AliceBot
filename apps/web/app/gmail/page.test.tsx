import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GmailPage from "./page";

const {
  getApiConfigMock,
  getGmailAccountDetailMock,
  hasLiveApiConfigMock,
  legacySurfacesEnabledMock,
  listGmailAccountsMock,
  listTaskWorkspacesMock,
  notFoundMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getGmailAccountDetailMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  legacySurfacesEnabledMock: vi.fn(),
  listGmailAccountsMock: vi.fn(),
  listTaskWorkspacesMock: vi.fn(),
  notFoundMock: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  notFound: notFoundMock,
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("../../lib/legacy-surfaces.server", () => ({
  legacySurfacesEnabled: legacySurfacesEnabledMock,
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getGmailAccountDetail: getGmailAccountDetailMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listGmailAccounts: listGmailAccountsMock,
    listTaskWorkspaces: listTaskWorkspacesMock,
  };
});

const account = {
  id: "gmail-live-1",
  provider: "gmail",
  auth_kind: "oauth_access_token",
  provider_account_id: "acct-live-1",
  email_address: "live@gmail.example",
  display_name: "Live Owner",
  scope: "https://www.googleapis.com/auth/gmail.readonly",
  created_at: "2026-07-13T10:00:00Z",
  updated_at: "2026-07-13T10:00:00Z",
};

describe("GmailPage", () => {
  beforeEach(() => {
    for (const mock of [
      getApiConfigMock,
      getGmailAccountDetailMock,
      hasLiveApiConfigMock,
      legacySurfacesEnabledMock,
      listGmailAccountsMock,
      listTaskWorkspacesMock,
      notFoundMock,
    ]) {
      mock.mockReset();
    }
    getApiConfigMock.mockReturnValue({ apiBaseUrl: "", userId: "" });
    hasLiveApiConfigMock.mockReturnValue(false);
    legacySurfacesEnabledMock.mockReturnValue(true);
    notFoundMock.mockImplementation(() => {
      throw new Error("NEXT_NOT_FOUND");
    });
  });

  afterEach(cleanup);

  it("returns not found before any reads when legacy surfaces are disabled", async () => {
    legacySurfacesEnabledMock.mockReturnValue(false);

    await expect(GmailPage({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "NEXT_NOT_FOUND",
    );
    expect(notFoundMock).toHaveBeenCalledOnce();
    expect(listGmailAccountsMock).not.toHaveBeenCalled();
  });

  it("renders fixture state and disables secret-bearing connection without live config", async () => {
    render(await GmailPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect Gmail account" })).toBeDisabled();
    expect(listGmailAccountsMock).not.toHaveBeenCalled();
  });

  it("normalizes an array account parameter and renders live account detail", async () => {
    getApiConfigMock.mockReturnValue({ apiBaseUrl: "https://api.example.com", userId: "user-1" });
    hasLiveApiConfigMock.mockReturnValue(true);
    listGmailAccountsMock.mockResolvedValue({
      items: [account],
      summary: { total_count: 1, order: ["created_at_asc", "id_asc"] },
    });
    getGmailAccountDetailMock.mockResolvedValue({ account });
    listTaskWorkspacesMock.mockResolvedValue({
      items: [],
      summary: { total_count: 0, order: ["created_at_asc", "id_asc"] },
    });

    render(
      await GmailPage({
        searchParams: Promise.resolve({ account: [` ${account.id} `, "ignored"] }),
      }),
    );

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getAllByText(account.email_address).length).toBeGreaterThan(0);
    expect(getGmailAccountDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      account.id,
      "user-1",
    );
  });

  it("shows live-read failures while retaining explicit fixture fallback", async () => {
    getApiConfigMock.mockReturnValue({ apiBaseUrl: "https://api.example.com", userId: "user-1" });
    hasLiveApiConfigMock.mockReturnValue(true);
    listGmailAccountsMock.mockRejectedValue(new Error("gmail list failed"));
    listTaskWorkspacesMock.mockRejectedValue(new Error("workspace list failed"));

    render(await GmailPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText(/gmail list failed/i)).toBeInTheDocument();
    expect(screen.getByText(/workspace list failed/i)).toBeInTheDocument();
    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
  });
});
