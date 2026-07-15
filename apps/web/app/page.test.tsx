import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "./page";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => <a href={href} className={className}>{children}</a>,
}));

vi.mock("../lib/legacy-surfaces.server", () => ({
  legacySurfacesEnabled: () => false,
}));

describe("HomePage", () => {
  afterEach(cleanup);

  it("resolves the default server route to the core-only console", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: "Continuity and memory review console" })).toBeInTheDocument();
    expect(screen.getByText("Core surfaces only")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Legacy Approval Inbox/i })).not.toBeInTheDocument();
  });
});
