"use client";

import type { ReactNode } from "react";

import Link from "next/link";
import { usePathname } from "next/navigation";

const coreNavigation = [
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
    href: "/artifacts",
    label: "Artifacts",
    caption: "Review persisted artifacts and ordered chunk evidence",
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

const legacyNavigation = [
  {
    href: "/approvals",
    label: "Approvals",
    caption: "Legacy approval queue and execution inspector",
  },
  {
    href: "/tasks",
    label: "Tasks",
    caption: "Legacy task lifecycle and step inspection",
  },
  {
    href: "/gmail",
    label: "Gmail",
    caption: "Legacy manual account and message ingestion",
  },
  {
    href: "/calendar",
    label: "Calendar",
    caption: "Legacy manual account and event ingestion",
  },
];

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname.startsWith(href);
}

export function AppShell({
  children,
  legacySurfacesEnabled,
}: {
  children: ReactNode;
  legacySurfacesEnabled: boolean;
}) {
  const pathname = usePathname();
  const navigation = legacySurfacesEnabled
    ? [...coreNavigation, ...legacyNavigation]
    : coreNavigation;

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
            <p className="brand-title">Continuity console</p>
            <p className="brand-description">
              Calm, local-first review for memory, continuity, artifacts, entity context,
              retrieval quality, and explainability.
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
                <p className="eyebrow">Alice continuity layer</p>
                <p className="shell-topbar__title">Evidence-first review console</p>
              </div>

              <div className="topbar-status" aria-label="Shell status">
                <span className="subtle-chip">Local-first</span>
                <span className="subtle-chip">
                  {legacySurfacesEnabled ? "Legacy surfaces enabled" : "Core surfaces only"}
                </span>
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
