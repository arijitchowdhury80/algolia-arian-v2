"use client";

import {
  Building2,
  Layers,
  BarChart3,
  DollarSign,
  Newspaper,
  Users,
  MessageSquare,
  TrendingUp,
  Handshake,
  Globe,
  GitCompare,
  FlaskConical,
  Eye,
  ShieldCheck,
  Briefcase,
  Rocket,
  FileText,
  Megaphone,
  Zap,
  AlertCircle,
  Database,
} from "lucide-react";
import type { ModuleResult } from "@/lib/types";

// ---------------------------------------------------------------------------
// Icon map by module name
// ---------------------------------------------------------------------------

const MODULE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "intel-company": Building2,
  "intel-techstack": Layers,
  "intel-traffic": BarChart3,
  "intel-financial-public": DollarSign,
  "intel-financial-private": DollarSign,
  "intel-news": Newspaper,
  "intel-hiring": Users,
  "intel-social": MessageSquare,
  "intel-investor": TrendingUp,
  "intel-partner": Handshake,
  "intel-industry": Globe,
  "intel-competitors": GitCompare,
  "intel-queries": FlaskConical,
  "audit-browser": Eye,
  "audit-factcheck": ShieldCheck,
  "synth-business-case": Briefcase,
  "synth-sales-plays": Rocket,
  "audit-report": FileText,
  "campaign-abx": Megaphone,
  "insights-engine": BarChart3,
};

// ---------------------------------------------------------------------------
// Module display names
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
// Key findings extractor
// ---------------------------------------------------------------------------

