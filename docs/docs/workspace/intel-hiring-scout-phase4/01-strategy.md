# Strategy — intel-hiring Scout Phase 4

## 1. Does this fit the product vision?

Yes. PRISM's core value is ground-truth company intelligence for sales reps. Hiring data is one of the strongest buying signals — a company hiring search engineers is making a build-vs-buy decision about search technology, which is exactly what Algolia sells into.

Currently `intel-hiring` runs as a single-track Perplexity call. Perplexity's web search can find job listings, but it has two weaknesses: (1) it aggregates from cached web data, not live career portals; (2) it loses the raw structure of individual job descriptions. Injecting Scout-fetched career page content gives Perplexity the actual ground truth — live, structured job listings from the company's own careers portal.

This fits the research cluster architecture: Track 1 (WebFetch via Scout) + Track 2 (Perplexity) produces higher-confidence hiring signals than Track 2 alone.

## 2. Who is the target segment?

**System consumer**: The `intel-hiring` module. No direct user — the output flows through to the audit UI for sales reps.

**Job to be done (system level)**: "When evaluating a prospect account, determine whether their hiring patterns signal active search investment, build-vs-buy intent, or leadership change — with enough confidence to act on in sales outreach."

The sales rep doesn't interact with this module directly. They read the `hiring_narrative` field in the UI. So the real JTBD is "give a sales rep a 2-sentence hiring signal they can cite in an outreach email."

## 3. What's the trade-off?

**Choosing NOT to build**:
- LinkedIn scraping via Apify — LinkedIn blocks crawlers; Scout would hit the same wall; Perplexity handles LinkedIn via web search
- Full job listing extraction via LLM (`/extract` endpoint) — overkill; markdown injection into Perplexity's context is sufficient
- Tier 2 as a generic Scout proxy for all PRISM modules — Phase 4 is targeted: tier2_stealth.py (benefits BrowserClient consumers) + intel_hiring direct Scout call

**Trade-off**: Adds Playwright cost per intel-hiring run (20-40s latency per career page attempt). Payoff: live career page data vs. Perplexity's cached index. For low-hiring-velocity companies (few/no open roles), the Track 1 fetch adds latency with little gain. Accepted: Track 1 failure is non-fatal; Perplexity still runs as Track 2.

## 4. What's the key metric?

**Primary**: Hiring narrative accuracy — does the `hiring_narrative` cite specific job titles that are actually open at the company today? (Measured by spot-checking 10 accounts against their live career portals.)

**Secondary**: `hiring_signal_score` precision — do high-score companies actually convert to pipeline at a higher rate than low-score companies? (Lagging indicator, tracked over 90 days.)

**Proxy for now**: Career page fetch rate — % of intel-hiring runs where Track 1 returns non-empty content. Target: >60% of real company domains.

## 5. What's the defensibility?

Three layers:
1. **Data freshness**: Scout fetches live career portals, not cached aggregators. This is not replicable with a Perplexity-only call.
2. **MEDDPICC mapping**: The schema maps roles to economic buyer / technical buyer / champion tiers. This is Algolia-specific IP, not a commodity hiring intelligence output.
3. **Pipeline integration**: `intel-hiring` output feeds downstream modules (buying signal inference, audit scoring). Replacing it requires re-integrating the whole pipeline.
