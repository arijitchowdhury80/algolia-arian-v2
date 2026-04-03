# Prism — Technical Specification v3.0
## Prospect Intelligence Platform: Light goes in. Intelligence comes out.

**Product name:** Prism (formerly PIP)
**Revision:** v3.0 — Temporal.io orchestration, deep module specs, data source strategy, Perplexity-primary architecture
**Date:** March 31, 2026
**Authors:** Arijit Chowdhury (Founder) + Claude (Chief Architect)

---

## 0. Global Data Source Strategy

**Perplexity is the primary intelligence engine for ALL web research.** One API covers company profiles, executives, competitors, news, social signals, industry research, executive quotes, and competitive analysis.

Specialized APIs are used ONLY where structured data is genuinely better:

| Source | Used For | Why Not Perplexity |
|---|---|---|
| **Perplexity** | ALL web intelligence: company intel, execs, competitors, news, quotes, social signals, industry research | PRIMARY — covers 80% of research |
| **BuiltWith** | Technology detection | Structured list of 3,000+ technologies with categories, first/last detected dates, removal history |
| **SimilarWeb** | Traffic analytics | Structured numbers: exact visits, source %, keyword rankings, device splits, trended |
| **Yahoo Finance** | Financial data | Structured JSON: stock price, revenue, margins, ratios — no LLM interpretation needed |
| **SEC EDGAR** | Official filings | Raw 10-K text and earnings transcripts — we parse with OUR LLM to extract specific quotes, not Perplexity's summary |
| **Apify** | LinkedIn scraping | LinkedIn is a walled garden Perplexity can't access. Apify actors scrape job posts and profiles |
| **Tavily** | BACKUP ONLY | If Perplexity is down or rate-limited. Not a primary source for anything |

### API Keys Required

```bash
# PRIMARY
PERPLEXITY_API_KEY=          # Most modules — company, news, social, investor, competitors
BUILTWITH_API_KEY=           # intel-techstack
SIMILARWEB_API_KEY=          # intel-traffic
APIFY_TOKEN=                 # intel-hiring, intel-social (LinkedIn)

# FREE (no key needed)
# Yahoo Finance              # intel-financial-public
# SEC EDGAR                  # intel-investor

# BACKUP
TAVILY_API_KEY=              # Fallback only — if Perplexity is unavailable
```

### Field-Level Source Provenance — MANDATORY

**Every data element in every module MUST have a source citation.** No exceptions. No naked data.

- Every field stored in the database has a corresponding `Source` record with `source_url`, `source_label`, and `evidence_tier`
- The UI renders every data point with an inline clickable citation link
- Perplexity returns inline citations (`[label](url)`) — these MUST be parsed and stored per-field, never stripped
- Data without attribution is considered unverified and must not be displayed to users

This is the entire reason we pay for Perplexity `sonar-pro` — it researches AND cites. A generic web search gives links; Perplexity gives facts tied to sources. We must preserve that chain from API response → database → UI.

### No LLM for Deterministic Operations

**Never use an LLM to parse, map, or restructure structured data.** If the data source returns structured output (JSON from Perplexity, API responses from BuiltWith/SimilarWeb/Yahoo Finance), parse it with `json.loads()` + Pydantic `model_validate()`.

LLM parsing is non-deterministic, costs money, adds latency, and can silently produce wrong values. LLMs are for **research and generation** (e.g., Perplexity for web research, Claude for synthesis narratives). Never for field mapping.

### Single Composite API Calls

**Never split a query into multiple sequential API calls when one composite call returns the same data.** Perplexity handles large composite prompts well — ask for everything in one call and request JSON output. This saves API credits, reduces latency, and produces more coherent results because the model can cross-reference context within one response.

### Hub-and-Spoke Data Architecture

**`intel-company` is the hub. Every other module is a spoke.**

`intel-company` runs first and populates the `accounts` table with the canonical company profile — identity, executives, competitors, financials, classification, everything. Every spoke module queries the `accounts` table (by `company_name` or `domain`) to get the fields it needs, then runs its own specialized logic.

Inter-module data flows through the `accounts` table, not through JSONB blobs, not through `module_executions` lookups, not through parameters passed in code. One table, proper columns, one pattern.

### Database-First Caching

Every module result is cached in PostgreSQL (`module_executions` table). Before any API call, the system checks for a fresh cached result. TTLs per data type:

| Data Type | TTL | Rationale |
|---|---|---|
| Technology stack | 7 days | Tech changes slowly |
| Traffic analytics | 24 hours | Monthly estimates update daily |
| Financial data | 1 hour | Market data moves fast |
| Hiring/jobs | 24 hours | Postings change daily |
| News | 6 hours | News cycle |
| Company profile | 7 days | Company identity is stable |
| Competitor list | 7 days | Competitive landscape is stable |

---

## 1. Revised Architecture Decision: Temporal.io

### 1.1 Why Temporal, not a custom runner

| Capability | Custom DAG runner | Temporal.io |
|---|---|---|
| Build effort | ~200 lines (but throwaway) | ~200 lines (production code) |
| Retry per activity | Manual implementation | `RetryPolicy(max_attempts=3)` — built in |
| Resume from failure | Not possible (restart entire run) | Durable execution — resumes from exact failure point |
| Parallel fan-out | `asyncio.gather` (works) | `asyncio.gather` (same, but with durability) |
| Timeout enforcement | Manual `asyncio.wait_for` | `start_to_close_timeout` — enforced by server |
| Visibility into runs | Custom logging | Temporal Web UI — visual timeline of every activity |
| Queue management | Redis (manual) | Built-in task queues with worker scaling |
| Production readiness | Needs rewrite | Already production-ready |
| Operational overhead | Zero | `temporal server start-dev` locally; Temporal Cloud for prod |

### 1.2 Local Development

```bash
# One-time install
brew install temporal        # macOS
# or: curl -sSf https://temporal.download/cli | sh

# Start local dev server (includes Web UI at localhost:8233)
temporal server start-dev

# That's it. No Docker needed for Temporal itself.
```

### 1.3 Temporal Concepts Mapped to Prism

