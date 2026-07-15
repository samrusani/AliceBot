import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "../app/page";
import { AppShell } from "./app-shell";
import { GmailAccountDetail } from "./gmail-account-detail";
import { WorkspaceLoading } from "./workspace-loading";

vi.mock("next/link", () => ({
  default: ({ href, children, className, "aria-current": ariaCurrent }: {
    href: string; children: React.ReactNode; className?: string; "aria-current"?: "page";
  }) => <a href={href} className={className} aria-current={ariaCurrent}>{children}</a>,
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/gmail" }));

describe("shell coverage", () => {
  afterEach(cleanup);

  it("renders the public home route cards", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: "Operator shell for governed work" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Gmail Review/i })).toHaveAttribute("href", "/gmail");
    expect(screen.getByRole("link", { name: /Continuity Workspace/i })).toHaveAttribute("href", "/continuity");
    expect(screen.getByRole("link", { name: /Chief-of-Staff/i })).toHaveAttribute("href", "/chief-of-staff");
    expect(screen.getByText("16")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText(/live backend data, explicit fixtures, or a mixed state/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Hosted Onboarding Guide/i })).toHaveTextContent("Preview");
    expect(screen.getByText("Governed by default")).toBeInTheDocument();
  });

  it("marks the current navigation item and exposes the skip target", () => {
    render(<AppShell><p>content</p></AppShell>);
    const gmailLinks = screen.getAllByRole("link", { name: /Gmail Review connected accounts/i });
    expect(gmailLinks).toHaveLength(2);
    expect(gmailLinks.every((link) => link.getAttribute("aria-current") === "page")).toBe(true);
    expect(screen.getAllByRole("link", { name: /Continuity Capture, recall/i })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: /Chief-of-Staff Deterministic priorities/i })).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute("href", "#main-content");
  });

  it("renders bounded loading state and unavailable Gmail detail", () => {
    const { rerender } = render(
      <WorkspaceLoading eyebrow="Gmail" title="Loading Gmail" description="Resolving accounts" />,
    );
    expect(screen.getByText("Loading route state")).toBeInTheDocument();
    expect(screen.getByText("Primary workspace")).toBeInTheDocument();

    rerender(<GmailAccountDetail account={null} source="unavailable" unavailableReason="backend down" />);
    expect(screen.getByText("Account detail unavailable")).toBeInTheDocument();
    expect(screen.getByText("backend down")).toBeInTheDocument();
  });
});
