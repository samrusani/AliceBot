import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ArtifactsPage from "./page";
import ArtifactsLoading from "./loading";
import { taskArtifactFixtures } from "../../lib/fixtures";

const {
  getApiConfigMock,
  getTaskArtifactDetailMock,
  hasLiveApiConfigMock,
  listTaskArtifactChunksMock,
  listTaskArtifactsMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getTaskArtifactDetailMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listTaskArtifactChunksMock: vi.fn(),
  listTaskArtifactsMock: vi.fn(),
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
    getTaskArtifactDetail: getTaskArtifactDetailMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listTaskArtifactChunks: listTaskArtifactChunksMock,
    listTaskArtifacts: listTaskArtifactsMock,
  };
});

describe("ArtifactsPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getTaskArtifactDetailMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listTaskArtifactChunksMock.mockReset();
    listTaskArtifactsMock.mockReset();

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
    const { container } = render(<ArtifactsLoading />);

    expect(container.firstElementChild).toHaveAttribute("aria-busy", "true");
    expect(container.firstElementChild).toHaveAttribute("aria-live", "polite");
  });

  it("keeps route state explicit when live chunks fall back to fixture", async () => {
    const fixtureArtifact = taskArtifactFixtures[0];
    if (!fixtureArtifact) {
      throw new Error("Expected at least one task artifact fixture.");
    }

    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);

    listTaskArtifactsMock.mockResolvedValue({
      items: [
        {
          id: fixtureArtifact.id,
          task_id: fixtureArtifact.task_id,
          task_workspace_id: fixtureArtifact.task_workspace_id,
          status: "registered",
          ingestion_status: "ingested",
          relative_path: fixtureArtifact.relative_path,
          media_type_hint: fixtureArtifact.media_type_hint,
          created_at: fixtureArtifact.created_at,
          updated_at: fixtureArtifact.updated_at,
        },
      ],
      summary: {
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    getTaskArtifactDetailMock.mockResolvedValue({
      artifact: {
        id: fixtureArtifact.id,
        task_id: fixtureArtifact.task_id,
        task_workspace_id: fixtureArtifact.task_workspace_id,
        status: "registered",
        ingestion_status: "ingested",
        relative_path: fixtureArtifact.relative_path,
        media_type_hint: fixtureArtifact.media_type_hint,
        created_at: fixtureArtifact.created_at,
        updated_at: fixtureArtifact.updated_at,
      },
    });

    listTaskArtifactChunksMock.mockRejectedValue(new Error("chunks down"));

    render(
      await ArtifactsPage({
        searchParams: Promise.resolve({
          artifact: fixtureArtifact.id,
        }),
      }),
    );

    expect(screen.getByText("Mixed fallback")).toBeInTheDocument();
    expect(screen.getByText("Live list")).toBeInTheDocument();
    expect(screen.getByText("Live detail")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Persisted identity" })).toBeInTheDocument();
    expect(screen.getAllByText(fixtureArtifact.task_workspace_id)).toHaveLength(2);
    expect(screen.getByText("Fixture chunks")).toBeInTheDocument();
    expect(screen.getByText(/Live chunk read failed:\s*chunks down/i)).toBeInTheDocument();

    expect(listTaskArtifactsMock).toHaveBeenCalledWith("https://api.example.com", "user-1");
    expect(getTaskArtifactDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      fixtureArtifact.id,
      "user-1",
    );
    expect(listTaskArtifactChunksMock).toHaveBeenCalledWith(
      "https://api.example.com",
      fixtureArtifact.id,
      "user-1",
    );
  });

  it("loads chunk evidence without calling the legacy task-workspace client", async () => {
    const artifact = taskArtifactFixtures[0];
    if (!artifact) {
      throw new Error("Expected at least one task artifact fixture.");
    }

    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listTaskArtifactsMock.mockResolvedValue({
      items: [artifact],
      summary: { total_count: 1, order: ["created_at_asc", "id_asc"] },
    });
    getTaskArtifactDetailMock.mockResolvedValue({ artifact });

    listTaskArtifactChunksMock.mockResolvedValue({
      items: [],
      summary: {
        total_count: 0,
        total_characters: 0,
        media_type: artifact.media_type_hint,
        chunking_rule: "artifact_ingestion_v0",
        order: ["sequence_no_asc", "id_asc"],
      },
    });

    render(
      await ArtifactsPage({
        searchParams: Promise.resolve({ artifact: artifact.id }),
      }),
    );

    expect(listTaskArtifactChunksMock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("heading", { name: "Persisted identity" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "No persisted chunks" })).toBeInTheDocument();
  });

  it("marks a failed live detail read unavailable and does not invent chunk state", async () => {
    const artifact = {
      id: "artifact-live-without-fixture",
      task_id: "task-live-1",
      task_workspace_id: "workspace-live-1",
      status: "registered",
      ingestion_status: "ingested",
      relative_path: "reports/live-only.md",
      media_type_hint: "text/markdown",
      created_at: "2026-07-21T09:00:00Z",
      updated_at: "2026-07-21T09:05:00Z",
    };
    getApiConfigMock.mockReturnValue({ apiBaseUrl: "https://api.example.com", userId: "user-1" });
    hasLiveApiConfigMock.mockReturnValue(true);
    listTaskArtifactsMock.mockResolvedValue({
      items: [artifact],
      summary: { total_count: 1, order: ["created_at_asc", "id_asc"] },
    });
    getTaskArtifactDetailMock.mockRejectedValue(new Error("artifact detail down"));

    render(
      await ArtifactsPage({
        searchParams: Promise.resolve({ artifact: artifact.id }),
      }),
    );

    expect(screen.getByText("Detail unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Live detail")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Chunk review unavailable" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("artifact detail down");
    expect(listTaskArtifactChunksMock).not.toHaveBeenCalled();
  });
});