```python
# ── WORKFLOW: The full audit ──────────────────────────────────────
# This is the orchestrator. It's Python code, not a prompt.
# Temporal guarantees it runs to completion or reports exactly where it stopped.

@workflow.defn
class AuditWorkflow:
    """Full prospect audit — Waves 1-7 with gates."""

    @workflow.run
    async def run(self, input: AuditInput) -> AuditResult:
        # Wave 1: Intelligence collection (parallel)
        wave1_modules = [
            "intel-company", "intel-techstack", "intel-traffic",
            "intel-competitors", "intel-hiring", "intel-social",
            "intel-news", "intel-investor", "intel-partner",
            "intel-industry",
            "intel-financial-public" if input.ticker else "intel-financial-private",
        ]

        wave1_results = await asyncio.gather(*[
            workflow.execute_activity(
                run_module,
                RunModuleInput(module_name=name, audit_id=input.audit_id, domain=input.domain),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3, backoff_coefficient=2.0),
            )
            for name in wave1_modules
        ])

        # Gate 1: Verify all Wave 1 modules produced valid output
        gate1 = check_wave_gate(wave1_results, required_pass=8)
        if not gate1.passed:
            return AuditResult(status="blocked", gate_failure=gate1)

        # Wave 2: Query generation (depends on company + techstack)
        wave2_result = await workflow.execute_activity(
            run_module,
            RunModuleInput(module_name="intel-queries", ...),
            start_to_close_timeout=timedelta(minutes=3),
        )

        # Wave 3: Browser audit
        wave3_result = await workflow.execute_activity(
            run_module,
            RunModuleInput(module_name="audit-browser", ...),
            start_to_close_timeout=timedelta(minutes=15),
        )

        # ... Waves 4-7 follow same pattern ...

        return AuditResult(status="complete", results=all_results)


# ── ACTIVITY: A single module execution ───────────────────────────
# Activities are the units of work. Each module is an activity.
# Temporal handles retry, timeout, and state for each one independently.

@activity.defn
async def run_module(input: RunModuleInput) -> ModuleResult:
    """Execute a single module. Temporal retries this on failure."""
    module = MODULE_REGISTRY[input.module_name]

    # Build context with upstream results from DB
    context = await build_execution_context(input)

    # Execute
    result = await module.execute(context)

    # Validate
    validation = await module.validate(result)
    if not validation.passed:
        raise ModuleValidationError(module=input.module_name, errors=validation.errors)

    # Persist to PostgreSQL
    await save_module_result(input.audit_id, input.module_name, result)

    return result
```

### 1.4 What the Temporal Web UI Gives You

When you open `localhost:8233` and look at an audit run, you see:

```
Audit Workflow: Dell Technologies (dell.com)
├─ Wave 1 [COMPLETED 4m32s]
│  ├─ intel-company     ✓ 12s     $0.003 LLM
│  ├─ intel-techstack   ✓ 8s      $0.000
│  ├─ intel-traffic     ✓ 5s      $0.000
│  ├─ intel-competitors ✓ 23s     $0.008 LLM
│  ├─ intel-hiring      ✓ 45s     $0.000
│  ├─ intel-social      ✗ RETRY 1 → ✓ 31s  $0.000
│  ├─ intel-news        ✓ 18s     $0.000
│  ├─ intel-investor    ✓ 52s     $0.012 LLM
│  ├─ intel-partner     ✓ 15s     $0.005 LLM
│  ├─ intel-industry    ✓ 28s     $0.009 LLM
│  └─ intel-financial   ✓ 9s      $0.004 LLM
├─ Gate 1 [PASSED: 11/11 modules]
├─ Wave 2 [COMPLETED 18s]
│  └─ intel-queries     ✓ 18s     $0.006 LLM
├─ Wave 3 [RUNNING]
│  └─ audit-browser     ⟳ 3m12s elapsed...
```

No hallucination. No "I've completed this." A real timeline with real durations.

### 1.5 Production Path

| Stage | Temporal setup |
|---|---|
| Local dev (you + Claude Code) | `temporal server start-dev` |
| Team testing (5-10 users) | Self-hosted Temporal on Railway (single container) |
| Production (100 users) | Temporal Cloud ($200/mo) — zero ops |

The workflow code doesn't change between stages. Only the connection string changes.

---

## 2. Deep Module Specifications

Each module is its own product. Here's the depth of thinking required,
using `intel-hiring` as the worked example, then the pattern for all others.

---

### 2.1 MODULE: intel-hiring (People Intelligence)

**Current state:** Calls Apify LinkedIn Jobs scraper, classifies into ICP tiers, writes markdown.
**Target state:** Comprehensive people intelligence platform — not just job postings but organizational structure, buying committee identification, champion signals, and contact enrichment.

#### 2.1a Data Sources (current → target)

| Source | Current | Target | What it adds |
|---|---|---|---|
| **LinkedIn Jobs (Apify)** | ✓ | ✓ Enhanced | Open roles → ICP tier classification |
| **LinkedIn Company Employees (Apify)** | ✗ | ✓ NEW | Current employee directory → org chart inference |
| **LinkedIn Profile Scraper (PhantomBuster)** | ✗ | ✓ NEW | Key executive profiles: tenure, previous companies, skills, connections, recent activity |
| **LinkedIn Profile Posts (Apify)** | ✗ | ✓ NEW | Executive personal posts → search/digital pain signals |
| **Glassdoor/Comparably** | ✗ | ✓ NEW | CEO approval, culture ratings, "digital transformation" mentions in reviews |
| **Indeed/ZipRecruiter** | ✗ | ✓ NEW | Cross-platform job posting validation |
| **Crunchbase People** | ✗ | ✓ NEW | Executive backgrounds, board connections |
| **Google Search (structured)** | ✗ | ✓ NEW | Conference talks, podcast appearances, published articles |

#### 2.1b Output Schema (comprehensive)

