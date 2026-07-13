import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { VNextBrainWorkspace } from "../../components/vnext-brain-workspace";
import {
  fixtureWorkspace,
  getVNextWorkspaceFixtureContract,
  summarizeSources,
} from "../../components/vnext-workspace-model";
import {
  VNextHomeMetrics,
  VNextSurfaceNavigation,
} from "../../components/vnext-workspace-overview";

describe("bounded vNext coverage", () => {
  afterEach(() => {
    cleanup();
  });

  it("executes representative capture and review mutation handlers", () => {
    render(<VNextBrainWorkspace initialSource="fixture" />);

    expect(screen.getByText("Demo fixture")).toBeInTheDocument();
    expect(screen.getAllByText("Source capture").length).toBeGreaterThan(0);
    expect(getVNextWorkspaceFixtureContract().connectorIds).toContain("browser_clipper");

    fireEvent.change(screen.getByLabelText("Note or source text"), {
      target: { value: "Fact: Coverage validates representative workspace behavior." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add note/source" }));
    expect(
      screen.getAllByText("Demo source captured and candidate memory generated.").length,
    ).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(screen.getAllByText("Demo memory review action applied: accept.").length).toBeGreaterThan(0);
  }, 30_000);

  it("executes representative artifact generation and scheduler handlers", () => {
    render(<VNextBrainWorkspace initialSource="fixture" />);

    fireEvent.click(screen.getByRole("button", { name: "Generate daily brief" }));
    expect(screen.getAllByText("Demo daily artifact generated.").length).toBeGreaterThan(0);

    fireEvent.click(screen.getAllByRole("button", { name: "Enable" })[0]);
    expect(screen.getAllByText("Demo scheduler action applied: enable.").length).toBeGreaterThan(0);
  }, 30_000);

  it("executes representative connector and charter handlers", () => {
    render(<VNextBrainWorkspace initialSource="fixture" />);

    fireEvent.change(screen.getByLabelText("Connector"), {
      target: { value: "browser_clipper" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save connector settings" }));
    expect(screen.getAllByText("Demo connector settings saved.").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Brain Charter Markdown"), {
      target: { value: "# ALICE.md\n\nRequire evidence before promotion." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Brain Charter" }));
    expect(screen.getAllByText("Demo Brain Charter settings saved.").length).toBeGreaterThan(0);
  }, 30_000);

  it("executes the extracted model and overview surfaces", () => {
    const workspace = fixtureWorkspace();
    render(
      <>
        <VNextSurfaceNavigation />
        <VNextHomeMetrics workspace={workspace} />
      </>,
    );

    expect(screen.getByRole("navigation", { name: "Alice vNext surfaces" })).toBeInTheDocument();
    expect(screen.getByText("Schedules on")).toBeInTheDocument();
    expect(summarizeSources(["source-a", "source-b"])).toBe("source-a, source-b");
  });
});
