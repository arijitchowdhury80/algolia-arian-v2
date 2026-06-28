"use client";

import { useState, useRef, useEffect } from "react";
import {
  ChevronDown,
  CheckCircle2,
  Circle,
  Building2,
  Users,
  Globe,
  Search,
  Rocket,
  BarChart3,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { usePrismStore, TOOL_TO_MODULE } from "@/lib/store";
import { TOOL_GROUPS, TOOL_DISPLAY_NAMES } from "@/lib/tools";
import type { ModuleResult } from "@/lib/types";

// Card component imports
import { CompanyCard } from "@/components/prism/company-card";
import { TechStackCard } from "@/components/prism/tech-stack-card";
import { TrafficCard } from "@/components/prism/traffic-card";
import { FinancialCard } from "@/components/prism/financial-card";
import { NewsCard } from "@/components/prism/news-card";
import { HiringCard } from "@/components/prism/hiring-card";
import { SocialCard } from "@/components/prism/social-card";
import { InvestorCard } from "@/components/prism/investor-card";
import { PartnerCard } from "@/components/prism/partner-card";
import { IndustryCard } from "@/components/prism/industry-card";
import { CompetitorMatrixCard } from "@/components/prism/competitor-matrix-card";
import { QueriesCard } from "@/components/prism/queries-card";
import { BrowserAuditCard } from "@/components/prism/browser-audit-card";
import { FactcheckCard } from "@/components/prism/factcheck-card";
import { BusinessCaseCard } from "@/components/prism/business-case-card";
import { SalesPlaysCard } from "@/components/prism/sales-plays-card";
import { AuditReportCard } from "@/components/prism/audit-report-card";
import { CampaignCard } from "@/components/prism/campaign-card";
import { BenchmarksCard } from "@/components/prism/benchmarks-card";

// ---------------------------------------------------------------------------
// Card renderer map
// ---------------------------------------------------------------------------

const CARD_MAP: Record<
  string,
  React.ComponentType<{ data: ModuleResult }>
> = {
  "intel-company": CompanyCard,
  "intel-techstack": TechStackCard,
  "intel-traffic": TrafficCard,
  "intel-financial-public": FinancialCard,
  "intel-financial-private": FinancialCard,
  "intel-news": NewsCard,
  "intel-hiring": HiringCard,
  "intel-social": SocialCard,
  "intel-investor": InvestorCard,
  "intel-partner": PartnerCard,
  "intel-industry": IndustryCard,
  "intel-competitors": CompetitorMatrixCard,
  "intel-queries": QueriesCard,
  "audit-browser": BrowserAuditCard,
  "audit-factcheck": FactcheckCard,
  "synth-business-case": BusinessCaseCard,
  "synth-sales-plays": SalesPlaysCard,
  "audit-report": AuditReportCard,
  "campaign-abx": CampaignCard,
  "insights-engine": BenchmarksCard,
};

// ---------------------------------------------------------------------------
// Group icons
// ---------------------------------------------------------------------------

const GROUP_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "Company Intelligence": Building2,
  "People Intelligence": Users,
  "Market Intelligence": Globe,
  "Audit & Analysis": Search,
  "Sales Enablement": Rocket,
  Benchmarks: BarChart3,
};

// ---------------------------------------------------------------------------
// Module display names (from module key, not tool name)
// ---------------------------------------------------------------------------

const MODULE_DISPLAY_NAMES: Record<string, string> = {
  "intel-company": "Company Profile",
  "intel-techstack": "Technology Analysis",
  "intel-traffic": "Traffic Analysis",
  "intel-financial-public": "Public Financials",
  "intel-financial-private": "Private Financials",
  "intel-news": "Company News",
  "intel-hiring": "Hiring Intelligence",
  "intel-social": "Social Intelligence",
  "intel-investor": "Investor Intelligence",
  "intel-partner": "Partner Ecosystem",
  "intel-industry": "Industry Benchmarks",
  "intel-competitors": "Competitor Matrix",
  "intel-queries": "Test Queries",
  "audit-browser": "Browser Audit",
  "audit-factcheck": "Factcheck Gate",
  "synth-business-case": "Business Case",
  "synth-sales-plays": "Sales Plays",
  "audit-report": "Audit Report",
  "campaign-abx": "ABX Campaign",
  "insights-engine": "Vertical Benchmarks",
};

