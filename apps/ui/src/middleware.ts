import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { isAuthDisabled } from "@/lib/auth-mode";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/webhooks(.*)",
]);

// Paths that bots/scanners probe but don't exist in the app.
// Return 404 immediately to avoid Clerk parsing malformed request bodies.
const BOT_PROBE_PATHS = ["/webhook", "/register", "/admin", "/wp-admin", "/xmlrpc.php"];

function isBotProbe(request: NextRequest): boolean {
  const path = request.nextUrl.pathname;
  return BOT_PROBE_PATHS.some((probe) => path.startsWith(probe));
}

const demoMiddleware = (request: NextRequest) => {
  if (isBotProbe(request)) {
    return new NextResponse(null, { status: 404 });
  }
  return NextResponse.next();
};

const authenticatedMiddleware = clerkMiddleware(async (auth, request) => {
  // Block known bot probe paths early — prevents FormData parsing errors
  if (isBotProbe(request)) {
    return new NextResponse(null, { status: 404 });
  }

  // Protect all routes except public ones
  if (!isPublicRoute(request)) {
    const { userId } = await auth();

    if (!userId) {
      // Preserve the return URL when redirecting to sign-in
      const baseUrl = process.env.NEXT_PUBLIC_URL || request.url;
      const signInUrl = new URL("/sign-in", baseUrl);
      const returnUrl = new URL(request.nextUrl.pathname + request.nextUrl.search, baseUrl);
      signInUrl.searchParams.set("redirect_url", returnUrl.toString());
      return NextResponse.redirect(signInUrl);
    }
  }
});

export default isAuthDisabled() ? demoMiddleware : authenticatedMiddleware;

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