```python
class HiringOutput(BaseModel):
    """Complete people intelligence for an account."""

    # ── Open Roles ────────────────────────────────────────
    open_roles: list[OpenRole]
    role_count_by_tier: dict[str, int]  # tier1: 3, tier2: 5, etc.
    hiring_velocity: HiringVelocity     # roles posted per month, trend
    build_vs_buy_signal: BuildVsBuySignal

    # ── Buying Committee ──────────────────────────────────
    buying_committee: BuyingCommittee
    # economic_buyer: Person (VP/SVP/C-level who signs the check)
    # technical_buyer: Person (architect/principal who evaluates)
    # champion: Person (user-level who feels the pain daily)
    # influencers: list[Person] (anyone with a voice in the decision)
    # blocker: Optional[Person] (someone who might resist change)

    # ── Organizational Intelligence ───────────────────────
    org_structure: OrgStructure
    # digital_team_size: int
    # engineering_team_size: int
    # reporting_chain: list[ReportingLevel]
    # recent_hires: list[RecentHire] (< 6 months — "make my mark" signal)
    # recent_departures: list[Departure] (< 6 months — instability signal)
    # avg_tenure_digital_team: float (months)

    # ── Champion Signals ──────────────────────────────────
    champion_signals: list[ChampionSignal]
    # person who:
    #   - posted about search/discovery/personalization on LinkedIn
    #   - previously worked at an Algolia customer
    #   - attended a relevant conference (Shoptalk, NRF, etc.)
    #   - has Algolia connections on LinkedIn
    #   - published articles about search/commerce

    # ── Contact Enrichment ────────────────────────────────
    contacts: list[EnrichedContact]
    # name, title, linkedin_url, email (if public),
    # tenure_months, previous_companies, relevant_skills,
    # linkedin_activity_score (0-10: how active are they?)
    # algolia_connection_score (0-10: how close to Algolia's network?)


class OpenRole(BaseModel):
    title: str
    department: str
    location: str
    posted_date: Optional[str]
    url: str
    icp_tier: Literal["tier1_economic", "tier2_technical", "tier3_champion", "tier4_user"]
    relevance_score: float              # 0-1: how relevant to Algolia pitch
    search_related: bool                # mentions search, discovery, relevance, etc.
    signals: list[str]                  # what this role tells us about buying intent
    source: str                         # linkedin, indeed, careers_page
    evidence_tier: EvidenceTier


class BuyingCommittee(BaseModel):
    economic_buyer: Optional[Person]
    technical_buyer: Optional[Person]
    champion: Optional[Person]
    influencers: list[Person]
    blocker: Optional[Person]
    confidence: Literal["high", "medium", "low"]
    # high = all roles identified with LinkedIn profiles
    # medium = roles identified but some from job postings (person not yet hired)
    # low = inferred from org structure, not confirmed
    methodology: str                    # How we identified each person


class ChampionSignal(BaseModel):
    person: Person
    signal_type: Literal[
        "posted_about_search",          # LinkedIn post about search/discovery
        "former_algolia_customer",      # Previously worked at Algolia customer
        "conference_speaker",           # Spoke at Shoptalk, NRF, etc.
        "algolia_connection",           # Connected to Algolia employees on LinkedIn
        "published_article",            # Wrote about search/commerce
        "new_hire_digital",             # Joined < 6 months ago in digital role
        "skill_match",                  # LinkedIn skills include search/ML/personalization
    ]
    evidence: str                       # The specific post/connection/article
    evidence_url: Optional[str]
    evidence_tier: EvidenceTier
    signal_strength: Literal["strong", "moderate", "weak"]


class HiringVelocity(BaseModel):
    roles_last_30d: int
    roles_last_90d: int
    trend: Literal["accelerating", "steady", "decelerating"]
    yoy_change_pct: Optional[float]     # vs. same period last year
    interpretation: str                 # "Dell is aggressively hiring for digital..."


class BuildVsBuySignal(BaseModel):
    signal: Literal["build", "buy", "mixed", "insufficient_data"]
    evidence: list[str]
    # "build" = hiring search engineers, ML engineers → building in-house
    # "buy" = hiring for vendor management, platform administration → buying
    # "mixed" = both signals present
    # "insufficient_data" = can't determine from available data
    confidence: Literal["high", "medium", "low"]
```

#### 2.1c Collector Implementation (multi-source)

```python
class HiringCollector:
    """Deterministic data collection from multiple sources."""

    async def collect_all(self, domain: str, company_name: str) -> RawHiringData:
        """Run all collection sources in parallel. Each source independent."""

        results = await asyncio.gather(
            self.collect_linkedin_jobs(company_name),       # Apify
            self.collect_linkedin_employees(company_name),  # Apify
            self.collect_careers_page(domain),              # HTTP scrape
            self.collect_glassdoor(company_name),           # Apify or HTTP
            self.collect_indeed(company_name),              # Apify
            return_exceptions=True,  # Don't fail all if one source fails
        )

        return RawHiringData(
            linkedin_jobs=results[0] if not isinstance(results[0], Exception) else [],
            linkedin_employees=results[1] if not isinstance(results[1], Exception) else [],
            careers_page_roles=results[2] if not isinstance(results[2], Exception) else [],
            glassdoor_data=results[3] if not isinstance(results[3], Exception) else None,
            indeed_roles=results[4] if not isinstance(results[4], Exception) else [],
            errors=[str(r) for r in results if isinstance(r, Exception)],
        )

    async def collect_linkedin_jobs(self, company_name: str) -> list[dict]:
        """Apify: curious_coder/linkedin-jobs-scraper"""
        # 3 searches: digital/search roles, engineering roles, executive roles
        queries = [
            f"{company_name} search OR discovery OR personalization",
            f"{company_name} software engineer OR platform OR architecture",
            f"{company_name} VP OR director OR head digital OR commerce",
        ]
        all_jobs = []
        for query in queries:
            jobs = await self.apify.run_actor(
                "curious_coder/linkedin-jobs-scraper",
                input={"searchQueries": [query], "maxResults": 25},
                timeout=120,
            )
            all_jobs.extend(jobs)
        return deduplicate_by_url(all_jobs)

    async def collect_linkedin_employees(self, company_name: str) -> list[dict]:
        """Apify: company employee directory scraper"""
        return await self.apify.run_actor(
            "anchor/linkedin-company-employees",
            input={"company": company_name, "maxResults": 100},
            timeout=180,
        )

    async def collect_careers_page(self, domain: str) -> list[dict]:
        """Direct HTTP: try common careers page URLs"""
        careers_urls = [
            f"https://{domain}/careers",
            f"https://{domain}/jobs",
            f"https://careers.{domain}",
            f"https://jobs.{domain}",
        ]
        for url in careers_urls:
            response = await self.http.get(url, timeout=15)
            if response.status == 200:
                return self.parse_careers_page(response.text, url)
        return []
```

