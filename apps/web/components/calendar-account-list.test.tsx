import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CalendarAccountList } from "./calendar-account-list";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    "aria-current": ariaCurrent,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
    "aria-current"?: string;
  }) => (
    <a href={href} className={className} aria-current={ariaCurrent}>
      {children}
    </a>
  ),
}));

const baseAccounts = [
  {
    id: "calendar-account-1",
    provider: "google_calendar",
    auth_kind: "oauth_access_token",
    provider_account_id: "acct-owner-001",
    email_address: "owner@gmail.example",
    display_name: "Owner",
    scope: "https://www.googleapis.com/auth/calendar.readonly" as const,
    created_at: "2026-03-18T10:00:00Z",
    updated_at: "2026-03-18T10:00:00Z",
  },
  {
    id: "calendar-account-2",
    provider: "google_calendar",
    auth_kind: "oauth_access_token",
    provider_account_id: "acct-ops-002",
    email_address: "ops@gmail.example",
    display_name: "Ops",
    scope: "https://www.googleapis.com/auth/calendar.readonly" as const,
    created_at: "2026-03-18T11:00:00Z",
    updated_at: "2026-03-18T11:00:00Z",
  },
];

describe("CalendarAccountList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders account links that preserve selected account state", () => {
    render(
      <CalendarAccountList
        accounts={baseAccounts}
        selectedAccountId="calendar-account-2"
        summary={null}
        source="live"
      />,
    );

    expect(screen.getByRole("link", { name: /owner@gmail.example/i })).toHaveAttribute(
      "href",
      "/calendar?account=calendar-account-1",
    );
    expect(screen.getByRole("link", { name: /ops@gmail.example/i })).toHaveAttribute(
      "href",
      "/calendar?account=calendar-account-2",
    );
    expect(screen.getByRole("link", { name: /ops@gmail.example/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("renders empty state when no Calendar accounts are available", () => {
    render(<CalendarAccountList accounts={[]} selectedAccountId="" summary={null} source="fixture" />);

    expect(screen.getByText("No connected accounts")).toBeInTheDocument();
  });
});
