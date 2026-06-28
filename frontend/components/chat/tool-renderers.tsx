"use client";

import { makeAssistantToolUI } from "@assistant-ui/react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Loader2,
  Search,
  Building,
  Globe,
  DollarSign,
  Newspaper,
  Users,
  Share2,
  TrendingUp,
  Handshake,
  BarChart3,
  Swords,
  ListChecks,
  Monitor,
  ShieldCheck,
  Briefcase,
  Target,
  FileText,
  Megaphone,
  LineChart,
} from "lucide-react";
import { useEffect, useRef } from "react";
import type { ModuleResult, AuditResponse, RunAuditResponse } from "@/lib/types";
import { CompactSummary } from "@/components/prism/compact-summary";
import { AuditLaunchedCard } from "./audit-launched-card";
import { usePrismStore, TOOL_TO_MODULE } from "@/lib/store";

// ── Helper: loading indicator shown while a tool is running ──
function ToolLoading({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: React.ReactNode;
}) {
  return (
    <div className="my-2 flex items-center gap-2 text-sm text-[var(--muted-text)]">
      {icon}
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      <span>{label}</span>
    </div>
  );
}

// ── Helper: error card shown when a tool call fails ──
function ToolErrorCard({ message }: { message: string }) {
  return (
    <Card className="my-2 border-destructive/30 bg-destructive/5">
      <CardContent className="py-3 text-sm text-destructive">
        {message}
      </CardContent>
    </Card>
  );
}

// ── Helper: detect AI SDK error results ──
// When a tool throws, assistant-ui may set result = { error: "..." } with
// status.type still "complete" (message-level), so status checks alone are
// insufficient. This helper checks the result shape directly.
function isToolError(result: unknown): result is { error: string } {
  return (
    result != null &&
    typeof result === "object" &&
    "error" in result &&
    !("module_name" in result) &&
    !("audit" in result)
  );
}

function getToolErrorMessage(result: unknown, fallback: string): string {
  if (isToolError(result)) {
    return typeof result.error === "string"
      ? result.error
      : fallback;
  }
  return fallback;
}

// ── Helper: validate that a result looks like a ModuleResult ──
function isModuleResult(result: unknown): result is ModuleResult {
  return (
    result != null &&
    typeof result === "object" &&
    "module_name" in result &&
    "status" in result
  );
}

// ── Helper: renders CompactSummary and adds result to store ──
function CompactResultRenderer({
  toolName,
  result,
}: {
  toolName: string;
  result: ModuleResult;
}) {
  const moduleName = TOOL_TO_MODULE[toolName] ?? toolName;
  const viewModuleDetails = usePrismStore((s) => s.viewModuleDetails);
  const addResult = usePrismStore((s) => s.addResult);
  const addedRef = useRef(false);

  // Add result to the store ONCE via useEffect (not during render)
  useEffect(() => {
    if (!addedRef.current) {
      addResult(moduleName, result);
      addedRef.current = true;
    }
  }, [moduleName, result, addResult]);

  return (
    <CompactSummary
      moduleName={moduleName}
      toolName={toolName}
      data={result}
      onViewDetails={() => viewModuleDetails(toolName, result)}
    />
  );
}

