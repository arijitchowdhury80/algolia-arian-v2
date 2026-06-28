"use client";

/**
 * Demo page — renders CompanyCard with Nike mock data.
 * Shows CURRENT state (v1 card) + DATA NOT SHOWN (v2 fields waiting to be rendered).
 * No auth required. http://localhost:3000/demo
 */

import { CompanyCard } from "@/components/prism/company-card";
import type { ModuleResult } from "@/lib/types";

// ── Mock data shaped like CompanySeedOutput v2 ──────────────────────────────
const NIKE_MOCK: ModuleResult = {
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
    // Identity
    legal_name: "NIKE, Inc.",
    common_name: "Nike",
    domain: "nike.com",
    headquarters: "Beaverton, Oregon, USA",
    employee_count: 79000,
    employee_count_source: "LinkedIn",
    year_founded: 1964,
    business_model:
      "Nike designs, develops, markets, and sells athletic footwear, apparel, equipment, and accessories for a wide range of sports and fitness activities. Revenue streams include wholesale (department stores, specialty retailers), Direct-to-Consumer (nike.com, 1,000+ branded stores), and digital memberships (Nike+, SNKRS). Manufacturing is fully outsourced to contract factories in Asia.",

    // Classification
    industry: "Consumer Goods — Athletic Apparel & Footwear",
    sub_vertical: "Sports Retail / DTC",
    is_public: true,
    ticker: "NKE",
    parent_company: null,
    parent_domain: null,
    revenue_estimate: 51200000000,
    revenue_source: "SEC 10-K FY2024",

    // Subsidiaries
    subsidiaries: [
      { name: "Jordan Brand", domain: "jordan.com", description: "Premium basketball footwear and apparel sub-brand." },
      { name: "Converse", domain: "converse.com", description: "Iconic casual sneaker brand acquired in 2003." },
      { name: "Hurley", domain: null, description: "Surf-inspired apparel brand (sold 2020, still licensed)." },
    ],

    // Executives
    executives: [
      {
        full_name: "Elliott Hill",
        title: "President & CEO",
        role_classification: "economic_buyer",
        linkedin_url: "https://www.linkedin.com/in/elliotthill/",
        tenure_description: "Since October 2024",
        previous_company: "Nike (retired 2020, re-hired 2024)",
      },
      {
        full_name: "Matthew Friend",
        title: "Executive VP & CFO",
        role_classification: "economic_buyer",
        linkedin_url: null,
        tenure_description: "Since 2020",
        previous_company: null,
      },
      {
        full_name: "Heidi O'Neill",
        title: "President, Consumer, Product & Brand",
        role_classification: "champion",
        linkedin_url: null,
        tenure_description: "Since 2023",
        previous_company: null,
      },
      {
        full_name: "Craig Williams",
        title: "President, Geographies & Marketplace",
        role_classification: "economic_buyer",
        linkedin_url: null,
        tenure_description: "Since 2021",
        previous_company: "Jordan Brand",
      },
      {
        full_name: "John Donahoe",
        title: "Former President & CEO",
        role_classification: null,
        linkedin_url: null,
        tenure_description: "Left October 2024",
        previous_company: "ServiceNow",
      },
      {
        full_name: "VP, Digital Commerce",
        title: "VP, Digital Commerce & Platforms",
        role_classification: "technical_buyer",
        linkedin_url: null,
        tenure_description: "Since 2022",
        previous_company: null,
      },
    ],

    // Competitors
    competitors: [
      {
        company_name: "Adidas",
        domain: "adidas.com",
        why_competitor: "Global #2 athletic apparel brand competing in same categories and markets",
        ticker: "ADDYY",
        linkedin_url: "https://www.linkedin.com/company/adidas/",
        twitter_handle: "adidas",
        youtube_url: "https://www.youtube.com/@adidas",
      },
      {
        company_name: "Under Armour",
        domain: "underarmour.com",
        why_competitor: "Performance athletics brand with strong DTC and digital presence",
        ticker: "UA",
        linkedin_url: "https://www.linkedin.com/company/under-armour/",
        twitter_handle: "UnderArmour",
        youtube_url: null,
      },
      {
        company_name: "Lululemon",
        domain: "lululemon.com",
        why_competitor: "Premium athleisure DTC brand with rapidly growing footwear line",
        ticker: "LULU",
        linkedin_url: "https://www.linkedin.com/company/lululemon-athletica/",
        twitter_handle: "lululemon",
        youtube_url: null,
      },
      {
        company_name: "New Balance",
        domain: "newbalance.com",
        why_competitor: "Heritage athletic brand gaining significant market share in running and lifestyle",
        ticker: null,
        linkedin_url: "https://www.linkedin.com/company/new-balance/",
        twitter_handle: "newbalance",
        youtube_url: null,
      },
    ],

    // Website snapshot
    product_categories: ["Running", "Basketball", "Training", "Football", "Golf", "Lifestyle", "Jordan", "Kids"],
    company_linkedin_url: "https://www.linkedin.com/company/nike/",
    twitter_handle: "Nike",
    youtube_url: "https://www.youtube.com/@nike",
    recent_headline: "Nike names Elliott Hill as CEO in October 2024, replacing John Donahoe amid declining sales and stock pressure",
  },
};

