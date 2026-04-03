# Prism Frontend — Full AI-Native Interface
# Paste this ENTIRE document into Claude Code.
# Read the frontend architecture spec at docs/specs/prism-frontend-architecture-spec.md first.

## BEFORE YOU START — READ THESE FIRST

1. **Read the Anthropic frontend-design skill** at `/mnt/skills/public/frontend-design/SKILL.md` before writing ANY component code. Follow its design principles for all UI work. This is mandatory.

2. **Use agent teams mode.** Tasks 3, 5, 6, 7, and 8 are independent — run them in parallel with developer+QA agent pairs. Each developer agent must have a corresponding QA agent that writes and runs tests. Neither marks complete until QA passes. Write progress to `docs/decisions/session-log-frontend-{date}.md` after every task.

3. **Read the frontend architecture spec** at `docs/specs/prism-frontend-architecture-spec.md` for the full context on what we're building and why.

---

## WHAT YOU'RE BUILDING

The complete frontend for Prism — an AI-native prospect intelligence platform. Three-panel layout with fluid, resizable panels. Conversational interface as the primary UX. Rich component rendering inline in chat. Thinking/transparency mode showing tool execution. Authentication via Google SSO. Account management with search and alphabetic navigation.

This is enterprise-grade from day one. No prototypes. No shortcuts.

## TECH STACK

- **Next.js 15** (App Router)
- **Vercel AI SDK 6** (`ai` + `@ai-sdk/anthropic`)
- **assistant-ui** (`@assistant-ui/react` + `@assistant-ui/react-ai-sdk`)
- **21st.dev** — component library (community-curated, polished components via shadcn/ui install infrastructure)
- **Tailwind CSS v4** — styling
- **Clerk** — authentication (Google OAuth SSO)
- **TypeScript** — strict mode, no `any` types

## PROJECT STRUCTURE

```
frontend/
├── package.json
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── components.json
├── middleware.ts                    # Clerk auth middleware
├── .env.local
│
├── app/
│   ├── layout.tsx                   # Root layout with ClerkProvider
│   ├── globals.css
│   ├── sign-in/[[...sign-in]]/
│   │   └── page.tsx                 # Clerk sign-in page
│   ├── (authenticated)/             # Route group — requires auth
│   │   ├── layout.tsx               # Three-panel shell layout
│   │   ├── page.tsx                 # Main app — redirects to chat
│   │   └── chat/
│   │       └── page.tsx             # The primary chat interface
│   └── api/
│       └── chat/
│           └── route.ts             # Vercel AI SDK endpoint with tools
│
├── components/
│   ├── layout/
│   │   ├── app-shell.tsx            # Three-panel layout container
│   │   ├── left-panel.tsx           # Account list + navigation
│   │   ├── center-panel.tsx         # Chat area wrapper
│   │   ├── right-panel.tsx          # Detail/tools panel (expandable)
│   │   └── header.tsx               # Top bar with Prism branding + user
│   │
│   ├── accounts/
│   │   ├── account-list.tsx         # Scrollable account list with virtualization
│   │   ├── account-search.tsx       # Search bar with instant filter
│   │   ├── account-item.tsx         # Single account row (name, domain, status, tier)
│   │   ├── alpha-index.tsx          # A-Z alphabetic jump buttons
│   │   └── thread-list.tsx          # Conversation threads per account
│   │
│   ├── chat/
│   │   ├── prism-chat.tsx           # Main chat with assistant-ui Thread
│   │   ├── tool-renderers.tsx       # Maps ALL tool results to components
│   │   ├── thinking-block.tsx       # Collapsible execution transparency
│   │   └── welcome-message.tsx      # Initial state with suggested actions
│   │
│   ├── prism/                       # Intelligence card components
│   │   ├── overview-card.tsx        # 4-quadrant overview
│   │   ├── tech-stack-card.tsx      # Technology detection
│   │   ├── score-card.tsx           # Search quality score
│   │   ├── signal-card.tsx          # Timing signals (Why Act Now)
│   │   ├── action-card.tsx          # Recommended next action
│   │   ├── financial-card.tsx       # Revenue, earnings quotes
│   │   ├── competitor-matrix.tsx    # Side-by-side comparison
│   │   ├── hiring-card.tsx          # Hiring signals, buying committee
│   │   ├── news-card.tsx            # Recent news and leadership changes
│   │   ├── partner-card.tsx         # Co-sell opportunities
│   │   ├── audit-progress.tsx       # Module-by-module execution progress
│   │   └── evidence-badge.tsx       # Source pill with tier color
│   │
│   ├── tools/                       # Right panel standalone tools
│   │   ├── roi-calculator.tsx       # Interactive ROI model
│   │   ├── full-report.tsx          # Complete scored audit view
│   │   ├── playbook-viewer.tsx      # MEDDPICC, SPIN, objection handling
│   │   ├── campaign-editor.tsx      # ABX email sequence editor
│   │   └── screenshot-gallery.tsx   # Annotated search audit screenshots
│   │
│   └── ui/                          # 21st.dev components (installed via shadcn cli)
│       └── ...
│
├── lib/
│   ├── prism-api.ts                 # FastAPI client with error handling
│   ├── tools.ts                     # Claude tool definitions
│   ├── types.ts                     # TypeScript types matching Pydantic schemas
│   └── utils.ts                     # Shared utilities
│
├── hooks/
│   ├── use-accounts.ts              # Account list management
│   ├── use-active-account.ts        # Currently selected account
│   └── use-right-panel.ts           # Right panel open/close state
│
└── public/
    └── prism-logo.svg
```

