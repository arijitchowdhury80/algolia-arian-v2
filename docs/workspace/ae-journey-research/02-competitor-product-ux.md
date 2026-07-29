# Competitor Product UX — Pre-Call Brief, Drill-Down & Artifact Panels

**Research date:** 2026-06-27
**Purpose:** Inform the PRISM AE journey design. Target language: calm, Claude-Desktop-like — conversation-as-hero, deep artifacts (full report, ROI/business case, playbook) slide in on demand. Hero surface = a "60-second pre-call brief."

**What this is:** A study of how best-in-class sales-intelligence / revenue tools present a pre-call brief, how reps drill into evidence, and how AI artifact systems (Claude, ChatGPT/Codex) expand a deep object beside a conversation. Each claim is cited. Verdict: the market has converged on **proactive (auto-ready) briefs** + **citation-backed drill-down**. PRISM should match that and differentiate on a calm conversation-first surface.

---

## 1. Gong — the reference implementation for a pre-call brief

Gong is the closest existing analog to PRISM's hero surface. Two relevant surfaces: **AI Meeting Prep** (the pre-call brief) and **Ask Anything** (the conversational drill-in).

### At-a-glance brief (AI Meeting Prep page)
The meeting-prep page is organized top-down by prominence:

- **Top (hero):** a *Pre-Meeting Summary* — "Meeting objectives" and "Key topics to be discussed," with sub-blocks for overview, prior-discussion highlights, action items, and additional context. Plus **"Suggested questions to ask"** and **"General reminders."**
- **Middle:** *Participants* (attendees from both orgs — you can "drill down into individuals to see any activity timeline"); an **"Ask anything"** box (e.g. Use cases, Challenges, Business goals); and *Recent activity* (past calls and emails, filterable by digital interactions / CRM changes / texts).
- **Lower:** a collaboration area for notes and team tagging.

