import { create } from "zustand";
import type { ModuleResult, AuditStreamEvent } from "./types";

/** Maps tool names to their module display names for the data explorer */
export const TOOL_TO_MODULE: Record<string, string> = {
  check_account_freshness: "freshness-check",
  get_company_profile: "intel-company",
  get_tech_stack: "intel-techstack",
  get_traffic_analysis: "intel-traffic",
  get_financial_data: "intel-financial-public",
  get_private_financials: "intel-financial-private",
  get_company_news: "intel-news",
  get_hiring_intel: "intel-hiring",
  get_social_intel: "intel-social",
  get_investor_intel: "intel-investor",
  get_partner_intel: "intel-partner",
  get_industry_benchmarks: "intel-industry",
  get_competitor_matrix: "intel-competitors",
  get_test_queries: "intel-queries",
  get_browser_audit: "audit-browser",
  get_factcheck_verdict: "audit-factcheck",
  get_business_case: "synth-business-case",
  get_sales_plays: "synth-sales-plays",
  get_audit_report: "audit-report",
  get_abx_campaign: "campaign-abx",
  get_vertical_benchmarks: "insights-engine",
};

/** Dashboard tab identifiers */
export type DashboardTab =
  | "overview"
  | "research"
  | "search-audit"
  | "business-case"
  | "competitive"
  | "sales-actions";

/** Tab display configuration */
export const DASHBOARD_TABS: { id: DashboardTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "research", label: "Research" },
  { id: "search-audit", label: "Search Audit" },
  { id: "business-case", label: "Business Case" },
  { id: "competitive", label: "Competitive" },
  { id: "sales-actions", label: "Sales Actions" },
];

/** Maps navigate_to targets from aRRIe tool results to tab + section */
export const NAVIGATE_MAP: Record<string, { tab: DashboardTab; section?: string }> = {
  // Overview cross-links
  "research": { tab: "research" },
  "search-audit": { tab: "search-audit" },
  "business-case": { tab: "business-case" },
  "competitive": { tab: "competitive" },
  "sales-actions": { tab: "sales-actions" },
  // Research sections
  "company-snapshot": { tab: "research", section: "company-snapshot" },
  "financial-profile": { tab: "research", section: "financial-profile" },
  "technology-stack": { tab: "research", section: "technology-stack" },
  "traffic-digital": { tab: "research", section: "traffic-digital" },
  "hiring-signals": { tab: "research", section: "hiring-signals" },
  "news-signals": { tab: "research", section: "news-signals" },
  "social-intelligence": { tab: "research", section: "social-intelligence" },
  "investor-intelligence": { tab: "research", section: "investor-intelligence" },
  "partner-intelligence": { tab: "research", section: "partner-intelligence" },
  "industry-benchmarks": { tab: "research", section: "industry-benchmarks" },
  // Search audit sections
  "score-summary": { tab: "search-audit", section: "score-summary" },
  "score-dimensions": { tab: "search-audit", section: "score-dimensions" },
  "findings": { tab: "search-audit", section: "findings" },
  // Business case sections
  "said-vs-found": { tab: "business-case", section: "said-vs-found" },
  "roi-calculator": { tab: "business-case", section: "roi-calculator" },
  "customer-proof": { tab: "business-case", section: "customer-proof" },
  "why-act-now": { tab: "business-case", section: "why-act-now" },
  // Competitive sections
  "comparison-matrix": { tab: "competitive", section: "comparison-matrix" },
  "battle-cards": { tab: "competitive", section: "battle-cards" },
  "golden-angle": { tab: "competitive", section: "golden-angle" },
  // Sales actions sections
  "meddpicc": { tab: "sales-actions", section: "meddpicc" },
  "spin-questions": { tab: "sales-actions", section: "spin-questions" },
  "objection-handling": { tab: "sales-actions", section: "objection-handling" },
  "buying-committee": { tab: "sales-actions", section: "buying-committee" },
  "outreach-sequence": { tab: "sales-actions", section: "outreach-sequence" },
};

interface PrismStore {
  /** Which company domain we're currently looking at */
  currentDomain: string | null;
  setCurrentDomain: (domain: string | null) => void;