// ── Helper: standard module tool render function ──
// Centralised render logic for all module tools. Handles running, incomplete,
// error results, and invalid result shapes in a single place.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function createModuleToolRender(
  toolName: string,
  icon: React.ReactNode,
  labelFn: (domain: string) => React.ReactNode,
  errorPrefix: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): any {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (props: any) => {
    const { args, result, status } = props;
    const domain = (args?.domain as string) ?? "unknown";
    if (status?.type === "running") {
      return <ToolLoading icon={icon} label={labelFn(domain)} />;
    }
    if (status?.type === "incomplete") {
      return <ToolErrorCard message={`${errorPrefix} ${domain}.`} />;
    }
    if (result) {
      if (isToolError(result)) {
        return <ToolErrorCard message={getToolErrorMessage(result, `${errorPrefix} ${domain}.`)} />;
      }
      if (!isModuleResult(result)) {
        return <ToolErrorCard message={`${errorPrefix} ${domain} — unexpected response format.`} />;
      }
      return <CompactResultRenderer toolName={toolName} result={result} />;
    }
    return null;
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// WAVE 1 — Intelligence modules (13 tools)
// ═══════════════════════════════════════════════════════════════════════════════

/** get_company_profile */
export const GetCompanyProfileToolUI = makeAssistantToolUI({
  toolName: "get_company_profile",
  render: createModuleToolRender(
    "get_company_profile",
    <Building className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Researching <strong>{d}</strong>...</>,
    "Failed to fetch company profile for",
  ),
});

/** get_tech_stack */
export const GetTechStackToolUI = makeAssistantToolUI({
  toolName: "get_tech_stack",
  render: createModuleToolRender(
    "get_tech_stack",
    <Search className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Analyzing tech stack for <strong>{d}</strong>...</>,
    "Failed to fetch tech stack for",
  ),
});

/** get_traffic_analysis */
export const GetTrafficAnalysisToolUI = makeAssistantToolUI({
  toolName: "get_traffic_analysis",
  render: createModuleToolRender(
    "get_traffic_analysis",
    <Globe className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Analyzing traffic for <strong>{d}</strong>...</>,
    "Failed to fetch traffic data for",
  ),
});

/** get_financial_data */
export const GetFinancialDataToolUI = makeAssistantToolUI({
  toolName: "get_financial_data",
  render: createModuleToolRender(
    "get_financial_data",
    <DollarSign className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Pulling financials for <strong>{d}</strong>...</>,
    "Failed to fetch financial data for",
  ),
});

/** get_private_financials */
export const GetPrivateFinancialsToolUI = makeAssistantToolUI({
  toolName: "get_private_financials",
  render: createModuleToolRender(
    "get_private_financials",
    <DollarSign className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Estimating financials for <strong>{d}</strong>...</>,
    "Failed to estimate financials for",
  ),
});

/** get_company_news */
export const GetCompanyNewsToolUI = makeAssistantToolUI({
  toolName: "get_company_news",
  render: createModuleToolRender(
    "get_company_news",
    <Newspaper className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Scanning news for <strong>{d}</strong>...</>,
    "Failed to fetch news for",
  ),
});

/** get_hiring_intel */
export const GetHiringIntelToolUI = makeAssistantToolUI({
  toolName: "get_hiring_intel",
  render: createModuleToolRender(
    "get_hiring_intel",
    <Users className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Analyzing hiring signals for <strong>{d}</strong>...</>,
    "Failed to fetch hiring data for",
  ),
});

/** get_social_intel */
export const GetSocialIntelToolUI = makeAssistantToolUI({
  toolName: "get_social_intel",
  render: createModuleToolRender(
    "get_social_intel",
    <Share2 className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Collecting social signals for <strong>{d}</strong>...</>,
    "Failed to fetch social data for",
  ),
});

/** get_investor_intel */
export const GetInvestorIntelToolUI = makeAssistantToolUI({
  toolName: "get_investor_intel",
  render: createModuleToolRender(
    "get_investor_intel",
    <TrendingUp className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Mining investor intelligence for <strong>{d}</strong>...</>,
    "Failed to fetch investor data for",
  ),
});

/** get_partner_intel */
export const GetPartnerIntelToolUI = makeAssistantToolUI({
  toolName: "get_partner_intel",
  render: createModuleToolRender(
    "get_partner_intel",
    <Handshake className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Mapping partner ecosystem for <strong>{d}</strong>...</>,
    "Failed to fetch partner data for",
  ),
});

/** get_industry_benchmarks */
export const GetIndustryBenchmarksToolUI = makeAssistantToolUI({
  toolName: "get_industry_benchmarks",
  render: createModuleToolRender(
    "get_industry_benchmarks",
    <BarChart3 className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Collecting industry benchmarks for <strong>{d}</strong>...</>,
    "Failed to fetch industry benchmarks for",
  ),
});

/** get_competitor_matrix */
export const GetCompetitorMatrixToolUI = makeAssistantToolUI({
  toolName: "get_competitor_matrix",
  render: createModuleToolRender(
    "get_competitor_matrix",
    <Swords className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Building competitor matrix for <strong>{d}</strong>...</>,
    "Failed to build competitor matrix for",
  ),
});

/** get_test_queries */
export const GetTestQueriesToolUI = makeAssistantToolUI({
  toolName: "get_test_queries",
  render: createModuleToolRender(
    "get_test_queries",
    <ListChecks className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Generating test queries for <strong>{d}</strong>...</>,
    "Failed to generate test queries for",
  ),
});

// ═══════════════════════════════════════════════════════════════════════════════
// WAVE 2 — Experience Audit (1 tool)
// ═══════════════════════════════════════════════════════════════════════════════

/** get_browser_audit */
export const GetBrowserAuditToolUI = makeAssistantToolUI({
  toolName: "get_browser_audit",
  render: createModuleToolRender(
    "get_browser_audit",
    <Monitor className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Running browser audit on <strong>{d}</strong>...</>,
    "Browser audit failed for",
  ),
});

// ═══════════════════════════════════════════════════════════════════════════════
// WAVE 3 — Synthesis (3 tools)
// ═══════════════════════════════════════════════════════════════════════════════

/** get_business_case */
export const GetBusinessCaseToolUI = makeAssistantToolUI({
  toolName: "get_business_case",
  render: createModuleToolRender(
    "get_business_case",
    <Briefcase className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Building business case for <strong>{d}</strong>...</>,
    "Failed to build business case for",
  ),
});

/** get_sales_plays */
export const GetSalesPlaysToolUI = makeAssistantToolUI({
  toolName: "get_sales_plays",
  render: createModuleToolRender(
    "get_sales_plays",
    <Target className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Generating sales plays for <strong>{d}</strong>...</>,
    "Failed to generate sales plays for",
  ),
});

/** get_audit_report */
export const GetAuditReportToolUI = makeAssistantToolUI({
  toolName: "get_audit_report",
  render: createModuleToolRender(
    "get_audit_report",
    <FileText className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Compiling audit report for <strong>{d}</strong>...</>,
    "Failed to compile audit report for",
  ),
});

// ═══════════════════════════════════════════════════════════════════════════════
// WAVE 4 — Activation (1 tool)
// ═══════════════════════════════════════════════════════════════════════════════

/** get_abx_campaign */
export const GetAbxCampaignToolUI = makeAssistantToolUI({
  toolName: "get_abx_campaign",
  render: createModuleToolRender(
    "get_abx_campaign",
    <Megaphone className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Creating ABX campaign for <strong>{d}</strong>...</>,
    "Failed to create ABX campaign for",
  ),
});

// ═══════════════════════════════════════════════════════════════════════════════
// WAVE 5 — Quality Gate (1 tool)
// ═══════════════════════════════════════════════════════════════════════════════

/** get_factcheck_verdict */
export const GetFactcheckVerdictToolUI = makeAssistantToolUI({
  toolName: "get_factcheck_verdict",
  render: createModuleToolRender(
    "get_factcheck_verdict",
    <ShieldCheck className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Fact-checking audit for <strong>{d}</strong>...</>,
    "Fact-check failed for",
  ),
});

// ═══════════════════════════════════════════════════════════════════════════════
// WAVE 6 — Benchmarking (1 tool)
// ═══════════════════════════════════════════════════════════════════════════════

/** get_vertical_benchmarks */
export const GetVerticalBenchmarksToolUI = makeAssistantToolUI({
  toolName: "get_vertical_benchmarks",
  render: createModuleToolRender(
    "get_vertical_benchmarks",
    <LineChart className="h-4 w-4 text-[var(--accent-warm)]" />,
    (d) => <>Computing vertical benchmarks for <strong>{d}</strong>...</>,
    "Failed to compute benchmarks for",
  ),
});

// ═══════════════════════════════════════════════════════════════════════════════
// Orchestration tools (run_full_audit, get_audit_status) — keep original cards
// ═══════════════════════════════════════════════════════════════════════════════

/** run_full_audit — 3D tilt company card + thinking stream */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const RunFullAuditToolUI = makeAssistantToolUI({
  toolName: "run_full_audit",
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  render: (props: any) => {
    const { args, result, status } = props;
    if (status.type === "running") {
      return (
        <ToolLoading
          icon={<Search className="h-4 w-4 text-[#003DFF]" />}
          label={
            <>
              Starting audit for <strong>{args.company_name}</strong> ({args.domain})...
            </>
          }
        />
      );
    }
    if (status.type === "incomplete") {
      return <ToolErrorCard message={`Failed to start audit for ${args.domain}.`} />;
    }
    if (result) {
      // Guard: when a tool throws, assistant-ui may set result = { error: "..." }
      // with status.type still "complete" (message-level). Catch this case.
      if (isToolError(result)) {
        return <ToolErrorCard message={getToolErrorMessage(result, `Failed to start audit for ${args.domain}.`)} />;
      }
      const typed = result as Record<string, unknown>;
      const audit = typed.audit as AuditResponse | undefined;
      const workflow = typed.workflow as RunAuditResponse | undefined;
      const auditMode = (typed.audit_mode as string) ?? "full";
      if (!audit?.id || !workflow?.workflow_id) {
        return <ToolErrorCard message={`Audit launched for ${args.domain} but response was incomplete.`} />;
      }
      return (
        <AuditLaunchedCard
          audit={audit}
          workflow={workflow}
          auditMode={auditMode}
        />
      );
    }
    return null;
  },
});

/** get_audit_status — minimal inline status (thinking stream shows progress) */
export const GetAuditStatusToolUI = makeAssistantToolUI<
  { audit_id: string },
  AuditResponse
>({
  toolName: "get_audit_status",
  render: ({ status }) => {
    if (status.type === "running") {
      return (
        <div className="my-1 flex items-center gap-2 text-xs text-[var(--muted-text)]">
          <Loader2 className="h-3 w-3 animate-spin" />
          Checking status...
        </div>
      );
    }
    return null;
  },
});
