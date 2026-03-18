import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { EntityEdgeList } from "./entity-edge-list";

describe("EntityEdgeList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders idle state when no entity is selected", () => {
    render(
      <EntityEdgeList
        entityId={null}
        edges={[]}
        summary={null}
        source={null}
      />,
    );

    expect(screen.getByText("Edge review is idle")).toBeInTheDocument();
  });

  it("renders ordered edge rows with direction and source memories", () => {
    render(
      <EntityEdgeList
        entityId="entity-1"
        edges={[
          {
            id: "edge-1",
            from_entity_id: "entity-1",
            to_entity_id: "entity-2",
            relationship_type: "prefers_merchant",
            valid_from: "2026-03-18T00:00:00Z",
            valid_to: null,
            source_memory_ids: ["memory-1", "memory-2"],
            created_at: "2026-03-18T00:01:00Z",
          },
        ]}
        summary={{
          entity_id: "entity-1",
          total_count: 1,
          order: ["created_at_asc", "id_asc"],
        }}
        source="fixture"
      />,
    );

    expect(screen.getByText("prefers_merchant")).toBeInTheDocument();
    expect(screen.getByText("entity-1 to entity-2")).toBeInTheDocument();
    expect(screen.getByText("memory-1")).toBeInTheDocument();
    expect(screen.getByText("memory-2")).toBeInTheDocument();
    expect(screen.getByText("Fixture edges")).toBeInTheDocument();
  });
});
