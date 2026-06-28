/**
 * PRISM hub — grounded "chat with this audit" proxy (Vercel Edge function).
 *
 * Each published report page (/<slug>/) gets a chat widget that POSTs here with the
 * page's slug. We stream a grounded report-QA answer from the Hermes-PRISM API
 * (/v1/responses) — the SAME brain + grounding gate as the Telegram bot — and relay
 * it as plain text. The Hermes bearer + URL stay SERVER-SIDE (env), never in the
 * browser, and the call is same-origin so there is no CORS surface.
 *
 * The Hermes prism-report-qa plugin binds the report by content-matching the message
 * text per session; we prefix `[Account: <slug>]` so the right company's report is
 * bound deterministically.
 *
 * Env (Vercel project settings — server-side only):
 *   HERMES_API_URL  https://judge.contentengagement.info/hermes-api
 *   HERMES_API_KEY  the bearer
 */

export const config = { runtime: "edge" };

const HERMES_API_URL = process.env.HERMES_API_URL;
const HERMES_API_KEY = process.env.HERMES_API_KEY;

const MAX_MESSAGE_CHARS = 2000;

function bad(status, msg) {
  return new Response(JSON.stringify({ error: msg }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export default async function handler(req) {
  if (req.method !== "POST") return bad(405, "method not allowed");
  if (!HERMES_API_URL || !HERMES_API_KEY) return bad(500, "chat not configured");

  let body;
  try {
    body = await req.json();
  } catch {
    return bad(400, "invalid body");
  }

  const message = typeof body.message === "string" ? body.message.trim() : "";
  const slug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";
  // Per-browser anonymous id from the widget (localStorage) → stable thread per visitor+page.
  const sid = (typeof body.sid === "string" && body.sid.slice(0, 40)) || "anon";

  if (!message) return bad(400, "empty message");
  if (message.length > MAX_MESSAGE_CHARS) return bad(413, "message too long");
  if (!slug) return bad(400, "missing slug");

  const sessionKey = `agent:main:prism:web:${sid}:acct:${slug}`.replace(/[\r\n\x00]/g, "");
  const conversation = `prism:web:${sid}:${slug}`;
  // Tag every turn (invisible to the visitor) so the report-QA plugin binds this company.
  const input = message.toLowerCase().includes(slug.split("-")[0])
    ? message
    : `[Account: ${slug}] ${message}`;

  let upstream;
  try {
    upstream = await fetch(`${HERMES_API_URL}/v1/responses`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${HERMES_API_KEY}`,
        "Content-Type": "application/json",
        "X-Hermes-Session-Key": sessionKey,
      },
      body: JSON.stringify({
        model: "hermes-agent",
        input,
        conversation,
        stream: true,
        store: true,
      }),
    });
  } catch (e) {
    return bad(502, "upstream unreachable");
  }
  if (!upstream.ok || !upstream.body) return bad(502, `upstream ${upstream.status}`);

  // Transform the Hermes OpenAI-Responses SSE into a plain-text delta stream the widget appends.
  const reader = upstream.body.getReader();
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();
  let buf = "";

  const stream = new ReadableStream({
    async pull(controller) {
      const { done, value } = await reader.read();
      if (done) {
        controller.close();
        return;
      }
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        let event = "message";
        const dataLines = [];
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
        }
        if (event === "response.output_text.delta" && dataLines.length) {
          try {
            const payload = JSON.parse(dataLines.join("\n"));
            if (payload.delta) controller.enqueue(encoder.encode(payload.delta));
          } catch {
            /* skip malformed frame */
          }
        }
      }
    },
    cancel() {
      reader.cancel().catch(() => {});
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Accel-Buffering": "no",
    },
  });
}
