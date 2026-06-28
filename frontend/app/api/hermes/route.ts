/**
 * W-D Track A — server-side proxy: SPA chat → Hermes-PRISM (one brain).
 *
 * Streams grounded report-QA answers from the Hermes API (/v1/responses) and
 * re-emits them as an AI-SDK v6 UI-message stream so the existing assistant-ui
 * <Thread> renders them unchanged. Bearer + Hermes URL stay SERVER-SIDE (never
 * reach the browser), so there is no CORS surface.
 *
 * Grounding is enforced Hermes-side by the prism-report-qa plugin (same gate as
 * Telegram). v1 = TEXT only (report-QA calls no tools). The interactive
 * run-modules / tool flow is v2.
 *
 * Hermes SSE grammar (captured live — K-r1-deploy.md):
 *   response.created → response.output_item.added → N× response.output_text.delta
 *   (token in `delta`) → response.output_text.done → response.output_item.done →
 *   response.completed (+usage). Provider errors (gemini 429 / anthropic 402) are
 *   NOT SSE error events — they arrive as a normal output_text with status completed.
 *
 * Env (server-side only):
 *   HERMES_API_URL  e.g. https://judge.contentengagement.info/hermes-api
 *   HERMES_API_KEY  the bearer (value after API_SERVER_KEY= in the VPS note file)
 */

import { auth } from "@clerk/nextjs/server";
import { createUIMessageStream, createUIMessageStreamResponse } from "ai";
import { resolveHermesScope, tagAccountForBinding } from "@/lib/hermes-session";

export const maxDuration = 60;

const HERMES_API_URL = process.env.HERMES_API_URL;
const HERMES_API_KEY = process.env.HERMES_API_KEY;
const BYPASS_AUTH = process.env.BYPASS_AUTH === "true";

type UIMessageLike = { role?: string; parts?: Array<{ type?: string; text?: string }>; content?: unknown };

/** Pull plain text out of an AI-SDK UI message (parts[].text) or a plain string. */
function messageText(m: UIMessageLike | undefined): string {
  if (!m) return "";
  if (typeof m.content === "string") return m.content;
  const parts = m.parts ?? [];
  return parts.filter((p) => p?.type === "text" && typeof p.text === "string").map((p) => p.text).join("");
}

/** Minimal SSE parser over a byte ReadableStream → yields {event, data} frames. */
async function* parseSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<{ event: string; data: string }> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx: number;
      // Frames are separated by a blank line.
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        let event = "message";
        const dataLines: string[] = [];
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
        }
        if (dataLines.length) yield { event, data: dataLines.join("\n") };
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function POST(req: Request): Promise<Response> {
  // ── auth: Clerk userId is the cross-device identity anchor (phone↔laptop web) ──
  let repSource = "arijit"; // BYPASS_AUTH dev identity (recon C: hardcoded single rep)
  if (!BYPASS_AUTH) {
    const { userId } = await auth();
    if (!userId) return new Response("Unauthorized", { status: 401 });
    repSource = userId;
  }

  if (!HERMES_API_URL || !HERMES_API_KEY) {
    return new Response(
      JSON.stringify({ error: "Hermes proxy not configured (HERMES_API_URL / HERMES_API_KEY)" }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }

  let body: { messages?: UIMessageLike[]; domain?: string } = {};
  try {
    body = await req.json();
  } catch {
    return new Response("Bad request", { status: 400 });
  }

  const messages = body.messages ?? [];
  const userMessages = messages.filter((m) => m.role === "user");
  const userText = messageText(userMessages[userMessages.length - 1]);
  // The SPA passes the current account domain (Zustand currentDomain) via transport body.
  // If absent, we skip the binding tag and rely on the user naming the company.
  const domain = (body.domain ?? "").trim();

  // Same key+conversation from phone and laptop → one thread, one memory scope.
  const scope = resolveHermesScope(repSource, domain || "unscoped");
  const input = domain ? tagAccountForBinding(userText, domain) : userText;

  const hermesRes = await fetch(`${HERMES_API_URL}/v1/responses`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${HERMES_API_KEY}`,
      "Content-Type": "application/json",
      "X-Hermes-Session-Key": scope.sessionKey,
    },
    body: JSON.stringify({
      model: "hermes-agent",
      input,
      conversation: scope.conversation,
      stream: true,
      store: true,
    }),
  });

  if (!hermesRes.ok || !hermesRes.body) {
    const detail = await hermesRes.text().catch(() => "");
    return new Response(
      JSON.stringify({ error: `Hermes ${hermesRes.status}`, detail: detail.slice(0, 500) }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  const hermesBody = hermesRes.body;
  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const id = crypto.randomUUID();
      writer.write({ type: "text-start", id });
      for await (const frame of parseSSE(hermesBody)) {
        // Hermes uses the OpenAI Responses event grammar.
        if (frame.event === "response.output_text.delta") {
          try {
            const payload = JSON.parse(frame.data) as { delta?: string };
            if (payload.delta) writer.write({ type: "text-delta", id, delta: payload.delta });
          } catch {
            /* skip malformed frame */
          }
        } else if (frame.event === "response.completed" || frame.event === "response.error") {
          break;
        }
      }
      writer.write({ type: "text-end", id });
    },
    onError: (e) => (e instanceof Error ? e.message : "Hermes stream error"),
  });

  return createUIMessageStreamResponse({ stream });
}