// ── V2 fields that are NOT rendered by current CompanyCard ──────────────────
const MISSING_FIELDS = [
  { label: "HQ", value: "Beaverton, Oregon, USA" },
  { label: "Founded", value: "1964" },
  { label: "Employees", value: "79,000 (LinkedIn)" },
  { label: "Ticker", value: "NKE (public)" },
  { label: "Business Model", value: "51-char rich description of how they make money" },
  { label: "Subsidiaries", value: "Jordan, Converse, Hurley (3 brands)" },
  { label: "Executives", value: "6 people with MEDDPICC roles: economic_buyer × 3, technical_buyer × 1, champion × 1" },
  { label: "Competitors", value: "Adidas, Under Armour, Lululemon, New Balance — with social URLs" },
  { label: "Product Categories", value: "Running, Basketball, Training, Football, Golf, Lifestyle, Jordan, Kids" },
  { label: "Social Links", value: "LinkedIn · Twitter · YouTube" },
  { label: "Recent Headline", value: "Elliott Hill named CEO October 2024 amid declining sales" },
];

export default function DemoPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#F8F9FB",
        fontFamily: "var(--font-sora), system-ui, sans-serif",
        padding: "40px",
      }}
    >
      {/* Page header */}
      <div style={{ marginBottom: "32px" }}>
        <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#003DFF", marginBottom: "6px" }}>
          PRISM · DESIGN DEMO
        </div>
        <h1 style={{ fontSize: "28px", fontWeight: 700, color: "#23263B", margin: 0 }}>
          Company Intel UI — Current vs. Target
        </h1>
        <p style={{ fontSize: "14px", color: "#6B7280", marginTop: "6px" }}>
          Nike mock data · intel-company v2 schema
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "32px", maxWidth: "1100px" }}>

        {/* LEFT — Current card */}
        <div>
          <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#6B7280", marginBottom: "12px" }}>
            CURRENT (v1 CompanyCard — 3 data points)
          </div>
          <CompanyCard data={NIKE_MOCK} />
        </div>

        {/* RIGHT — What v2 schema has that we're not showing */}
        <div>
          <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#DC2626", marginBottom: "12px" }}>
            NOT RENDERED (v2 data waiting to be shown)
          </div>
          <div
            style={{
              background: "rgba(255,255,255,0.72)",
              backdropFilter: "blur(20px)",
              border: "1px solid rgba(220,38,38,0.2)",
              borderRadius: "20px",
              padding: "24px 28px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06)",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {MISSING_FIELDS.map((field) => (
                <div key={field.label} style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <div
                    style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: "#6B7280",
                      minWidth: "110px",
                      paddingTop: "1px",
                    }}
                  >
                    {field.label}
                  </div>
                  <div style={{ fontSize: "13px", color: "#23263B", fontWeight: 500, lineHeight: 1.4 }}>
                    {field.value}
                  </div>
                </div>
              ))}
            </div>

            <div
              style={{
                marginTop: "20px",
                paddingTop: "16px",
                borderTop: "1px solid rgba(0,0,0,0.07)",
                fontSize: "12px",
                color: "#DC2626",
                fontWeight: 600,
              }}
            >
              11 fields × 0 rendered = all invisible to AEs
            </div>
          </div>
        </div>
      </div>

      {/* Bottom: full v2 data dump so we can see schema shape */}
      <div style={{ maxWidth: "1100px", marginTop: "40px" }}>
        <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#6B7280", marginBottom: "12px" }}>
          FULL V2 PAYLOAD (what the backend returns)
        </div>
        <pre
          style={{
            background: "#1E1E2E",
            color: "#CDD6F4",
            borderRadius: "16px",
            padding: "24px",
            fontSize: "11px",
            lineHeight: 1.6,
            overflowX: "auto",
            maxHeight: "500px",
            overflowY: "auto",
          }}
        >
          {JSON.stringify(NIKE_MOCK.output, null, 2)}
        </pre>
      </div>
    </div>
  );
}
