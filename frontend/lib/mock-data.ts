/**
 * mock-data.ts — dev-only mock intel for UI development.
 * Two contrasting companies: Nike (public, no parent, sub-brands)
 * and Oriental Trading (private, parent = Berkshire Hathaway, subsidiary brands).
 */

import type { ModuleResult } from "./types";
import type { Account } from "@/components/accounts/account-item";

// ── Nike ────────────────────────────────────────────────────────────────────

export const NIKE_ACCOUNT: Account = {
  id: "mock-nike",
  company_name: "Nike",
  domain: "nike.com",
  status: "complete",
  last_audit: "2026-04-14",
  score: 4.2,
};

export const NIKE_INTEL: ModuleResult = {
  module_name: "intel-company",
  module_version: "2.0",
  status: "success",
  duration_ms: 4200,
  errors: [],
  warnings: [],
  sources: [
    {
      field: "revenue_estimate",
      value: "51200000000",
      tier: "VERIFIED",
      source_url: "https://investors.nike.com/investors/financial-information/annual-reports/default.aspx",
      source_label: "Nike FY2024 Annual Report",
      method: "webfetch",
      retrieved_at: "2026-04-14T10:00:00Z",
      confidence: "high",
    },
  ],
  output: {
    legal_name: "NIKE, Inc.",
    common_name: "Nike",
    domain: "nike.com",
    headquarters: "Beaverton, Oregon, USA",
    employee_count: 79000,
    employee_count_source: "LinkedIn",
    year_founded: 1964,
    business_model:
      "Nike designs, develops, markets, and sells athletic footwear, apparel, equipment, and accessories across sports and fitness. Revenue streams: wholesale to department/specialty retailers (~55%), Direct-to-Consumer via nike.com and 1,000+ branded stores (~45%), and digital memberships (Nike+, SNKRS). Manufacturing fully outsourced to contract factories in Vietnam, China, Indonesia.",
    industry: "Consumer Goods — Athletic Apparel & Footwear",
    sub_vertical: "Sports Retail / DTC",
    is_public: true,
    ticker: "NKE",
    parent_company: null,
    parent_domain: null,
    revenue_estimate: 51200000000,
    revenue_source: "SEC 10-K FY2024",
    subsidiaries: [
      { name: "Jordan Brand", domain: "jordan.com", description: "Premium basketball footwear and apparel sub-brand targeting streetwear and performance segments." },
      { name: "Converse", domain: "converse.com", description: "Iconic casual sneaker brand acquired in 2003, anchoring the lifestyle/heritage segment." },
    ],
    executives: [
      { full_name: "Elliott Hill", title: "President & CEO", role_classification: "economic_buyer", linkedin_url: "https://www.linkedin.com/in/elliotthill/", tenure_description: "Since October 2024", previous_company: "Nike (retired 2020, re-hired 2024)" },
      { full_name: "Matthew Friend", title: "Executive VP & CFO", role_classification: "economic_buyer", linkedin_url: null, tenure_description: "Since 2020", previous_company: null },
      { full_name: "Heidi O'Neill", title: "President, Consumer, Product & Brand", role_classification: "champion", linkedin_url: null, tenure_description: "Since 2023", previous_company: null },
      { full_name: "Craig Williams", title: "President, Geographies & Marketplace", role_classification: "economic_buyer", linkedin_url: null, tenure_description: "Since 2021", previous_company: "Jordan Brand" },
      { full_name: "Kirsten Gracia", title: "VP, Digital Commerce & Platforms", role_classification: "technical_buyer", linkedin_url: null, tenure_description: "Since 2022", previous_company: null },
      { full_name: "Paul Truss", title: "VP, Product Engineering", role_classification: "technical_buyer", linkedin_url: null, tenure_description: "Since 2021", previous_company: "Shopify" },
    ],
    competitors: [
      { company_name: "Adidas", domain: "adidas.com", why_competitor: "Global #2 athletic apparel brand competing in same footwear, apparel, and DTC categories", ticker: "ADDYY", linkedin_url: "https://www.linkedin.com/company/adidas/", twitter_handle: "adidas", youtube_url: "https://www.youtube.com/@adidas" },
      { company_name: "Under Armour", domain: "underarmour.com", why_competitor: "Performance-focused athletic brand with strong DTC and digital platform investment", ticker: "UA", linkedin_url: "https://www.linkedin.com/company/under-armour/", twitter_handle: "UnderArmour", youtube_url: null },
      { company_name: "Lululemon", domain: "lululemon.com", why_competitor: "Premium athleisure DTC brand with rapidly growing footwear line eroding Nike's lifestyle share", ticker: "LULU", linkedin_url: "https://www.linkedin.com/company/lululemon-athletica/", twitter_handle: "lululemon", youtube_url: null },
      { company_name: "New Balance", domain: "newbalance.com", why_competitor: "Heritage athletic brand gaining significant market share in running and lifestyle categories", ticker: null, linkedin_url: "https://www.linkedin.com/company/new-balance/", twitter_handle: "newbalance", youtube_url: null },
    ],
    product_categories: ["Running", "Basketball", "Training", "Football", "Golf", "Lifestyle", "Jordan", "Kids"],
    company_linkedin_url: "https://www.linkedin.com/company/nike/",
    twitter_handle: "Nike",
    youtube_url: "https://www.youtube.com/@nike",
    recent_headline: "Nike names Elliott Hill as CEO in October 2024, replacing John Donahoe amid declining sales and stock pressure",
  },
};

// ── Oriental Trading ─────────────────────────────────────────────────────────

