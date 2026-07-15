import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import OnboardingPage from "./page";

describe("OnboardingPage", () => {
  afterEach(() => {
    cleanup();
  });

  it("labels hosted onboarding as instruction-only guidance without live controls", () => {
    render(<OnboardingPage />);

    expect(screen.getByText("Hosted Onboarding Guide")).toBeInTheDocument();
    expect(screen.getByText("Magic-link Setup Checklist")).toBeInTheDocument();
    expect(screen.getByText(/instruction-only page does not execute onboarding operations/i)).toBeInTheDocument();
    expect(screen.getByText(/does not submit magic-link requests/i)).toBeInTheDocument();
    expect(screen.getByText(/open Settings to link Telegram/i)).toBeInTheDocument();
    expect(screen.getByText("Onboarding Failure Visibility")).toBeInTheDocument();
    expect(screen.getByText(/inspect hosted admin incidents/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
