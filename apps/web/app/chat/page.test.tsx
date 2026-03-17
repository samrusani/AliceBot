import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChatPage from "./page";

const { getApiConfigMock, hasLiveApiConfigMock } = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
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
    hasLiveApiConfig: hasLiveApiConfigMock,
  };
});

describe("ChatPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    hasLiveApiConfigMock.mockReset();
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

    render(await ChatPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Live submission enabled")).toBeInTheDocument();
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

    render(
      await ChatPage({
        searchParams: Promise.resolve({
          mode: "request",
        }),
      }),
    );

    expect(screen.getByText("Live submission enabled")).toBeInTheDocument();
    expect(screen.getByText("No governed requests yet")).toBeInTheDocument();
    expect(screen.queryByText("Fixture preview")).not.toBeInTheDocument();
    expect(screen.queryByText(/place_order \/ supplements/i)).not.toBeInTheDocument();
  });
});