function extractKeyFindings(moduleName: string, output: Record<string, unknown>): string {
  switch (moduleName) {
    case "intel-company": {
      const name = (output?.common_name as string) ?? "Unknown";
      const industry = (output?.industry as string) ?? "";
      const empCount = output?.employee_count as number | null;
      const comps = output?.competitors as unknown[] | undefined;
      const parts = [name];
      if (industry) parts.push(industry);
      if (empCount != null) parts.push(`${empCount.toLocaleString()} employees`);
      if (comps?.length) parts.push(`${comps.length} competitors`);
      return parts.join(" · ");
    }
    case "intel-techstack": {
      const sv = output?.search_vendor as Record<string, unknown> | null;
      const techs = output?.all_technologies as unknown[] | undefined;
      const parts: string[] = [];
      if (sv?.name) parts.push(`Search: ${sv.name} (${sv?.status ?? "UNKNOWN"})`);
      if (techs?.length != null) parts.push(`${techs.length} technologies`);
      return parts.length > 0 ? parts.join(" · ") : "Technology data available";
    }
    case "intel-traffic": {
      const visits = output?.monthly_visits as number | null;
      const bounce = output?.bounce_rate as number | null;
      const ds = output?.device_split as Record<string, unknown> | null;
      const parts: string[] = [];
      if (visits != null) parts.push(`${visits.toLocaleString()} visits/mo`);
      if (bounce != null) parts.push(`Bounce: ${bounce}%`);
      if (ds?.mobile != null) parts.push(`Mobile: ${ds.mobile}%`);
      return parts.length > 0 ? parts.join(" · ") : "Traffic data available";
    }
    case "intel-financial-public": {
      const ticker = (output?.ticker as string) ?? "";
      const parts: string[] = [];
      if (ticker) parts.push(ticker);
      if (output?.revenue_3yr) parts.push("Revenue trend available");
      if (output?.market_cap) parts.push("Market cap data");
      return parts.length > 0 ? parts.join(" · ") : "Financial data available";
    }
    case "intel-financial-private": {
      const conf = (output?.confidence as string) ?? "";
      const parts: string[] = ["Revenue estimate available"];
      if (conf) parts.push(`Confidence: ${conf}`);
      return parts.join(" · ");
    }
    case "intel-news": {
      const news = output?.news_items as unknown[] | undefined;
      const urgency = output?.urgency_signals as unknown[] | undefined;
      const parts: string[] = [];
      if (news?.length != null) parts.push(`${news.length} articles`);
      if (urgency?.length != null) parts.push(`${urgency.length} urgency signals`);
      return parts.length > 0 ? parts.join(" · ") : "News data available";
    }
    case "intel-hiring": {
      const total = output?.total_roles as number | null;
      const bvb = (output?.build_vs_buy_signal as string) ?? "";
      const champs = output?.champion_signals as unknown[] | undefined;
      const parts: string[] = [];
      if (total != null) parts.push(`${total} roles`);
      if (bvb) parts.push(`Build signal: ${bvb}`);
      if (champs?.length != null) parts.push(`${champs.length} champions`);
      return parts.length > 0 ? parts.join(" · ") : "Hiring data available";
    }
    case "intel-social": {
      const posts = output?.executive_posts as unknown[] | undefined;
      const quotes = output?.quotable_statements as unknown[] | undefined;
      const parts: string[] = [];
      if (posts?.length != null) parts.push(`${posts.length} exec posts`);
      if (quotes?.length != null) parts.push(`${quotes.length} quotable statements`);
      return parts.length > 0 ? parts.join(" · ") : "Social data available";
    }
    case "intel-investor": {
      const svf = output?.said_vs_found as unknown[] | undefined;
      const eq = output?.earnings_quotes as unknown[] | undefined;
      const sa = output?.sales_angles as unknown[] | undefined;
      const parts: string[] = [];
      if (svf?.length != null) parts.push(`${svf.length} Said vs Found`);
      if (eq?.length != null) parts.push(`${eq.length} quotes`);
      if (sa?.length != null) parts.push(`${sa.length} angles`);
      return parts.length > 0 ? parts.join(" · ") : "Investor data available";
    }
    case "intel-partner": {
      const si = output?.si_relationships as unknown[] | undefined;
      const play = (output?.partner_play_recommendation as string) ?? "";
      const parts: string[] = [];
      if (si?.length != null) parts.push(`${si.length} partners`);
      if (play) parts.push(`Play: ${play}`);
      return parts.length > 0 ? parts.join(" · ") : "Partner data available";
    }
    case "intel-industry": {
      const vertical = (output?.vertical as string) ?? "";
      const benchmarks = output?.benchmarks as unknown[] | undefined;
      const trends = output?.trends as unknown[] | undefined;
      const parts: string[] = [];
      if (vertical) parts.push(vertical);
      if (benchmarks?.length != null) parts.push(`${benchmarks.length} benchmarks`);
      if (trends?.length != null) parts.push(`${trends.length} trends`);
      return parts.length > 0 ? parts.join(" · ") : "Industry data available";
    }
    case "intel-competitors": {
      const comps = output?.competitors as unknown[] | undefined;
      const parts: string[] = [];
      if (comps?.length != null) parts.push(`${comps.length} competitors`);
      const best = comps?.[0] as Record<string, unknown> | undefined;
      if (best?.scenario) parts.push(`Scenario: ${best.scenario}`);
      return parts.length > 0 ? parts.join(" · ") : "Competitor data available";
    }
    case "intel-queries": {
      const qc = output?.query_count as number | null;
      const pq = output?.prospect_queries as unknown[] | undefined;
      const types = new Set<string>();
      if (Array.isArray(pq)) {
        for (const q of pq) {
          const t = (q as Record<string, unknown>)?.query_type as string | undefined;
          if (t) types.add(t);
        }
      }
      const parts: string[] = [];
      if (qc != null) parts.push(`${qc} queries`);
      if (types.size > 0) parts.push(`${types.size} types`);
      return parts.length > 0 ? parts.join(" · ") : "Query data available";
    }
    case "audit-browser": {
      const ds = output?.dimension_scores as unknown[] | undefined;
      let overall = 0;
      if (Array.isArray(ds) && ds.length > 0) {
        const sum = ds.reduce((a: number, d) => a + ((d as Record<string, unknown>)?.score as number ?? 0), 0);
        overall = Math.round((sum / ds.length) * 10) / 10;
      }
      const provider = (output?.detected_search_provider as string) ?? "";
      const parts: string[] = [];
      if (overall > 0) parts.push(`Score: ${overall}/10`);
      if (provider) parts.push(`Provider: ${provider}`);
      return parts.length > 0 ? parts.join(" · ") : "Browser audit data available";
    }
    case "synth-business-case": {
      const svf = output?.said_vs_found as unknown[] | undefined;
      const roi = output?.total_roi_conservative as number | null;
      const parts: string[] = [];
      if (svf?.length != null) parts.push(`${svf.length} angles`);
      if (roi != null) parts.push(`ROI: $${roi.toLocaleString()}`);
      return parts.length > 0 ? parts.join(" · ") : "Business case available";
    }
    case "synth-sales-plays": {
      const spin = output?.spin_questions as unknown[] | undefined;
      const parts: string[] = ["MEDDPICC mapped"];
      if (spin?.length != null) parts.push(`${spin.length} questions`);
      return parts.join(" · ");
    }
    case "audit-report": {
      const score = output?.overall_score as number | null;
      const parts: string[] = [];
      if (score != null) parts.push(`Score: ${score}/10`);
      parts.push("Pre-call brief ready");
      return parts.join(" · ");
    }
    case "campaign-abx": {
      const lm = output?.linkedin_messages as unknown[] | undefined;
      const parts: string[] = ["5-email sequence"];
      if (lm?.length != null) parts.push(`${lm.length} LinkedIn msgs`);
      return parts.join(" · ");
    }
    case "audit-factcheck": {
      const verdict = (output?.verdict as string) ?? "";
      const verified = output?.verified_count as number | null;
      const total = output?.total_claims as number | null;
      const parts: string[] = [];
      if (verdict) parts.push(`Verdict: ${verdict}`);
      if (verified != null && total != null) parts.push(`${verified}/${total} verified`);
      return parts.length > 0 ? parts.join(" · ") : "Factcheck data available";
    }
    case "insights-engine": {
      return "Benchmarks available";
    }
    default:
      return "Data available";
  }
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    success: "bg-green-100 text-green-700",
    partial: "bg-amber-100 text-amber-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}
    >
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// CompactSummary
// ---------------------------------------------------------------------------

interface CompactSummaryProps {
  moduleName: string;
  toolName: string;
  data: ModuleResult;
  onViewDetails: () => void;
}

export function CompactSummary({
  moduleName,
  toolName: _toolName,
  data,
  onViewDetails,
}: CompactSummaryProps) {
  const Icon = MODULE_ICONS[moduleName] ?? Zap;
  const displayName = MODULE_DISPLAY_NAMES[moduleName] ?? moduleName;
  const isFailed = data.status === "failed";

  const findings = isFailed
    ? data.errors?.[0] ?? "Module execution failed"
    : extractKeyFindings(moduleName, data.output ?? {});

  return (
    <div className="my-2 flex items-start gap-3 rounded-lg border border-[#E8E8E8] bg-[#FAFAFA] px-4 py-3 transition-shadow hover:shadow-sm">
      {/* Icon */}
      <div className="mt-0.5 shrink-0">
        {isFailed ? (
          <AlertCircle className="h-4 w-4 text-red-500" />
        ) : (
          <Icon className="h-4 w-4 text-[#5468FF]" />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        {/* Line 1: Name + status + duration */}
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-[#23263B]">
            {displayName}
          </span>
          <StatusBadge status={data.status} />
          <span className="inline-flex items-center gap-1 text-[12px] text-[var(--muted-text)]">
            <Database className="h-3 w-3" />
            PRISM
          </span>
          <span className="text-[11px] font-mono text-[#23263B]/40">
            {data.duration_ms}ms
          </span>
        </div>

        {/* Line 2: Key findings */}
        <p
          className={`mt-0.5 text-[12px] leading-relaxed ${isFailed ? "text-red-600" : "text-[#23263B]"}`}
        >
          {findings}
        </p>

        {/* Line 3: Action link */}
        <button
          type="button"
          onClick={onViewDetails}
          className="mt-1 text-[12px] font-medium text-[#003DFF] hover:underline"
        >
          {isFailed ? "Retry" : "View details"} &rarr;
        </button>
      </div>
    </div>
  );
}
