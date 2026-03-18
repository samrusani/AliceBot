import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ArtifactList } from "./artifact-list";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    "aria-current": ariaCurrent,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
    "aria-current"?: string;
  }) => (
    <a href={href} className={className} aria-current={ariaCurrent}>
      {children}
    </a>
  ),
}));

const baseArtifacts = [
  {
    id: "artifact-1",
    task_id: "task-1",
    task_workspace_id: "workspace-1",
    status: "registered" as const,
    ingestion_status: "ingested" as const,
    relative_path: "docs/a.md",
    media_type_hint: "text/markdown",
    created_at: "2026-03-18T10:00:00Z",
    updated_at: "2026-03-18T10:10:00Z",
  },
  {
    id: "artifact-2",
    task_id: "task-2",
    task_workspace_id: "workspace-2",
    status: "registered" as const,
    ingestion_status: "pending" as const,
    relative_path: "gmail/mail.eml",
    media_type_hint: "message/rfc822",
    created_at: "2026-03-18T11:00:00Z",
    updated_at: "2026-03-18T11:05:00Z",
  },
];

describe("ArtifactList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders artifact links that preserve selected artifact state", () => {
    render(
      <ArtifactList
        artifacts={baseArtifacts}
        selectedArtifactId="artifact-2"
        summary={null}
        source="live"
      />,
    );

    expect(screen.getByRole("link", { name: /docs\/a.md/i })).toHaveAttribute(
      "href",
      "/artifacts?artifact=artifact-1",
    );
    expect(screen.getByRole("link", { name: /gmail\/mail.eml/i })).toHaveAttribute(
      "href",
      "/artifacts?artifact=artifact-2",
    );
    expect(screen.getByRole("link", { name: /gmail\/mail.eml/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("renders empty state when artifact list is empty", () => {
    render(<ArtifactList artifacts={[]} selectedArtifactId="" summary={null} source="fixture" />);

    expect(screen.getByText("No persisted artifacts")).toBeInTheDocument();
  });
});
