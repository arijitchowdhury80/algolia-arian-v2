# Cassandra Canonical Output Contract

**Status:** active · **Decided:** 2026-06-30 · **Scope:** Telegram + SPA (WhatsApp/SMS deferred)
**Architecture:** A — Subset (plain-text-safe LCD), no per-channel transform layer.

## The problem it solves

Cassandra (Hermes prism-report-qa) answers the same prospect over multiple channels. Each channel
renders Markdown differently. Goal: output that renders **identically** on every channel without a
fragile per-channel transform layer.

## Key realization

The hard cross-channel break (headers / tables / bullet brochures rendering differently) **does not
exist by design.** `SOUL.md` already forbids those features — Cassandra "texts, doesn't lecture,"
defaults to 2–4 sentences, "never a brochure," no bullet lists, no bold headers. So the canonical
format is *already* close to plain conversational prose, which renders identically everywhere.

The only genuine divergence left is **links**: a Markdown link `[text](url)` renders on SPA but
shows literally on Telegram (no `parse_mode` set). And a **bare URL** autolinks natively on Telegram
but was *not* clickable on SPA (the SPA renderer only linked `[text](url)`).

## The contract

Cassandra's output, when it must include a reference/URL:

| Rule | Why |
|---|---|
| Emit **bare URLs** (`https://…`), never `[text](url)` Markdown links | Bare URL autolinks on Telegram natively; SPA now autolinks it too (see fix). Identical clickable render on both. |
| No `**bold**` / `*italic*` *as load-bearing meaning* | Telegram (no parse_mode) shows the asterisks literally. SOUL already discourages this. |
| No `#` headers, no tables, no numbered-list brochures | SOUL already forbids. Render literally on Telegram. |
| `- ` bullets allowed *only* when explicitly asked to "break it down" | Degrade to readable plain text on Telegram; render as `<ul>` on SPA. Both acceptable. |
| Default = short conversational prose | Renders identically with zero transform. |

This is the **floor renderer = plain text**. Anything in the contract survives a channel that does no
Markdown parsing at all.

## Implementation

1. **SPA renderer** (`~/prism-hub/chat-widget.js`, `mdToHtml`): added bare-URL autolinking after the
   `[text](url)` rule. Preceding-char guard skips URLs already inside an `href="…"`; trailing
   punctuation kept outside the link. Verified: bare URL links, `[text](url)` keeps its label, no
   double-linking, `).` trailing handled. **DONE.**
2. **Telegram**: no change. No `parse_mode` set = plain text; bare URLs autolink natively; prose +
   `- ` bullets read fine. The contract is built around this behavior.
3. **SOUL.md addendum** (prod, `/root/.hermes-prism/SOUL.md` on VPS, sudo): one belt-and-suspenders
   line — *"When you point someone to a source, write the bare URL (https://…), never a
   `[text](url)` markdown link."* **STAGED, not deployed** — editing prod SOUL needs VPS sudo + a
   `hermes sessions delete <id>` to apply to live sessions (SOUL is frozen per session). Deploy only
   on user go-ahead; the SPA fix already covers the SPA side regardless, and Cassandra's
   conversational voice rarely emits markdown links anyway.

## When WhatsApp/SMS lands later

This contract is already the WhatsApp/SMS floor — those channels also do no Markdown. The future
gateway (webhook → Hermes bridge) needs **no transform**: bare URLs, prose, and `- ` bullets all
read fine as plain SMS/WhatsApp text. That's the payoff of choosing the subset architecture over a
per-channel transform layer.
