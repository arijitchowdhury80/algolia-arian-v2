import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

/*
Scenario list:
- Happy path: backend creates a sandbox LiveAvatar embed with API key + context ID and returns only browser-safe fields.
- Empty configuration: missing API key returns an unconfigured payload and never calls LiveAvatar.
- Context fallback: missing context ID creates a Cassandra context before creating the embed.
- Contract: landing page exposes a Cassandra Live mount and loads the browser module.
- Contract: chat widget exposes a Live Avatar affordance inside the existing Cassandra drawer.
- Failure mode: LiveAvatar upstream errors return a controlled unavailable payload.
*/

import {
  EMBED_SANDBOX_AVATAR_ID,
  buildCassandraContextPrompt,
  createLiveAvatarEmbed,
  readLiveAvatarConfig,
} from "../api/avatar/_liveavatar.js";

const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
const chatWidget = await readFile(new URL("../chat-widget.js", import.meta.url), "utf8");

test("readLiveAvatarConfig_without_api_key_disables_backend_calls", async () => {
  const calls = [];
  const result = await createLiveAvatarEmbed({
    env: {},
    slug: "petsmart",
    fetchImpl: async (...args) => {
      calls.push(args);
      throw new Error("fetch should not be called");
    },
  });

  assert.deepEqual(result, {
    configured: false,
    reason: "missing_api_key",
    mode: "embed",
    sandbox: true,
  });
  assert.equal(calls.length, 0);
});

test("createLiveAvatarEmbed_with_context_id_returns_browser_safe_embed_url", async () => {
  const calls = [];
  const result = await createLiveAvatarEmbed({
    env: {
      LIVEAVATAR_API_KEY: "secret-liveavatar-key",
      LIVEAVATAR_CONTEXT_ID: "ctx_123",
    },
    slug: "petsmart",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      assert.equal(url, "https://api.liveavatar.com/v2/embeddings");
      assert.equal(init.headers["X-API-KEY"], "secret-liveavatar-key");
      assert.deepEqual(JSON.parse(init.body), {
        avatar_id: EMBED_SANDBOX_AVATAR_ID,
        context_id: "ctx_123",
        is_sandbox: true,
      });
      return Response.json({
        data: { url: "https://embed.liveavatar.com/v1/demo" },
      });
    },
  });

  assert.equal(calls.length, 1);
  assert.deepEqual(result, {
    configured: true,
    mode: "embed",
    sandbox: true,
    avatar_id: EMBED_SANDBOX_AVATAR_ID,
    url: "https://embed.liveavatar.com/v1/demo",
  });
  assert.doesNotMatch(JSON.stringify(result), /secret-liveavatar-key/);
});

test("createLiveAvatarEmbed_without_context_id_creates_cassandra_context_first", async () => {
  const calls = [];
  const result = await createLiveAvatarEmbed({
    env: { LIVEAVATAR_API_KEY: "secret-liveavatar-key" },
    slug: "nike",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      if (url.endsWith("/v1/contexts")) {
        const body = JSON.parse(init.body);
        assert.match(body.name, /PRISM Cassandra/);
        assert.match(body.prompt, /Nike/);
        assert.match(body.prompt, /PRISM report/);
        return Response.json({ data: { id: "ctx_created" } });
      }
      assert.equal(url, "https://api.liveavatar.com/v2/embeddings");
      assert.equal(JSON.parse(init.body).context_id, "ctx_created");
      return Response.json({ data: { url: "https://embed.liveavatar.com/v1/created" } });
    },
  });

  assert.equal(calls.length, 2);
  assert.equal(result.url, "https://embed.liveavatar.com/v1/created");
});

test("createLiveAvatarEmbed_when_upstream_fails_returns_unavailable_payload", async () => {
  const result = await createLiveAvatarEmbed({
    env: {
      LIVEAVATAR_API_KEY: "secret-liveavatar-key",
      LIVEAVATAR_CONTEXT_ID: "ctx_123",
    },
    slug: "petsmart",
    fetchImpl: async () => new Response("nope", { status: 500 }),
  });

  assert.deepEqual(result, {
    configured: false,
    reason: "liveavatar_unavailable",
    mode: "embed",
    sandbox: true,
  });
});

test("buildCassandraContextPrompt_keeps_avatar_grounded_in_prism", () => {
  const prompt = buildCassandraContextPrompt({ slug: "petsmart" });

  assert.match(prompt, /Cassandra/);
  assert.match(prompt, /senior sales coach/);
  assert.match(prompt, /Petsmart/);
  assert.match(prompt, /active PRISM report/);
  assert.match(prompt, /Do not invent/);
});

test("landing_page_mounts_cassandra_live_avatar_panel", () => {
  assert.match(html, /<script src="\/cassandra-live\.js" defer><\/script>/);
  assert.match(html, /data-cassandra-live/);
  assert.match(html, /data-avatar-slug="landing"/);
  assert.match(html, /Start live avatar/);
  assert.match(html, /LiveAvatar/);
});

test("chat_widget_offers_live_avatar_inside_cassandra_drawer", () => {
  assert.match(chatWidget, /id="prism-chat-live"/);
  assert.match(chatWidget, /data-cassandra-live/);
  assert.match(chatWidget, /Start live avatar/);
  assert.match(chatWidget, /cassandra-live\.js/);
});

test("liveavatar_config_defaults_to_sandbox_embed", () => {
  const config = readLiveAvatarConfig({
    LIVEAVATAR_API_KEY: "secret-liveavatar-key",
    LIVEAVATAR_CONTEXT_ID: "ctx_123",
  });

  assert.equal(config.mode, "embed");
  assert.equal(config.sandbox, true);
  assert.equal(config.avatarId, EMBED_SANDBOX_AVATAR_ID);
});