#### 2.1d Enricher Implementation (Claude API for judgment)

```python
class HiringEnricher:
    """Claude API calls for tasks requiring judgment."""

    async def identify_buying_committee(
        self,
        employees: list[dict],
        open_roles: list[OpenRole],
        company_context: dict,          # From intel-company module
    ) -> BuyingCommittee:
        """Use Claude to map people to MEDDPICC buying roles."""

        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system="You are an enterprise sales intelligence analyst...",
            messages=[{
                "role": "user",
                "content": f"""Given this company's employee directory and open roles,
                identify the buying committee for an Algolia deal.

                Company: {company_context['company_name']}
                Vertical: {company_context['vertical']}
                Employee list: {json.dumps(employees[:50])}
                Open roles: {json.dumps([r.model_dump() for r in open_roles[:20]])}

                Respond with JSON matching this schema: {BuyingCommittee.model_json_schema()}
                """
            }],
            # STRUCTURED OUTPUT: Force Claude to return valid JSON
            tools=[{
                "name": "identify_committee",
                "description": "Identify the buying committee",
                "input_schema": BuyingCommittee.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": "identify_committee"},
        )

        # Parse structured output — guaranteed to match schema
        tool_result = response.content[0]  # tool_use block
        return BuyingCommittee.model_validate(tool_result.input)

    async def enrich_key_contacts(
        self,
        committee: BuyingCommittee,
    ) -> list[EnrichedContact]:
        """PhantomBuster: deep profile enrichment for buying committee."""

        key_people = [
            committee.economic_buyer,
            committee.technical_buyer,
            committee.champion,
            *committee.influencers[:3],
        ]

        enriched = []
        for person in key_people:
            if not person or not person.linkedin_url:
                continue

            profile = await self.phantombuster.scrape_profile(person.linkedin_url)
            if not profile:
                continue

            enriched.append(EnrichedContact(
                name=person.name,
                title=person.title,
                linkedin_url=person.linkedin_url,
                tenure_months=self.calculate_tenure(profile.get("experience", [])),
                previous_companies=self.extract_companies(profile.get("experience", [])),
                relevant_skills=self.filter_relevant_skills(profile.get("skills", [])),
                recent_posts=await self.get_recent_posts(person.linkedin_url),
                algolia_connection_score=await self.check_algolia_connections(profile),
                evidence_tier=EvidenceTier.FACT,
                source_url=person.linkedin_url,
            ))

        return enriched
```

#### 2.1e Validator

```python
class HiringValidator:
    async def validate(self, result: ModuleResult) -> ValidationResult:
        checks = [
            ("has_open_roles_or_explanation",
                len(result.output.get("open_roles", [])) > 0
                or "no open roles" in result.output.get("notes", "").lower()),
            ("tier_counts_match_roles",
                sum(result.output.get("role_count_by_tier", {}).values())
                == len(result.output.get("open_roles", []))),
            ("buying_committee_has_at_least_economic_buyer",
                result.output.get("buying_committee", {}).get("economic_buyer") is not None),
            ("hiring_velocity_calculated",
                result.output.get("hiring_velocity") is not None),
            ("build_vs_buy_assessed",
                result.output.get("build_vs_buy_signal", {}).get("signal") is not None),
            ("all_roles_have_source",
                all(r.get("source") for r in result.output.get("open_roles", []))),
            ("all_roles_have_evidence_tier",
                all(r.get("evidence_tier") for r in result.output.get("open_roles", []))),
            ("contacts_have_linkedin_urls",
                all(c.get("linkedin_url") for c in result.output.get("contacts", []))),
        ]

        passed = [name for name, ok in checks if ok]
        failed = [name for name, ok in checks if not ok]

        return ValidationResult(
            passed=len(failed) == 0,
            checks_run=len(checks),
            checks_passed=len(passed),
            errors=failed,
        )
```

---

### 2.2 MODULE: intel-techstack (Technology Intelligence)

**Current → Target Enhancement:**

| Capability | Current | Target |
|---|---|---|
| BuiltWith detection | ✓ Full API | ✓ Same |
| SimilarWeb tech cross-check | ✓ | ✓ Same |
| Wappalyzer (3rd source) | ✗ | ✓ NEW — client-side tech detection |
| Network-level search vendor verification | ✗ | ✓ NEW — HTTP request to search endpoint, check response headers |
| Technology change timeline | ✗ | ✓ NEW — BuiltWith historical: when was search vendor added/removed |
| Frontend framework detection | ✗ | ✓ NEW — React/Vue/Next/Nuxt affects Algolia integration story |
| Search endpoint discovery | ✗ | ✓ NEW — find the actual search API URL for browser audit |
| Competitor tech comparison | ✗ | ✓ NEW — same BuiltWith calls for top 3 competitors |

---

### 2.3 MODULE: intel-competitors (Competitive Intelligence)

**Data sources:** Perplexity (competitive positioning, market analysis, G2/TrustRadius reviews), SimilarWeb (from intel-traffic), BuiltWith (from intel-techstack). Reads competitor seed list from intel-company output.

**Current → Target Enhancement:**

| Capability | Current | Target |
|---|---|---|
| SimilarWeb similar sites | ✓ | ✓ Same |
| BuiltWith per competitor | ✓ | ✓ Same |
| Golden Angle (competitors using Algolia) | ✓ | ✓ Enhanced — deeper case study matching |
| Algolia customer portfolio scan | ✓ | ✓ Same |
| G2/TrustRadius review scraping | ✗ | ✓ NEW — competitor product complaints |
| Competitor search quality testing | ✗ | ✓ NEW — automated search test on competitor sites |
| Competitor hiring comparison | ✗ | ✓ NEW — are competitors also hiring search engineers? |
| Win/loss intelligence | ✗ | ✓ NEW — Crossbeam + internal data on deals won/lost vs each competitor |
| Case study matching by finding type | ✗ | ✓ NEW — NLP gap → NLP case study (programmatic, not LLM judgment) |

