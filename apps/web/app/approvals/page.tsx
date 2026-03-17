import { ApprovalList, type ApprovalItem } from "../../components/approval-list";
import { PageHeader } from "../../components/page-header";

const approvalFixtures: ApprovalItem[] = [
  {
    id: "approval-101",
    thread_id: "thread-magnesium",
    task_step_id: "step-21",
    status: "pending",
    request: {
      thread_id: "thread-magnesium",
      tool_id: "tool-purchase",
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Thorne",
        item: "Magnesium Bisglycinate",
        quantity: "1",
        budget_note: "Prefer previously approved merchant and package size.",
      },
    },
    tool: {
      id: "tool-purchase",
      tool_key: "merchant_proxy",
      name: "Merchant Proxy",
      description: "Proxy for governed ecommerce actions.",
      version: "0.1.0",
      metadata_version: "tool_metadata_v0",
      active: true,
      tags: ["commerce", "approval"],
      action_hints: ["place_order"],
      scope_hints: ["supplements"],
      domain_hints: ["ecommerce"],
      risk_hints: ["purchase"],
      metadata: {},
      created_at: "2026-03-15T08:00:00Z",
    },
    routing: {
      decision: "require_approval",
      reasons: [
        {
          code: "policy_effect_require_approval",
          source: "policy",
          message: "Purchases require explicit user approval before execution.",
          tool_id: "tool-purchase",
          policy_id: "policy-purchase-approval",
          consent_key: null,
        },
        {
          code: "tool_metadata_matched",
          source: "tool",
          message: "Merchant proxy supports the requested purchase scope.",
          tool_id: "tool-purchase",
          policy_id: null,
          consent_key: null,
        },
      ],
      trace: {
        trace_id: "trace-approval-101",
        trace_event_count: 6,
      },
    },
    created_at: "2026-03-17T06:50:00Z",
    resolution: null,
  },
  {
    id: "approval-100",
    thread_id: "thread-vitamin-d",
    task_step_id: "step-14",
    status: "approved",
    request: {
      thread_id: "thread-vitamin-d",
      tool_id: "tool-purchase",
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Fullscript",
        item: "Vitamin D3 + K2",
        quantity: "1",
        note: "Matched prior merchant and approved dosage plan.",
      },
    },
    tool: {
      id: "tool-purchase",
      tool_key: "merchant_proxy",
      name: "Merchant Proxy",
      description: "Proxy for governed ecommerce actions.",
      version: "0.1.0",
      metadata_version: "tool_metadata_v0",
      active: true,
      tags: ["commerce", "approval"],
      action_hints: ["place_order"],
      scope_hints: ["supplements"],
      domain_hints: ["ecommerce"],
      risk_hints: ["purchase"],
      metadata: {},
      created_at: "2026-03-14T09:15:00Z",
    },
    routing: {
      decision: "require_approval",
      reasons: [
        {
          code: "matched_policy",
          source: "policy",
          message: "Repeat supplement purchases remain approval-gated even when the merchant and dosage are known.",
          tool_id: "tool-purchase",
          policy_id: "policy-purchase-approval",
          consent_key: null,
        },
      ],
      trace: {
        trace_id: "trace-approval-100",
        trace_event_count: 5,
      },
    },
    created_at: "2026-03-16T14:10:00Z",
    resolution: {
      resolved_at: "2026-03-16T14:22:00Z",
      resolved_by_user_id: "operator-1",
    },
  },
];

function getApiConfig() {
  return {
    apiBaseUrl:
      process.env.NEXT_PUBLIC_ALICEBOT_API_BASE_URL ?? process.env.ALICEBOT_API_BASE_URL ?? "",
    userId: process.env.NEXT_PUBLIC_ALICEBOT_USER_ID ?? process.env.ALICEBOT_USER_ID ?? "",
  };
}

async function loadApprovals(): Promise<{ items: ApprovalItem[]; source: "live" | "fixture" }> {
  const { apiBaseUrl, userId } = getApiConfig();
  if (!apiBaseUrl || !userId) {
    return { items: approvalFixtures, source: "fixture" };
  }

  try {
    const response = await fetch(
      `${apiBaseUrl.replace(/\/$/, "")}/v0/approvals?user_id=${encodeURIComponent(userId)}`,
      { cache: "no-store" },
    );

    if (!response.ok) {
      throw new Error("approval list request failed");
    }

    const payload = (await response.json()) as { items?: ApprovalItem[] };
    return {
      items: payload.items ?? approvalFixtures,
      source: "live",
    };
  } catch {
    return { items: approvalFixtures, source: "fixture" };
  }
}

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function ApprovalsPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const selectedId = typeof params.approval === "string" ? params.approval : undefined;
  const { items, source } = await loadApprovals();

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Approvals"
        title="Approval inbox and review"
        description="Review consequential actions with one stable split layout: queue on the left, rationale and request detail on the right."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{source === "live" ? "Live API" : "Fixture-backed"}</span>
            <span className="subtle-chip">{items.length} items</span>
          </div>
        }
      />

      <ApprovalList items={items} selectedId={selectedId} />
    </div>
  );
}
