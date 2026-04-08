import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import HostedAdminPage from "./page";

describe("HostedAdminPage", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders hosted admin launch-readiness controls", () => {
    render(<HostedAdminPage />);

    expect(screen.getByRole("heading", { level: 1, name: "Hosted Admin" })).toBeInTheDocument();
    expect(screen.getByText("Hosted Beta Operations")).toBeInTheDocument();
    expect(screen.getByText(/rate-limit evidence for beta support/i)).toBeInTheDocument();
    expect(screen.getByText(/alice connect hosted beta operations/i)).toBeInTheDocument();
  });
});
