/**
 * PRISM hub — grounded "chat with this audit" proxy (Vercel NODE serverless function).
 *
 * NOTE: this project deploys /api as a Node Lambda (it does NOT honor an `edge`
 * runtime config), so the handler is the Node signature (req, res) and MUST end the
 * response with res.end(). Returning a Web Response here hangs (HTTP 000).
 *
 * Streams a grounded report-QA answer from the Hermes-PRISM API (/v1/responses) — the
 * SAME brain + grounding gate as the Telegram bot — as plain text. Bearer + URL stay
 * server-side (env), same-origin (no CORS). The page's slug binds the right company's
 * report via an invisible [Account: <slug>] prefix.
 *
 * Env (Vercel project — server-side only):
 *   HERMES_API_URL  https://judge.contentengagement.info/hermes-api
 *   HERMES_API_KEY  the bearer
 */

export const config = { maxDuration: 60 };

const HERMES_API_URL = process.env.HERMES_API_URL;
const HERMES_API_KEY = process.env.HERMES_API_KEY;
const MAX_MESSAGE_CHARS = 2000;

// URL slug (page dir) → Hermes report-store slug, where they differ.
const SLUG_ALIASES = { orientaltrading: "oriental-trading" };

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method not allowed" });
    return;
  }
  if (!HERMES_API_URL || !HERMES_API_KEY) {
    res.status(500).json({ error: "chat not configured" });
    return;
  }

  // Vercel parses JSON bodies into req.body; tolerate string/undefined too.
  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  body = body || {};

  const message = typeof body.message === "string" ? body.message.trim() : "";
  const slug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";
  const sid = (typeof body.sid === "string" && body.sid.slice(0, 40)) || "anon";

  if (!message) { res.status(400).json({ error: "empty message" }); return; }
  if (message.length > MAX_MESSAGE_CHARS) { res.status(413).json({ error: "message too long" }); return; }
  if (!slug) { res.status(400).json({ error: "missing slug" }); return; }

  const reportSlug = SLUG_ALIASES[slug] || slug;
  const sessionKey = `agent:main:prism:web:${sid}:acct:${reportSlug}`.replace(/[\r\n\x00]/g, "");
  const conversation = `prism:web:${sid}:${reportSlug}`;
  // Tag every turn (invisible to the visitor) so the report-QA plugin binds this company.
  const input = message.toLowerCase().includes(reportSlug.split("-")[0])
    ? message
    : `[Account: ${reportSlug}] ${message}`;

  let upstream;
  try {
    upstream = await fetch(`${HERMES_API_URL}/v1/responses`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${HERMES_API_KEY}`,
        "Content-Type": "application/json",
        "X-Hermes-Session-Key": sessionKey,
      },
      body: JSON.stringify({ model: "hermes-agent", input, conversation, stream: true, store: true }),
    });
  } catch {
    res.status(502).json({ error: "upstream unreachable" });
    return;
  }
  if (!upstream.ok || !upstream.body) {
    res.status(502).json({ error: `upstream ${upstream.status}` });
    return;
  }

  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("X-Accel-Buffering", "no");

  // Transform the Hermes OpenAI-Responses SSE → plain-text delta stream via res.write().
  const reader = upstream.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
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
            if (payload.delta) res.write(payload.delta);
          } catch {
            /* skip malformed frame */
          }
        }
      }
    }
  } catch {
    /* upstream cut — end what we have */
  }
  res.end();
}
