import { tool } from "ai";
import { z } from "zod";
import { prismFetch } from "./prism-api";
import type { ModuleResult, AuditResponse, RunAuditResponse } from "./types";

// ---------------------------------------------------------------------------
// Domain normalizer — mirrors prism_platform/core/domain_normalizer.py
// ---------------------------------------------------------------------------

/**
 * Normalize any domain input to a clean domain string.
 *
 * Strips protocol, www., path, query, fragment, port. Lowercases.
 * If the input has no dots (e.g. a company name), returns it as-is.
 */
function normalizeDomain(input: string): string {
  if (!input) return input;
  let d = input.trim().toLowerCase();
  // Strip protocol
  d = d.replace(/^https?:\/\//, "");
  // Strip www.
  d = d.replace(/^www\./, "");
  // Strip path, query, fragment
  d = d.split("/")[0];
  // Strip port
  d = d.split(":")[0];
  // If no dots, it's probably a company name — return original trimmed input
  if (!d.includes(".")) {
    return input.trim();
  }
  return d;
}

// ---------------------------------------------------------------------------
// Helper: execute a module via the PRISM backend
// ---------------------------------------------------------------------------

async function executeModule(
  moduleName: string,
  rawDomain: string,
  companyName?: string
): Promise<ModuleResult> {
  const domain = normalizeDomain(rawDomain);
  const startMs = Date.now();
  console.info(`[tools] executeModule started`, {
    module: moduleName,
    domain,
    rawDomain: rawDomain !== domain ? rawDomain : undefined,
    companyName: companyName ?? domain,
    timestamp: new Date().toISOString(),
  });

  try {
    const result = await prismFetch<ModuleResult>(
      `/api/v1/modules/${moduleName}/execute/`,
      {
        method: "POST",
        body: JSON.stringify({
          domain,
          company_name: companyName ?? domain,
        }),
      }
    );

    const durationMs = Date.now() - startMs;
    console.info(`[tools] executeModule complete`, {
      module: moduleName,
      domain,
      status: result?.status,
      durationMs,
      outputKeys: result?.output ? Object.keys(result.output).slice(0, 10) : [],
      sourcesCount: result?.sources?.length ?? 0,
      errorsCount: result?.errors?.length ?? 0,
      warningsCount: result?.warnings?.length ?? 0,
    });

    return result;
  } catch (error) {
    const durationMs = Date.now() - startMs;
    console.error(`[tools] executeModule FAILED`, {
      module: moduleName,
      domain,
      durationMs,
      error: error instanceof Error ? error.message : String(error),
      errorType: error instanceof Error ? error.constructor.name : typeof error,
    });
    throw error;
  }
}

// ---------------------------------------------------------------------------
// Quick Intelligence Tools
// ---------------------------------------------------------------------------

export const tools = {
  check_account_freshness: tool({
    description:
      "Check when the last audit was run for an account and which modules have stale data. IMPORTANT: Always call this tool FIRST before running any audit or intelligence module. It checks for existing data and prevents unnecessary reruns.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain to check freshness for"),
    }),
    execute: async ({ domain: rawDomain }) => {
      const domain = normalizeDomain(rawDomain);
      const startMs = Date.now();
      console.info("[tools] check_account_freshness started", { domain });
      try {
        const result = await prismFetch<Record<string, unknown>>(
          `/api/v1/accounts/${encodeURIComponent(domain)}/freshness`
        );
        console.info("[tools] check_account_freshness complete", {
          domain,
          recommendation: result?.recommendation,
          durationMs: Date.now() - startMs,
        });
        return result;
      } catch (error) {
        console.error("[tools] check_account_freshness failed", {
          domain,
          error: error instanceof Error ? error.message : String(error),
        });
        // Return a "no data" result instead of throwing
        return {
          domain,
          last_full_audit: null,
          days_since_audit: null,
          modules: [],
          stale_modules: [],
          fresh_modules: [],
          recommendation: "no_data",
        };
      }
    },
  }),

  get_company_profile: tool({
    description:
      "Get comprehensive company intelligence including executives, competitors, business model, org structure, and recent activity for a domain. This is the foundation module — run it first.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain, e.g. 'dell.com'"),
      company_name: z.string().describe("Company name, e.g. 'Dell Technologies'"),
    }),
    execute: async ({ domain, company_name }) =>
      executeModule("intel-company", normalizeDomain(domain), company_name),
  }),

  get_tech_stack: tool({
    description:
      "Get technology stack detection for a domain using BuiltWith. Returns search vendor, ecommerce platform, CMS, CDN, analytics tools, and Golden Angle detection (competitor using Algolia).",
    inputSchema: z.object({
      domain: z.string().describe("Website domain to analyze"),
    }),
    execute: async ({ domain }) => executeModule("intel-techstack", domain),
  }),

  get_traffic_analysis: tool({
    description:
      "Get traffic analytics from SimilarWeb: monthly visits, traffic sources, top countries, device split, keywords, referrals, Google Trends momentum, and competitor traffic comparison.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain to analyze"),
    }),
    execute: async ({ domain }) => executeModule("intel-traffic", domain),
  }),

  get_financial_data: tool({
    description:
      "Get public company financials from Yahoo Finance + SEC EDGAR: 3-year revenue trend, margins, market cap, analyst consensus, earnings call highlights, and investor presentation insights.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain of a public company"),
    }),
    execute: async ({ domain }) =>
      executeModule("intel-financial-public", domain),
  }),

  get_private_financials: tool({
    description:
      "Get private company revenue estimates via 6-source waterfall: press releases, industry reports, Crunchbase, employee model, news, competitor comparison. All labeled ESTIMATE tier.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain of a private company"),
    }),
    execute: async ({ domain }) =>
      executeModule("intel-financial-private", domain),
  }),

  get_company_news: tool({
    description:
      "Get 90-day news sweep: company news, executive media quotes, competitor news, urgency signals (leadership changes, funding, tech investments). Includes sell signal classification.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("intel-news", domain),
  }),

  get_hiring_intel: tool({
    description:
      "Get hiring intelligence: open roles by ICP tier (economic buyer to user), build-vs-buy signal, buying committee mapping, champion signals, and competitor hiring comparison.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("intel-hiring", domain),
  }),

  get_social_intel: tool({
    description:
      "Get executive social intelligence: LinkedIn activity for top 5 executives, public statements, conference quotes, topic classification, Algolia relevance scoring, and quotable statements.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("intel-social", domain),
  }),

  get_investor_intel: tool({
    description:
      "Get investor intelligence: earnings call quotes, Said vs Found mapping (exec statements → sales angles), YouTube appearances, board composition, 10-K risk factors. THE key module for deal strategy.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("intel-investor", domain),
  }),

  get_partner_intel: tool({
    description:
      "Get partner ecosystem intelligence: SI relationships, co-sell opportunities, Crossbeam account overlaps, vertical case studies, and partner play recommendation.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("intel-partner", domain),
  }),

  get_industry_benchmarks: tool({
    description:
      "Get industry/vertical benchmarks: conversion rates, AOV, digital revenue share for the prospect's vertical. Includes industry trends, pain points mapped to Algolia capabilities, and case studies.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("intel-industry", domain),
  }),

  get_competitor_matrix: tool({
    description:
      "Get competitive comparison matrix across technology, traffic, financial, hiring, and sentiment dimensions with GOLDEN/OFFENSIVE/DEFENSIVE/DISPLACEMENT scenario classification per competitor.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("intel-competitors", domain),
  }),

  get_test_queries: tool({
    description:
      "Get 16 vertically-calibrated test queries for browser-based search audit. 8 types (exact product, category, NLP, misspelled, zero-result, long-tail, competitor product, ambiguous) with difficulty scoring.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("intel-queries", domain),
  }),

  // ---------------------------------------------------------------------------
  // Audit Tools
  // ---------------------------------------------------------------------------

  run_full_audit: tool({
    description:
      "Run a full Prism intelligence audit. Creates an audit and triggers the Temporal workflow with wave-based execution. Supports modes: 'full' (all 20 modules), 'quick' (3 intel modules, ~10s), 'bulk_triage' (quick + scoring).",
    inputSchema: z.object({
      domain: z.string().describe("Website domain to audit"),
      company_name: z.string().describe("Company name"),
      audit_mode: z
        .enum(["full", "quick", "bulk_triage"])
        .default("full")
        .describe("Audit mode: full (all waves), quick (3 modules), bulk_triage (quick + scoring)"),
    }),
    execute: async ({ domain: rawDomain, company_name, audit_mode }) => {
      const domain = normalizeDomain(rawDomain);
      const startMs = Date.now();
      console.info("[tools] run_full_audit started", {
        domain,
        company_name,
        audit_mode,
        timestamp: new Date().toISOString(),
      });

      try {
        // Step 1: Create the audit
        console.info("[tools] run_full_audit: creating audit", { domain, company_name });
        const audit = await prismFetch<AuditResponse>("/api/v1/audits/", {
          method: "POST",
          body: JSON.stringify({ domain, company_name }),
        });
        console.info("[tools] run_full_audit: audit created", {
          audit_id: audit?.id,
          status: audit?.status,
        });

        // Step 2: Trigger the workflow
        console.info("[tools] run_full_audit: triggering workflow", {
          audit_id: audit?.id,
          audit_mode,
        });
        const run = await prismFetch<RunAuditResponse>(
          `/api/v1/audits/${audit.id}/run`,
          {
            method: "POST",
            body: JSON.stringify({ audit_mode }),
          }
        );
        console.info("[tools] run_full_audit: workflow triggered", {
          audit_id: audit?.id,
          workflow_id: run?.workflow_id,
          run_id: run?.run_id,
          status: run?.status,
          durationMs: Date.now() - startMs,
        });

        return { audit, workflow: run, audit_mode };
      } catch (error) {
        console.error("[tools] run_full_audit FAILED", {
          domain,
          company_name,
          audit_mode,
          durationMs: Date.now() - startMs,
          error: error instanceof Error ? error.message : String(error),
          errorType: error instanceof Error ? error.constructor.name : typeof error,
        });
        throw error;
      }
    },
  }),

  get_audit_status: tool({
    description: "Check the current status of a running or completed audit.",
    inputSchema: z.object({
      audit_id: z.string().describe("The audit UUID"),
    }),
    execute: async ({ audit_id }) =>
      prismFetch<AuditResponse>(`/api/v1/audits/${audit_id}`),
  }),

  get_browser_audit: tool({
    description:
      "Run a live browser-based search experience audit using Playwright. Tests prospect + competitors with 10-dimension scoring via Gemini Vision. Produces screenshots and search quality scores.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain to test"),
    }),
    execute: async ({ domain }) => executeModule("audit-browser", domain),
  }),

  get_factcheck_verdict: tool({
    description:
      "Run the GAN-inspired factcheck quality gate. Verifies all claims across 8 categories and produces a PROCEED/WARN/BLOCKED verdict with correction manifest.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("audit-factcheck", domain),
  }),

  // ---------------------------------------------------------------------------
  // Synthesis Tools
  // ---------------------------------------------------------------------------

  get_business_case: tool({
    description:
      "Generate the business case: Said vs Found 4-column matrix (exec quotes → sales angles), 6-lever ROI calculator, displacement cost model, customer proof matching, and timing signals.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) =>
      executeModule("synth-business-case", domain),
  }),

  get_sales_plays: tool({
    description:
      "Generate sales plays: MEDDPICC mapping, SPIN discovery questions, objection handlers with data-backed counters, executive-language talk tracks, and power map.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) =>
      executeModule("synth-sales-plays", domain),
  }),

  get_audit_report: tool({
    description:
      "Generate the full audit report: 10-dimension search quality score, competitor benchmarks, 60-second pre-call brief, prospect-safe leave-behind, and full audit JSON.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("audit-report", domain),
  }),

  get_abx_campaign: tool({
    description:
      "Generate the ABX campaign package: 5-email sequence, LinkedIn messages per buying committee member, Loom video script, collateral schedule, and competitor-specific messaging.",
    inputSchema: z.object({
      domain: z.string().describe("Website domain"),
    }),
    execute: async ({ domain }) => executeModule("campaign-abx", domain),
  }),

  // ---------------------------------------------------------------------------
  // Customer Evidence
  // ---------------------------------------------------------------------------

  find_customer_evidence: tool({
    description:
      "Find Algolia customer evidence that matches a prospect — case studies from the same vertical, customer quotes, proof points, and whether any of the prospect's competitors are Algolia customers. Use this after running intel-company to find relevant proof points for the business case.",
    inputSchema: z.object({
      domain: z.string().describe("Prospect website domain to match evidence against"),
    }),
    execute: async ({ domain: rawDomain }) => {
      const domain = normalizeDomain(rawDomain);
      const startMs = Date.now();
      console.info("[tools] find_customer_evidence started", { domain });
      try {
        const result = await prismFetch<Record<string, unknown>>(
          `/api/v1/evidence/match?domain=${encodeURIComponent(domain)}`
        );
        console.info("[tools] find_customer_evidence complete", {
          domain,
          matchedCustomers: (result?.matched_customers as unknown[])?.length ?? 0,
          matchedCaseStudies: (result?.matched_case_studies as unknown[])?.length ?? 0,
          competitorIsCustomer: result?.competitor_is_customer,
          durationMs: Date.now() - startMs,
        });
        return result;
      } catch (error) {
        console.error("[tools] find_customer_evidence failed", {
          domain,
          error: error instanceof Error ? error.message : String(error),
        });
        return { domain, error: "No evidence data available yet" };
      }
    },
  }),

  find_case_studies: tool({
    description:
      "Search for Algolia case studies by industry or customer name. Returns case study URLs, features used, key results, and competitor takeout information.",
    inputSchema: z.object({
      industry: z.string().optional().describe("Industry to filter case studies"),
      customer: z.string().optional().describe("Customer name to search for"),
    }),
    execute: async ({ industry, customer }) => {
      const startMs = Date.now();
      console.info("[tools] find_case_studies started", { industry, customer });
      try {
        const params = new URLSearchParams();
        if (industry) params.set("industry", industry);
        if (customer) params.set("customer", customer);
        const result = await prismFetch<Record<string, unknown>[]>(
          `/api/v1/evidence/case-studies?${params.toString()}`
        );
        console.info("[tools] find_case_studies complete", {
          count: result?.length ?? 0,
          durationMs: Date.now() - startMs,
        });
        return result;
      } catch (error) {
        console.error("[tools] find_case_studies failed", {
          error: error instanceof Error ? error.message : String(error),
        });
        return [];
      }
    },
  }),

  find_customer_quotes: tool({
    description:
      "Find customer quotes about Algolia from a specific industry. Use these as proof points in business cases and email sequences.",
    inputSchema: z.object({
      industry: z.string().optional().describe("Industry to filter quotes"),
      feature: z.string().optional().describe("Algolia feature to search quotes for"),
    }),
    execute: async ({ industry, feature }) => {
      const startMs = Date.now();
      console.info("[tools] find_customer_quotes started", { industry, feature });
      try {
        const params = new URLSearchParams();
        if (industry) params.set("industry", industry);
        if (feature) params.set("feature", feature);
        const result = await prismFetch<Record<string, unknown>[]>(
          `/api/v1/evidence/quotes?${params.toString()}`
        );
        console.info("[tools] find_customer_quotes complete", {
          count: result?.length ?? 0,
          durationMs: Date.now() - startMs,
        });
        return result;
      } catch (error) {
        console.error("[tools] find_customer_quotes failed", {
          error: error instanceof Error ? error.message : String(error),
        });
        return [];
      }
    },
  }),

  find_partner_customers: tool({
    description:
      "Find Algolia customers that use a specific technology partner (e.g. Adobe, Salesforce, Shopify). Use when the prospect's tech stack reveals a platform — cross-reference for co-sell angles. Also supports filtering by feature (e.g. 'Neural Search', 'Personalization') and ARR tier (e.g. 'Enterprise 100k+').",
    inputSchema: z.object({
      partner: z.string().optional().describe("Partner/platform name (e.g. 'Adobe', 'Salesforce')"),
      industry: z.string().optional().describe("Industry vertical to filter"),
      feature: z.string().optional().describe("Algolia feature (e.g. 'Neural Search', 'AI Browse')"),
      arr_tier: z.string().optional().describe("ARR tier (e.g. 'Enterprise 100k+', 'Mid-Market')"),
    }),
    execute: async ({ partner, industry, feature, arr_tier }) => {
      const startMs = Date.now();
      console.info("[tools] find_partner_customers started", { partner, industry, feature, arr_tier });
      try {
        const params = new URLSearchParams();
        if (partner) params.set("partner", partner);
        if (industry) params.set("industry", industry);
        if (feature) params.set("feature", feature);
        if (arr_tier) params.set("arr_tier", arr_tier);
        const result = await prismFetch<Record<string, unknown>[]>(
          `/api/v1/evidence/customers?${params.toString()}`
        );
        console.info("[tools] find_partner_customers complete", {
          count: result?.length ?? 0,
          durationMs: Date.now() - startMs,
        });
        return result;
      } catch (error) {
        console.error("[tools] find_partner_customers failed", {
          error: error instanceof Error ? error.message : String(error),
        });
        return [];
      }
    },
  }),

  // ---------------------------------------------------------------------------
  // Benchmarks
  // ---------------------------------------------------------------------------

  get_vertical_benchmarks: tool({
    description:
      "Get cross-audit vertical benchmarks: average search quality, common search vendors, missing capabilities, tech stack patterns, and hiring trends for a specific industry vertical.",
    inputSchema: z.object({
      vertical: z
        .string()
        .describe("Industry vertical name, e.g. 'Consumer Electronics' or 'Retail'"),
    }),
    execute: async ({ vertical }) =>
      prismFetch<Record<string, unknown>[]>(
        `/api/v1/benchmarks/${encodeURIComponent(vertical)}`
      ),
  }),
};

