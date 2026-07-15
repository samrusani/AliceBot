import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { legacySurfacesEnabled } from "./lib/legacy-surfaces.server";

export function middleware(request: NextRequest) {
  if (legacySurfacesEnabled()) {
    return NextResponse.next();
  }

  const notFoundUrl = request.nextUrl.clone();
  notFoundUrl.pathname = "/_not-found";
  return NextResponse.rewrite(notFoundUrl, { status: 404 });
}

export const config = {
  matcher: ["/approvals", "/tasks", "/gmail", "/calendar"],
};
