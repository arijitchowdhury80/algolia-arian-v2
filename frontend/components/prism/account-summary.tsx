"use client";

import { useRef, useMemo, useCallback, useEffect } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { usePrismStore } from "@/lib/store";
import type { ModuleResult } from "@/lib/types";

/* ── Formatting ── */
function fmtNum(n: unknown): string | null {
  if (n == null) return null;
  const v = Number(n);
  if (isNaN(v)) return null;
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return String(Math.round(v));
}
function fmtCur(n: unknown): string | null {
  const f = fmtNum(n);
  return f ? `$${f}` : null;
}

/* ── Section data ── */
interface SectionData {
  id: string;
  eyebrow: string;
  title: string;
  subtitle: string | null;
  items: { label: string; value: string }[];
  hasData: boolean;
  highlight?: string;
  primaryModule: string;
  accentColor: string;
}

const MODULE_MAP: Record<string, string> = {
  company: "intel-company",
  technology: "intel-techstack",
  market: "intel-traffic",
  financial: "intel-financial-public",
  competitive: "intel-competitors",
  signals: "intel-news",
  "business-case": "synth-business-case",
  "sales-ready": "synth-sales-plays",
};

/* ── Extract section data from module results ── */
function buildSections(results: Record<string, ModuleResult>): SectionData[] {
  const g = (mod: string): Record<string, unknown> | undefined =>
    results[mod]?.output as Record<string, unknown> | undefined;

  const company = g("intel-company");
  const tech = g("intel-techstack");
  const traffic = g("intel-traffic");
  const finPub = g("intel-financial-public");
  const finPriv = g("intel-financial-private");
  const comp = g("intel-competitors");
  const news = g("intel-news");
  const hiring = g("intel-hiring");
  const investor = g("intel-investor");
  const bcase = g("synth-business-case");
  const report = g("audit-report");
  const sales = g("synth-sales-plays");
  const campaign = g("campaign-abx");

  const sv = tech?.search_vendor as Record<string, unknown> | undefined;
  const execs = (company?.executives as Array<Record<string, unknown>>) ?? [];
  const compList = (comp?.competitors as Array<Record<string, unknown>>) ?? [];
  const newsItems = (news?.news_items as Array<Record<string, unknown>>) ?? [];
  const urgency = (news?.urgency_signals as Array<Record<string, unknown>>) ?? [];
  const quotes = (investor?.earnings_quotes as Array<Record<string, unknown>>) ?? [];

  const it = (label: string, val: unknown): { label: string; value: string } | null =>
    val != null && val !== "" && val !== "Unknown" ? { label, value: String(val) } : null;

  return [
    {
      id: "company",
      eyebrow: "COMPANY OVERVIEW",
      title: String(company?.common_name ?? company?.legal_name ?? "Company"),
      subtitle: company?.industry ? String(company.industry) : null,
      items: [
        it("Employees", fmtNum(company?.employee_count)),
        it("Revenue", fmtCur(company?.revenue_estimate)),
        it("Headquarters", company?.headquarters),
        it("Business Model", company?.business_model),
        ...execs.slice(0, 3).map((e) => it(String(e.title ?? "Executive"), String(e.full_name ?? ""))),
      ].filter((x): x is { label: string; value: string } => x !== null),
      hasData: !!company,
      primaryModule: "intel-company",
      accentColor: "#003DFF",
    },
    {
      id: "technology",
      eyebrow: "TECHNOLOGY & SEARCH",
      title: sv?.name ? `Search: ${sv.name}` : "Search Technology",
      subtitle: tech?.ecommerce_platform ? `Platform: ${tech.ecommerce_platform}` : null,
      items: [
        it("Search Status", sv?.status),
        it("Technologies Detected", `${(tech?.all_technologies as unknown[])?.length ?? 0}`),
        it("CMS", tech?.cms),
      ].filter((x): x is { label: string; value: string } => x !== null),
      hasData: !!tech,
      highlight: tech?.algolia_detected ? "⚡ Competitor uses Algolia — displacement opportunity" : undefined,
      primaryModule: "intel-techstack",
      accentColor: "#5468FF",
    },
    {
      id: "market",
      eyebrow: "TRAFFIC & MARKET",
      title: traffic?.monthly_visits ? `${fmtNum(traffic.monthly_visits)} monthly visits` : "Traffic Intelligence",
      subtitle: traffic?.bounce_rate != null ? `Bounce rate: ${Number(traffic.bounce_rate).toFixed(1)}%` : null,
      items: [
        it("Top Countries", ((traffic?.top_countries as Array<Record<string, unknown>>) ?? []).slice(0, 3).map((c) => c.country).join(", ") || null),
        it("Device Split", traffic?.device_split ? `${Number((traffic.device_split as Record<string, unknown>).desktop ?? 0).toFixed(0)}% desktop / ${Number((traffic.device_split as Record<string, unknown>).mobile ?? 0).toFixed(0)}% mobile` : null),
      ].filter((x): x is { label: string; value: string } => x !== null),
      hasData: !!traffic,
      primaryModule: "intel-traffic",
      accentColor: "#059669",
    },
    {
      id: "financial",
      eyebrow: "FINANCIAL PICTURE",
      title: finPub?.market_cap ? `${fmtCur(finPub.market_cap)} market cap` : finPriv?.revenue_best_estimate ? `${fmtCur(finPriv.revenue_best_estimate)} estimated revenue` : "Financial Data",
      subtitle: finPub ? "Public Company" : finPriv ? "Private Company (estimated)" : null,
      items: [
        it("Revenue", fmtCur(finPub ? (finPub.revenue_3yr as Array<Record<string, unknown>>)?.at(-1)?.revenue : finPriv?.revenue_best_estimate)),
        it("Gross Margin", finPub?.gross_margin != null ? `${(Number(finPub.gross_margin) * 100).toFixed(1)}%` : null),
        it("Analyst View", finPub?.analyst_consensus),
      ].filter((x): x is { label: string; value: string } => x !== null),
      hasData: !!finPub || !!finPriv,
      primaryModule: finPub ? "intel-financial-public" : "intel-financial-private",
      accentColor: "#7C3AED",
    },
    {
      id: "competitive",
      eyebrow: "COMPETITIVE LANDSCAPE",
      title: compList.length > 0 ? `${compList.length} competitors analyzed` : "Competitive Analysis",
      subtitle: compList.find((c) => c.scenario === "GOLDEN") ? `🏆 Golden Angle: ${compList.find((c) => c.scenario === "GOLDEN")?.company_name}` : null,
      items: compList.slice(0, 4).map((c) => ({
        label: String(c.scenario ?? "UNKNOWN"),
        value: String(c.company_name ?? c.name ?? ""),
      })),
      hasData: !!comp,
      primaryModule: "intel-competitors",
      accentColor: "#DC2626",
    },
    {
      id: "signals",
      eyebrow: "SIGNALS & TIMING",
      title: urgency[0]?.title ? String(urgency[0].title) : newsItems[0]?.headline ? String(newsItems[0].headline) : "Signal Intelligence",
      subtitle: `${newsItems.length} news items · ${urgency.length} urgency signals`,
      items: [
        it("Hiring Signal", hiring?.total_roles != null ? `${hiring.total_roles} roles (${hiring.build_vs_buy_signal ?? "?"})` : null),
        it("Exec Quote", quotes[0]?.quote ? `"${String(quotes[0].quote).slice(0, 80)}..."` : null),
        it("Top Signal", urgency[0]?.title ? String(urgency[0].title) : null),
      ].filter((x): x is { label: string; value: string } => x !== null),
      hasData: !!news || !!hiring || !!investor,
      primaryModule: "intel-news",
      accentColor: "#D97706",
    },
    {
      id: "business-case",
      eyebrow: "THE BUSINESS CASE",
      title: report?.overall_score != null ? `Search Quality: ${report.overall_score}/10` : bcase ? "Business Case Ready" : "Business Case",
      subtitle: bcase?.total_roi_moderate ? `Estimated ROI: ${fmtCur(bcase.total_roi_moderate)}` : null,
      items: [
        it("Said vs Found", (bcase?.said_vs_found as unknown[])?.length ? `${(bcase!.said_vs_found as unknown[]).length} insights` : null),
        it("Critical Gaps", (report?.dimension_scores as Array<Record<string, unknown>>)?.filter((d) => d.severity === "critical").length || null),
      ].filter((x): x is { label: string; value: string } => x !== null),
      hasData: !!bcase || !!report,
      primaryModule: "synth-business-case",
      accentColor: "#003DFF",
    },
    {
      id: "sales-ready",
      eyebrow: "SALES READY",
      title: sales?.meddpicc ? `MEDDPICC ${Math.round(((sales.meddpicc as unknown[]).length / 8) * 100)}% complete` : "Sales Playbook",
      subtitle: campaign?.email_sequence ? `${(campaign.email_sequence as unknown[]).length}-email sequence ready` : null,
      items: [
        it("Objection Handlers", (sales?.objection_handlers as unknown[])?.length ? `${(sales!.objection_handlers as unknown[]).length} prepared` : null),
        it("Discovery Questions", (sales?.spin_questions as unknown[])?.length ? `${(sales!.spin_questions as unknown[]).length} SPIN questions` : null),
      ].filter((x): x is { label: string; value: string } => x !== null),
      hasData: !!sales || !!campaign,
      primaryModule: "synth-sales-plays",
      accentColor: "#059669",
    },
  ];
}

