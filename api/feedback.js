// api/feedback.js - Vercel Node lambda. Stateless FS, so this forwards to console + returns ok.
// Durable capture for prism.chowmes.com is the VPS chat-proxy route (Step 3).
export default async function handler(req, res) {
  if (req.method !== "POST") { res.status(405).json({ ok: false }); return; }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  console.log("IA_FEEDBACK", JSON.stringify({ ...body, ts: new Date().toISOString() }));
  res.status(200).json({ ok: true });
}
