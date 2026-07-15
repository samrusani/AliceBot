import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "../components/app-shell";
import { legacySurfacesEnabled } from "../lib/legacy-surfaces.server";

import "./globals.css";

export const metadata: Metadata = {
  title: "Alice Continuity Console",
  description:
    "Local-first review console for memory, continuity, retrieval, artifacts, entities, and traces.",
};

// The server-only legacy switch is resolved when the runtime mounts, not frozen at build time.
export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell legacySurfacesEnabled={legacySurfacesEnabled()}>{children}</AppShell>
      </body>
    </html>
  );
}
