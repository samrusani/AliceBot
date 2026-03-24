import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChatPage from "./page";

const {
  getApiConfigMock,
  getThreadResumptionBriefMock,
  getThreadDetailMock,
  getThreadEventsMock,
  getThreadSessionsMock,
  hasLiveApiConfigMock,
  listAgentProfilesMock,
  listThreadsMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getThreadResumptionBriefMock: vi.fn(),
  getThreadDetailMock: vi.fn(),
  getThreadEventsMock: vi.fn(),
  getThreadSessionsMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listAgentProfilesMock: vi.fn(),
  listThreadsMock: vi.fn(),
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

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getThreadResumptionBrief: getThreadResumptionBriefMock,
    getThreadDetail: getThreadDetailMock,
    getThreadEvents: getThreadEventsMock,
    getThreadSessions: getThreadSessionsMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listAgentProfiles: listAgentProfilesMock,
    listThreads: listThreadsMock,
  };
});

function buildResumptionBriefFixture() {
  return {
    brief: {
      assembly_version: "resumption_brief_v0",
      thread: {
        id: "thread-1",
        title: "Gamma thread",
        agent_profile_id: "assistant_default",
        created_at: "2026-03-17T10:00:00Z",
        updated_at: "2026-03-17T10:00:00Z",
      },
      conversation: {
        items: [],
        summary: {
          limit: 8,
          returned_count: 0,
          total_count: 0,
          order: ["sequence_no_asc"],
          kinds: ["message.user", "message.assistant"],
        },
      },
      open_loops: {
        items: [],
        summary: {
          limit: 5,
          returned_count: 0,
          total_count: 0,
          order: ["opened_at_desc", "created_at_desc", "id_desc"],
        },
      },
      memory_highlights: {
        items: [],
        summary: {
          limit: 5,
          returned_count: 0,
          total_count: 0,
          order: ["updated_at_asc", "created_at_asc", "id_asc"],
        },
      },
      workflow: null,
      sources: ["threads", "events", "open_loops", "memories"],
    },
  };
}