## BUILD ORDER (STRICT — do not skip ahead)

### Task 1: Scaffold and configure

```bash
mkdir frontend && cd frontend
npx create-next-app@latest . --typescript --tailwind --app --src-dir=false
```

Install all dependencies:

```bash
# AI SDK + Anthropic provider
pnpm add ai @ai-sdk/anthropic

# assistant-ui
pnpm add @assistant-ui/react @assistant-ui/react-ai-sdk

# Clerk auth
pnpm add @clerk/nextjs

# UI utilities
pnpm add react-window react-resizable-panels @tanstack/react-query lucide-react clsx

# shadcn/ui infrastructure init (required — 21st.dev components install through this)
pnpm dlx shadcn@latest init

# IMPORTANT: Source ALL visual components from 21st.dev, NOT base shadcn/ui.
# 21st.dev components are dramatically more polished and match our design standard.
# Browse https://21st.dev to find the best component for each need.
# Install pattern: pnpm dlx shadcn@latest add "https://21st.dev/r/{author}/{component}"
#
# For each component you need (card, badge, button, input, etc.):
#   1. Search 21st.dev for the component type
#   2. Pick the one that best matches the visual quality of our existing audit SPA
#   3. Install it via the npx shadcn command from 21st.dev
#   4. If you genuinely cannot find a suitable component on 21st.dev, STOP and ASK
#      the user what to do. Do NOT silently fall back to base shadcn/ui.
#
# Example installs (find the actual best components on 21st.dev):
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/card"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/badge"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/button"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/separator"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/scroll-area"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/input"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/dialog"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/sheet"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/tooltip"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/avatar"
pnpm dlx shadcn@latest add "https://21st.dev/r/shadcn/dropdown-menu"

# assistant-ui chat components (these come from assistant-ui's own registry)
pnpm dlx shadcn@latest add "https://r.assistant-ui.com/shadcn/thread"
```

Create `.env.local`:
```
ANTHROPIC_API_KEY=
PRISM_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/chat
```

**Verify:** `pnpm dev` runs without errors. Page loads at localhost:3000.

### Task 2: Authentication with Clerk

`middleware.ts` — protect all routes except sign-in:
```typescript
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher(["/sign-in(.*)", "/api/chat(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};
```

`app/layout.tsx` — wrap in ClerkProvider:
```tsx
import { ClerkProvider } from "@clerk/nextjs";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}
```

`app/sign-in/[[...sign-in]]/page.tsx` — Clerk sign-in page:
```tsx
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center space-y-6">
        <h1 className="text-3xl font-bold">Prism</h1>
        <p className="text-muted-foreground">Light goes in. Intelligence comes out.</p>
        <SignIn />
      </div>
    </div>
  );
}
```

**Note on Clerk setup:** If CLERK_PUBLISHABLE_KEY is not yet configured, implement the auth structure but add a bypass flag so development works without Clerk during initial build. Set `BYPASS_AUTH=true` in .env.local for local development. Wire real Clerk keys later.

**Verify:** Auth gate works — unauthenticated users redirect to /sign-in.

### Task 3: Three-panel layout shell with fluid resizable panels

