import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MemoryLabelForm } from "./memory-label-form";

const { submitMemoryLabelMock, refreshMock } = vi.hoisted(() => ({
  submitMemoryLabelMock: vi.fn(),
  refreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    submitMemoryLabel: submitMemoryLabelMock,
  };
});

describe("MemoryLabelForm", () => {
  beforeEach(() => {
    submitMemoryLabelMock.mockReset();
    refreshMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("submits memory labels through the shipped endpoint when live mode is available", async () => {
    submitMemoryLabelMock.mockResolvedValue({
      label: {
        id: "label-1",
        memory_id: "memory-1",
        reviewer_user_id: "user-1",
        label: "incorrect",
        note: "Conflicts with newer thread evidence.",
        created_at: "2026-03-18T10:00:00Z",
      },
      summary: {
        memory_id: "memory-1",
        total_count: 2,
        counts_by_label: {
          correct: 1,
          incorrect: 1,
          outdated: 0,
          insufficient_evidence: 0,
        },
        order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
      },
    });

    render(
      <MemoryLabelForm
        memoryId="memory-1"
        source="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />,
    );

    fireEvent.change(screen.getByLabelText("Review label"), {
      target: { value: "incorrect" },
    });
    fireEvent.change(screen.getByLabelText("Reviewer note (optional)"), {
      target: { value: "Conflicts with newer thread evidence." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit review label" }));

    await waitFor(() => {
      expect(submitMemoryLabelMock).toHaveBeenCalledWith("https://api.example.com", "memory-1", {
        user_id: "user-1",
        label: "incorrect",
        note: "Conflicts with newer thread evidence.",
      });
    });

    expect(refreshMock).toHaveBeenCalled();
    expect(screen.getByText(/Label saved\./i)).toBeInTheDocument();
  });

  it("keeps submission disabled when live API mode is unavailable", () => {
    render(<MemoryLabelForm memoryId="memory-1" source="fixture" />);

    expect(screen.getByRole("button", { name: "Submit review label" })).toBeDisabled();
    expect(
      screen.getByText(
        "Label submission is unavailable until live API configuration and live memory detail are present.",
      ),
    ).toBeInTheDocument();
    expect(submitMemoryLabelMock).not.toHaveBeenCalled();
  });
});
