import Link from "next/link";

import { PageHeader } from "../components/page-header";
import { SectionCard } from "../components/section-card";
import { StatusBadge } from "../components/status-badge";

const coreRouteCards = [
  {
    href: "/vnext",
    title: "vNext Brain Workspace",
    description:
      "Review memory candidates, provenance-aware answers, briefs, projects, beliefs, loops, graph state, and privacy labels.",
    status: "active",
  },
  {
    href: "/artifacts",
    title: "Artifact Review",
    description:
      "Inspect persisted artifact metadata and ordered chunk evidence without depending on the legacy task-workspace API.",
    status: "ingested",
  },
  {
    href: "/memories",
    title: "Memory Review",
    description: "Inspect active memories, revisions, labels, quality gates, and review queues.",
    status: "requires_review",
  },
  {
    href: "/continuity",
    title: "Continuity Workspace",
    description:
      "Capture and recall continuity, review corrections and open loops, and inspect daily, weekly, and resumption views.",
    status: "active",
  },
  {
    href: "/entities",
    title: "Entity Review",
    description: "Inspect tracked entities, selected detail, and related edges.",
    status: "active",
  },
  {
    href: "/traces",
    title: "Explain-Why Review",
    description: "Trace context assembly and governed actions through an evidence-first review surface.",
    status: "executed",
  },
];

const legacyRouteCards = [
  {
    href: "/approvals",
    title: "Legacy Approval Inbox",
    description: "Review the compatibility approval and execution workflow.",
    status: "legacy",
  },
  {
    href: "/tasks",
    title: "Legacy Task Inspection",
    description: "Inspect compatibility task, run, and step lifecycle state.",
    status: "legacy",
  },
  {
    href: "/gmail",
    title: "Legacy Gmail Review",
    description: "Use the manual operator-token account and message-ingestion path.",
    status: "legacy",
  },
  {
    href: "/calendar",
    title: "Legacy Calendar Review",
    description: "Use the manual operator-token account and event-ingestion path.",
    status: "legacy",
  },
];

const consoleNotes = [
  "Memory and retrieval quality stay visible beside their evidence and review state.",
  "The default console contains only core and adjacent continuity surfaces.",
  "Legacy task and connector workflows require an explicit server-side opt-in.",
  "Removed hosted, chat, and chief-of-staff surfaces are not advertised or routable.",
];

export function HomePageContent({
  legacyEnabled,
}: {
  legacyEnabled: boolean;
}) {
  const routeCards = legacyEnabled
    ? [...coreRouteCards, ...legacyRouteCards]
    : coreRouteCards;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Alice"
        title="Continuity and memory review console"
        description="A local-first interface for retrieval quality, continuity state, durable artifacts, and explainable agent context."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">v0.11 candidate</span>
            <span className="subtle-chip">
              {legacyEnabled ? "Legacy surfaces enabled" : "Core surfaces only"}
            </span>
          </div>
        }
      />

      <section className="metric-grid" aria-label="Console summary">
        <SectionCard className="section-card--metric">
          <div className="metric-value">{legacyEnabled ? "11" : "7"}</div>
          <div className="metric-label">Visible views</div>
          <p className="metric-detail">
            Seven core and adjacent views are always available; four compatibility views require
            the server-side legacy flag.
          </p>
        </SectionCard>
        <SectionCard className="section-card--metric">
          <div className="metric-value">11</div>
          <div className="metric-label">Core MCP tools</div>
          <p className="metric-detail">
            The default agent interface stays centered on capture, recall, resume, review,
            correction, explanation, and memory management.
          </p>
        </SectionCard>
        <SectionCard className="section-card--metric">
          <div className="metric-value">2</div>
          <div className="metric-label">Storage engines</div>
          <p className="metric-detail">
            Shared memory and retrieval contracts remain exercised against PostgreSQL and SQLite.
          </p>
        </SectionCard>
        <SectionCard className="section-card--metric">
          <div className="metric-value">1</div>
          <div className="metric-label">Local workspace</div>
          <p className="metric-detail">
            The active identity boundary is a deterministic single-workspace bootstrap.
          </p>
        </SectionCard>
      </section>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Review surfaces"
          title="Continuity layer"
          description="Every default route supports agent context, retrieval quality, or evidence review."
        >
          <div className="route-grid">
            {routeCards.map((route) => (
              <Link key={route.href} href={route.href} className="nav-card">
                <div className="nav-card__topline">
                  <h3>{route.title}</h3>
                  <StatusBadge status={route.status} />
                </div>
                <p>{route.description}</p>
                <span className="nav-card__cta">Open view</span>
              </Link>
            ))}
          </div>
        </SectionCard>

        <div className="stack">
          <SectionCard
            eyebrow="Product boundary"
            title="Narrow by design"
            description="The console matches the advertised agent-interface and memory-quality product."
          >
            <ul className="bullet-list">
              {consoleNotes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </SectionCard>
          <SectionCard
            eyebrow="Compatibility"
            title="Legacy surfaces are explicit"
            description="Approvals, tasks, Gmail, and Calendar are absent by default and mount only when ALICE_LEGACY_SURFACES=1."
          >
            <p className="muted-copy">
              The flag is resolved on the server. Browser code receives only the resolved boolean,
              so there is no public-environment bypass.
            </p>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

