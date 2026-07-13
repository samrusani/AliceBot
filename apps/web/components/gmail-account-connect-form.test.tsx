import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GmailAccountConnectForm } from "./gmail-account-connect-form";

const { connectGmailAccountMock, pushMock, refreshMock } = vi.hoisted(() => ({
  connectGmailAccountMock: vi.fn(),
  pushMock: vi.fn(),
  refreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: refreshMock }),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return { ...actual, connectGmailAccount: connectGmailAccountMock };
});

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("Provider account ID"), { target: { value: " acct-1 " } });
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: " owner@example.com " } });
  fireEvent.change(screen.getByLabelText("Access token"), { target: { value: " secret-access " } });
}

describe("GmailAccountConnectForm", () => {
  beforeEach(() => {
    connectGmailAccountMock.mockReset();
    pushMock.mockReset();
    refreshMock.mockReset();
  });
  afterEach(cleanup);

  it("rejects a partial refresh bundle before any network write", () => {
    render(<GmailAccountConnectForm apiBaseUrl="https://api.example.com" userId="user-1" />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("Refresh token (optional bundle)"), {
      target: { value: "refresh-only" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Connect Gmail account" }));

    expect(screen.getByText(/Refresh credentials must include/i)).toBeInTheDocument();
    expect(connectGmailAccountMock).not.toHaveBeenCalled();
  });

  it("submits a normalized full bundle and clears secrets after success", async () => {
    connectGmailAccountMock.mockResolvedValue({
      account: { id: "gmail/account 1", email_address: "owner@example.com" },
    });
    render(<GmailAccountConnectForm apiBaseUrl="https://api.example.com" userId="user-1" />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("Display name (optional)"), { target: { value: " Owner " } });
    fireEvent.change(screen.getByLabelText("Refresh token (optional bundle)"), { target: { value: " refresh " } });
    fireEvent.change(screen.getByLabelText("Client ID (optional bundle)"), { target: { value: " client " } });
    fireEvent.change(screen.getByLabelText("Client secret (optional bundle)"), { target: { value: " client-secret " } });
    fireEvent.change(screen.getByLabelText("Access token expires at"), { target: { value: "2026-07-14T10:30" } });
    fireEvent.click(screen.getByRole("button", { name: "Connect Gmail account" }));

    await waitFor(() => expect(connectGmailAccountMock).toHaveBeenCalledTimes(1));
    const [, payload] = connectGmailAccountMock.mock.calls[0];
    expect(payload).toMatchObject({
      user_id: "user-1",
      provider_account_id: "acct-1",
      email_address: "owner@example.com",
      display_name: "Owner",
      access_token: "secret-access",
      refresh_token: "refresh",
      client_id: "client",
      client_secret: "client-secret",
    });
    expect(payload.access_token_expires_at).toBe(new Date("2026-07-14T10:30").toISOString());
    expect(screen.getByLabelText("Access token")).toHaveValue("");
    expect(screen.getByLabelText("Refresh token (optional bundle)")).toHaveValue("");
    expect(screen.getByLabelText("Client secret (optional bundle)")).toHaveValue("");
    expect(pushMock).toHaveBeenCalledWith("/gmail?account=gmail%2Faccount%201");
    expect(refreshMock).toHaveBeenCalled();
  });

  it("surfaces provider failure without navigating or clearing the access token", async () => {
    connectGmailAccountMock.mockRejectedValue(new Error("provider timeout"));
    render(<GmailAccountConnectForm apiBaseUrl="https://api.example.com" userId="user-1" />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Connect Gmail account" }));

    expect(await screen.findByText(/Unable to connect account: provider timeout/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Access token")).toHaveValue(" secret-access ");
    expect(pushMock).not.toHaveBeenCalled();
  });
});
