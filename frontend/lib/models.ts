/**
 * Available AI models — used by the chat route and the model selector UI.
 */
export const AVAILABLE_MODELS = [
  { id: "gpt-4o", label: "GPT-4o", provider: "openai" },
  { id: "gpt-4o-mini", label: "GPT-4o Mini", provider: "openai" },
  { id: "o3-mini", label: "o3-mini", provider: "openai" },
  { id: "claude-sonnet-4", label: "Claude Sonnet 4", provider: "anthropic" },
  { id: "claude-haiku-4.5", label: "Claude Haiku 4.5", provider: "anthropic" },
  { id: "gemini-3.1-flash-lite-preview", label: "Gemini 3.1 Flash Lite", provider: "google" },
  { id: "gemini-1.5-pro", label: "Gemini 1.5 Pro", provider: "google" },
] as const;

export type ModelId = (typeof AVAILABLE_MODELS)[number]["id"];
