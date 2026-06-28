import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// /api/chat removed from public — chat now flows through /api/hermes (Clerk-protected,
// non-public by default). No unauthenticated path reaches a brain that holds account intel.
const isPublicRoute = createRouteMatcher(["/sign-in(.*)", "/demo(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  // Bypass auth for local development
  if (process.env.BYPASS_AUTH === "true") {
    return NextResponse.next();
  }
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};
