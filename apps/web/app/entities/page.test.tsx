import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import EntitiesPage from "./page";
import EntitiesLoading from "./loading";

const {
  getApiConfigMock,
  getEntityDetailMock,
  hasLiveApiConfigMock,
  listEntitiesMock,
  listEntityEdgesMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getEntityDetailMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listEntitiesMock: vi.fn(),
  listEntityEdgesMock: vi.fn(),
}));

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
    "aria-current"?: React.AriaAttributes["aria-current"];
  }) => (
    <a href={href} className={className} aria-current={ariaCurrent}>
      {children}
    </a>
  ),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getEntityDetail: getEntityDetailMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listEntities: listEntitiesMock,
    listEntityEdges: listEntityEdgesMock,
  };
});

describe("EntitiesPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getEntityDetailMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listEntitiesMock.mockReset();
    listEntityEdgesMock.mockReset();

    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "",
      userId: "",
      defaultThreadId: "",
      defaultToolId: "",
    });
    hasLiveApiConfigMock.mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
  });

  it("announces the loading route without interrupting the operator", () => {
    const { container } = render(<EntitiesLoading />);

    expect(container.firstElementChild).toHaveAttribute("aria-busy", "true");
    expect(container.firstElementChild).toHaveAttribute("aria-live", "polite");
  });

  it("uses fixture-backed entity workspace state when live API config is absent", async () => {
    render(await EntitiesPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Fixture list")).toBeInTheDocument();
    expect(screen.getByText("Fixture detail")).toBeInTheDocument();
    expect(screen.getByText("Fixture edges")).toBeInTheDocument();
    expect(listEntitiesMock).not.toHaveBeenCalled();
  });

  it("renders live-backed entity list, detail, and edges when live reads succeed", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);

    listEntitiesMock.mockResolvedValue({
      items: [
        {
          id: "entity-live-1",
          entity_type: "person",
          name: "Live Alice",
          source_memory_ids: ["memory-live-1"],
          created_at: "2026-03-18T10:00:00Z",
        },
      ],
      summary: {
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    getEntityDetailMock.mockResolvedValue({
      entity: {
        id: "entity-live-1",
        entity_type: "person",
        name: "Live Alice",
        source_memory_ids: ["memory-live-1", "memory-live-2"],
        created_at: "2026-03-18T10:00:00Z",
      },
    });

    listEntityEdgesMock.mockResolvedValue({
      items: [
        {
          id: "edge-live-1",
          from_entity_id: "entity-live-1",
          to_entity_id: "entity-live-2",
          relationship_type: "prefers_merchant",
          valid_from: "2026-03-18T10:00:00Z",
          valid_to: null,
          source_memory_ids: ["memory-live-1"],
          created_at: "2026-03-18T10:01:00Z",
        },
      ],
      summary: {
        entity_id: "entity-live-1",
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    render(
      await EntitiesPage({
        searchParams: Promise.resolve({ entity: "entity-live-1" }),
      }),
    );

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getByText("Live list")).toBeInTheDocument();
    expect(screen.getByText("Live detail")).toBeInTheDocument();
    expect(screen.getByText("Live edges")).toBeInTheDocument();

    expect(listEntitiesMock).toHaveBeenCalledWith("https://api.example.com", "user-1");
    expect(getEntityDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "entity-live-1",
      "user-1",
    );
    expect(listEntityEdgesMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "entity-live-1",
      "user-1",
    );
  });

  it("shows explicit edge unavailable state when live edge read fails and no fixture fallback exists", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);

    listEntitiesMock.mockResolvedValue({
      items: [
        {
          id: "entity-live-missing",
          entity_type: "project",
          name: "Missing Fixture Entity",
          source_memory_ids: ["memory-live-missing"],
          created_at: "2026-03-18T11:00:00Z",
        },
      ],
      summary: {
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    getEntityDetailMock.mockResolvedValue({
      entity: {
        id: "entity-live-missing",
        entity_type: "project",
        name: "Missing Fixture Entity",
        source_memory_ids: ["memory-live-missing"],
        created_at: "2026-03-18T11:00:00Z",
      },
    });

    listEntityEdgesMock.mockRejectedValue(new Error("edges down"));

    render(
      await EntitiesPage({
        searchParams: Promise.resolve({ entity: "entity-live-missing" }),
      }),
    );

    expect(screen.getByText("Edge review unavailable")).toBeInTheDocument();
    expect(screen.getByText("Edges unavailable")).toBeInTheDocument();
    expect(screen.getByText("edges down")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("edges down");
  });

  it("marks a failed live detail read unavailable and does not invent edge state", async () => {
    const entity = {
      id: "entity-live-without-fixture",
      entity_type: "project",
      name: "Live-only entity",
      source_memory_ids: ["memory-live-1"],
      created_at: "2026-07-21T09:00:00Z",
    };
    getApiConfigMock.mockReturnValue({ apiBaseUrl: "https://api.example.com", userId: "user-1" });
    hasLiveApiConfigMock.mockReturnValue(true);
    listEntitiesMock.mockResolvedValue({
      items: [entity],
      summary: { total_count: 1, order: ["created_at_asc", "id_asc"] },
    });
    getEntityDetailMock.mockRejectedValue(new Error("entity detail down"));

    render(
      await EntitiesPage({
        searchParams: Promise.resolve({ entity: entity.id }),
      }),
    );

    expect(screen.getByText("Detail unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Live detail")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Edge review unavailable" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("entity detail down");
    expect(listEntityEdgesMock).not.toHaveBeenCalled();
  });
});
