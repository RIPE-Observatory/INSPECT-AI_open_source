import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { getServerApiV1BaseUrl } from "@/lib/api";
import { isAuthDisabled } from "@/lib/auth-mode";
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

async function proxyRequest(request: NextRequest, context: RouteContext) {
  const params = await context.params;

  const pathSegments = params?.path?.join("/") ?? "";
  const baseUrl = getServerApiV1BaseUrl().replace(/\/$/, "");
  const targetUrl = `${baseUrl}/${pathSegments}${request.nextUrl.search}`;

  const headers = new Headers(request.headers);
  headers.set("X-Forwarded-For", request.headers.get("x-forwarded-for") ?? "");
  headers.set("X-Forwarded-Host", request.headers.get("host") ?? "");
  headers.set("X-Forwarded-Proto", request.nextUrl.protocol.replace(":", ""));
  headers.delete("host");

  if (!isAuthDisabled()) {
    const { auth } = await import("@clerk/nextjs/server");
    const { userId, getToken } = await auth();

    if (!userId) {
      console.warn("Proxy request without authenticated user", {
        path: params?.path,
        headers: Array.from(request.headers.entries()).filter(([key]) => key.startsWith("x-clerk")),
      });
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const templateName = process.env.CLERK_JWT_TEMPLATE_NAME;
    if (!templateName) {
      return NextResponse.json(
        { error: "Backend access token template not configured" },
        { status: 500 },
      );
    }

    let token: string | null = null;
    try {
      token = await getToken({ template: templateName });
    } catch {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    if (!token) {
      console.error(
        `Clerk JWT template '${templateName}' did not return a token. Ensure the template exists and is assigned to the application.`,
      );
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    headers.set("Authorization", `Bearer ${token}`);
  }

  for (const hopHeader of HOP_BY_HOP_HEADERS) {
    headers.delete(hopHeader);
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
    cache: "no-store",
  };

  if (!/^(GET|HEAD)$/i.test(request.method)) {
    const body = await request.arrayBuffer();
    init.body = body;
  }

  const backendResponse = await fetch(targetUrl, init);

  const responseHeaders = new Headers();
  backendResponse.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  return new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

export function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function PATCH(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function HEAD(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function OPTIONS(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