This is a clean **3-tier information hierarchy**: AI narrative summary → participants + ask → evidence/activity. (Source: [Gong — AI meeting prep](https://help.gong.io/docs/get-ready-for-meetings-with-ai-powered-meeting-prep))

### AI Briefer (the underlying brief engine)
AI Briefer produces "structured summaries that unify data from conversations, emails, web information, and your CRM" — "a snapshot... organized into a template made up of sections." Each section is a **question + AI-generated answer** (e.g. "What are the customer's company pain points?", "What follow-up actions were agreed upon?"). Briefs are available "on the homepage, account console, deal boards, and call pages" — i.e. **context-summoned wherever you are**, but the meeting-prep version is **auto-triggered** (below). (Source: [Gong — AI Briefer](https://help.gong.io/docs/understanding-ai-briefer))

### Drill-down + evidence (Ask Anything)
This is the single most important pattern for PRISM. Gong's **Ask Anything** lets a rep ask natural-language questions about a deal/account/contact; it searches calls and emails and answers. Critically:

> "Responses include **citations** so you can **review the source and jump to the relevant moment in the call** or related source... it backs up its analysis by **providing evidence from interactions** with each answer."

Scope is bounded and disclosed (up to 60 calls / 500 emails for a deal; 80 emails / 10 calls for a contact; top 100 matched calls for a search). (Source: [Gong — AI Ask Anything](https://help.gong.io/docs/understanding-ai-ask-anything), [Ask anything about a deal/account/contact](https://help.gong.io/docs/pipeline-review-ask-anything-about-a-deal-or-account))

### Entry model: NUDGE-THEN-SUMMON (the important nuance)
Gong is **proactive on the nudge, on-demand on the brief itself**:
- Proactive nudges: a **7 AM daily digest** with the day's call schedule + links to prior calls with those prospects; a **mobile push 30 min before** each external meeting with a "Prepare" action; a Friday weekly account-update email; Slack real-time alerts. Deal warnings auto-surface on the pinned board column.
- But the **rich meeting-prep brief is generated when the rep opens the page** — Gong does NOT push a fully-baked generative brief into email/Slack. The brief is "manually summoned" (Homepage "Prepare", ON AIR calls ~15 min before start, keyboard shortcut **Shift+M**, account console, calendar, mobile).
- Net model: **proactive calendar/CRM/Slack trigger → rep clicks → brief generated on demand.**

(Sources: [Gong meeting prep](https://help.gong.io/docs/get-ready-for-meetings-with-ai-powered-meeting-prep), [Emails from Gong](https://help.gong.io/docs/emails-from-gong), [Notifications](https://help.gong.io/docs/customize-your-gong-notifications))

**Takeaway:** Gong nudges proactively but **generates the brief on open**, and is summonable everywhere. The brief is a sectioned AI narrative; the drill-in is conversational; the evidence is a citation that jumps you to the source moment (the latter confirmed for calls + Ask Anything; *not* documented for the AI Briefer text or deal warnings — a real gap PRISM can close by citing the brief itself).

### Gong deal/account brief (Deal Board + panel)
Beyond meeting prep, Gong's pipeline surface leads with a **pinned "Warnings" column** (signals first, not a data dump). Opening a deal shows "critical information cards" (value, close date, methodology compliance, activity timeline, AI risk) and a **tabbed deal panel**: Briefs / Warnings / Score ("what signals impact the deal positively or negatively") / Contacts / Activity Timeline / Playbook / Update CRM. Warnings have a tight interaction: hover the warning count to see what's flagged, click to open the Warnings tab. Call Spotlight is the richest drill: the Briefs tab auto-opens on a **Highlights** brief (1-paragraph recap + bullets + next steps), then Outline / Points of Interest / Slides tabs, each line a jump-to-moment. (Sources: [Gong deal boards](https://help.gong.io/docs/understanding-deal-boards), [Review a call](https://help.gong.io/docs/review-what-happened-in-a-call))

---

## 2. Salesloft (Rhythm / Conductor AI) & Outreach — the action-feed model

### Salesloft Rhythm — the only true push-feed home base of the SEPs
Rhythm is a **prioritized action feed, not a record or a static brief**, and it's the rep's start-of-day home (accessible as a side panel from anywhere, organized into Focus Zones: Rhythm / Cadence / Close). **Conductor AI** (patent-pending) ingests signals from Salesloft, CRM, and partners (G2, Seismic, Vidyard, Highspot — opens, site visits, job changes), and ranks every action by **immediacy × impact** via a Buyer Priority Score and Deal Priority Score, **re-sorting in real time without the rep asking**. A prospect who hits the pricing page "gets elevated to the top of the call queue" automatically. Meeting prep is delivered as an AI **"cheat sheet" inside the Rhythm workflow**.

The reusable evidence primitive is precise — the **triggering signal's plain-English description renders on the task itself**: *"Indicator Description: a plain English description of what the signal means... displayed on the Task that's generated"* (e.g. a task stamped *"Rhythm Demo was watched by more than 75 percent"*). For Conductor-ranked tasks the line is "why it's important" (importance, not granular source). "AI in Salesloft is always paired with an explanation."
(Sources: [Conductor AI](https://www.salesloft.com/platform/conductor-ai), [Rhythm](https://www.salesloft.com/platform/rhythm), [Sending Signals](https://developers.salesloft.com/docs/platform/rhythm-resources/sending-signals/), [Signals FAQ](https://developers.salesloft.com/docs/platform/rhythm-resources/signals-faq/))

### Outreach — hybrid, trending to push; and the one cited surface in the whole study
Outreach's first-glance account surface is the **Smart Account Plan** (configurable Sales Intelligence Tiles + persistent side panel). Its **Meeting Prep Agent** (Talking Points, Past Conversations, Account/Attendee/Opportunity Overview) was classically *summoned* via a **"Prep" button** that opens a side panel; as of Feb 2026 it "pulls together a concise meeting brief **ahead of time**" and surfaces summaries in **Slack** — moving from summon to push. Notably, Outreach's daily task list is **still manual sort/filter (a low/normal/high tag), NOT AI-ranked** — a real gap vs. Salesloft Rhythm.

**The standout finding:** Outreach's **Smart Account Assist** (a Q&A side panel) is the *single surface across all eight products studied* that does evidence right — it **discloses its bounded corpus** ("the last 80 meetings/calls and the latest 500 emails") and provides clickable **deep links under a "Sources" header** to the exact timestamp/email. But it's a Q&A panel, *not the pre-call brief* — Outreach's actual Meeting Prep brief ships **without citations**. (Sources: [Smart Account Plan](https://support.outreach.io/hc/en-us/articles/25693862869659-Smart-Account-Plan-Overview), [Smart Account Assist](https://support.outreach.io/hc/en-us/articles/25694433467931-Smart-Account-Assist-Overview), [Meeting Prep Agent FAQ](https://support.outreach.io/hc/en-us/articles/47081568952475-Meeting-Prep-Agent-FAQ), [Feb 2026 release](https://www.outreach.ai/resources/blog/february-2026-product-release))

**Takeaway:** the SEP direction of travel is **proactive push + a "why this matters" line on every surfaced item** — but *only Salesloft makes the ranked push feed the home base*; Apollo is pull, Outreach is hybrid. And the **cited pre-call brief remains an open lane** — even Outreach, which proves it can cite (Smart Account Assist), doesn't cite the brief itself.

---

## 3. Apollo.io — the lightweight pre-meeting card

Apollo surfaces **upcoming meetings** with attendees, date/time, and an **Apollo-AI-generated summary** inline. The drill-in primitive is an explicit affordance:

> "Click **'Read more insights'** to help prepare with pre-meeting insights."

Under the hood the record view is a **configurable widget canvas, not a single brief card** — a left column (Contact info, Tasks, Account, Deals, Notes) plus a right-hand "Prospect" tab with three intelligence widgets: **Company insights** (score, recent news, tech, funding, job postings, employee trends, visitors), **Meeting assistant**, and **Account overview**. The pre-meeting brief itself is **template-driven** (rep picks templates — priorities, decision makers, objections — and each template is a customizable AI prompt with a selectable model) and is **rep-initiated**: Meetings → Insights → Run, or "View pre-meeting insights" in the Google Calendar Chrome extension. AI is flagged with a **purple-star icon**; explainability is in-product descriptions + an "always double-check your research" disclaimer — **not inline citations**. Apollo's provenance is strongest at the **data-field level** (work-email "last verified" within 30–60 days, enrichment before/after diffs, "Flag as inaccurate"), not the AI-narrative level. **Entry model = pull**: confirmed *absent* is any time-based auto-push (no "30 min before → brief appears"). Note: Apollo acquired Pocus (March 2026). (Sources: [Apollo AI Overview](https://knowledge.apollo.io/hc/en-us/articles/37242880230541-Apollo-AI-Overview), [Research and Prepare for Meetings](https://knowledge.apollo.io/hc/en-us/articles/32598161249549-Research-and-Prepare-for-Upcoming-Meetings), [View/Edit Accounts](https://knowledge.apollo.io/hc/en-us/articles/5995865049229-View-and-Edit-Accounts))

**Takeaway:** Apollo's *surfacing* pattern is excellent — a **compact card with a single "Read more insights" expansion** into the deep view, a near-perfect minimal template for PRISM's brief → drill primitive. But its *entry model is pull* (rep must run it) and its *brief is uncited* — two places PRISM should diverge.

---

## 4. 6sense — score + buying stage + "why now," with shallow drill-down (a cautionary tale)

6sense classifies accounts into buying stages (Target → Awareness → Consideration → Decision → Purchase) and frames intelligence as "**why this account, why now, what's changing, and who's deciding**" — explicitly **cited intelligence** resolved from raw signals. Reps can drill into an account to see which keywords/topics triggered the in-market score. Dashboards are role-specific (AE vs ABM vs demand-gen).

**Best-documented drill-down in the set.** The account-details page is **tabbed**: *Activities* (web / B2B network / campaigns, with a Roll-Up vs Individual toggle), *Scoring Trend* (scores over time), *Timeline* (chronological, ~27 months), *Intent* (the specific keywords, page visits, Bombora Surge topics the account is researching, 6-month window), and *Persona Map* (people by title/division, filterable All / Engaged / Not Engaged / Not Reached to surface white space). The home view is the ranked **Accounts Dashboard** with Hot/Warm/Cold temperature and three top-line metrics per account: **Profile fit %, Buying stage, Account reach**. Entry is push-weighted (Slack/email alerts on new top accounts) plus a pull layer (Chrome extension on LinkedIn, RevvyAI chat). Its **RevvyAI** copilot answers account questions "grounded in Signalverse™ data." (Sources: [6sense account details page](https://support.6sense.com/docs/abm-account-details-page), [account prioritization](https://6sense.com/guides/account-prioritization/), [Chrome extension](https://support.6sense.com/docs/gain-company-insights-using-sales-intelligence-extension-for-chrome))

**The cautionary part:** reviewers report "**drill-downs are shallow... intent signals can feel vague at the account level, and users don't always get a clear explanation of what triggered an in-market score**." Resolution is account-level, not individual ("someone from Microsoft is interested" — not who). (Sources: [Magic Numbers: intent & engagement scores](https://6sense.com/blog/magic-numbers-breaking-down-6senses-intent-and-engagement-scores/), [Demandbase teardown of 6sense](https://www.demandbase.com/blog/6sense-features/))

**Takeaway for PRISM:** a number without a traceable "why" erodes trust. The headline "why now" is good; the **drill-in must reach actual evidence**, not dead-end at a vague score. This is exactly the gap PRISM's evidence-grounding can win on.

---

## 5. Pocus & Common Room — signal-based "why," in plain English

### Pocus (acquired by Apollo.io, March 2026)
The home surface is the **Intelligent Inbox** — a prioritized daily action feed, explicitly *"not a passive dashboard."* Its framing is the model PRISM should study: *"instead of 47 alerts, you get 3 priorities"* — 3–5 prioritized actions with dynamic re-ranking. A **"Morning Brief"** gives "who to contact, suggested talking points, and ready-to-send emails." Pocus' AI scoring **"explains every score in plain English"** — and uses **letter grades scored within a peer segment** ("B+ among mid-market SaaS"), not naked numbers. Instead of "73," a rep sees: *"Account graded A- because they're a 500-person fintech (fits your ICP), visited pricing page 4x this week, and posted 3 new engineering jobs."* Drill-in goes to **Unified Account Intelligence** (a 360 consolidating every call/email/interaction) with a natural-language **"Ask AI"** chat ("what were the action items from our last call?"). Entry is push-first; reviewers single out **Slack alerts as "the feature that changes rep behavior."** Caveat: G2's #1 complaint is *data accuracy* — the trust failure mode to design against. (Sources: [Pocus AI Scoring](https://www.pocus.com/blog/introducing-ai-scoring-account-prioritization-that-actually-works), [Pocus Signals](https://www.pocus.com/product/signals), [Intelligent Inbox](https://www.pocus.com/blog/introducing-intelligent-inbox), [G2 reviews](https://www.g2.com/products/pocus/reviews))

### Common Room (Person360 / RoomieAI)
Person360 "connects the person behind the signal" — a 360 view unifying "social reactions, community comments, employment activity, product usage spikes, web activity, and hundreds of additional signals," each **traced to a real person/account**, across 50+ named integrations (Slack, Discord, GitHub, Reddit, G2, Gong, Salesforce, Bombora...). Its **RoomieAI** account research lands "directly within the account profile view" as a widget — "an up-to-date executive summary... why it is or isn't the right fit, and how to position, right at the top of the page" (currently internet-search-grounded, ~10s, quarterly refresh). Distribution is push-first: the **Spark Brief** is "a daily briefing of the highest-priority accounts straight to reps in Slack and email" with one-click send. Honest review caveats: Slack alerts can be **"too thin" (company name only, must click through)** and "signal→action still requires manual steps." (Sources: [Common Room Person360](https://www.commonroom.io/product/person-360/), [AI research](https://www.commonroom.io/blog/ai-research-account-prioritization-and-personalization), [SyncGTM review](https://syncgtm.com/blog/common-room-review))

> **The single most important finding across all four (Pocus, Common Room, 6sense, Crayon):** every one of them *claims* its AI brief is "grounded" in its signal/data layer, but **none could be confirmed to render inline, per-claim citations** (footnote-style source links on each sentence). They name source *taxonomies* ("first-party / Bombora / 10-Ks"); they do not footnote each claim. The one confirmed exception is narrow — Crayon battlecards built from field intel cite back to the originating rep voice notes. **This is PRISM's sharpest differentiation wedge:** PRISM's "evidence on every data point / no naked numbers" rule is *stricter than what any incumbent demonstrably ships.* Lead with it.

**Takeaway:** the winning evidence pattern is **the score IS the sentence** — the rationale rendered as plain-English claims tied to source signals. PRISM should go one step further than the market and make each of those claims a *clickable citation*, which is the gap above.

---

## 6. Crayon — competitive briefs that travel to where the rep already is

Crayon's engine monitors thousands of competitor signals (product/pricing page changes, G2 patterns, LinkedIn job posts) and **auto-updates battlecards delivered directly in Salesforce and Slack** — "always current without manual maintenance," "right there when they need it — no context switching." A "Field Agent for Slack" lets reps both consume and contribute intel in-channel. (Sources: [Crayon — Slack Field Agent](https://www.crayon.co/blog/slack-field-agent), [Crayon — modern battlecard blueprint](https://www.crayon.co/blog/modern-battlecard-blueprint), [Crayon integrations](https://www.crayon.co/integrations))

Crayon also has one **confirmed citation behavior** (rare in this study): battlecard content built from field intel includes "citations linking back to the original field intel and rep voice notes." Its Slack motion is three-way — **summon** (`/crayon` + question → Crayon Answers Q&A), **push capture** (Field Agent pings the rep on Closed Won/Lost), and **receive** (competitor-move alerts). Battlecards are also embedded directly in each Salesforce opportunity record. (Sources: [Crayon — Slack Field Agent](https://www.crayon.co/blog/slack-field-agent), [Crayon — modern battlecard blueprint](https://www.crayon.co/blog/modern-battlecard-blueprint), [Crayon Answers](https://www.crayon.co/blog/introducing-crayon-answers), [Crayon integrations](https://www.crayon.co/integrations))

**Takeaway:** competitive intel is **pushed into the rep's existing surface** (CRM/Slack) and kept fresh automatically — reps don't go fetch it. Distribution-to-where-you-are beats a destination app.

---

## 6b. Clari (incl. Clari Copilot) — the deal-inspection brief

Clari is worth a section because its **brief structure is the most explicitly documented**. Its core Inspect surface uses a **"4-Point Deal Inspection"**: (1) **Deal Changes at a Glance** — color-coded deltas (green = trending up, red = down, blue = neutral) over 7/14/30-day windows; (2) **Win Probability** (a CRM Score; an Opportunity Score adds conversational signals like "competitors mentioned"); (3) **Engagement & Relationship Health**; (4) **Next Steps** via Smart CRM Suggestions. Risk flags **state their reason** — e.g. a deal "gone dark — *no files exchanged*" (provenance as the reason attached, not a bare flag).

**Clari Copilot Account View** (the deal/account brief): top-left = key deal info; top = engagement-frequency timeline; left = full sequence of calls/emails; right = contacts + risk warnings; plus an AI insights panel that "automatically pulls in data from emails and meetings" for a deal summary. Drill-in: click into linked opportunities, scroll the engagement sequence to open any call/email, **search across conversations and "listen in to relevant snippets on this screen"**; **Smart Topics/Chapters** are clickable visual timestamps that "drill down to specific call moments." **Ask Clari** answers prompt-driven questions over conversations; **"Ask Clari for a call"** answers call-specific questions ("Did we discuss pricing?").

**Evidence:** strong at the data layer — every call-summary topic, action item, and competitor mention carries timestamps + speaker IDs (per the Copilot API). **Caveat:** whether Ask Clari renders *inline clickable citations* in its answers could not be confirmed from public sources (its help pages are JS-rendered). **Entry model = hybrid**: proactive Slack alerts when a deal changes meaningfully (with the resulting CRM Score) and when "important prospect meetings are about to take place," plus a "View in Clari" deep-link — but the full pre-call brief (Account View / Ask Clari) is **summoned**, and live battlecards auto-surface during the call. (Sources: [Clari 4-Point Deal Inspection](https://community.clari.com/), [Clari Inspect](https://clari.com/products/inspect/), [Clari Copilot](https://clari.com/products/copilot/), [Copilot API](https://api-doc.copilot.clari.com/))

**Takeaway:** Clari confirms the cross-product pattern from a different angle — lead with **signals + color-coded change + a stated risk reason**, drill to the **clickable call moment**, and **nudge proactively but generate the brief on open**. Same unconfirmed-inline-citation gap as everyone else.

---

## 7. Artifact / side-panel interaction primitives (Claude & ChatGPT/Codex)

This is the interaction model PRISM's design language targets directly.

### Claude Artifacts
- An artifact **opens in a dedicated panel to the right of the chat** — a split-screen, conversation-left / object-right layout. The conversation stays the hero; the artifact is the on-demand deep object.
- **Auto-trigger:** Claude decides when content warrants an artifact (self-contained, substantial content — roughly >15 lines / reusable), opening the panel automatically; you can also explicitly summon one.
- **Collapse-back:** turn Artifacts off (or close the panel) and content renders inline in the chat instead — i.e. the panel is dismissible and the conversation degrades gracefully.
- **Versions:** a **version selector** switches between iterations; editing a prior message branches a new set of artifacts without losing prior work.
- **Live iteration:** prompt refinements update the artifact in place — no copy-out.

(Sources: [Claude Help — Artifacts](https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them), [Albato guide](https://albato.com/blog/publications/how-to-use-claude-artifacts-guide))

### ChatGPT Canvas / Codex
- Canvas "pops open a **side panel** with a shared editor" — **conversation on the left, editable document/code on the right.**
- **In-place targeted editing:** highlight a section on the right to ask for a rewrite/expand/simplify; responses auto-open the right-hand window.
- **Code affordances:** an Execute button runs code; output appears in a console at the bottom of the panel.
- Note: OpenAI has since (May 2026) folded Canvas back **into the thread as "writing blocks / code blocks"** on newer models — a signal that the *separate panel* can be collapsed back into the conversation when the object is small. (Sources: [OpenAI — Canvas help](https://help.openai.com/en/articles/9930697-what-is-the-canvas-feature-in-chatgpt-and-how-do-i-use-it), [OpenAI — Introducing Canvas](https://openai.com/index/introducing-canvas/))

### Codex (desktop / IDE) — for completeness
Codex follows the same conversation-steers / panel-inspects split: a chat task-thread in a sidebar drives an **artifact viewer** (previews generated files) and a **diff pane** (Git diff, with collapsible inline comments that become agent instructions, stage/revert per chunk, expand/collapse-all). Panel defaults to the right sidebar, draggable left/right. Conversation = steering layer; diff/artifact = inspection-and-action layer. (Sources: [Codex IDE](https://developers.openai.com/codex/ide), [Codex app features](https://developers.openai.com/codex/app/features))

### Reusable interaction primitives (the steal list)
1. **Conversation stays the hero; the artifact is secondary and on-demand** — it slides into a right-hand panel, never replaces the chat. The conversation is the *steering layer*; the panel is the *artifact/inspection layer*. (Universal across Claude, Canvas, Codex.)
2. **Slide-in panel, not a modal** — the chat remains visible and usable beside the open artifact (no context loss). A modal would block the chat.
3. **Two trigger paths — auto + manual override** — auto-detect substantial/self-contained content (Claude's ~15-line + reusable heuristic) AND give an explicit manual trigger ("+ New artifact", `/canvas`). Never rely on heuristics alone. (Map: a one-line stat stays in the brief; the full ROI model becomes an artifact — and the AE can also force it open.)
4. **Card-in-conversation as the handle** — the artifact is represented by a card/preview inline in the thread; clicking it (re)opens the panel. The object lives in the panel but is anchored to the message that produced it.
5. **Open-default sizing + expand-to-fullscreen** — half-screen default (Claude), escalating to fullscreen. *Continuous drag-to-resize is NOT confirmed in Claude* (only Codex's %-based file-tree resize is documented); the safe, confirmed primitive is a fullscreen toggle.
6. **Close-to-collapse with reflow** — a close control collapses the panel and reflows chat to full width; reopen from the inline card. (Confirmed for Canvas; the exact control is **unverified for Claude** — validate in-product.)
7. **Scoped editing via selection → attached instruction** — point at a region, attach an instruction (Claude "highlight → Edit with Claude"; Canvas "highlight → Ask ChatGPT"; Codex "inline comment on a diff chunk"). Same primitive, three guises; the edit is scoped to the selection, the rest untouched.
8. **First-class versioning inside the panel** — version selector / prev-next arrows / restore (Claude, Canvas), plus an inline red/green "show changes" diff (Canvas) and Git-diff stage/revert (Codex). Each AI edit spawns a new version; the user can step back and restore. (PRISM: regenerate/refresh the brief or business case as signals change.)
9. **Dual-view toggle within one artifact** — Code↔Preview (Claude), document vs. show-changes diff (Canvas), inline vs. detached review (Codex). One artifact, switchable representations — the closest real thing to "tabs within an artifact." *A full multi-tab system was NOT found in any product*, so PRISM's "full report / ROI / playbook as tabs in one panel" is a reasonable *extension* of the dual-view pattern, not a copied one — validate it holds at three+ tabs.
10. **Multiple artifacts, switchable, with a dedicated home** — several artifacts per conversation, switched via a control (Claude's slider icon, upper right), plus a persistent library to reopen them.
11. **No "pin" exists** — **unverified / not documented in either Claude or Canvas.** Do not assume a pin affordance; persistent-pinned artifacts would be net-new for PRISM, not a borrowed pattern.
12. **Publish / share as a terminal action** — separate from editing: Claude publishes to a public link + embed (allowed-domains control) + remix-into-new-conversation; Codex's equivalent is "create a PR." (PRISM: share/export the brief or report as a distinct action.)

> **URL note (from deeper research):** Anthropic's artifact docs now live on `claude.com` / `support.claude.com` (the `anthropic.com/news/artifacts` and `support.anthropic.com` URLs 301/308-redirect there). OpenAI's `openai.com` and `help.openai.com` pages return 403 to automated fetch — Canvas detail was corroborated via OpenAI Academy + Zapier / Tom's Guide / TechCrunch.

---

## Patterns worth stealing

1. **The 3-tier brief hierarchy (from Gong).** Tier 1 = AI narrative ("why now," objectives, top topics, suggested questions). Tier 2 = the cast (participants/contacts, each a one-click timeline) + an Ask box. Tier 3 = evidence/activity (calls, emails, signals). PRISM's 60-second brief is Tier 1; everything below is one click deep.

2. **The score IS the sentence (from Pocus / Common Room).** Never show a naked number. Render the rationale as plain-English claims, each bound to a source. This is identical to PRISM's "evidence on every data point" cardinal rule — the market validates it.

3. **Citations that jump to the source (from Gong Ask Anything + Outreach Smart Account Assist).** The proven mechanic: every claim carries a citation that, when clicked, takes the rep to the exact source moment, *and* the surface discloses its bounded corpus ("the last 80 calls / 500 emails"). Outreach is the only product that does this on a synthesized AI surface — but on a Q&A panel, not the brief.

3b. **THE OPEN LANE — a fully cited pre-call brief.** Across all eight products, *every actual pre-call/account brief ships without inline per-claim citations.* They name source taxonomies; they don't footnote each sentence (only narrow exceptions: Gong Ask Anything answers, Outreach's Q&A panel, Crayon field-intel battlecards). This is PRISM's single sharpest wedge: a brief where **every claim is a clickable citation** beats the entire field on the exact dimension PRISM is already built for.

4. **"Read more insights" single-affordance expansion (from Apollo).** One obvious control turns the compact card into the deep view. Don't make the rep hunt for the drill-in.

5. **A "why this matters" line on every surfaced item (from Salesloft Rhythm).** Anything you push to the rep states its own rationale. Builds trust and removes the "why am I seeing this?" friction.

6. **Push to where the rep already is, kept fresh (from Crayon / Common Room Slack).** Auto-updated, delivered into the existing surface (calendar/CRM/Slack/email), not a destination they must remember to visit.

7. **Artifact-as-slide-in-panel, conversation-as-hero (from Claude/Canvas).** The deep objects (full report, ROI, playbook) live in a dismissible right-hand panel; the brief/conversation stays primary. Use tabs *within* one panel rather than spawning many.

8. **Avoid 6sense's failure mode.** A "why now" headline with a shallow drill-down that dead-ends at a vague score destroys trust. PRISM's drill must always bottom out in real, cited evidence.

---

## Implications for the PRISM AE UI

### Information hierarchy of the 60-second brief
Lead with a **3-tier structure** mirroring Gong, rendered in PRISM's calm conversation-first style:

- **Top-line (the 60-second read, always visible):**
  - One-sentence **"Why now"** (the trigger / strategic angle), each clause cited.
  - 3–5 **plain-English claims** that double as the account's score rationale ("X because A, B, C" — the Pocus pattern).
  - **Suggested talking points / questions** for this specific call.
- **One-click-deep (Tier 2, inline expansions or quick chips):**
  - **Participants/contacts** — each opens an individual timeline.
  - **Evidence chips** — each claim's citation, click-to-source.
  - An **Ask box** ("ask anything about this account") that answers with citations.
- **Artifact panel (Tier 3, slide-in on demand):** Full report, ROI/business case, playbook — heavy objects that open in a right-hand panel as **tabs within one artifact**, never replacing the conversation.

### Brief → drill → artifact panel interaction
- **Brief lives in the conversation column** (the hero). Claims/citations and a single **"Open full report / ROI / playbook"** affordance (Apollo's "Read more insights") promote depth into a **right-hand slide-in panel** (Claude/Canvas), not a modal and not a page nav.
- Panel is **dismissible and collapses back** into the conversation; the chat stays visible beside it the whole time.
- Use **tabs inside one panel** (Full Report / Business Case / Playbook) rather than three separate panels — matches Canvas's doc/code tabbing and keeps the surface calm.
- **Versioning** for the brief itself (regenerate / refresh as signals change) — Claude's version selector model.
- Reserve the panel for **substantial, self-contained** objects (the trigger-threshold rule); keep small facts inline in the brief.

### Evidence / source presentation (PRISM's differentiator)
- **Every data point is a clickable citation** that resolves to its source — the Gong Ask-Anything "jump to the source moment" model is the gold standard, and it's exactly PRISM's "no naked numbers" rule.
- **Render rationale as plain-English claims, not scores** (Pocus). The brief should read like sentences a human would say, each footnoted.
- **Disclose scope/freshness** of the evidence (Gong discloses "up to 60 calls / 500 emails"; 6sense loses trust by not). Show "as of <date>, from <N sources>."
- Inline citation chips in the brief; full source list/provenance in the artifact panel. Clicking a brief citation can deep-link into the relevant section of the full-report artifact.

### Entry model — RECOMMENDATION: **Auto-ready, with summon as the secondary path.**

The market has converged on **proactive**, but with an important nuance the research surfaced — there are two sub-models:
- **Nudge-then-generate (Gong, Clari):** the *trigger* is proactive (calendar/CRM/Slack nudge — Gong's 7 AM digest + 30-min mobile push; Clari's deal-change Slack alert), but the rich brief is **generated when the rep opens it**. Neither pushes a fully-baked generative brief into email/Slack.
- **Pre-ranked push feed (Salesloft Rhythm):** the only product where the engine ranks the rep's whole day in real time and the feed *is* the home base; reps don't fetch. (Apollo is pull; Outreach is hybrid, moving toward push.)
- **Distribution-to-where-you-are (Crayon / Common Room / Pocus):** fresh intel pushed into Slack/CRM, with the brief as a daily Slack/email digest.
- Industry guidance is explicit: *"briefings arrive automatically without rep action... Manual workflows get skipped."* ([MarketBetter guide](https://marketbetter.ai/blog/ai-sales-meeting-prep-complete-guide-2026/), [Altisima 2026 review](https://altisima-advisory.com/blog/pre-call-preparation-tool-sales-teams-2026.html))

**Why auto-ready wins:** adoption. A pre-call brief that a rep must remember to summon competes with the 15-tab manual scramble and loses; the value only lands if it's *already there* when the meeting appears. The friction of summoning is exactly where these tools die in the field. PRISM should go further than the nudge-then-generate incumbents and pre-*generate* the brief (cheap to do when intel is already cached), so it's not just nudged but **ready** — closer to Rhythm's "it's already done for you" feel, in PRISM's calm conversational frame.

**The PRISM recommendation, concretely:**
- **Primary (proactive):** when a qualifying meeting lands on the AE's calendar (or a CRM trigger fires), PRISM **pre-generates the 60-second brief** and makes it ready — surfaced via a notification ~30 min out and waiting in the AE's home surface. The conversation opens already populated, framed as *"Here's your brief for the [Company] call at 2pm."*
- **Secondary (summon):** the AE can also ask for a brief any time ("brief me on Acme") — the calm conversational entry that fits the Claude-Desktop language. This is the on-ramp when there's no calendar event.
- **Do NOT** make summon the only path (the implicit pre-PRISM-v2 risk). And **do NOT** over-notify — one well-timed pre-meeting nudge (Gong's 30-min model), not a firehose (the trap Crayon/Rhythm avoid by ranking, not spamming).

This keeps PRISM's calm, conversation-as-hero feel **and** matches the proven adoption driver: the brief is ready before the rep thinks to ask.

---

## Source URLs (consolidated)
- Gong AI meeting prep: https://help.gong.io/docs/get-ready-for-meetings-with-ai-powered-meeting-prep
- Gong AI Briefer: https://help.gong.io/docs/understanding-ai-briefer
- Gong AI Ask Anything: https://help.gong.io/docs/understanding-ai-ask-anything
- Gong Ask Anything (deal/account/contact): https://help.gong.io/docs/pipeline-review-ask-anything-about-a-deal-or-account
- Gong view upcoming calls: https://help.gong.io/docs/view-upcoming-calls
- Gong deal boards: https://help.gong.io/docs/understanding-deal-boards
- Gong review a call (Spotlight): https://help.gong.io/docs/review-what-happened-in-a-call
- Gong emails / notifications: https://help.gong.io/docs/emails-from-gong | https://help.gong.io/docs/customize-your-gong-notifications
- Salesloft Conductor AI: https://www.salesloft.com/platform/conductor-ai
- Salesloft Rhythm: https://www.salesloft.com/platform/rhythm
- Salesloft Rhythm announcement: https://www.salesloft.com/company/newsroom/salesloft-announces-rhythm-powered-by-conductor-ai
- Salesloft Sending Signals (signal-on-task): https://developers.salesloft.com/docs/platform/rhythm-resources/sending-signals/
- Salesloft Signals FAQ: https://developers.salesloft.com/docs/platform/rhythm-resources/signals-faq/
- Outreach Smart Account Plan: https://support.outreach.io/hc/en-us/articles/25693862869659-Smart-Account-Plan-Overview
- Outreach Smart Account Assist (cited Q&A): https://support.outreach.io/hc/en-us/articles/25694433467931-Smart-Account-Assist-Overview
- Outreach Meeting Prep Agent FAQ: https://support.outreach.io/hc/en-us/articles/47081568952475-Meeting-Prep-Agent-FAQ
- Outreach Feb 2026 release (push): https://www.outreach.ai/resources/blog/february-2026-product-release
- Outreach Avis meeting prep: https://www.outreach.ai/resources/blog/how-avis-uses-outreach-meeting-prep-agent-to-help-reps-prepare-faster-and-sell-smarter
- Apollo AI: https://www.apollo.io/ai
- Apollo AI Overview: https://knowledge.apollo.io/hc/en-us/articles/37242880230541-Apollo-AI-Overview
- Apollo Research and Prepare for Meetings: https://knowledge.apollo.io/hc/en-us/articles/32598161249549-Research-and-Prepare-for-Upcoming-Meetings
- Apollo View/Edit Accounts: https://knowledge.apollo.io/hc/en-us/articles/5995865049229-View-and-Edit-Accounts
- Apollo conversations/briefs: https://knowledge.apollo.io/hc/en-us/articles/9632855570701-Access-and-Share-Conversations
- Clari Inspect: https://clari.com/products/inspect/
- Clari Copilot: https://clari.com/products/copilot/
- Clari Copilot API (timestamps/speakers): https://api-doc.copilot.clari.com/
- Clari community (4-Point Deal Inspection / Account View): https://community.clari.com/
- 6sense account details page: https://support.6sense.com/docs/abm-account-details-page
- 6sense account prioritization: https://6sense.com/guides/account-prioritization/
- 6sense intent/engagement scores: https://6sense.com/blog/magic-numbers-breaking-down-6senses-intent-and-engagement-scores/
- 6sense Chrome extension: https://support.6sense.com/docs/gain-company-insights-using-sales-intelligence-extension-for-chrome
- Demandbase 6sense teardown: https://www.demandbase.com/blog/6sense-features/
- Pocus AI scoring: https://www.pocus.com/blog/introducing-ai-scoring-account-prioritization-that-actually-works
- Pocus Signals: https://www.pocus.com/product/signals
- Pocus Intelligent Inbox: https://www.pocus.com/blog/introducing-intelligent-inbox
- Pocus G2 reviews: https://www.g2.com/products/pocus/reviews
- Common Room Person360: https://www.commonroom.io/product/person-360/
- Common Room Person360 intro: https://www.commonroom.io/blog/introducing-person360-connect-with-the-person-behind-the-signal/
- Common Room AI research: https://www.commonroom.io/blog/ai-research-account-prioritization-and-personalization
- Common Room review (SyncGTM): https://syncgtm.com/blog/common-room-review
- Crayon Slack Field Agent: https://www.crayon.co/blog/slack-field-agent
- Crayon modern battlecard: https://www.crayon.co/blog/modern-battlecard-blueprint
- Crayon Answers: https://www.crayon.co/blog/introducing-crayon-answers
- Crayon integrations: https://www.crayon.co/integrations
- Claude Artifacts help (claude.com): https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them
- Claude publishing/remixing artifacts: https://support.claude.com/en/articles/9547008-publishing-and-remixing-artifacts
- Claude Artifacts guide (Albato): https://albato.com/blog/publications/how-to-use-claude-artifacts-guide
- ChatGPT Canvas (OpenAI Academy): https://academy.openai.com/public/clubs/work-users-ynjqu/resources/canvas
- OpenAI Introducing Canvas: https://openai.com/index/introducing-canvas/
- ChatGPT Canvas guide (Zapier): https://zapier.com/blog/chatgpt-canvas/
- OpenAI Codex IDE: https://developers.openai.com/codex/ide
- OpenAI Codex app features: https://developers.openai.com/codex/app/features
- AI meeting-prep market guide (MarketBetter): https://marketbetter.ai/blog/ai-sales-meeting-prep-complete-guide-2026/
- Pre-call briefing tools 2026 (Altisima): https://altisima-advisory.com/blog/pre-call-preparation-tool-sales-teams-2026.html
