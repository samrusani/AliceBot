import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "../components/app-shell";

import "./globals.css";

export const metadata: Metadata = {
  title: "AliceBot Operator Shell",
  description: "Governed operator interface for requests, approvals, tasks, memories, and explainability.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