  /** Current account company name */
  currentCompanyName: string | null;
  setCurrentCompanyName: (name: string | null) => void;

  /** Callback to send a message to the chat (set by PrismChat) */
  sendChatMessage: ((text: string) => void) | null;
  setSendChatMessage: (fn: (text: string) => void) => void;

  /** Module results as they arrive from tool calls */
  availableResults: Record<string, ModuleResult>;
  addResult: (moduleName: string, result: ModuleResult) => void;
  clearResults: () => void;

  /** Which card is currently selected in the data explorer (legacy compat) */
  selectedModule: string | null;
  setSelectedModule: (moduleName: string | null) => void;

  /** Store a result and navigate to it in the dashboard */
  viewModuleDetails: (toolName: string, result: ModuleResult) => void;

  /** --- Dashboard navigation state --- */
  activeTab: DashboardTab;
  setActiveTab: (tab: DashboardTab) => void;

  /** Section to scroll to within the active tab */
  activeSection: string | null;
  setActiveSection: (section: string | null) => void;

  /** Highlighted section (for flash animation after navigate) */
  highlightedSection: string | null;
  setHighlightedSection: (section: string | null) => void;

  /** Navigate to a specific tab and optional section (called by aRRIe tool results) */
  navigateTo: (target: string) => void;

  /** Audit stream state */
  activeAuditId: string | null;
  auditStreamEvents: AuditStreamEvent[];
  auditStreamStatus: "idle" | "streaming" | "completed" | "failed";
  startAuditStream: (auditId: string) => void;
  addStreamEvent: (event: AuditStreamEvent) => void;
  endAuditStream: (status: "completed" | "failed") => void;
  clearAuditStream: () => void;
}

export const usePrismStore = create<PrismStore>((set) => ({
  currentDomain: null,
  setCurrentDomain: (domain) => set({ currentDomain: domain }),

  currentCompanyName: null,
  setCurrentCompanyName: (name) => set({ currentCompanyName: name }),

  sendChatMessage: null,
  setSendChatMessage: (fn) => set({ sendChatMessage: fn }),

  availableResults: {},
  addResult: (moduleName, result) =>
    set((state) => ({
      availableResults: {
        ...state.availableResults,
        [moduleName]: result,
      },
    })),
  clearResults: () => set({ availableResults: {} }),

  selectedModule: null,
  setSelectedModule: (moduleName) => set({ selectedModule: moduleName }),

  viewModuleDetails: (toolName, result) => {
    const moduleName = TOOL_TO_MODULE[toolName] ?? toolName;
    set((state) => ({
      availableResults: {
        ...state.availableResults,
        [moduleName]: result,
      },
      selectedModule: moduleName,
    }));
  },

  /** --- Dashboard navigation --- */
  activeTab: "overview",
  setActiveTab: (tab) => {
    set({ activeTab: tab, activeSection: null, highlightedSection: null });
    // Update URL hash
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${tab}`);
    }
  },

  activeSection: null,
  setActiveSection: (section) => set({ activeSection: section }),

  highlightedSection: null,
  setHighlightedSection: (section) => set({ highlightedSection: section }),

  navigateTo: (target) => {
    const mapping = NAVIGATE_MAP[target];
    if (!mapping) {
      console.warn("[store] navigateTo: unknown target", target);
      return;
    }
    set({
      activeTab: mapping.tab,
      activeSection: mapping.section ?? null,
      highlightedSection: mapping.section ?? null,
    });
    // Update URL hash
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${mapping.tab}`);
    }
    // Clear highlight after animation
    if (mapping.section) {
      setTimeout(() => {
        set({ highlightedSection: null });
      }, 2000);
    }
  },

  activeAuditId: null,
  auditStreamEvents: [],
  auditStreamStatus: "idle",
  startAuditStream: (auditId) =>
    set({ activeAuditId: auditId, auditStreamEvents: [], auditStreamStatus: "streaming" }),
  addStreamEvent: (event) =>
    set((state) => ({ auditStreamEvents: [...state.auditStreamEvents, event] })),
  endAuditStream: (status) =>
    set({ auditStreamStatus: status }),
  clearAuditStream: () =>
    set({ activeAuditId: null, auditStreamEvents: [], auditStreamStatus: "idle" }),
}));
