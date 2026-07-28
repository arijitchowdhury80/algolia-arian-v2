export const LIVEAVATAR_API_BASE = "https://api.liveavatar.com";
export const EMBED_SANDBOX_AVATAR_ID = "65f9e3c9-d48b-4118-b73a-4ae2e3cbb8f0";
export const SESSION_SANDBOX_AVATAR_ID = "dd73ea75-1218-4ef3-92ce-606d5f7fbc0a";

const DEFAULT_TIMEOUT_MS = 12000;

export function titleFromSlug(slug) {
  return String(slug || "landing")
    .replace(/[^a-z0-9-]/gi, "")
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ") || "PRISM";
}

export function buildCassandraContextPrompt({ slug = "landing" } = {}) {
  const account = titleFromSlug(slug);
  return [
    "You are Cassandra, the human-facing operator inside PRISM.",
    `You are speaking in the context of the ${account} PRISM report or PRISM product demo.`,
    "Sound like a sharp senior sales coach: direct, warm, concise, and useful.",
    "The active PRISM report, audit evidence, screenshots, findings, and sales assets are the source of truth.",
    "Do not invent prospect facts, ROI claims, competitors, search defects, or sales plays.",
    "If the answer is not in the active PRISM report, say that clearly and suggest what to inspect next.",
    "Keep answers short enough for a seller to use in a live account conversation.",
  ].join("\n");
}

export function readLiveAvatarConfig(env = {}) {
  const apiKey = env.LIVEAVATAR_API_KEY || env.HEYGEN_API_KEY || "";
  const mode = (env.LIVEAVATAR_MODE || "embed").toLowerCase();
  const sandbox = env.LIVEAVATAR_SANDBOX !== "0";
  return {
    apiKey,
    contextId: env.LIVEAVATAR_CONTEXT_ID || "",
    mode,
    sandbox,
    avatarId: env.LIVEAVATAR_AVATAR_ID || EMBED_SANDBOX_AVATAR_ID,
  };
}

export async function createLiveAvatarEmbed({ env = {}, slug = "landing", fetchImpl = fetch } = {}) {
  const config = readLiveAvatarConfig(env);
  if (!config.apiKey) return unavailable("missing_api_key", config);
  try {
    const contextId = config.contextId || await createContext({ config, slug, fetchImpl });
    const embed = await postJson({
      url: `${LIVEAVATAR_API_BASE}/v2/embeddings`,
      apiKey: config.apiKey,
      fetchImpl,
      body: { avatar_id: config.avatarId, context_id: contextId, is_sandbox: config.sandbox },
    });
    const url = embed?.data?.url;
    if (!url) return unavailable("liveavatar_unavailable", config);
    return { configured: true, mode: "embed", sandbox: config.sandbox, avatar_id: config.avatarId, url };
  } catch {
    return unavailable("liveavatar_unavailable", config);
  }
}

async function createContext({ config, slug, fetchImpl }) {
  const context = await postJson({
    url: `${LIVEAVATAR_API_BASE}/v1/contexts`,
    apiKey: config.apiKey,
    fetchImpl,
    body: {
      name: `PRISM Cassandra - ${titleFromSlug(slug)}`,
      prompt: buildCassandraContextPrompt({ slug }),
      opening_text: "I'm Cassandra. Ask me what PRISM found, what matters, or what to do next.",
    },
  });
  const contextId = context?.data?.id;
  if (!contextId) throw new Error("context_not_created");
  return contextId;
}

async function postJson({ url, apiKey, body, fetchImpl }) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  try {
    const response = await fetchImpl(url, {
      method: "POST",
      headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`liveavatar_${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

function unavailable(reason, config) {
  return { configured: false, reason, mode: "embed", sandbox: config.sandbox };
}