---

### 2.4 MODULE: intel-traffic (Traffic & Engagement Intelligence)

**Current → Target Enhancement:**

| Capability | Current | Target |
|---|---|---|
| SimilarWeb 11 endpoints | ✓ | ✓ Same |
| Google Trends momentum | ✗ | ✓ NEW — YoY traffic trend direction |
| SEO keyword gap analysis | ✗ | ✓ NEW — keywords where competitors rank higher |
| Mobile app traffic | ✗ | ✓ NEW — in-app search as separate opportunity |
| Search-to-purchase funnel | ✗ | ✓ NEW — estimate search's role in conversion path |
| Seasonal traffic patterns | ✗ | ✓ NEW — identify peak periods for timing the pitch |
| Content vs. commerce traffic split | ✗ | ✓ NEW — how much traffic goes to content vs. product pages |

---

### 2.5 MODULE: intel-company (Company Intelligence) — THE FOUNDATION HUB

**This module runs FIRST in every audit. All other modules depend on its output.** It is the HUB in the hub-and-spoke architecture. It establishes the canonical company profile in the `accounts` table, and every spoke module reads from that table.

**Data sources:**
- Perplexity API `sonar` — ONE composite call returning JSON with inline citations (primary, $0.25/M input). `sonar-pro` available as configurable upgrade for higher-quality research. Model is a config setting (`PERPLEXITY_MODEL`), not hardcoded.
- Company website HTTP fetch — search bar detection via regex (verification)

**What it produces (written to `accounts` table as proper columns):**
- Company legal name, common name, HQ, employees, year founded, business model, motto
- Industry classification and sub-vertical
- Public/private status, ticker, parent company, revenue estimate with source
- Executive team (8-12 people): name, title, LinkedIn URL, tenure, previous company
- Top 5-7 competitors: name, domain, why they compete, relative size
- Recent news and blog posts (last 90 days)
- Website snapshot: search bar present, product categories
- **Field-level source citations** for every data point (parsed from Perplexity inline citations)

#### `accounts` Table Schema (denormalized — no JSONB blobs)

```sql
CREATE TABLE accounts (
    -- Primary key
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity (populated by intel-company)
    legal_name                  TEXT,
    company_name                TEXT NOT NULL,       -- common/brand name
    domain                      TEXT UNIQUE NOT NULL, -- canonical domain
    headquarters                TEXT,
    employee_count              INTEGER,
    employee_count_source       TEXT,
    year_founded                INTEGER,
    business_model              TEXT,                -- min 50 chars, 3+ sentences
    motto                       TEXT,

    -- Classification
    industry                    TEXT,
    sub_vertical                TEXT,
    is_public                   BOOLEAN DEFAULT FALSE,
    ticker                      TEXT,
    parent_company              TEXT,
    revenue_estimate            NUMERIC(15,2),       -- USD, e.g. 1600000000.00
    revenue_source              TEXT,

    -- Website snapshot
    has_search_bar              BOOLEAN,
    product_categories          JSONB DEFAULT '[]',  -- array of strings

    -- Nested entities (JSONB arrays — variable-length, always read as a unit)
    executives                  JSONB DEFAULT '[]',  -- array of Executive objects
    competitors                 JSONB DEFAULT '[]',  -- array of Competitor objects
    recent_news                 JSONB DEFAULT '[]',  -- array of NewsItem objects
    recent_blog_posts           JSONB DEFAULT '[]',  -- array of BlogPost objects

    -- Field-level source citations (parsed from Perplexity inline citations)
    sources                     JSONB DEFAULT '[]',  -- array of {field, source_url, source_label}

    -- Metadata
    created_at                  TIMESTAMPTZ DEFAULT now(),
    updated_at                  TIMESTAMPTZ DEFAULT now()
);
```

Each entry in the `sources` JSONB array:
```json
{
    "field": "employee_count",
    "source_url": "https://www.cbinsights.com/company/jewson",
    "source_label": "cbinsights"
}
```

#### Pydantic Output Schema

```python
class CompanyProfileOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Perplexity may add extra fields like _notes

    # Identity
    legal_name: str
    common_name: str
    domain: str
    headquarters: str
    employee_count: int | None = None
    employee_count_source: str | None = None
    year_founded: int | None = None
    business_model: str
    motto: str | None = None

    # Classification
    industry: str
    sub_vertical: str | None = None
    is_public: bool = False
    ticker: str | None = None
    parent_company: str | None = None
    revenue_estimate: float | None = None
    revenue_source: str | None = None

    # People, competitors, activity
    executives: list[Executive]
    competitors: list[Competitor]
    recent_news: list[NewsItem]
    recent_blog_posts: list[BlogPost]

    # Website snapshot
    has_search_bar: bool | None = None
    product_categories: list[str] = Field(default_factory=list)


class Executive(BaseModel):
    model_config = ConfigDict(extra="ignore")
    full_name: str
    title: str
    linkedin_url: str | None = None
    tenure_description: str | None = None
    previous_company: str | None = None
    previous_role: str | None = None


class Competitor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_name: str
    domain: str
    why_competitor: str
    relative_size: Literal["larger", "smaller", "similar", "unknown"] = "unknown"


class NewsItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    headline: str
    source: str
    date: str
    url: str | None = None
    category: str = "other"
```

#### Data Flow (3 steps, no LLM parsing)

