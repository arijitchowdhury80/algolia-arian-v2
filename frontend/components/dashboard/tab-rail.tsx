"use client";

import { useCallback } from "react";
import { cn } from "@/lib/utils";
import { usePrismStore, DASHBOARD_TABS } from "@/lib/store";
import type { DashboardTab } from "@/lib/store";

export function TabRail() {
  const activeTab = usePrismStore((s) => s.activeTab);
  const setActiveTab = usePrismStore((s) => s.setActiveTab);

  const handleTabClick = useCallback(
    (tabId: DashboardTab) => {
      setActiveTab(tabId);
    },
    [setActiveTab]
  );

  return (
    <div className="sticky top-0 z-20 flex items-center justify-center px-6 py-3 bg-[#F8F9FB]/85 backdrop-blur-sm border-b border-[rgba(0,0,0,0.06)]">
      <div className="flex items-center gap-0.5 rounded-full bg-white border border-[rgba(0,0,0,0.10)] px-1.5 py-1 shadow-[0_4px_20px_rgba(0,0,0,0.12),0_1px_4px_rgba(0,0,0,0.06)]">
        {DASHBOARD_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => handleTabClick(tab.id)}
            className={cn(
              "rounded-full px-4 py-1.5 text-[12px] font-medium transition-all duration-200",
              activeTab === tab.id
                ? "bg-[#23263B] text-white font-semibold shadow-sm"
                : "text-[#6B7280] hover:bg-[#F5F5F7] hover:text-[#23263B]"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
