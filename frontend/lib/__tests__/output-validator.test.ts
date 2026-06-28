/**
 * Unit tests for the PRISM output validator.
 * Tests that aRRIe's responses are validated against tool result data.
 */

import { validateResponse, buildDataInventory, wrapToolResult } from "../output-validator";

// ---------------------------------------------------------------------------
// Mock tool results simulating real PRISM data
// ---------------------------------------------------------------------------

const mockCompanyResult = {
  module_name: "intel-company",
  status: "success",
  output: {
    common_name: "Dell Technologies",
    legal_name: "Dell Technologies Inc.",
    domain: "dell.com",
    employee_count: 133000,
    industry: "Technology",
    executives: [
      { full_name: "Michael Dell", title: "CEO" },
      { full_name: "Jeff Clarke", title: "COO" },
      { full_name: "Chuck Whitten", title: "Co-COO" },
    ],
    competitors: [
      { company_name: "HP Inc.", domain: "hp.com" },
      { company_name: "Lenovo", domain: "lenovo.com" },
    ],
    revenue_estimate: 102300000000,
  },
};

const mockTechStackResult = {
  module_name: "intel-techstack",
  status: "success",
  output: {
    search_vendor: { name: "Coveo", status: "ACTIVE" },
    cms: "WordPress",
    all_technologies: new Array(45).fill({ Name: "test" }),
  },
};

const mockInvestorResult = {
  module_name: "intel-investor",
  status: "success",
  output: {
    earnings_quotes: [
      {
        speaker: "Michael Dell",
        quote: "Digital platform investment is our top priority for fiscal year 2027",
        date: "Q3 2026",
      },
    ],
    said_vs_found: [
      { exec_said: "We are investing in digital transformation" },
    ],
    sales_angles: ["Displacement opportunity — Coveo to Algolia"],
  },
};

const mockTrafficResult = {
  module_name: "intel-traffic",
  status: "success",
  output: {
    monthly_visits: 5847000,
    bounce_rate: 42.3,
  },
};

function buildToolResults(): Map<string, unknown> {
  const map = new Map<string, unknown>();
  map.set("intel-company", mockCompanyResult);
  map.set("intel-techstack", mockTechStackResult);
  map.set("intel-investor", mockInvestorResult);
  map.set("intel-traffic", mockTrafficResult);
  return map;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("validateResponse", () => {
  const toolResults = buildToolResults();

  describe("CHECK 1 — Number Verification", () => {
    it("passes when numbers match tool data", () => {
      const response =
        "Dell has approximately 5.8 million monthly visits and 133,000 employees.";
      const result = validateResponse(response, toolResults);
      // 5.8M ≈ 5,847,000 within 15% tolerance, 133000 exact match
      const numberFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_NUMBER"
      );
      expect(numberFlags.length).toBe(0);
    });

    it("flags numbers not in tool data", () => {
      const response = "Dell has 250,000 employees and $500 billion in revenue.";
      const result = validateResponse(response, toolResults);
      const numberFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_NUMBER"
      );
      expect(numberFlags.length).toBeGreaterThan(0);
      expect(numberFlags[0].severity).toBe("warning");
    });
  });

  describe("CHECK 2 — Company Name Verification", () => {
    it("passes when company names are in tool data", () => {
      const response =
        "Dell Technologies is competing against HP Inc. and Lenovo in this space.";
      const result = validateResponse(response, toolResults);
      const companyFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_COMPANY"
      );
      expect(companyFlags.length).toBe(0);
    });

    it("always allows Algolia as domain expertise", () => {
      const response = "Algolia would be a strong replacement for Coveo here.";
      const result = validateResponse(response, toolResults);
      const companyFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_COMPANY"
      );
      expect(companyFlags.length).toBe(0);
    });

    it("flags unknown companies used as competitors (critical)", () => {
      const response =
        "Samsung is a major competitor versus Dell in this market.";
      const result = validateResponse(response, toolResults);
      const companyFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_COMPANY" && f.severity === "critical"
      );
      expect(companyFlags.length).toBeGreaterThan(0);
    });
  });

  describe("CHECK 3 — Executive Name Verification", () => {
    it("passes when executive names are in tool data", () => {
      const response =
        "CEO Michael Dell mentioned digital investment as a priority.";
      const result = validateResponse(response, toolResults);
      const execFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_EXECUTIVE"
      );
      expect(execFlags.length).toBe(0);
    });

    it("flags fabricated executive names (critical)", () => {
      const response =
        "VP Sarah Johnson confirmed the search platform budget increase.";
      const result = validateResponse(response, toolResults);
      const execFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_EXECUTIVE"
      );
      expect(execFlags.length).toBeGreaterThan(0);
      expect(execFlags[0].severity).toBe("critical");
    });
  });

  describe("CHECK 4 — Quote Verification", () => {
    it("passes when quotes match tool data", () => {
      const response =
        'Michael Dell said "Digital platform investment is our top priority for fiscal year 2027" in the Q3 call.';
      const result = validateResponse(response, toolResults);
      const quoteFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_QUOTE"
      );
      expect(quoteFlags.length).toBe(0);
    });

    it("flags fabricated quotes (critical)", () => {
      const response =
        'The CFO stated "We plan to triple our search budget by Q4 2027 and deploy across all regions."';
      const result = validateResponse(response, toolResults);
      const quoteFlags = result.flags.filter(
        (f) => f.type === "UNVERIFIED_QUOTE"
      );
      expect(quoteFlags.length).toBeGreaterThan(0);
      expect(quoteFlags[0].severity).toBe("critical");
    });
  });

  describe("Clean response generation", () => {
    it("strips sentences with critical flags", () => {
      const response =
        "Dell uses Coveo for search. VP Sarah Johnson confirmed the migration timeline. The tech stack shows 45 technologies.";
      const result = validateResponse(response, toolResults);
      expect(result.passed).toBe(false);
      expect(result.cleanResponse).not.toContain("Sarah Johnson");
      expect(result.cleanResponse).toContain("Dell uses Coveo");
      expect(result.cleanResponse).toContain(
        "could not be verified against PRISM data"
      );
    });

    it("passes clean responses through unchanged", () => {
      const response =
        "According to the tech stack analysis, Dell uses Coveo for search. They have approximately 5.8 million monthly visits.";
      const result = validateResponse(response, toolResults);
      expect(result.passed).toBe(true);
      expect(result.cleanResponse).toBe(response);
    });
  });
});

describe("buildDataInventory", () => {
  it("lists modules with and without data", () => {
    const toolResults = new Map<string, unknown>();
    toolResults.set("intel-company", { status: "success" });
    toolResults.set("intel-techstack", { status: "success" });

    const inventory = buildDataInventory(toolResults, "dell.com");
    expect(inventory).toContain("Domain: dell.com");
    expect(inventory).toContain("intel-company");
    expect(inventory).toContain("intel-techstack");
    expect(inventory).toContain("intel-traffic"); // in NOT yet run
  });

  it("handles null domain", () => {
    const inventory = buildDataInventory(new Map(), null);
    expect(inventory).toContain("Domain: not set");
    expect(inventory).toContain("Modules with verified data: none");
  });
});

describe("wrapToolResult", () => {
  it("wraps with boundary markers", () => {
    const wrapped = wrapToolResult("intel-company", "dell.com", '{"test": true}');
    expect(wrapped).toContain("[PRISM VERIFIED DATA — intel-company for dell.com");
    expect(wrapped).toContain('{"test": true}');
    expect(wrapped).toContain("[END PRISM DATA");
  });
});