```
Step 1: Collector
    ONE Perplexity sonar-pro call (composite prompt, JSON response requested)
    + ONE HTTP GET to homepage (search bar regex detection)

Step 2: Parser (deterministic — NO LLM)
    a. Extract inline citations [label](url) from raw response → Source[] array
    b. Strip citations from JSON string values
    c. json.loads() → dict
    d. CompanyProfileOutput.model_validate(dict) → typed, validated object
    e. _detect_search_bar(html) → bool (regex, not LLM)
    f. Cross-check competitors against known Algolia customer list

Step 3: Persist to accounts table
    Write every field to its proper column on the accounts table.
    Write Source[] array to accounts.sources JSONB column.
    Also persist full ModuleResult to module_executions (for audit history).
```

#### Perplexity Prompt (single composite call)

The collector sends ONE prompt to Perplexity (default: `sonar` at $0.25/M input tokens, configurable to `sonar-pro` via `PERPLEXITY_MODEL` env var) requesting JSON output:

```
Research the company that owns the website {domain}. Find comprehensive
information covering company identity, business model, financials, industry
classification, executive team, competitors, and recent activity.

For executives, prioritize: CEO, CTO, CFO, VP Engineering, VP Product, CMO,
VP/Head of E-commerce or Digital, VP/Head of Search, VP Data/Analytics, CIO, CDO.
Only include real LinkedIn URLs — do not guess.

For competitors, focus on companies that sell similar products/services to
similar customers and compete for the same market share.

For recent activity, cover the last 90 days only.

Be specific. Use exact numbers not ranges. Revenue as a raw number in USD.
Dates in YYYY-MM-DD format.

Return your response as valid JSON matching this EXACT structure:
{json_schema}
```

Where `{json_schema}` is the JSON representation of CompanyProfileOutput.

#### Citation Parsing (deterministic code)

Perplexity returns inline citations as `[label](url)` after string values. The parser:

```python
import json
import re

CITATION_PATTERN = re.compile(r'\s*\[([\w.\-]+)\]\((https?://[^\)]+)\)')

def parse_perplexity_response(raw_text: str) -> tuple[CompanyProfileOutput, list[Source]]:
    """Parse Perplexity JSON response into validated output + field-level sources."""
    sources: list[Source] = []

    # Extract all citations before stripping
    for match in CITATION_PATTERN.finditer(raw_text):
        label, url = match.group(1), match.group(2)
        # Associate with nearest JSON key (field-level attribution)
        sources.append(Source(field="", source_url=url, source_label=label, ...))

    # Strip citations from string values so JSON parses cleanly
    cleaned = CITATION_PATTERN.sub('', raw_text)

    data = json.loads(cleaned)
    profile = CompanyProfileOutput.model_validate(data)

    return profile, sources
```

No LLM. No Instructor. No Gemini. Deterministic.

#### Validation Checks (8 minimum)

1. company_name not empty
2. domain matches input
3. headquarters not empty
4. at least 3 executives found
5. at least 3 competitors found
6. at least 1 executive has linkedin_url
7. business_model at least 50 characters
8. at least 1 news item (warning if missing, not error)

#### Database Storage

Output writes to the `accounts` table — **proper columns, not JSONB blob.** Each field from `CompanyProfileOutput` maps to its own column. The `sources` JSONB array stores field-level citations parsed from Perplexity's inline annotations.

Full `ModuleResult` (including raw output, timing, cost) also persists to `module_executions` for audit history and provenance tracking.

**There is NO `accounts.intelligence` JSONB column.** That pattern is eliminated. All data lives in proper columns.

#### How Spoke Modules Read Hub Data

Every spoke module queries the `accounts` table by `company_name` or `domain` to get the fields it needs. One pattern, everywhere, no exceptions.

| Spoke Module | Reads from `accounts` | Purpose |
|---|---|---|
| intel-techstack | competitors[].domain | Run BuiltWith on competitors too |
| intel-traffic | competitors[].domain | Compare traffic vs competitors |
| intel-financial-public | ticker, is_public | Whether to hit Yahoo Finance/SEC |
| intel-hiring | executives[], domain | Verify buying committee, search open roles |
| intel-investor | ticker, executives[] | Search earnings calls for exec quotes |
| intel-social | executives[].linkedin_url | Fetch executive LinkedIn posts |
| intel-news | company_name, competitors[] | Deep news search with competitor context |
| intel-competitors | ALL fields | Full competitive synthesis from all data |
| intel-queries | industry, product_categories, competitors[] | Generate calibrated test queries |
| synth-business-case | revenue_estimate, business_model, industry | Build ROI model with correct framing |
| synth-sales-plays | executives[], competitors[] | Map MEDDPICC to real people |
| campaign-abx | executives[], business_model | Personalize outreach to specific people |

---

### 2.6 MODULE: intel-financial-public (Financial Intelligence — Public)

**Current → Target Enhancement:**

| Capability | Current | Target |
|---|---|---|
| Yahoo Finance MCP | ✓ | ✓ Same |
| SEC EDGAR 10-K (LLM reads) | ✓ | ✓ REPLACE with XBRL parser (deterministic) |
| Earnings call transcripts | ✓ | ✓ Enhanced — last 4 quarters, not 3 |
| Digital revenue extraction (10-K) | ✓ Manual | ✓ Automated XBRL parsing |
| Peer financial comparison | ✗ | ✓ NEW — same Yahoo Finance calls for 3 peers |
| Digital revenue as % of total (3-year trend) | ✗ | ✓ NEW — derive from XBRL data |
| Analyst consensus on digital investment | ✗ | ✓ NEW — Yahoo Finance recommendations + target prices |
| Earnings call keyword analysis | ✗ | ✓ NEW — frequency of "search", "digital", "personalization" in transcripts over time |

---

### 2.7 MODULE: intel-investor (Investor & Executive Intelligence)

**Data sources:** SEC EDGAR (raw earnings transcripts, 10-K filings — official documents), Yahoo Finance (structured data), Perplexity (investor sentiment, analyst coverage, board composition, executive media quotes)

**Current → Target Enhancement:**

