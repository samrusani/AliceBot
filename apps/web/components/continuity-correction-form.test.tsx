import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContinuityCorrectionForm } from "./continuity-correction-form";

const { applyContinuityCorrectionMock, refreshMock } = vi.hoisted(() => ({
  applyContinuityCorrectionMock: vi.fn(),
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
    applyContinuityCorrection: applyContinuityCorrectionMock,
  };
});

const reviewFixture = {
  continuity_object: {
    id: "object-1",
    capture_event_id: "capture-1",
    object_type: "Decision" as const,
    status: "active",
    title: "Decision: Keep rollout phased",
    body: { decision_text: "Keep rollout phased" },
    provenance: {},
    confidence: 0.95,
    last_confirmed_at: null,
    supersedes_object_id: null,
    superseded_by_object_id: null,
    created_at: "2026-03-30T10:00:00Z",
    updated_at: "2026-03-30T10:00:00Z",
  },
  correction_events: [],
  supersession_chain: {
    supersedes: null,
    superseded_by: null,
  },
};

describe("ContinuityCorrectionForm", () => {
  beforeEach(() => {
    applyContinuityCorrectionMock.mockReset();
    refreshMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders empty state when no review object is selected", () => {
    render(<ContinuityCorrectionForm source="fixture" review={null} />);

    expect(screen.getByText("No continuity object selected")).toBeInTheDocument();
  });

  it("submits confirm corrections through the shipped endpoint", async () => {
    applyContinuityCorrectionMock.mockResolvedValue({
      continuity_object: {
        ...reviewFixture.continuity_object,
        last_confirmed_at: "2026-03-30T10:01:00Z",
      },
      correction_event: {
        id: "event-1",
        continuity_object_id: "object-1",
        action: "confirm",
        reason: "Reviewed",
        before_snapshot: {},
        after_snapshot: {},
        payload: {},
        created_at: "2026-03-30T10:01:00Z",
      },
      replacement_object: null,
    });

    render(
      <ContinuityCorrectionForm
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        source="live"
        review={reviewFixture}
      />,
    );

    fireEvent.change(screen.getByLabelText("Reason (optional)"), {
      target: { value: "Reviewed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply correction" }));

    await waitFor(() => {
      expect(applyContinuityCorrectionMock).toHaveBeenCalledWith(
        "https://api.example.com",
        "object-1",
        {
          user_id: "user-1",
          action: "confirm",
          reason: "Reviewed",
          title: undefined,
          confidence: undefined,
          replacement_title: undefined,
          replacement_confidence: undefined,
        },
      );
    });

    expect(refreshMock).toHaveBeenCalled();
    expect(screen.getByText(/Correction applied/i)).toBeInTheDocument();
  });
});
