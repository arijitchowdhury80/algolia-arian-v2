"use client";

import { usePrismStore } from "@/lib/store";
import { OverviewTab } from "./tabs/overview-tab";
import { ResearchTab } from "./tabs/research-tab";
import { SearchAuditTab } from "./tabs/search-audit-tab";
import { BusinessCaseTab } from "./tabs/business-case-tab";
import { CompetitiveTab } from "./tabs/competitive-tab";
import { SalesActionsTab } from "./tabs/sales-actions-tab";

/**
 * TabContent — renders the correct tab component based on activeTab.
 */
export function TabContent() {
  const activeTab = usePrismStore((s) => s.activeTab);
  const availableResults = usePrismStore((s) => s.availableResults);

  switch (activeTab) {
    case "overview":
      return <OverviewTab results={availableResults} />;
    case "research":
      return <ResearchTab results={availableResults} />;
    case "search-audit":
      return <SearchAuditTab results={availableResults} />;
    case "business-case":
      return <BusinessCaseTab results={availableResults} />;
    case "competitive":
      return <CompetitiveTab results={availableResults} />;
    case "sales-actions":
      return <SalesActionsTab results={availableResults} />;
    default:
      return <OverviewTab results={availableResults} />;
  }
}