| Capability | Current | Target |
|---|---|---|
| Earnings call quotes | ✓ | ✓ Enhanced — structured extraction |
| SEC 10-K risk factors | ✓ | ✓ Automated XBRL |
| Yahoo Finance news | ✓ | ✓ Same |
| Executive media quotes (Perplexity) | ✓ | ✓ Enhanced — Perplexity replaces Tavily as primary |
| Podcast/conference talk scraping | ✗ | ✓ NEW — YouTube transcripts, podcast appearances |
| Quote-to-product mapping | ✗ | ✓ NEW — which Algolia product does each quote support? |
| Sentiment trajectory | ✗ | ✓ NEW — is executive tone on digital becoming more urgent over quarters? |
| Board composition analysis | ✗ | ✓ NEW — do any board members have tech/digital backgrounds? |

---

### 2.8 MODULE: audit-browser (Search Experience Audit)

**Current → Target Enhancement:**

| Capability | Current | Target |
|---|---|---|
| Per-company Playwright scripts | ✓ (unreliable) | ✗ REPLACE with visual agent |
| WAF bypass (stealth mode) | ✓ (inconsistent) | ✓ Enhanced — multi-strategy |
| Screenshot evidence | ✓ | ✓ Same |
| 20-step test protocol | In SKILL.md | ✓ As config (JSON state machine) |
| Competitor search comparison | ✗ | ✓ NEW — same 20 tests on top 2 competitors |
| Network-level analysis | ✗ | ✓ NEW — intercept API calls, measure latency |
| Mobile viewport testing | ✗ | ✓ NEW — same tests in 375px viewport |
| Accessibility scoring | ✗ | ✓ NEW — WCAG compliance of search UI |
| Video recording | ✗ | ✓ NEW — Playwright video capture for Loom-style playback |

---

### 2.9 MODULE: synth-business-case (ROI Model)

**Current → Target Enhancement:**

| Capability | Current | Target |
|---|---|---|
| 6-component ROI model | ✓ | ✓ Same |
| Show-all-math rule | ✓ | ✓ Same |
| Conservative/Moderate scenarios | ✓ | ✓ Enhanced — add Aggressive |
| Dynamic benchmark injection by vertical | ✗ | ✓ NEW — benchmark DB keyed by vertical + company size |
| Sensitivity analysis | ✗ | ✓ NEW — "if digital revenue share is X%, opportunity is Y" |
| Competitor displacement cost model | ✗ | ✓ NEW — cost of staying with Coveo vs. switching to Algolia |
| Time-to-value projection | ✗ | ✓ NEW — implementation timeline → when ROI starts |
| Case study ROI evidence | ✗ | ✓ NEW — pull exact ROI numbers from matching Algolia case studies |

---

### 2.10 MODULE: audit-factcheck (Quality Gate)

**Current → Target Enhancement:**

| Capability | Current | Target |
|---|---|---|
| 20-dimension verification | ✓ | ✓ Same methodology |
| Multi-agent parallel verification | ✓ (unreliable in Claude Code) | ✓ As Temporal child workflows (reliable) |
| Claim registry | ✓ | ✓ Automated (reads from module_executions table) |
| Source URL verification | ✓ | ✓ Same |
| API data re-verification | ✓ | ✓ Same |
| Evidence tiering (Tier 1/2/3) | ✓ | ✓ Same |
| FACTCHECK_GATE | ✓ | ✓ Same |
| Correction manifest | ✓ | ✓ Enhanced — auto-applies simple fixes |
| Skill feedback loop | ✓ | ✓ As module performance metrics in DB |

**Key architectural change:** The factcheck module is a Temporal **child workflow**,
not a single activity. It spawns its own parallel activities for each verification dimension.
Temporal handles the fan-out/fan-in natively.

```python
@workflow.defn
class FactcheckWorkflow:
    """Child workflow: parallel verification dimensions."""

    @workflow.run
    async def run(self, input: FactcheckInput) -> FactcheckResult:
        # Phase 1: Build claim registry (sequential, deterministic)
        registry = await workflow.execute_activity(
            build_claim_registry,
            input.audit_id,
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Phase 2: Parallel verification (4 activities simultaneously)
        verifications = await asyncio.gather(
            workflow.execute_activity(verify_api_data, registry, ...),
            workflow.execute_activity(verify_source_urls, registry, ...),
            workflow.execute_activity(verify_quotes, registry, ...),
            workflow.execute_activity(verify_browser_findings, registry, ...),
        )

        # Phase 3: Score and generate gate
        gate = await workflow.execute_activity(
            generate_factcheck_gate,
            registry, verifications,
            ...
        )

        return FactcheckResult(gate=gate, verifications=verifications)
```

---

## 3. Revised Project Structure

