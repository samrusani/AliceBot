import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MemoryLabelList } from "./memory-label-list";
import { MemoryRevisionList } from "./memory-revision-list";

describe("memory secondary review lists", () => {
  afterEach(() => {
    cleanup();
  });

  it("does not turn unavailable revision history into a successful empty result", () => {
    render(
      <MemoryRevisionList
        memoryId="memory-1"
        revisions={[]}
        summary={null}
        source="unavailable"
        unavailableReason="detail unavailable"
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Revision history unavailable" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("detail unavailable");
    expect(screen.queryByText("No revisions returned")).not.toBeInTheDocument();
  });

  it("does not fabricate zero label counts when label history is unavailable", () => {
    render(
      <MemoryLabelList
        memoryId="memory-1"
        labels={[]}
        summary={null}
        source="unavailable"
        unavailableReason="labels unavailable"
      />,
    );

    expect(screen.getByRole("heading", { name: "Review labels unavailable" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("labels unavailable");
    expect(screen.queryByText("No labels yet")).not.toBeInTheDocument();
    expect(screen.queryByText("0 total labels")).not.toBeInTheDocument();
  });
});