**The panels must be resizable by dragging — exactly like Claude Desktop.** Users can drag the dividers between panels to resize them, double-click a divider to collapse a panel, and each panel has sensible min/max widths. This is not optional — fixed-width panels feel rigid and dated.

Install the resizable panels library:
```bash
pnpm add react-resizable-panels
```

`components/layout/app-shell.tsx` — fluid three-panel layout:

```tsx
"use client";

import { useState } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { LeftPanel } from "./left-panel";
import { CenterPanel } from "./center-panel";
import { RightPanel } from "./right-panel";
import { Header } from "./header";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [rightPanelContent, setRightPanelContent] = useState<string | null>(null);

  return (
    <div className="flex h-screen flex-col bg-background">
      <Header />
      <PanelGroup direction="horizontal" className="flex-1">
        {/* Left: Account navigation — resizable, collapsible */}
        <Panel
          defaultSize={18}
          minSize={12}
          maxSize={30}
          collapsible
          collapsedSize={0}
        >
          <LeftPanel />
        </Panel>

        <PanelResizeHandle className="w-[3px] bg-border hover:bg-primary/20 transition-colors cursor-col-resize" />

        {/* Center: Chat — takes remaining space */}
        <Panel defaultSize={rightPanelOpen ? 52 : 82} minSize={35}>
          <CenterPanel>{children}</CenterPanel>
        </Panel>

        {/* Right: Detail panel — resizable, collapsible */}
        {rightPanelOpen && (
          <>
            <PanelResizeHandle className="w-[3px] bg-border hover:bg-primary/20 transition-colors cursor-col-resize" />
            <Panel
              defaultSize={30}
              minSize={20}
              maxSize={45}
              collapsible
              collapsedSize={0}
              onCollapse={() => setRightPanelOpen(false)}
            >
              <RightPanel
                content={rightPanelContent}
                onClose={() => setRightPanelOpen(false)}
              />
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  );
}
```

**Resize handle styling:** The handle should be a subtle 3px line that highlights on hover — exactly like VS Code and Claude Desktop. Not a thick bar. Not invisible. A thin, discoverable drag handle that feels premium.

**Panel behavior:**
- Left panel: drag to resize between 12-30% width. Double-click handle or drag to 0% to collapse completely. Shows just the Prism logo when collapsed, click to expand.
- Center panel: always visible, minimum 35% width. Grows automatically when other panels collapse.
- Right panel: opens with animation when user selects a tool or clicks a card. Drag to resize between 20-45%. Drag to 0% or click X to collapse/close.
- All panel sizes persist to localStorage so they're remembered across sessions.

**Verify:** Panels render. Drag handles work. Panels resize smoothly. Collapse/expand works. Sizes persist across page refreshes.

`components/layout/header.tsx`:
```tsx
import { UserButton } from "@clerk/nextjs";

export function Header() {
  return (
    <header className="h-14 border-b flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <span className="text-xl font-bold tracking-tight">Prism</span>
        <span className="text-sm text-muted-foreground hidden sm:inline">
          Light goes in. Intelligence comes out.
        </span>
      </div>
      <UserButton afterSignOutUrl="/sign-in" />
    </header>
  );
}
```

**Left panel** (`components/layout/left-panel.tsx`):
- Search bar at top (components/accounts/account-search.tsx)
- Alphabetic index below search (components/accounts/alpha-index.tsx)
- Scrollable account list using react-window for virtualization
- Each account shows: company name, domain, tier badge, status dot, last audit date
- Clicking an account sets it as active and switches the chat context
- Thread management under each account (conversation history)

**Right panel** (`components/layout/right-panel.tsx`):
- Header with title + close button
- Renders different tool components based on what was selected:
  - ROI Calculator
  - Full Report
  - Sales Playbook
  - Campaign Editor
  - Screenshot Gallery
- Saves state per account per audit to the backend

**Verify:** Three panels render correctly. Left panel scrolls. Right panel slides in/out. Responsive behavior works.

### Task 4: Chat API route with tools

`app/api/chat/route.ts`:

```typescript
import { anthropic } from "@ai-sdk/anthropic";
import { streamText } from "ai";
import { tools } from "@/lib/tools";

export const maxDuration = 120;

export async function POST(req: Request) {
  const { messages } = await req.json();

  const result = streamText({
    model: anthropic("claude-sonnet-4-20250514"),
    system: `You are Prism, an AI-powered prospect intelligence assistant built for Algolia's commercial team.