/* ── Single sticky section with scroll-driven animation ── */

function StickySection({ section, index }: { section: SectionData; index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Find the scroll parent (overflow-y: auto ancestor)
  useEffect(() => {
    if (!ref.current) return;
    let el = ref.current.parentElement;
    while (el) {
      const style = getComputedStyle(el);
      if (style.overflowY === "auto" || style.overflowY === "scroll") {
        (containerRef as React.MutableRefObject<HTMLDivElement | null>).current = el as HTMLDivElement;
        break;
      }
      el = el.parentElement;
    }
  }, []);

  const { scrollYProgress } = useScroll({
    target: ref,
    container: containerRef,
    offset: ["start end", "end start"],
  });

  // Content fades and scales in as the section enters
  const opacity = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [0, 1, 1, 0]);
  const scale = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [0.85, 1, 1, 0.95]);
  const y = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], [60, 0, 0, -40]);

  const store = usePrismStore.getState;

  const handleClick = useCallback(() => {
    if (section.hasData) {
      const s = store();
      s.setSelectedModule(section.primaryModule);
    }
  }, [section.hasData, section.primaryModule, store]);

  return (
    <div
      ref={ref}
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 32px",
      }}
    >
      <motion.div
        style={{ opacity, scale, y }}
        onClick={handleClick}
        className="w-full max-w-2xl cursor-pointer"
      >
        {/* Card */}
        <div
          style={{
            background: "rgba(255,255,255,0.92)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            borderRadius: 24,
            padding: "40px 48px",
            boxShadow: "0 4px 6px rgba(0,0,0,0.03), 0 12px 32px rgba(0,0,0,0.08), 0 32px 64px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.9)",
            border: "1px solid rgba(0,0,0,0.06)",
            opacity: section.hasData ? 1 : 0.4,
          }}
        >
          {/* Eyebrow */}
          <div style={{
            fontSize: 11, fontWeight: 800, textTransform: "uppercase" as const,
            letterSpacing: "0.14em", color: section.accentColor,
            marginBottom: 12,
          }}>
            {section.eyebrow}
          </div>

          {/* Title */}
          <h2 style={{
            fontSize: 36, fontWeight: 700, color: "#23263B",
            letterSpacing: "-0.5px", lineHeight: 1.15, marginBottom: 8,
          }}>
            {section.title}
          </h2>

          {/* Subtitle */}
          {section.subtitle && (
            <p style={{ fontSize: 16, color: "#6B7280", marginBottom: 24, lineHeight: 1.5 }}>
              {section.subtitle}
            </p>
          )}

          {/* Highlight banner */}
          {section.highlight && (
            <div style={{
              padding: "10px 16px", borderRadius: 12,
              background: "#FEF3C7", border: "1px solid #FDE68A",
              fontSize: 14, fontWeight: 600, color: "#D97706",
              marginBottom: 24,
            }}>
              {section.highlight}
            </div>
          )}

          {/* Data items */}
          {section.items.length > 0 && (
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 1fr",
              gap: "16px 32px", marginBottom: 24,
            }}>
              {section.items.map((item, i) => (
                <div key={i}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "#94A3B8", textTransform: "uppercase" as const, letterSpacing: "0.06em", marginBottom: 2 }}>
                    {item.label}
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "#23263B", lineHeight: 1.4 }}>
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Footer */}
          <div style={{ borderTop: "1px solid rgba(0,0,0,0.06)", paddingTop: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: "0.08em", color: section.hasData ? section.accentColor : "#CBD5E1" }}>
              {section.hasData ? "Click for details →" : "Not yet collected"}
            </span>
            <span style={{ fontSize: 10, color: "#CBD5E1" }}>
              {index + 1} / 8
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

