import { createLiveAvatarEmbed } from "./_liveavatar.js";

export const config = { maxDuration: 20 };

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method not allowed" });
    return;
  }

  let body = req.body || {};
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }

  const slug = typeof body.slug === "string" ? body.slug : "landing";
  const payload = await createLiveAvatarEmbed({ env: process.env, slug });
  res.setHeader("Cache-Control", "no-store");
  res.status(200).json(payload);
}
