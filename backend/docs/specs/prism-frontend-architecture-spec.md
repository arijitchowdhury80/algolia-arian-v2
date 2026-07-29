# Prism Frontend — Architecture & UX Requirements
## Captured from founder's design session, March 30, 2026

---

## CRITICAL ARCHITECTURE PRINCIPLE

**The chat is the UI layer. Temporal is the brain. PostgreSQL is the memory.**

The chat layer (Claude + Vercel AI SDK) ONLY does:
- Understand what the user wants (NLP)
- Make tool calls to the FastAPI backend (HTTP requests)
- Present results conversationally with rich components
- Each tool call is INDEPENDENT — no accumulated state in chat context

The orchestration layer (Temporal) ONLY does:
- Execute multi-module audit workflows
- Manage dependencies between modules (Wave 1 before Wave 2)
- Handle retries, timeouts, failures
- Persist all results to PostgreSQL
- Runs completely independently of the chat — if the browser closes, the audit keeps running

PostgreSQL ONLY does:
- Store all module results, evidence, audit history
- Source of truth for ALL data — chat reads from it, Temporal writes to it
- Nothing important lives in the chat context

**Why this won't fail like the old system:** The old system had ONE LLM trying to orchestrate AND analyze AND track state. This system has Claude doing ONLY conversation, Temporal doing ONLY orchestration, and PostgreSQL doing ONLY persistence. No single component is overloaded.

---

## CONTEXT MANAGEMENT STRATEGY

### Chat context stays light
- The chat NEVER accumulates module outputs in its context window
- When user asks "What's Dell's tech stack?" → tool call fetches from DB → renders card → the card content is NOT retained in chat history as raw JSON
- Tool results are displayed as rendered components but stored as lightweight references in chat history (e.g., "Displayed TechStackCard for dell.com" not the full 5KB JSON)
- For long conversations, assistant-ui supports thread management — users can start new threads, and old threads are summarized

### Audit execution is context-free
- Temporal workflows don't use LLM for coordination — they're pure Python code
- Each module activity runs in its own context — module A's context doesn't bleed into module B
- LLM calls INSIDE modules (for enrichment/synthesis) are scoped to that single module — they receive only the data relevant to that module, not the entire audit
- The Instructor library handles structured output with auto-retry — if a module's LLM call fails validation, it retries with ONLY the validation error, not the entire conversation

### Synthesis modules get curated context
- When the synth-business-case module runs, it doesn't get "everything" — it gets a curated input assembled by Temporal from the specific module outputs it needs (financials + traffic + competitors + techstack)
- Each synthesis module's Pydantic input schema defines exactly what data it receives — no more, no less
- This is fundamentally different from the old system where one LLM tried to hold all 20 modules' outputs simultaneously

---

## THREE-PANEL LAYOUT

### Left Panel (narrow, ~250px)
**Account navigation + thread management**

- **Search bar at top** — type "COS" and Costco appears. Instant filter.
- **Alphabetic index** — A B C D ... Z buttons for quick jump
- **Account list** — scrollable, showing:
  - Company name
  - Domain
  - Last audit date
  - Tier badge (HOT / WARM / COLD) if scored
  - Status indicator (green = audit complete, amber = running, gray = no audit)
- **Thread management** — under each account, show conversation threads
  - "Dell — initial research" 
  - "Dell — pre-call prep March 28"
  - Start new thread button
- **Quick actions** at bottom:
  - "Run new audit" button
  - "Bulk import" button
  - Settings

### Center Panel (primary, flexible width)
**The conversation — THIS IS THE MAIN INTERFACE**

- assistant-ui Thread component
- User types or speaks
- Responses stream in with rich components rendered inline:
  - Tech stack cards
  - Financial profile cards
  - Competitive benchmark matrices
  - Signal cards (hiring surge, exec change, etc.)
  - Evidence badges on every data point
- **Thinking mode / transparency:**
  - When a tool is executing, show a collapsible "thinking" block:
    - "Calling BuiltWith API for dell.com..."
    - "Received 47 technologies, classifying search vendor..."
    - "Cross-checking with SimilarWeb..."
    - "Formatting results..."
  - User can click to expand and see the raw process
  - When complete, the thinking block collapses and the card appears
  - This mirrors Claude desktop's thinking mode exactly
- **Progressive rendering:**
  - As each module completes during a full audit, its card appears in the conversation
  - User sees intelligence building up in real-time
  - No waiting for everything to finish — each piece streams in as it's ready

### Right Panel (expandable, ~400px, hidden by default)
**Deep detail and standalone tools**

- Opens when user clicks on a card or selects a tool from the menu
- Standalone tools that don't need to be in the chat:
  - **ROI Calculator** — interactive, user adjusts inputs, saves results per account
  - **Full audit report** — the complete scored assessment (existing 10-dimension view)
  - **Search audit screenshots** — the annotated screenshot gallery
  - **Competitive matrix** — full side-by-side comparison table
  - **Sales playbook** — MEDDPICC, SPIN, objection handling
  - **ABX campaign editor** — edit/customize the generated email sequences
