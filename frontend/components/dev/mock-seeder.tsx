"use client";

/**
 * MockSeeder — development-only component.
 * When ?demo=1 is in the URL, seeds the Zustand store with Nike mock data
 * so we can see the Research tab / CompanyCard in context without a real DB.
 *
 * Usage: http://localhost:3000/?demo=1
 */

import { useEffect } from "react";
import { usePrismStore } from "@/lib/store";
import type { ModuleResult } from "@/lib/types";

const NIKE_MODULE_RESULT: ModuleResult = {
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
      "Nike designs, develops, markets, and sells athletic footwear, apparel, equipment, and accessories for a wide range of sports and fitness activities. Revenue streams include wholesale (department stores, specialty retailers), Direct-to-Consumer (nike.com, 1,000+ branded stores), and digital memberships (Nike+, SNKRS). Manufacturing is fully outsourced to contract factories in Asia.",
    industry: "Consumer Goods — Athletic Apparel & Footwear",
    sub_vertical: "Sports Retail / DTC",
    is_public: true,
    ticker: "NKE",
    parent_company: null,
    parent_domain: null,
    revenue_estimate: 51200000000,
    revenue_source: "SEC 10-K FY2024",
    subsidiaries: [
      { name: "Jordan Brand", domain: "jordan.com", description: "Premium basketball footwear and apparel sub-brand." },
      { name: "Converse", domain: "converse.com", description: "Iconic casual sneaker brand acquired in 2003." },
      { name: "Hurley", domain: null, description: "Surf-inspired apparel brand (sold 2020, still licensed)." },
    ],
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
        full_name: "Kirsten Gracia",
        title: "VP, Digital Commerce & Platforms",
        role_classification: "technical_buyer",
        linkedin_url: null,
        tenure_description: "Since 2022",
        previous_company: null,
      },
    ],
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
    product_categories: ["Running", "Basketball", "Training", "Football", "Golf", "Lifestyle", "Jordan", "Kids"],
    company_linkedin_url: "https://www.linkedin.com/company/nike/",
    twitter_handle: "Nike",
    youtube_url: "https://www.youtube.com/@nike",
    recent_headline:
      "Nike names Elliott Hill as CEO in October 2024, replacing John Donahoe amid declining sales and stock pressure",
  },
};

export function MockSeeder() {
  const setCurrentDomain = usePrismStore((s) => s.setCurrentDomain);
  const setCurrentCompanyName = usePrismStore((s) => s.setCurrentCompanyName);
  const addResult = usePrismStore((s) => s.addResult);
  const setActiveTab = usePrismStore((s) => s.setActiveTab);

  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    setCurrentDomain("nike.com");
    setCurrentCompanyName("Nike");
    addResult("intel-company", NIKE_MODULE_RESULT);
    setActiveTab("research");
  }, [setCurrentDomain, setCurrentCompanyName, addResult, setActiveTab]);

  return null;
}