Your role is to help AEs, BDRs, SEs, and PAMs prepare for prospect meetings with deep, verified intelligence.

When a user mentions a company name or domain:
1. Use the get_tech_stack tool to fetch their technology profile
2. Present the results conversationally, highlighting the most actionable insights
3. Always mention evidence tiers (VERIFIED, WEBFETCH, ESTIMATE)
4. If competitive data is available, highlight where the prospect stands vs peers

When a user asks to "run an audit" or "do a deep dive":
1. Use the run_full_audit tool to trigger the Temporal workflow
2. Explain that modules are executing and results will stream in
3. As results arrive, present each module's findings with its card component

When presenting data:
- Lead with what matters most for a sales conversation
- Never make up data — only present what tools return
- If you don't have data, say so and offer to run an audit
- Use the prospect's executive language when available (from earnings calls)
- Frame everything in terms of "why this matters for the deal"

You are conversational but precise. You are briefing a sales professional, not writing a report.

Prism's motto: Light goes in. Intelligence comes out.`,
    messages,
    tools,
  });

  return result.toDataStreamResponse();
}
```

`lib/tools.ts` — tool definitions calling the Prism FastAPI backend:

Define these tools:
1. **get_tech_stack** — POST /api/v1/modules/intel-techstack/execute with { domain }
2. **run_full_audit** — POST /api/v1/audits then POST /api/v1/audits/{id}/run
3. **get_audit_status** — GET /api/v1/audits/{id}
4. **get_account_info** — GET /api/v1/accounts?domain={domain}

Each tool:
- Has a clear description so Claude knows when to use it
- Uses zod for parameter validation
- Wraps the fetch call in try/catch with proper error handling
- Returns structured data that maps to a card component
- Logs the call for transparency (used by thinking-block component)

**Verify:** API route responds to POST requests. Tool definitions are valid.

### Task 5: Chat interface with assistant-ui

`components/chat/prism-chat.tsx` — the core chat experience:

Use assistant-ui's Thread component with custom tool result rendering. Register a tool UI renderer for EACH tool:

```tsx
const TechStackToolUI = makeAssistantToolUI({
  toolName: "get_tech_stack",
  render: ({ result, status }) => {
    if (status === "running") return <ThinkingBlock tool="get_tech_stack" />;
    if (!result) return null;
    return <TechStackCard data={result} />;
  },
});
```

The pattern for every tool:
- **While running:** Show ThinkingBlock (collapsible transparency)
- **When complete:** Show the appropriate card component
- **On error:** Show error state with retry option

`components/chat/welcome-message.tsx` — shown when conversation is empty:
```
Welcome to Prism ✦

Try asking:
• "What technology does dell.com use?"
• "Run a full audit on brooks.com"
• "Compare Costco's search to their competitors"
• "What should I know before my meeting with Nordstrom?"

Or select an account from the left panel to start.
```

**Verify:** Chat accepts messages. Welcome state shows suggested queries.

### Task 6: Thinking/transparency block

`components/chat/thinking-block.tsx` — THE MOST IMPORTANT UX ELEMENT

This shows exactly what Prism is doing behind the scenes, just like Claude desktop's thinking mode.

```tsx
interface ThinkingBlockProps {
  tool: string;
  steps?: ThinkingStep[];
  isComplete?: boolean;
}

