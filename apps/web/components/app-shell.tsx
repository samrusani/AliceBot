"use client";

import type { ReactNode } from "react";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  {
    href: "/",
    label: "Overview",
    caption: "Shell landing and governed surface summary",
  },
  {
    href: "/vnext",
    label: "vNext Brain",
    caption: "Second-brain dashboard, review, briefs, generated artifacts, and graph",
  },
  {
    href: "/onboarding",
    label: "Onboarding",
    caption: "Instruction-only hosted setup guide",
  },
  {
    href: "/settings",
    label: "Settings",
    caption: "Hosted preferences and device visibility",
  },
  {
    href: "/admin",
    label: "Admin",
    caption: "Hosted workspace, delivery, rollout, and incident visibility",
  },
  {
    href: "/chat",
    label: "Requests",
    caption: "Compose bounded operator requests",
  },
  {
    href: "/approvals",
    label: "Approvals",
    caption: "Review approval queue and inspector",
  },
  {
    href: "/tasks",
    label: "Tasks",
    caption: "Inspect lifecycle state and task steps",
  },
  {
    href: "/artifacts",
    label: "Artifacts",
    caption: "Review task artifacts, workspaces, and chunks",
  },
  {
    href: "/gmail",
    label: "Gmail",
    caption: "Review connected accounts and ingest one selected message",
  },
  {
    href: "/calendar",
    label: "Calendar",
    caption: "Review connected accounts and ingest one selected event",
  },
  {
    href: "/memories",
    label: "Memories",
    caption: "Review memory detail, revisions, and labels",
  },
  {
    href: "/continuity",
    label: "Continuity",
    caption: "Capture, recall, review, and resume continuity state",
  },
  {
    href: "/chief-of-staff",
    label: "Chief-of-Staff",
    caption: "Deterministic priorities, rationale, and next action",
  },
  {
    href: "/entities",
    label: "Entities",
    caption: "Review entity detail and related edges",
  },
  {
    href: "/traces",
    label: "Traces",
    caption: "Explain-why and governed action review",
  },
];

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="shell-chrome">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <div className="shell">
        <aside className="shell-sidebar" aria-label="Primary navigation">
          <div className="brand-copy">
            <span className="brand-mark" aria-hidden="true">
              AB
            </span>
            <p className="eyebrow">AliceBot</p>
            <p className="brand-title">Operator shell</p>
            <p className="brand-description">
              Calm, governed views for hosted onboarding/settings plus requests, approvals, tasks,
              hosted admin operations, artifacts, Gmail, Calendar, memories, chief-of-staff
              priorities, continuity, vNext second-brain review, entities, and explainability.
            </p>
          </div>

          <nav className="shell-nav">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`shell-nav__item${isActive(pathname, item.href) ? " is-active" : ""}`}
                aria-current={isActive(pathname, item.href) ? "page" : undefined}
              >
                <span className="shell-nav__title">{item.label}</span>
                <span className="shell-nav__caption">{item.caption}</span>
              </Link>
            ))}
          </nav>

          <div className="shell-note">
            <p className="shell-note__title">Current posture</p>
            <p className="muted-copy">
              This shell stays narrow on purpose. It exposes existing backend seams without adding
              new product scope or hiding governance state.
            </p>
          </div>
        </aside>

        <div className="shell-column">
          <header className="shell-topbar">
            <div className="shell-topbar__row">
              <div className="brand-copy">
                <p className="eyebrow">MVP Web Shell</p>
                <p className="shell-topbar__title">Governed operator interface</p>
              </div>

              <div className="topbar-status" aria-label="Shell status">
                <span className="subtle-chip">Single-user v1</span>
                <span className="subtle-chip">Hosted bootstrap seams + operator shell</span>
              </div>
            </div>

            <nav className="shell-nav shell-nav--mobile" aria-label="Mobile navigation">
              {navigation.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`shell-nav__item${isActive(pathname, item.href) ? " is-active" : ""}`}
                  aria-current={isActive(pathname, item.href) ? "page" : undefined}
                >
                  <span className="shell-nav__title">{item.label}</span>
                  <span className="shell-nav__caption">{item.caption}</span>
                </Link>
              ))}
            </nav>
          </header>

          <main id="main-content" className="shell-main" tabIndex={-1}>
            <div className="content-frame">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
