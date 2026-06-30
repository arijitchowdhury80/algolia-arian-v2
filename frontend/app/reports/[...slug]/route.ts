import { auth } from "@clerk/nextjs/server";
import { readFile, realpath } from "node:fs/promises";
import path from "node:path";

const REPORTS_DIR = path.resolve(
  process.env.REPORTS_HTML_DIR ?? path.join(process.cwd(), "report-data"),
);

const CONTENT_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".ico": "image/x-icon",
};

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug?: string[] }> },
): Promise<Response> {
  // Load-bearing: dotted paths (.png/.js) bypass middleware, so gate HERE.
  const { userId } = await auth();
  if (!userId) return new Response("Unauthorized", { status: 401 });
  // Note: this handler self-authenticates because Next middleware skips dotted
  // paths (.png). BYPASS_AUTH (middleware-only) does NOT apply here — dev access
  // to gated reports requires a real signed-in Clerk session.

  const segments = (await params).slug ?? [];
  const rel = segments.join("/");
  // A bare /reports/<slug> or trailing slash → that report's index.html.
  const requested = !rel || rel.endsWith("/") || !path.extname(rel)
    ? path.join(rel, "index.html")
    : rel;

  const abs = path.resolve(REPORTS_DIR, requested);
  // Path-traversal guard: resolved path must stay inside REPORTS_DIR.
  if (abs !== REPORTS_DIR && !abs.startsWith(REPORTS_DIR + path.sep)) {
    return new Response("Forbidden", { status: 403 });
  }

  // Resolve symlinks and re-check containment (a symlink inside REPORTS_DIR
  // could otherwise point outside it and be followed by readFile).
  const realBase = await realpath(REPORTS_DIR).catch(() => REPORTS_DIR);
  const realAbs = await realpath(abs).catch(() => null);
  if (!realAbs) return new Response("Not found", { status: 404 });
  if (realAbs !== realBase && !realAbs.startsWith(realBase + path.sep)) {
    return new Response("Forbidden", { status: 403 });
  }

  let data: Buffer;
  try {
    data = await readFile(realAbs);
  } catch {
    return new Response("Not found", { status: 404 });
  }
  const ext = path.extname(abs).toLowerCase();
  return new Response(new Uint8Array(data), {
    status: 200,
    headers: { "Content-Type": CONTENT_TYPES[ext] ?? "application/octet-stream" },
  });
}
