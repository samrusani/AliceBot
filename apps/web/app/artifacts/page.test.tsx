import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ArtifactsPage from "./page";
import { taskArtifactFixtures } from "../../lib/fixtures";

const {
  getApiConfigMock,
  getTaskArtifactDetailMock,
  getTaskWorkspaceDetailMock,
  hasLiveApiConfigMock,
  listTaskArtifactChunksMock,
  listTaskArtifactsMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getTaskArtifactDetailMock: vi.fn(),
  getTaskWorkspaceDetailMock: vi.fn(),
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
    "aria-current"?: string;
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
    getTaskWorkspaceDetail: getTaskWorkspaceDetailMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listTaskArtifactChunks: listTaskArtifactChunksMock,
    listTaskArtifacts: listTaskArtifactsMock,
  };
});

describe("ArtifactsPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getTaskArtifactDetailMock.mockReset();
    getTaskWorkspaceDetailMock.mockReset();
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

  it("keeps route state explicit when live reads partially fail and workspace/chunks fall back to fixture", async () => {
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

    getTaskWorkspaceDetailMock.mockRejectedValue(new Error("workspace down"));
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
    expect(screen.getByText("Fixture workspace")).toBeInTheDocument();
    expect(screen.getByText("Fixture chunks")).toBeInTheDocument();
    expect(screen.getByText(/Live workspace read failed:\s*workspace down/i)).toBeInTheDocument();
    expect(screen.getByText(/Live chunk read failed:\s*chunks down/i)).toBeInTheDocument();

    expect(listTaskArtifactsMock).toHaveBeenCalledWith("https://api.example.com", "user-1");
    expect(getTaskArtifactDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      fixtureArtifact.id,
      "user-1",
    );
    expect(getTaskWorkspaceDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      fixtureArtifact.task_workspace_id,
      "user-1",
    );
    expect(listTaskArtifactChunksMock).toHaveBeenCalledWith(
      "https://api.example.com",
      fixtureArtifact.id,
      "user-1",
    );
  });
});
