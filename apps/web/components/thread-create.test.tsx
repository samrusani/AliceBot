import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { createThreadMock, refreshMock, pushMock } = vi.hoisted(() => ({
  createThreadMock: vi.fn(),
  pushMock: vi.fn(),
  refreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    createThread: createThreadMock,
  };
});

import { ThreadCreate } from "./thread-create";

describe("ThreadCreate", () => {
  beforeEach(() => {
    createThreadMock.mockReset();
    pushMock.mockReset();
    refreshMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("creates a live thread and routes the operator to the new selection", async () => {
    createThreadMock.mockResolvedValue({
      thread: {
        id: "thread-2",
        title: "Delta thread",
        created_at: "2026-03-17T11:00:00Z",
        updated_at: "2026-03-17T11:00:00Z",
      },
    });

    render(
      <ThreadCreate
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        currentMode="assistant"
      />,
    );

    fireEvent.change(screen.getByLabelText("Thread title"), {
      target: { value: "Delta thread" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create thread" }));

    await waitFor(() => {
      expect(createThreadMock).toHaveBeenCalledWith("https://api.example.com", {
        user_id: "user-1",
        title: "Delta thread",
      });
    });

    expect(pushMock).toHaveBeenCalledWith("/chat?thread=thread-2");
    expect(refreshMock).toHaveBeenCalled();
  });

  it("shows an explicit unavailable state when live API configuration is absent", () => {
    render(<ThreadCreate currentMode="assistant" />);

    expect(screen.getByRole("button", { name: "Create thread" })).toBeDisabled();
    expect(
      screen.getByText(/Thread creation becomes available when the live web API base URL and user ID are configured/i),
    ).toBeInTheDocument();
  });
});
