import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContinuityCaptureForm } from "./continuity-capture-form";

const { createContinuityCaptureMock, refreshMock } = vi.hoisted(() => ({
  createContinuityCaptureMock: vi.fn(),
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
    createContinuityCapture: createContinuityCaptureMock,
  };
});

describe("ContinuityCaptureForm", () => {
  beforeEach(() => {
    createContinuityCaptureMock.mockReset();
    refreshMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("submits continuity capture through the shipped endpoint when live mode is available", async () => {
    createContinuityCaptureMock.mockResolvedValue({
      capture: {
        capture_event: {
          id: "capture-1",
          raw_content: "Finalize launch checklist",
          explicit_signal: "task",
          admission_posture: "DERIVED",
          admission_reason: "explicit_signal_task",
          created_at: "2026-03-29T09:00:00Z",
        },
        derived_object: {
          id: "object-1",
          capture_event_id: "capture-1",
          object_type: "NextAction",
          status: "active",
          title: "Next Action: Finalize launch checklist",
          body: {
            action_text: "Finalize launch checklist",
            raw_content: "Finalize launch checklist",
            explicit_signal: "task",
          },
          provenance: {
            capture_event_id: "capture-1",
            source_kind: "continuity_capture_event",
          },
          confidence: 1,
          created_at: "2026-03-29T09:00:00Z",
          updated_at: "2026-03-29T09:00:00Z",
        },
      },
    });

    render(
      <ContinuityCaptureForm
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        source="live"
      />,
    );

    fireEvent.change(screen.getByLabelText("Capture text"), {
      target: { value: "Finalize launch checklist" },
    });
    fireEvent.change(screen.getByLabelText("Explicit signal (optional)"), {
      target: { value: "task" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Capture" }));

    await waitFor(() => {
      expect(createContinuityCaptureMock).toHaveBeenCalledWith("https://api.example.com", {
        user_id: "user-1",
        raw_content: "Finalize launch checklist",
        explicit_signal: "task",
      });
    });

    expect(refreshMock).toHaveBeenCalled();
    expect(screen.getByText(/Derived NextAction with provenance/i)).toBeInTheDocument();
  });

  it("keeps submission disabled when live mode is unavailable", () => {
    render(<ContinuityCaptureForm source="fixture" />);

    expect(screen.getByRole("button", { name: "Capture" })).toBeDisabled();
    expect(
      screen.getByText("Capture submission is unavailable until live API configuration is present."),
    ).toBeInTheDocument();
    expect(createContinuityCaptureMock).not.toHaveBeenCalled();
  });
});
