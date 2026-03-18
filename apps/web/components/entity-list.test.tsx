import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EntityList } from "./entity-list";

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

const baseEntities = [
  {
    id: "entity-1",
    entity_type: "person" as const,
    name: "Alice",
    source_memory_ids: ["memory-1"],
    created_at: "2026-03-18T10:00:00Z",
  },
  {
    id: "entity-2",
    entity_type: "merchant" as const,
    name: "Thorne",
    source_memory_ids: ["memory-2"],
    created_at: "2026-03-18T11:00:00Z",
  },
];

describe("EntityList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders entity links that preserve selected entity state", () => {
    render(
      <EntityList
        entities={baseEntities}
        selectedEntityId="entity-2"
        summary={null}
        source="live"
      />,
    );

    expect(screen.getByRole("link", { name: /alice/i })).toHaveAttribute(
      "href",
      "/entities?entity=entity-1",
    );
    expect(screen.getByRole("link", { name: /thorne/i })).toHaveAttribute(
      "href",
      "/entities?entity=entity-2",
    );
    expect(screen.getByRole("link", { name: /thorne/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("renders empty state when entity list is empty", () => {
    render(<EntityList entities={[]} selectedEntityId="" summary={null} source="fixture" />);

    expect(screen.getByText("No tracked entities")).toBeInTheDocument();
  });
});
