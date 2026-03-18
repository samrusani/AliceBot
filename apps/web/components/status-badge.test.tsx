import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { StatusBadge } from "./status-badge";

describe("StatusBadge", () => {
  afterEach(() => {
    cleanup();
  });

  it("maps memory label statuses to expected tones", () => {
    const { rerender } = render(<StatusBadge status="correct" />);
    expect(screen.getByText("Correct")).toHaveClass("status-badge--success");

    rerender(<StatusBadge status="incorrect" />);
    expect(screen.getByText("Incorrect")).toHaveClass("status-badge--danger");

    rerender(<StatusBadge status="outdated" />);
    expect(screen.getByText("Outdated")).toHaveClass("status-badge--warning");
  });

  it("renders unavailable as neutral tone", () => {
    render(<StatusBadge status="unavailable" />);

    expect(screen.getByText("Unavailable")).toHaveClass("status-badge--neutral");
  });
});
