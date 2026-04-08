import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import SettingsPage from "./page";

describe("SettingsPage", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders telegram channel settings and preserves continuity boundary claims", () => {
    render(<SettingsPage />);

    expect(screen.getByRole("heading", { level: 1, name: "Hosted Settings" })).toBeInTheDocument();
    expect(screen.getByText("Telegram Channel Settings")).toBeInTheDocument();
    expect(
      screen.getByText("Issue a deterministic link challenge bound to the active hosted workspace."),
    ).toBeInTheDocument();
    expect(screen.getByText(/does not claim beta admin dashboards/i)).toBeInTheDocument();
  });
});