describe("ChatPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getThreadResumptionBriefMock.mockReset();
    getThreadDetailMock.mockReset();
    getThreadEventsMock.mockReset();
    getThreadSessionsMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listAgentProfilesMock.mockReset();
    listThreadsMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("does not seed fixture assistant history when live API configuration is present", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listAgentProfilesMock.mockResolvedValue({
      items: [
        {
          id: "assistant_default",
          name: "Assistant Default",
          description: "General-purpose assistant profile for baseline conversations.",
        },
        {
          id: "coach_default",
          name: "Coach Default",
          description: "Coaching-oriented profile focused on guidance and accountability.",
        },
      ],
      summary: { total_count: 2, order: ["id_asc"] },
    });
    listThreadsMock.mockResolvedValue({
      items: [
        {
          id: "thread-1",
          title: "Gamma thread",
          agent_profile_id: "assistant_default",
          created_at: "2026-03-17T10:00:00Z",
          updated_at: "2026-03-17T10:00:00Z",
        },
      ],
      summary: { total_count: 1, order: ["created_at_desc", "id_desc"] },
    });
    getThreadDetailMock.mockResolvedValue({
      thread: {
        id: "thread-1",
        title: "Gamma thread",
        agent_profile_id: "assistant_default",
        created_at: "2026-03-17T10:00:00Z",
        updated_at: "2026-03-17T10:00:00Z",
      },
    });
    getThreadSessionsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadEventsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadResumptionBriefMock.mockResolvedValue(buildResumptionBriefFixture());

    render(await ChatPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Live continuity enabled")).toBeInTheDocument();
    expect(screen.getByText("Selected: Gamma thread")).toBeInTheDocument();
    expect(screen.getAllByText("Profile Assistant Default").length).toBeGreaterThan(0);
    expect(screen.getByText("No assistant replies yet")).toBeInTheDocument();
    expect(screen.queryByText("Fixture response preview")).not.toBeInTheDocument();
    expect(screen.queryByText(/What do I need to know about the last Vitamin D request/i)).not.toBeInTheDocument();
    expect(listAgentProfilesMock).toHaveBeenCalledWith("https://api.example.com");
  });

  it("does not seed fixture governed-request history when live API configuration is present", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listAgentProfilesMock.mockResolvedValue({
      items: [
        {
          id: "assistant_default",
          name: "Assistant Default",
          description: "General-purpose assistant profile for baseline conversations.",
        },
      ],
      summary: { total_count: 1, order: ["id_asc"] },
    });
    listThreadsMock.mockResolvedValue({
      items: [
        {
          id: "thread-1",
          title: "Gamma thread",
          agent_profile_id: "assistant_default",
          created_at: "2026-03-17T10:00:00Z",
          updated_at: "2026-03-17T10:00:00Z",
        },
      ],
      summary: { total_count: 1, order: ["created_at_desc", "id_desc"] },
    });
    getThreadDetailMock.mockResolvedValue({
      thread: {
        id: "thread-1",
        title: "Gamma thread",
        agent_profile_id: "assistant_default",
        created_at: "2026-03-17T10:00:00Z",
        updated_at: "2026-03-17T10:00:00Z",
      },
    });
    getThreadSessionsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadEventsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadResumptionBriefMock.mockResolvedValue(buildResumptionBriefFixture());

    render(
      await ChatPage({
        searchParams: Promise.resolve({
          mode: "request",
        }),
      }),
    );

    expect(screen.getByText("Live continuity enabled")).toBeInTheDocument();
    expect(screen.getByText("No governed requests yet")).toBeInTheDocument();
    expect(screen.queryByText("Fixture preview")).not.toBeInTheDocument();
    expect(screen.queryByText(/place_order \/ supplements/i)).not.toBeInTheDocument();
  });

  it("shows an unavailable continuity status when live continuity reads fail", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listAgentProfilesMock.mockResolvedValue({
      items: [
        {
          id: "assistant_default",
          name: "Assistant Default",
          description: "General-purpose assistant profile for baseline conversations.",
        },
      ],
      summary: { total_count: 1, order: ["id_asc"] },
    });
    listThreadsMock.mockResolvedValue({
      items: [
        {
          id: "thread-1",
          title: "Gamma thread",
          agent_profile_id: "assistant_default",
          created_at: "2026-03-17T10:00:00Z",
          updated_at: "2026-03-17T10:00:00Z",
        },
      ],
      summary: { total_count: 1, order: ["created_at_desc", "id_desc"] },
    });
    getThreadDetailMock.mockRejectedValue(new Error("detail failed"));
    getThreadSessionsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadEventsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadResumptionBriefMock.mockRejectedValue(new Error("brief failed"));

    render(await ChatPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Continuity unavailable")).toBeInTheDocument();
    expect(screen.getByText("Summary unavailable")).toBeInTheDocument();
  });

  it("shows resumption brief unavailable state when brief read fails but continuity is live", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listAgentProfilesMock.mockResolvedValue({
      items: [
        {
          id: "assistant_default",
          name: "Assistant Default",
          description: "General-purpose assistant profile for baseline conversations.",
        },
      ],
      summary: { total_count: 1, order: ["id_asc"] },
    });
    listThreadsMock.mockResolvedValue({
      items: [
        {
          id: "thread-1",
          title: "Gamma thread",
          agent_profile_id: "assistant_default",
          created_at: "2026-03-17T10:00:00Z",
          updated_at: "2026-03-17T10:00:00Z",
        },
      ],
      summary: { total_count: 1, order: ["created_at_desc", "id_desc"] },
    });
    getThreadDetailMock.mockResolvedValue({
      thread: {
        id: "thread-1",
        title: "Gamma thread",
        agent_profile_id: "assistant_default",
        created_at: "2026-03-17T10:00:00Z",
        updated_at: "2026-03-17T10:00:00Z",
      },
    });
    getThreadSessionsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadEventsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadResumptionBriefMock.mockRejectedValue(new Error("resumption brief failed"));

    render(await ChatPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Live continuity enabled")).toBeInTheDocument();
    expect(screen.getByText("Resumption brief unavailable")).toBeInTheDocument();
    expect(screen.getByText("resumption brief failed")).toBeInTheDocument();
  });

  it("falls back to fixture profiles when live profile registry read fails", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listAgentProfilesMock.mockRejectedValue(new Error("profile registry failed"));
    listThreadsMock.mockResolvedValue({
      items: [
        {
          id: "thread-1",
          title: "Gamma thread",
          agent_profile_id: "coach_default",
          created_at: "2026-03-17T10:00:00Z",
          updated_at: "2026-03-17T10:00:00Z",
        },
      ],
      summary: { total_count: 1, order: ["created_at_desc", "id_desc"] },
    });
    getThreadDetailMock.mockResolvedValue({
      thread: {
        id: "thread-1",
        title: "Gamma thread",
        agent_profile_id: "coach_default",
        created_at: "2026-03-17T10:00:00Z",
        updated_at: "2026-03-17T10:00:00Z",
      },
    });
    getThreadSessionsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadEventsMock.mockResolvedValue({
      items: [],
      summary: { thread_id: "thread-1", total_count: 0, order: [] },
    });
    getThreadResumptionBriefMock.mockResolvedValue(buildResumptionBriefFixture());

    render(await ChatPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Live continuity enabled")).toBeInTheDocument();
    expect(screen.getAllByText("Profile Coach Default").length).toBeGreaterThan(0);
  });
});
