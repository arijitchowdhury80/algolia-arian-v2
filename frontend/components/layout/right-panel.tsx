"use client";

import { Diamond } from "lucide-react";
import { usePrismStore } from "@/lib/store";
import { PrismChat } from "@/components/chat/prism-chat";

/**
 * RightPanel — aRRIe chat panel (340px, always visible).
 *
 * Contains the AI chat interface with tool renderers, thinking blocks,
 * and compact summaries. The chat input is pinned to the bottom.
 */
export function RightPanel() {
  const currentDomain = usePrismStore((s) => s.currentDomain);
  const companyName = usePrismStore((s) => s.currentCompanyName);

  return (
    <div className="flex h-full flex-col bg-white border-l border-[#E5E7EB]">
      {/* Panel header */}
      <div className="shrink-0 border-b border-[#E5E7EB] px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#003DFF]/10">
            <Diamond className="h-3.5 w-3.5 text-[#003DFF]" />
          </div>
          <span className="text-sm font-semibold text-[#23263B] tracking-tight">
            aRRIe
          </span>
        </div>
        <p className="mt-1 text-[11px] text-[#6B7280]">
          {currentDomain
            ? `Ask me anything about ${companyName ?? currentDomain}`
            : "Select an account to get started"}
        </p>
      </div>

      {/* Chat area — fills remaining space */}
      <div className="flex-1 min-h-0">
        <PrismChat />
      </div>
    </div>
  );
}