/* ── AccountSummary — Apple-style sequential sticky scroll ── */

export function AccountSummary() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const results = usePrismStore((s) => s.availableResults);
  const domain = usePrismStore((s) => s.currentDomain);

  const sections = useMemo(() => buildSections(results), [results]);
  const dataCount = sections.filter((s) => s.hasData).length;

  // Forward wheel events from overflow:hidden panel ancestors to our scroll container
  useEffect(() => {
    const scrollEl = scrollRef.current;
    if (!scrollEl) return;

    const onWheel = (e: WheelEvent) => {
      const rect = scrollEl.getBoundingClientRect();
      if (e.clientX >= rect.left && e.clientX <= rect.right &&
          e.clientY >= rect.top && e.clientY <= rect.bottom) {
        scrollEl.scrollTop += e.deltaY;
        e.preventDefault();
      }
    };

    document.addEventListener("wheel", onWheel, { passive: false });
    return () => document.removeEventListener("wheel", onWheel);
  }, []);

  return (
    <div
      ref={scrollRef}
      style={{
        height: "100%",
        overflowY: "auto",
        background: "linear-gradient(180deg, #F5F5F7 0%, #FAFAFA 100%)",
      }}
    >
      {/* Header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 10,
        padding: "12px 24px",
        background: "rgba(245,245,247,0.85)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(0,0,0,0.06)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div>
          <span style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase" as const, letterSpacing: "0.12em", color: "#003DFF" }}>
            Intelligence Briefing
          </span>
          <span style={{ fontSize: 12, color: "#6B7280", marginLeft: 10 }}>
            {domain} — {dataCount}/8 chapters with data
          </span>
        </div>
        <span style={{ fontSize: 10, color: "#94A3B8" }}>
          Scroll to explore ↓
        </span>
      </div>

      {/* Sections — each is 100vh tall, content animates in/out as you scroll */}
      {sections.map((section, i) => (
        <StickySection key={section.id} section={section} index={i} />
      ))}

      {/* End spacer */}
      <div style={{ height: "30vh" }} />
    </div>
  );
}