/** All tool names for type safety */
export type ToolName = keyof typeof tools;

/** Tool names grouped by category for UI */
export const TOOL_GROUPS = {
  "Account Health": ["check_account_freshness"],
  "Company Intelligence": [
    "get_company_profile",
    "get_tech_stack",
    "get_traffic_analysis",
    "get_financial_data",
    "get_private_financials",
    "get_company_news",
  ],
  "People Intelligence": [
    "get_hiring_intel",
    "get_social_intel",
    "get_investor_intel",
  ],
  "Market Intelligence": [
    "get_competitor_matrix",
    "get_industry_benchmarks",
    "get_partner_intel",
  ],
  "Audit & Analysis": [
    "get_browser_audit",
    "get_test_queries",
    "get_factcheck_verdict",
  ],
  "Sales Enablement": [
    "get_business_case",
    "get_sales_plays",
    "get_audit_report",
    "get_abx_campaign",
  ],
  "Customer Evidence": [
    "find_customer_evidence",
    "find_case_studies",
    "find_customer_quotes",
  ],
  Benchmarks: ["get_vertical_benchmarks"],
} as const;

/** Human-readable display names for tools */
export const TOOL_DISPLAY_NAMES: Record<string, string> = {
  check_account_freshness: "Account Freshness Check",
  get_company_profile: "Company Profile",
  get_tech_stack: "Technology Analysis",
  get_traffic_analysis: "Traffic Analysis",
  get_financial_data: "Public Financials",
  get_private_financials: "Private Financials",
  get_company_news: "Company News",
  get_hiring_intel: "Hiring Intelligence",
  get_social_intel: "Social Intelligence",
  get_investor_intel: "Investor Intelligence",
  get_partner_intel: "Partner Ecosystem",
  get_industry_benchmarks: "Industry Benchmarks",
  get_competitor_matrix: "Competitor Matrix",
  get_test_queries: "Test Queries",
  run_full_audit: "Full Intelligence Audit",
  get_audit_status: "Audit Status Check",
  get_browser_audit: "Browser Audit",
  get_factcheck_verdict: "Factcheck Gate",
  get_business_case: "Business Case",
  get_sales_plays: "Sales Plays",
  get_audit_report: "Audit Report",
  get_abx_campaign: "ABX Campaign",
  get_vertical_benchmarks: "Vertical Benchmarks",
  find_customer_evidence: "Customer Evidence Match",
  find_case_studies: "Case Studies",
  find_customer_quotes: "Customer Quotes",
};
