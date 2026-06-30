import { auth } from "@clerk/nextjs/server";

export const maxDuration = 60;

const HERMES_API_URL = process.env.HERMES_API_URL;
const HERMES_API_KEY = process.env.HERMES_API_KEY;
const SLUG_ALIASES: Record<string, string> = { orientaltrading: "oriental-trading" };
const MAX_MESSAGE_CHARS = 2000;

export async function POST(req: Request): Promise<Response> {
  const { userId } = await auth();
  if (!userId) return new Response("Unauthorized", { status: 401 });
  if (!HERMES_API_URL || !HERMES_API_KEY) return new Response("chat not configured", { status: 500 });

  let body: { message?: string; slug?: string; sid?: string } = {};
  try {
    body = await req.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  const message = typeof body.message === "string" ? body.message.trim() : "";
  const slug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";
  const sid = (typeof body.sid === "string" && body.sid.slice(0, 40)) || "anon";
  if (!message) return new Response("empty message", { status: 400 });
  if (message.length > MAX_MESSAGE_CHARS) return new Response("message too long", { status: 413 });
  if (!slug) return new Response("missing slug", { status: 400 });

  const reportSlug = SLUG_ALIASES[slug] || slug;
  const sessionKey = `agent:main:prism:web:${sid}:acct:${reportSlug}`.replace(/[\r\n\x00]/g, "");
  const conversation = `prism:web:${sid}:${reportSlug}`;
  const input = message.toLowerCase().includes(reportSlug.split("-")[0])
    ? message
    : `[Account: ${reportSlug}] ${message}`;

  const upstream = await fetch(`${HERMES_API_URL}/v1/responses`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${HERMES_API_KEY}`,
      "Content-Type": "application/json",
      "X-Hermes-Session-Key": sessionKey,
    },
    body: JSON.stringify({ model: "hermes-agent", input, conversation, stream: true, store: true }),
  }).catch(() => null);

  if (!upstream || !upstream.ok || !upstream.body) {
    return new Response("upstream error", { status: 502 });
  }

  const upstreamBody = upstream.body;
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const reader = upstreamBody.getReader();
      const decoder = new TextDecoder();
      const encoder = new TextEncoder();
      let buf = "";
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx: number;
          while ((idx = buf.indexOf("\n\n")) !== -1) {
            const frame = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            let event = "message";
            const dataLines: string[] = [];
            for (const line of frame.split("\n")) {
              if (line.startsWith("event:")) event = line.slice(6).trim();
              else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
            }
            if (event === "response.output_text.delta" && dataLines.length) {
              try {
                const payload = JSON.parse(dataLines.join("\n")) as { delta?: string };
                if (payload.delta) controller.enqueue(encoder.encode(payload.delta));
              } catch {
                /* skip malformed frame */
              }
            } else if (event === "response.completed" || event === "response.error") {
              break;
            }
          }
        }
      } catch {
        /* upstream cut — end what we have */
      } finally {
        reader.releaseLock();
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
  });
}
