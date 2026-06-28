"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { usePrismStore } from "@/lib/store";
import { ChevronDown } from "lucide-react";
import type { ModuleResult } from "@/lib/types";

/* ── Card component imports ── */
import { CompanyIntelCard } from "@/components/prism/company-intel-card";
// company-card.tsx is deprecated — replaced by company-intel-card.tsx
import { FinancialCard } from "@/components/prism/financial-card";
import { TechStackCard } from "@/components/prism/tech-stack-card";
import { TrafficCard } from "@/components/prism/traffic-card";
import { HiringCard } from "@/components/prism/hiring-card";
import { NewsCard } from "@/components/prism/news-card";
import { SocialCard } from "@/components/prism/social-card";
import { InvestorCard } from "@/components/prism/investor-card";
import { PartnerCard } from "@/components/prism/partner-card";
import { IndustryCard } from "@/components/prism/industry-card";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface TabProps {
  results: Record<string, ModuleResult>;
}

interface SectionConfig {
  id: string;
  eyebrow: string;
  title: string;
  moduleKeys: string[];
  CardComponent: React.ComponentType<{ data: ModuleResult }>;
}

/* ------------------------------------------------------------------ */
/*  Section definitions                                                */
/* ------------------------------------------------------------------ */

const SECTIONS: SectionConfig[] = [
  {
    id: "financial-profile",
    eyebrow: "FINANCIAL PROFILE",
    title: "Financial Profile",
    moduleKeys: ["intel-financial-public", "intel-financial-private"],
    CardComponent: FinancialCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
  {
    id: "technology-stack",
    eyebrow: "TECHNOLOGY STACK",
    title: "Technology Stack",
    moduleKeys: ["intel-techstack"],
    CardComponent: TechStackCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
  {
    id: "traffic-digital",
    eyebrow: "TRAFFIC & DIGITAL PRESENCE",
    title: "Traffic & Digital Presence",
    moduleKeys: ["intel-traffic"],
    CardComponent: TrafficCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
  {
    id: "hiring-signals",
    eyebrow: "HIRING SIGNALS",
    title: "Hiring Signals",
    moduleKeys: ["intel-hiring"],
    CardComponent: HiringCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
  {
    id: "news-signals",
    eyebrow: "NEWS & SIGNALS",
    title: "News & Signals",
    moduleKeys: ["intel-news"],
    CardComponent: NewsCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
  {
    id: "social-intelligence",
    eyebrow: "SOCIAL INTELLIGENCE",
    title: "Social Intelligence",
    moduleKeys: ["intel-social"],
    CardComponent: SocialCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
  {
    id: "investor-intelligence",
    eyebrow: "INVESTOR INTELLIGENCE",
    title: "Investor Intelligence",
    moduleKeys: ["intel-investor"],
    CardComponent: InvestorCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
  {
    id: "partner-intelligence",
    eyebrow: "PARTNER INTELLIGENCE",
    title: "Partner Intelligence",
    moduleKeys: ["intel-partner"],
    CardComponent: PartnerCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
  {
    id: "industry-benchmarks",
    eyebrow: "INDUSTRY BENCHMARKS",
    title: "Industry Benchmarks",
    moduleKeys: ["intel-industry"],
    CardComponent: IndustryCard as unknown as React.ComponentType<{ data: ModuleResult }>,
  },
];

/* ------------------------------------------------------------------ */
/*  Helper: find module data                                           */
/* ------------------------------------------------------------------ */

function findModuleData(
  results: Record<string, ModuleResult>,
  moduleKeys: string[],
): ModuleResult | undefined {
  for (const key of moduleKeys) {
    if (results[key]) return results[key];
  }
  return undefined;
}

/* ------------------------------------------------------------------ */
/*  CollapsibleSection                                                 */
/* ------------------------------------------------------------------ */

interface CollapsibleSectionProps {
  config: SectionConfig;
  data: ModuleResult | undefined;
  isHighlighted: boolean;
}

function CollapsibleSection({
  config,
  data,
  isHighlighted,
}: CollapsibleSectionProps) {
  const hasData = data != null;
  const [isOpen, setIsOpen] = useState(hasData);

  // Re-expand when data arrives
  useEffect(() => {
    if (hasData) setIsOpen(true);
  }, [hasData]);

  // Scroll into view when highlighted
  useEffect(() => {
    if (isHighlighted) {
      const el = document.getElementById(config.id);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }, [isHighlighted, config.id]);

  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  const { CardComponent } = config;

  return (
    <div
      id={config.id}
      className={cn(
        "rounded-[20px] border border-[#E5E7EB] overflow-hidden transition-colors duration-500",
        isHighlighted && "animate-[highlight_2s_ease-out]",
      )}
      style={{
        background: "rgba(255, 255, 255, 0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06)",
      }}
    >
      {/* Header — always visible */}
      <button
        type="button"
        onClick={toggle}
        className="flex w-full items-center justify-between px-6 py-5 text-left hover:bg-black/[0.02] transition-colors"
      >
        <div>
          <div className="text-[14px] font-bold uppercase tracking-wide text-[#003DFF] mb-0.5">
            {config.eyebrow}
          </div>
          <h3 className="text-[1.75rem] font-semibold text-[#23263B] leading-tight">
            {config.title}
          </h3>
        </div>
        <ChevronDown
          className={cn(
            "h-5 w-5 text-[#6B7280] shrink-0 transition-transform duration-200",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {/* Collapsible body */}
      <div
        className={cn(
          "overflow-hidden transition-[max-height,opacity] duration-300 ease-in-out",
          isOpen ? "max-h-[5000px] opacity-100" : "max-h-0 opacity-0",
        )}
      >
        <div className="px-6 pb-6">
          {hasData ? (
            <CardComponent data={data} />
          ) : (
            <div className="py-8 text-center">
              <p className="text-sm text-[#6B7280]">
                No data yet — run the audit to populate
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ResearchTab — main export                                          */
/* ------------------------------------------------------------------ */

export function ResearchTab({ results }: TabProps) {
  const highlighted = usePrismStore((s) => s.highlightedSection);
  const activeSection = usePrismStore((s) => s.activeSection);

  // When activeSection changes, scroll to it
  useEffect(() => {
    if (activeSection) {
      // Small delay to ensure render is complete
      const timer = setTimeout(() => {
        const el = document.getElementById(activeSection);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [activeSection]);

  const companyData = results["intel-company"];

  return (
    <div className="px-6 py-8 space-y-6">
      {/* Company Intelligence — always open, anchors the top of the Research tab */}
      {companyData && (
        <div id="company-snapshot">
          <CompanyIntelCard data={companyData} />
        </div>
      )}

      {SECTIONS.map((section) => {
        const data = findModuleData(results, section.moduleKeys);
        return (
          <CollapsibleSection
            key={section.id}
            config={section}
            data={data}
            isHighlighted={highlighted === section.id}
          />
        );
      })}

      <style jsx>{`
        @keyframes highlight {
          0% {
            background: #fef3c7;
          }
          100% {
            background: transparent;
          }
        }
      `}</style>
    </div>
  );
}