// ---------------------------------------------------------------------------
// DataExplorer
// ---------------------------------------------------------------------------

export function DataExplorer() {
  const { availableResults, selectedModule, setSelectedModule } =
    usePrismStore();

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [dropdownOpen]);

  const currentDisplayName = selectedModule
    ? MODULE_DISPLAY_NAMES[selectedModule] ?? selectedModule
    : "Select a module";

  const CardComponent = selectedModule ? CARD_MAP[selectedModule] : null;
  const cardData = selectedModule ? availableResults[selectedModule] : null;

  return (
    <div className="flex h-full flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-[var(--border-warm)] px-4 py-2.5">
        <span className="text-xs font-bold text-[#23263B] uppercase tracking-wider">
          Data Explorer
        </span>
        <span className="text-xs text-[#23263B]/40">Legacy</span>
      </div>

      {/* Navigator dropdown */}
      <div className="relative px-4 py-3" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setDropdownOpen((prev) => !prev)}
          className="flex w-full items-center justify-between rounded-lg border border-[#E8E8E8] bg-white px-3 py-2 text-sm text-[#23263B] transition-colors hover:border-[#5468FF]/30"
        >
          <span className="truncate font-medium">{currentDisplayName}</span>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-[#23263B]/40 transition-transform",
              dropdownOpen && "rotate-180"
            )}
          />
        </button>

        {/* Dropdown menu */}
        {dropdownOpen && (
          <div className="absolute left-4 right-4 top-full z-50 mt-1 max-h-[60vh] overflow-y-auto rounded-lg border border-[#E8E8E8] bg-white shadow-lg">
            {Object.entries(TOOL_GROUPS).map(([groupName, toolNames]) => {
              const GroupIcon = GROUP_ICONS[groupName] ?? Wrench;
              return (
                <div key={groupName}>
                  {/* Group header */}
                  <div className="flex items-center gap-2 px-3 py-2 border-b border-[#F5F5F7]">
                    <GroupIcon className="h-3 w-3 text-[#23263B]/40" />
                    <span className="text-[10px] font-semibold text-[#23263B]/50 uppercase tracking-wider">
                      {groupName}
                    </span>
                  </div>
                  {/* Group items */}
                  {(toolNames as readonly string[]).map((toolName) => {
                    const moduleName = TOOL_TO_MODULE[toolName] ?? toolName;
                    const hasData = Boolean(availableResults[moduleName]);
                    const isSelected = selectedModule === moduleName;
                    const displayName =
                      TOOL_DISPLAY_NAMES[toolName] ?? toolName;
                    return (
                      <button
                        key={toolName}
                        type="button"
                        onClick={() => {
                          setSelectedModule(moduleName);
                          setDropdownOpen(false);
                        }}
                        className={cn(
                          "flex w-full items-center gap-2 px-4 py-2 text-left text-[12px] transition-colors",
                          isSelected
                            ? "bg-[#003DFF]/5 text-[#003DFF] font-medium"
                            : "text-[#23263B] hover:bg-[#F5F5F7]",
                          !hasData && "opacity-50"
                        )}
                      >
                        {hasData ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
                        ) : (
                          <Circle className="h-3.5 w-3.5 text-[#23263B]/20 shrink-0" />
                        )}
                        <span className="truncate">{displayName}</span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Card display area */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {CardComponent && cardData ? (
          <CardComponent data={cardData} />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center px-6">
              <Globe className="h-8 w-8 text-[#23263B]/10 mx-auto mb-3" />
              <p className="text-sm text-[#23263B]/40">
                {selectedModule && !cardData
                  ? "No data available for this module yet. Run the tool first."
                  : "Run an audit or ask about a company to see intelligence here."}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
