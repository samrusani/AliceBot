import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChatPage from "./page";

const {
  getApiConfigMock,
  getThreadDetailMock,
  getThreadEventsMock,
  getThreadSessionsMock,
  hasLiveApiConfigMock,
  listThreadsMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getThreadDetailMock: vi.fn(),
  getThreadEventsMock: vi.fn(),
  getThreadSessionsMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
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
    getThreadDetail: getThreadDetailMock,
    getThreadEvents: getThreadEventsMock,
    getThreadSessions: getThreadSessionsMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listThreads: listThreadsMock,
  };
});

describe("ChatPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getThreadDetailMock.mockReset();
    getThreadEventsMock.mockReset();
    getThreadSessionsMock.mockReset();
    hasLiveApiConfigMock.mockReset();
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
    listThreadsMock.mockResolvedValue({
      items: [
        {
          id: "thread-1",
          title: "Gamma thread",
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

    render(await ChatPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Live continuity enabled")).toBeInTheDocument();
    expect(screen.getByText("Selected: Gamma thread")).toBeInTheDocument();
    expect(screen.getByText("No assistant replies yet")).toBeInTheDocument();
    expect(screen.queryByText("Fixture response preview")).not.toBeInTheDocument();
    expect(screen.queryByText(/What do I need to know about the last Vitamin D request/i)).not.toBeInTheDocument();
  });

  it("does not seed fixture governed-request history when live API configuration is present", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listThreadsMock.mockResolvedValue({
      items: [
        {
          id: "thread-1",
          title: "Gamma thread",
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
    listThreadsMock.mockResolvedValue({
      items: [
        {
          id: "thread-1",
          title: "Gamma thread",
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

    render(await ChatPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Continuity unavailable")).toBeInTheDocument();
    expect(screen.getByText("Summary unavailable")).toBeInTheDocument();
  });
});