```
prism_platform/
├── pyproject.toml
├── docker-compose.yml              # PostgreSQL + Redis + Temporal dev server
├── alembic/                         # Database migrations
│   └── versions/
├── prism_platform/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application
│   ├── config.py                    # Settings (env vars, API keys)
│   │
│   ├── core/                        # ═══ LAYER 1: Contracts ═══
│   │   ├── types.py                 # EvidenceTier, Source, ModuleResult, ValidationResult
│   │   ├── module.py                # ModuleInterface (ABC)
│   │   ├── schemas.py               # Shared Pydantic models (Person, Company, etc.)
│   │   └── registry.py              # MODULE_REGISTRY: all modules registered here
│   │
│   ├── orchestrator/                # ═══ LAYER 2: Temporal Workflows ═══
│   │   ├── workflows.py             # AuditWorkflow (main), FactcheckWorkflow (child)
│   │   ├── activities.py            # run_module, save_result, check_gate
│   │   ├── worker.py                # Temporal worker process
│   │   └── dependencies.py          # Wave resolution from module declarations
│   │
│   ├── db/                          # ═══ LAYER 3: Persistence ═══
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── session.py               # Database session management
│   │   └── queries.py               # Common queries
│   │
│   ├── api/                         # ═══ LAYER 4: HTTP Interface ═══
│   │   ├── routers/
│   │   │   ├── audits.py
│   │   │   ├── accounts.py
│   │   │   ├── modules.py
│   │   │   └── admin.py
│   │   ├── middleware.py             # Auth, rate limiting, CORS
│   │   └── dependencies.py          # FastAPI dependency injection
│   │
│   ├── services/                    # ═══ Shared Services ═══
│   │   ├── claude.py                # Anthropic API client (Langfuse-wrapped)
│   │   ├── builtwith.py             # BuiltWith API client
│   │   ├── similarweb.py            # SimilarWeb API client
│   │   ├── yahoo_finance.py         # Yahoo Finance client
│   │   ├── apify.py                 # Apify actor runner
│   │   ├── crossbeam.py             # Crossbeam API client
│   │   ├── phantombuster.py         # PhantomBuster API client
│   │   ├── storage.py               # S3/R2 file storage
│   │   └── cache.py                 # Redis cache
│   │
│   └── modules/                     # ═══ LAYER 5: Intelligence Modules ═══
│       ├── intel_company/
│       │   ├── __init__.py
│       │   ├── module.py             # CompanyModule(ModuleInterface)
│       │   ├── schemas.py            # CompanyInput, CompanyProfileOutput
│       │   ├── collector.py          # ONE Perplexity call (JSON) + homepage fetch
│       │   ├── parser.py             # Deterministic: json.loads + citation extraction + Pydantic
│       │   ├── validator.py          # Output validation (8 checks)
│       │   └── tests/
│       │
│       │   NOTE on enricher.py vs parser.py:
│       │   - parser.py = deterministic parsing (json.loads + Pydantic). Used when the
│       │     data source returns structured output (Perplexity JSON, API responses).
│       │   - enricher.py = LLM-powered synthesis/generation. Used ONLY when the module
│       │     needs to GENERATE new content (narratives, battle cards, campaign copy),
│       │     NOT for parsing or field mapping.
│       │
│       ├── intel_techstack/          # Same structure
│       ├── intel_traffic/
│       ├── intel_competitors/
│       ├── intel_financial_public/
│       ├── intel_financial_private/
│       ├── intel_investor/
│       ├── intel_hiring/
│       ├── intel_social/
│       ├── intel_news/
│       ├── intel_partner/
│       ├── intel_industry/
│       ├── intel_queries/
│       ├── audit_browser/
│       ├── synth_business_case/
│       ├── synth_sales_plays/
│       ├── audit_report/
│       ├── campaign_abx/
│       └── audit_factcheck/
│
├── frontend/                        # React app (Phase 5)
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   ├── components/
│   │   └── api/
│   └── ...
│
└── tests/
    ├── conftest.py                  # Shared fixtures (test DB, mock APIs)
    ├── test_workflows.py            # Temporal workflow tests
    └── test_integration.py          # End-to-end audit test
```

---

## 4. Build Plan (Current State: March 31, 2026)

### Phase 0: Foundation — ✅ COMPLETE
All tasks 0.1-0.11 done. 19/19 tests passing. Docker + Temporal + FastAPI + PostgreSQL + Redis running. intel-techstack module live with database-first caching. Frontend shell with three-panel resizable layout, Clerk auth, AI SDK v6 chat integration, Algolia branding.

### Phase 1: Intelligence Modules (IN PROGRESS)

**Wave execution order — intel-company MUST complete first:**

```
Wave 1: intel-company (ALONE — seeds all other modules)
    │
    ▼
Wave 2 (parallel): intel-techstack (enhanced with competitors)
                    intel-traffic
                    intel-financial-public
                    intel-hiring
                    intel-news
                    intel-social
                    intel-partner
                    intel-industry
    │
    ▼
Wave 3: intel-investor (needs financial data + exec list)
        intel-competitors (synthesizes from Wave 2 outputs)
        intel-queries (needs vertical + competitor data)
    │
    ▼
Wave 4: audit-browser (needs queries + competitors)
    │
    ▼
Wave 5: synth-business-case, synth-sales-plays, audit-report
    │
    ▼
Wave 6: campaign-abx
    │
    ▼
Wave 7: audit-factcheck (verifies everything)
    │
    ▼
Wave 8 (background): insights-engine (cross-audit patterns)
```

### Phase 2: Frontend Intelligence Cards
Each module gets a corresponding card component in the frontend chat. As modules complete, their cards render inline in the conversation with evidence badges, loading skeletons, and thinking/transparency blocks.

### Phase 3: Synthesis & Deliverables
Business case generation, sales playbooks, audit reports, ABX campaigns.

### Phase 4: Browser Audit
Playwright + Claude Vision for live search experience testing.

### Phase 5: Quality Gate
GAN-inspired factcheck with Temporal child workflow.

### Phase 6: Production Hardening
Supabase migration, Temporal Cloud, Clerk production keys, rate limiting, monitoring.

---

## 5. Claude Code Handoff Template

For each phase, give Claude Code:

```
I'm building Prism — an AI-powered Prospect Intelligence Platform.
Motto: "Light goes in. Intelligence comes out."

Technical specification: docs/specs/algolia-pip-spec-v2-temporal.md

Current phase: Phase {N} — {Name}

The stack is:
- FastAPI + Temporal.io + PostgreSQL + Redis
- Python 3.13, uv for packages, ruff for formatting, mypy for types
- Pydantic v2 for all schemas (extra="forbid", strict=True)
- Instructor library for all Claude structured output (max_retries=3)
- Every module implements ModuleInterface from prism_platform/core/module.py
- Temporal workflows in prism_platform/orchestrator/workflows.py
- Temporal activities in prism_platform/orchestrator/activities.py
- Database-first caching: check module_executions before any API call
- Perplexity is the primary intelligence engine for ALL web research
- Specialized APIs (BuiltWith, SimilarWeb, Yahoo Finance, SEC EDGAR, Apify) only where structured data is genuinely better

Tasks for this phase:
{paste task list}

Definition of done:
{paste definition of done}

RULES:
1. Show me the file structure before writing any code
2. Write schemas.py BEFORE implementation code
3. Every function has type annotations and try/catch with structlog
4. Every module has a validate() method with minimum 8 checks
5. Write tests alongside implementation — all tests use real API calls, never mock
6. Verify each task works before moving to the next
7. If something fails, fix it — don't skip it and claim it's done
8. Source ALL frontend components from 21st.dev — never base shadcn
9. Use agent teams mode for independent tasks
10. Write progress to docs/decisions/session-log-{date}.md after every task
```
