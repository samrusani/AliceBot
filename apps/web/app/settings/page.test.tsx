import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import SettingsPage from "./page";

describe("SettingsPage", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders hosted settings foundations and no Telegram delivery claim", () => {
    render(<SettingsPage />);

    expect(screen.getByRole("heading", { level: 1, name: "Hosted Settings" })).toBeInTheDocument();
    expect(screen.getByText("Preference Foundations")).toBeInTheDocument();
    expect(
      screen.getByText("Persist IANA timezone for future scheduled brief orchestration."),
    ).toBeInTheDocument();
    expect(screen.getByText(/do not claim Telegram linkage/i)).toBeInTheDocument();
  });
});
