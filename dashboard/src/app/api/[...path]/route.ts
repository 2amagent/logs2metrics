const API_URL = process.env.LOGTRIAGE_API_URL ?? "http://localhost:8000";

async function proxy(request: Request, path: string[]): Promise<Response> {
  const incoming = new URL(request.url);
  // FastAPI's template endpoints live under /api/... themselves, so forward
  // the full matched path (not just the [...path] segments) to preserve it.
  const target = new URL(`api/${path.join("/")}`, `${API_URL}/`);
  target.search = incoming.search;

  const headers = new Headers(request.headers);
  headers.delete("host");

  const init: RequestInit = {
    method: request.method,
    headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.text(),
  };

  const upstream = await fetch(target, init);
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: Request, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function POST(request: Request, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxy(request, path);
}
