import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import OnboardingPage from "./page";

describe("OnboardingPage", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders hosted onboarding scope and guards Telegram claims", () => {
    render(<OnboardingPage />);

    expect(screen.getByText("Hosted Onboarding")).toBeInTheDocument();
    expect(screen.getByText("Magic-link Identity")).toBeInTheDocument();
    expect(screen.getByText(/not available in P10-S1/i)).toBeInTheDocument();
    expect(screen.getByText(/readiness only/i)).toBeInTheDocument();
    expect(screen.getByText("Onboarding Failure Visibility")).toBeInTheDocument();
    expect(screen.getByText(/inspect hosted admin incidents/i)).toBeInTheDocument();
  });
});
