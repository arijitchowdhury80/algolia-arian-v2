"use client";

import { useEffect, useRef, useState } from "react";
import { TabRail } from "@/components/dashboard/tab-rail";
import { TabContent } from "@/components/dashboard/tab-content";
import { usePrismStore } from "@/lib/store";
import { Diamond } from "lucide-react";

/**
 * CenterPanel — Intelligence Dashboard.
 * Scroll progress bar (DSW-style) at top of scrollable content area.
 */
export function CenterPanel({ children }: { children?: React.ReactNode }) {
  const currentDomain = usePrismStore((s) => s.currentDomain);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollPct, setScrollPct] = useState(0);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    function onScroll() {
      const { scrollTop, scrollHeight, clientHeight } = el!;
      const max = scrollHeight - clientHeight;
      setScrollPct(max > 0 ? (scrollTop / max) * 100 : 0);
    }
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="flex h-full flex-col bg-[#F8F9FB]">
      {/* Scroll progress bar — DSW style */}
      <div
        style={{
          height: 2,
          background: "rgba(0,0,0,0.06)",
          position: "relative",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            right: `${100 - scrollPct}%`,
            background: "linear-gradient(90deg, #003DFF, #5468FF)",
            transition: "right 0.08s linear",
          }}
        />
      </div>

      {/* Tab rail — always visible */}
      <TabRail />

      {/* Scrollable content area */}
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
        {!currentDomain ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center max-w-md px-8">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#003DFF]/10 mx-auto mb-5">
                <Diamond className="h-8 w-8 text-[#003DFF]" />
              </div>
              <h2 className="text-xl font-semibold text-[#23263B] mb-2">
                Intelligence Dashboard
              </h2>
              <p className="text-sm text-[#6B7280] leading-relaxed">
                Select an account and run an audit to see intelligence here.
                Or ask aRRIe to get started →
              </p>
            </div>
          </div>
        ) : (
          <TabContent />
        )}
      </div>
    </div>
  );
}
