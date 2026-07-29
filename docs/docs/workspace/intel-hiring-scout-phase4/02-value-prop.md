# Value Proposition — intel-hiring Scout Phase 4

## JTBD Template

### 1. Who
The `intel-hiring` module (internal pipeline consumer). Downstream: the PRISM audit UI that surfaces `hiring_narrative` and `hiring_signal_score` to sales reps.

### 2. Why
The module needs to answer: "Is this company actively investing in search technology right now, and what role are they hiring for?" Perplexity alone answers this from cached web data — typically job aggregators (Indeed, LinkedIn) that lag reality by days or weeks. For fast-moving hiring cycles (new CTO → immediate search RFP), stale data equals missed signal.

### 3. What Before
`intel-hiring` is a single-track Perplexity call. Perplexity searches job boards and returns a structured JSON blob. Two failure modes:
- Perplexity's index is stale — a role posted yesterday isn't found
- Perplexity hallucinate job titles that sound plausible but aren't actually open
No ground truth. Sales rep can't cite a specific job posting.

### 4. How
Two tracks:
- **Track 1 (Scout)**: Fetch the company's own careers portal (`/careers`, `/jobs`, subdomains) via Crawl4AI Playwright. Return raw markdown of live job listings + detect LinkedIn redirect.
- **Track 2 (Perplexity)**: Run with Track 1 content injected as `{upstream_careers_page}`. Perplexity now synthesizes live page data + its own web search — citations point to real job URLs.

Track 1 failure is non-fatal. LinkedIn redirect is flagged (`redirected_to_linkedin=True`) so the UI can prompt the user to check LinkedIn manually.

### 5. What After
- `open_roles` fields cite actual job titles from the live career page
- `hiring_narrative` can reference specific postings: "Dell is hiring a Search Platform Lead (posted this week) and 2 Elasticsearch engineers — strong build signal"
- `hiring_signal_score` confidence is higher because it's backed by ground truth
- LinkedIn redirect flag surfaces the data gap so the rep knows when to investigate manually

### 6. Alternatives

| Alternative | Why rejected |
|---|---|
| Apify LinkedIn scraper | LinkedIn blocks crawlers; Apify API adds billing complexity; Perplexity already searches LinkedIn via web search |
| Extend BrowserClient with a hire-specific path | BrowserClient's role is generic tiered fetching, not module-specific logic. Module-specific path discovery (career URL patterns) belongs in the module |
| LLM extraction (`/extract`) for structured job parsing | Adds LLM API cost + latency; markdown injection into Perplexity's context achieves 90% of the value at zero extra LLM cost |
| Poll job APIs (Greenhouse, Lever, Workday) | Requires knowing which ATS the company uses; fragile; Scout handles Workday/Greenhouse JS rendering automatically |

## Value Prop Statement

Scout gives `intel-hiring` a live ground-truth career page as Track 1 input, so Perplexity's research is grounded in today's actual job postings rather than cached aggregator data — producing hiring signals a sales rep can cite by name in their outreach.