interface ThinkingStep {
  label: string;           // "Calling BuiltWith API"
  detail?: string;         // "GET https://api.builtwith.com/v21/..."
  status: "running" | "complete" | "error";
  duration_ms?: number;
  timestamp: string;
}
```

**Behavior:**
- Starts collapsed with a subtle animation: "⟳ Analyzing dell.com..."
- User can click to expand and see step-by-step progress:
  ```
  ▼ Analyzing technology stack for dell.com
    ✓ Calling BuiltWith API... 342ms
    ✓ Received 47 technologies
    ✓ Classifying search vendor: Elasticsearch detected
    ✓ Cross-referencing with known vendor list (12 vendors)
    ⟳ Formatting results...
  ```
- When complete, collapses to a single line: "✓ Technology analysis complete — 1.2s"
- The expanded view shows the raw process — API calls, data sizes, classifications
- Styled with monospace font for the detail lines, subtle background
- Animated step-by-step as each sub-step completes (streamed via tool execution events)

**This is critical to the user experience.** It builds trust. Users see that Prism is doing real work with real data, not hallucinating. It mirrors the transparency that makes Claude desktop feel trustworthy.

**Verify:** Thinking block renders, expands/collapses, shows step-by-step progress.

### Task 7: Intelligence card components

Build the card components that render tool results in the conversation. These should match the visual quality of the existing audit SPA (screenshots provided in the spec).

**tech-stack-card.tsx:**
- Card with subtle border, rounded corners
- Header: "TECHNOLOGY STACK" in small caps with evidence-badge
- Search vendor prominently displayed with vendor icon if available
- Detection source badge (BuiltWith, SimilarWeb, Network)
- Ecommerce platform
- Key categories: Analytics, Personalization, CDN, Bot Detection
- Technology pills in grouped rows
- If Algolia detected: green highlight banner
- If competitor detected (Coveo, Elasticsearch, etc.): amber highlight with displacement signal
- Evidence tier badge on every data point

**evidence-badge.tsx:**
- ✅ VERIFIED — green pill, solid
- 🌐 WEBFETCH — blue pill
- 🔍 WEBSEARCH — amber pill
- 📊 ESTIMATE — gray pill
- Hoverable tooltip showing source URL and retrieval date

**score-card.tsx:**
- Large score number (e.g., 3.8/10) with color coding
  - 0-3: Red (CRITICAL)
  - 3-5: Amber (NEEDS WORK)
  - 5-7: Yellow (AVERAGE)
  - 7-10: Green (STRONG)
- Severity badge
- List of critical gaps as bullet points
- Clickable to open full audit detail in right panel

**signal-card.tsx:**
- "WHY ACT NOW" header
- Signal list with icons:
  - 💬 Exec Statement — quote with source
  - ⚠️ Competitor Move — what competitor did
  - 📉 Industry Risk — financial signal
  - 👤 Leadership Change — new hire
  - 💼 Hiring Surge — open roles
- Each signal has severity (HIGH / MEDIUM / LOW) badge
- Source link on every signal

**All cards must:**
- Have proper loading skeletons (not just a spinner)
- Handle error states gracefully
- Be responsive (work in the chat column width)
- Match the visual quality of the existing Vercel SPA audit pages
- Use 21st.dev Card, Badge, Separator as base — browse 21st.dev for the most polished versions
- Include evidence-badge on every sourced data point
- If you need a component type (e.g., a specific card variant, a data table, a progress indicator) that you haven't installed yet, browse 21st.dev first. If nothing fits, ASK — do not fall back to plain shadcn

**Verify:** Each card renders correctly with sample data. Evidence badges show correct colors. Cards are visually polished.

### Task 8: Account list in left panel

`components/accounts/account-list.tsx`:
- Uses react-window FixedSizeList for virtualized scrolling (handles 1000+ accounts)
- Each row: company name, domain (small text), tier badge, status dot
- Tier badges: HOT (red), WARM (amber), COLD (gray)
- Status: green dot (audit complete), amber dot (running), gray dot (no audit)
- Click selects account → updates chat context
- Active account highlighted with accent background

`components/accounts/account-search.tsx`:
- Input at top of left panel
- Instant filter as user types — filters the virtualized list
- Debounced (150ms) for performance
- Clear button (X) to reset
- Shows match count: "3 of 847 accounts"

`components/accounts/alpha-index.tsx`:
- Vertical strip of A-Z buttons (compact)
- Click jumps the virtualized list to first account starting with that letter
- Current letter highlighted based on scroll position
- Dimmed letters with no matching accounts

`components/accounts/thread-list.tsx`:
- Under the active account, show conversation threads
- Each thread: title, date, preview of last message
- "New thread" button
- Click switches the chat to that thread's context

**Data source for now:** Load accounts from the Prism API GET /api/v1/accounts. If that endpoint doesn't exist yet, create a static JSON file at `public/accounts.json` with 20 sample accounts and note in the code where to wire up the real API.

**Verify:** Account list renders, search filters instantly, alphabetic index jumps correctly, clicking an account updates the UI.

### Task 9: Right panel structure

`components/layout/right-panel.tsx`:
- Header with content title + close button (X)
- Scrollable content area
- Tool menu when no specific content is selected:
  - ROI Calculator
  - Full Audit Report
  - Sales Playbook
  - ABX Campaign
  - Screenshot Gallery
- Each tool is a stub for now with a "Coming soon" message
- The ROI Calculator can be a basic implementation:
  - Input fields: Annual Digital Revenue, Baseline Conv Rate, Avg Order Value
  - Sliders for value levers: Conversion Lift %, AOV Increase %, Bounce Reduction %
  - Live-updating total impact calculation
  - Save button (saves to localStorage for now, PostgreSQL in Phase 2)

**Verify:** Right panel opens/closes with animation. Tool menu renders. ROI calculator computes.

### Task 10: Wire it all together and test

Full integration test:

1. Start all backends:
   ```bash
   docker compose up -d
   temporal server start-dev
   python scripts/start_worker.py
   uvicorn prism_platform.main:app --reload --port 8000
   ```

2. Start frontend:
   ```bash
   cd frontend && pnpm dev
   ```

3. Test the full flow:
   - Open localhost:3000
   - Auth gate shows (or bypassed in dev)
   - Three-panel layout renders
   - Left panel shows account list
   - Type in chat: "What technology does brooks.com use?"
   - Thinking block appears with step-by-step progress
   - TechStackCard renders with real BuiltWith data
   - Evidence badges show correct tiers
   - Clicking on score opens right panel (stub)
   - Search in left panel filters accounts
   - Alphabetic index jumps correctly

**Verify all of these before marking complete.**
- [ ] Three-panel layout renders correctly
- [ ] Panel resize handles work — drag to resize all three panels
- [ ] Left panel collapses and expands
- [ ] Right panel opens and closes with animation
- [ ] Panel sizes persist across page refresh (localStorage)
- [ ] Chat input accepts messages and streams responses
- [ ] Typing "What tech does brooks.com use?" triggers the get_tech_stack tool
- [ ] Thinking block appears with step-by-step progress while tool executes
- [ ] TechStackCard renders with real BuiltWith data when tool completes
- [ ] Evidence badges show correct tier colors (green for VERIFIED, amber for WEBFETCH, etc.)
- [ ] Search in left panel filters accounts instantly
- [ ] Alphabetic index jumps to correct position
- [ ] Clicking an account updates the active state
- [ ] Auth gate works (or bypass flag works in dev mode)
- [ ] `pnpm build` succeeds with zero errors
- [ ] `pnpm lint` passes
- [ ] The UI looks polished and premium — not like a prototype, not like a factory floor

---

## CODING STANDARDS

- TypeScript strict mode — zero `any` types
- Every API call in try/catch with structured error logging
- Every component has TypeScript props interface
- Tailwind for all styling — no inline styles, no CSS files
- **21st.dev is the ONLY component source.** Browse https://21st.dev for every visual component (cards, buttons, badges, inputs, layouts, data display). Install via `pnpm dlx shadcn@latest add "https://21st.dev/r/{author}/{component}"`. Do NOT use base shadcn/ui defaults — they look like a factory floor. If you cannot find a suitable component on 21st.dev, STOP and ASK the user. Never silently fall back to base shadcn.
- assistant-ui for chat primitives (Thread, Composer, Message)
- Proper loading skeletons on all async components
- Error boundaries on all panels
- Responsive: minimum 1024px viewport (desktop-first, this is a sales tool)
- Match the visual quality of the existing audit SPA — dark header, card-based design, evidence badges, severity colors, source pills. That SPA was built with 21st.dev components. The new interface must look equally polished or better.

## WHAT NOT TO DO

- Do NOT build a separate search box for running audits — the chat IS the interface
- Do NOT store intelligence data in chat context — always fetch from the API
- Do NOT use raw JSON display for tool results — always render as a card component
- Do NOT skip the thinking block — transparency is a core UX principle
- Do NOT use mock data — if the API isn't ready for a tool, show "Module not yet available" in the card
- Do NOT skip error states — every card needs a proper error view
- Do NOT skip loading skeletons — every async operation shows a skeleton, not a spinner
- Do NOT use base shadcn/ui components directly — ALWAYS source from 21st.dev. If you can't find what you need on 21st.dev, ASK the user instead of falling back to base shadcn. Base shadcn looks like a factory floor. We are building a premium product.

## WRITE PROGRESS TO SESSION LOG

After every completed task, append to `docs/decisions/session-log-frontend-{date}.md`.

## START NOW

Begin with Task 1 (scaffold). Read the architecture spec first. Show the file structure before writing component code. Use agent teams — parallel agents for independent components.
