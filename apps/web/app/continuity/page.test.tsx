import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ContinuityPage from "./page";

const {
  getApiConfigMock,
  getContinuityCaptureDetailMock,
  hasLiveApiConfigMock,
  listContinuityCapturesMock,
  refreshMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getContinuityCaptureDetailMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listContinuityCapturesMock: vi.fn(),
  refreshMock: vi.fn(),
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
    refresh: refreshMock,
  }),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getContinuityCaptureDetail: getContinuityCaptureDetailMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listContinuityCaptures: listContinuityCapturesMock,
  };
});

describe("ContinuityPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getContinuityCaptureDetailMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listContinuityCapturesMock.mockReset();
    refreshMock.mockReset();

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

  it("uses fixture continuity state when live API config is absent", async () => {
    render(await ContinuityPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Fixture inbox")).toBeInTheDocument();
    expect(screen.getAllByText("Finalize launch checklist").length).toBeGreaterThan(0);
    expect(screen.getByText("Maybe revisit this next month")).toBeInTheDocument();
    expect(screen.getByText("No durable object")).toBeInTheDocument();
    expect(listContinuityCapturesMock).not.toHaveBeenCalled();
  });

  it("renders live continuity inbox and detail when live reads succeed", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listContinuityCapturesMock.mockResolvedValue({
      items: [
        {
          capture_event: {
            id: "capture-live-1",
            raw_content: "Decision: Keep admission conservative",
            explicit_signal: null,
            admission_posture: "DERIVED",
            admission_reason: "high_confidence_prefix_decision",
            created_at: "2026-03-29T09:20:00Z",
          },
          derived_object: {
            id: "object-live-1",
            capture_event_id: "capture-live-1",
            object_type: "Decision",
            status: "active",
            title: "Decision: Keep admission conservative",
            body: {
              decision_text: "Keep admission conservative",
            },
            provenance: {
              capture_event_id: "capture-live-1",
              source_kind: "continuity_capture_event",
            },
            confidence: 0.95,
            created_at: "2026-03-29T09:20:00Z",
            updated_at: "2026-03-29T09:20:00Z",
          },
        },
      ],
      summary: {
        limit: 20,
        returned_count: 1,
        total_count: 1,
        derived_count: 1,
        triage_count: 0,
        order: ["created_at_desc", "id_desc"],
      },
    });
    getContinuityCaptureDetailMock.mockResolvedValue({
      capture: {
        capture_event: {
          id: "capture-live-1",
          raw_content: "Decision: Keep admission conservative",
          explicit_signal: null,
          admission_posture: "DERIVED",
          admission_reason: "high_confidence_prefix_decision",
          created_at: "2026-03-29T09:20:00Z",
        },
        derived_object: {
          id: "object-live-1",
          capture_event_id: "capture-live-1",
          object_type: "Decision",
          status: "active",
          title: "Decision: Keep admission conservative",
          body: {
            decision_text: "Keep admission conservative",
          },
          provenance: {
            capture_event_id: "capture-live-1",
            source_kind: "continuity_capture_event",
          },
          confidence: 0.95,
          created_at: "2026-03-29T09:20:00Z",
          updated_at: "2026-03-29T09:20:00Z",
        },
      },
    });

    render(await ContinuityPage({ searchParams: Promise.resolve({ capture: "capture-live-1" }) }));

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getByText("Live inbox")).toBeInTheDocument();
    expect(screen.getByText("Live detail")).toBeInTheDocument();
    expect(screen.getAllByText("Decision: Keep admission conservative").length).toBeGreaterThan(0);
    expect(screen.getByText("Derived object")).toBeInTheDocument();
    expect(screen.getByText("Provenance")).toBeInTheDocument();

    expect(listContinuityCapturesMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      limit: 20,
    });
    expect(getContinuityCaptureDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "capture-live-1",
      "user-1",
    );
  });
});