- Each tool saves its state to PostgreSQL per account per audit
- Right panel can be pinned open or collapsed

---

## AUTHENTICATION

### Single Sign-On via Google Workspace (Algolia email)
- Users log in with their @algolia.com Google account
- No separate registration — if you have an Algolia email, you're in
- For the internal Algolia version: **Clerk** with Google OAuth
  - Clerk supports Google Workspace SSO out of the box
  - RBAC: Admin, AE, BDR, SE, PAM roles
  - Each role sees appropriate data and features
- For the future standalone product: Clerk supports Okta SAML SSO for enterprise customers

### Role-based access
| Role | Can run audits | Can see all accounts | Can edit playbooks | Admin panel |
|------|---------------|---------------------|-------------------|-------------|
| Admin | ✅ | ✅ | ✅ | ✅ |
| AE | ✅ | Own accounts only | ✅ | ❌ |
| BDR | ❌ (can request) | Assigned accounts | ❌ | ❌ |
| SE | ❌ | Assigned accounts | ✅ (technical only) | ❌ |
| PAM | ✅ | Partner accounts | ✅ | ❌ |

---

## ADMIN PANEL

### Account Management
- Import accounts (CSV upload from ZoomInfo/Demandbase)
- Assign accounts to AEs/BDRs
- View all audits across the organization
- Export audit data

### System Health
- Module status dashboard (which modules are healthy, which are failing)
- API usage and costs (BuiltWith, SimilarWeb, Claude API)
- Audit queue (what's running, what's pending, what failed)
- Temporal workflow monitor (link to Temporal Web UI for admins only)

### Configuration
- Module enable/disable per organization
- API key management
- Branding customization (for future white-label)
- Notification settings (Slack webhook, email alerts)

---

## AUDIT EXECUTION — USER EXPERIENCE

### Starting an audit via chat
User: "Run a full audit on dell.com"
Prism: "Starting a full Prism audit for Dell Technologies (dell.com). I'll analyze their technology, financials, competitive landscape, hiring patterns, and more. This typically takes 15-25 minutes. I'll show you results as each module completes."

[Thinking block appears — collapsible]
> Module 1/20: intel-techstack — Calling BuiltWith... ✓ 47 technologies detected
> Module 2/20: intel-company — Enriching company profile... ✓ Dell Technologies, $102B revenue
> Module 3/20: intel-traffic — Fetching SimilarWeb data... ⏳ running
> Module 4/20: intel-competitors — Identifying competitors... ⏳ running
> ...

[As each module completes, its card streams into the conversation]
[TechStackCard appears] → "Dell uses Elasticsearch for search, with Salesforce Commerce Cloud. Here's the full stack..."
[FinancialCard appears] → "Dell's digital revenue has grown 23% YoY..."
[CompetitorCard appears] → "HP and Lenovo are the primary competitors. HP uses Algolia..."

### Quick lookup via chat
User: "What search vendor does Costco use?"
Prism: [Calls get_tech_stack tool]
[TechStackCard appears with just the search vendor section]
"Costco uses a custom/proprietary search solution. No enterprise search vendor was detected via BuiltWith."

### Asking follow-up questions
User: "How does that compare to their competitors?"
Prism: [Calls get_competitors tool for costco.com]
[CompetitorMatrixCard appears]
"Here's how Costco's search compares to BJ's, Walmart, Target, and Sam's Club..."

### Accessing standalone tools
User clicks "ROI Calculator" in the right panel menu
→ Right panel opens with the interactive calculator
→ Pre-populated with Dell's financial data from the audit
→ User adjusts inputs (conversion rate, AOV)
→ Clicks "Save" → saved to PostgreSQL for this account

---

## SCALE CONSIDERATIONS

### 500-1000 accounts
- Left panel with search + alphabetic index handles this
- Virtualized list (react-window) for smooth scrolling
- Accounts loaded in pages, not all at once
- Search is instant (client-side filter on loaded accounts)

### Concurrent audits
- Temporal handles queueing — max 5 concurrent audits configurable
- Rate limiting on external APIs handled by Redis
- Users see queue position if their audit is waiting

### Data storage
- PostgreSQL handles audit data efficiently
- Old audit results archived after 90 days (configurable)
- Module outputs stored as JSONB — queryable without separate tables per module

---

## WHAT WE BUILD TONIGHT (Phase 1 Minimum)

1. ✅ Backend foundation (Phase 0 — DONE)
2. Next.js frontend with assistant-ui chat
3. Three-panel layout (left account list, center chat, right detail — right panel stubbed)
4. Chat API route with Claude + tools
5. get_tech_stack tool calling the Prism backend
6. TechStackCard component rendering in conversation
7. Thinking/transparency mode on tool execution
8. Basic account list in left panel (hardcoded initially, DB-backed in Phase 2)
9. Clerk auth with Google OAuth (basic — just login gate)

**NOT tonight:**
- Full RBAC
- Admin panel
- Right panel tools (ROI calculator, etc.)
- Voice interface
- Bulk import
- Additional modules beyond intel-techstack

The goal tonight: type a question, see intelligence appear as a rich component, with thinking mode visible. That's the moment. Everything else builds on top.
