export const config = { maxDuration: 10 };

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method not allowed" });
    return;
  }

  res.setHeader("Cache-Control", "no-store");
  res.status(200).json({ ok: true, mode: "embed" });
}