export const OTC_ACCOUNT: Account = {
  id: "mock-otc",
  company_name: "Oriental Trading",
  domain: "orientaltrading.com",
  status: "complete",
  last_audit: "2026-04-12",
  score: 3.1,
};

export const OTC_INTEL: ModuleResult = {
  module_name: "intel-company",
  module_version: "2.0",
  status: "success",
  duration_ms: 3800,
  errors: [],
  warnings: [],
  sources: [
    {
      field: "parent_company",
      value: "Berkshire Hathaway Inc.",
      tier: "VERIFIED",
      source_url: "https://www.berkshirehathaway.com/subs/sublinks.html",
      source_label: "Berkshire Hathaway Subsidiaries Page",
      method: "webfetch",
      retrieved_at: "2026-04-12T08:00:00Z",
      confidence: "high",
    },
    {
      field: "revenue_estimate",
      value: "850000000",
      tier: "ESTIMATE",
      source_url: null,
      source_label: "LinkedIn headcount × revenue-per-employee model",
      method: "estimation",
      retrieved_at: "2026-04-12T08:00:00Z",
      confidence: "medium",
    },
  ],
  output: {
    legal_name: "Oriental Trading Company, Inc.",
    common_name: "Oriental Trading",
    domain: "orientaltrading.com",
    headquarters: "Omaha, Nebraska, USA",
    employee_count: 2200,
    employee_count_source: "LinkedIn",
    year_founded: 1932,
    business_model:
      "Oriental Trading is a direct-to-consumer and B2B e-commerce retailer specializing in party supplies, crafts, toys, gifts, and seasonal décor. Revenue comes from online orders (orientaltrading.com), catalog direct mail, and wholesale to schools, churches, and event planners. Acquired by Berkshire Hathaway in 2012. Operates multiple brand subsidiaries serving distinct customer segments.",
    industry: "E-commerce Retail — Party Supplies & Gifts",
    sub_vertical: "Seasonal / Event Retail",
    is_public: false,
    ticker: null,
    parent_company: "Berkshire Hathaway Inc.",
    parent_domain: "berkshirehathaway.com",
    revenue_estimate: 850000000,
    revenue_source: "LinkedIn headcount model [ESTIMATE]",
    subsidiaries: [
      { name: "MindWare", domain: "mindware.com", description: "Educational toys and games for K-12 targeting parents and educators." },
      { name: "Fun Express", domain: "funexpress.com", description: "Wholesale party supply distributor serving retailers, schools, and event businesses." },
      { name: "Smile Makers", domain: "smilemakers.com", description: "Dental office and pediatric practice rewards and toys." },
      { name: "Morris Costumes", domain: "morriscostumes.com", description: "Halloween and theatrical costumes wholesale supplier." },
    ],
    executives: [
      { full_name: "Steve Somers", title: "President & CEO", role_classification: "economic_buyer", linkedin_url: null, tenure_description: "Since 2019", previous_company: "Dollar Tree" },
      { full_name: "Jennifer Rhoads", title: "Chief Marketing Officer", role_classification: "champion", linkedin_url: null, tenure_description: "Since 2020", previous_company: null },
      { full_name: "Derek Schmidt", title: "VP, E-commerce & Digital Experience", role_classification: "technical_buyer", linkedin_url: null, tenure_description: "Since 2021", previous_company: "Cabela's" },
      { full_name: "Lisa Hartman", title: "VP, Customer Experience", role_classification: "influencer", linkedin_url: null, tenure_description: "Since 2022", previous_company: null },
      { full_name: "Michael Torres", title: "Director, Search & Merchandising", role_classification: "champion", linkedin_url: null, tenure_description: "Since 2023", previous_company: "Overstock" },
    ],
    competitors: [
      { company_name: "Party City", domain: "partycity.com", why_competitor: "Largest dedicated party supply retailer with strong DTC and physical store presence", ticker: null, linkedin_url: "https://www.linkedin.com/company/party-city/", twitter_handle: "PartyCity", youtube_url: null },
      { company_name: "Shindigz", domain: "shindigz.com", why_competitor: "Online-first party supply competitor targeting similar event-planning customer segment", ticker: null, linkedin_url: null, twitter_handle: "Shindigz", youtube_url: null },
      { company_name: "Current USA / Current Catalog", domain: "currentcatalog.com", why_competitor: "Direct catalog competitor in stationery, gifts, and seasonal décor", ticker: null, linkedin_url: null, twitter_handle: null, youtube_url: null },
      { company_name: "Zazzle", domain: "zazzle.com", why_competitor: "Custom gifts and party supplies marketplace overlapping in personalized product segment", ticker: null, linkedin_url: "https://www.linkedin.com/company/zazzle/", twitter_handle: "zazzle", youtube_url: null },
    ],
    product_categories: ["Party Supplies", "Seasonal Décor", "Crafts & Hobbies", "Toys & Games", "School Supplies", "Costumes", "Religious Supplies", "Gifts & Novelties"],
    company_linkedin_url: "https://www.linkedin.com/company/oriental-trading-company/",
    twitter_handle: "OTCfun",
    youtube_url: null,
    recent_headline: "Oriental Trading expands MindWare educational product line for 2026 back-to-school season amid rising K-12 EdTech demand",
  },
};

// ── Accounts list for left panel ─────────────────────────────────────────────

export const MOCK_ACCOUNTS: Account[] = [NIKE_ACCOUNT, OTC_ACCOUNT];

// ── Module result lookup by domain ──────────────────────────────────────────

export const MOCK_INTEL_BY_DOMAIN: Record<string, ModuleResult> = {
  "nike.com": NIKE_INTEL,
  "orientaltrading.com": OTC_INTEL,
};
