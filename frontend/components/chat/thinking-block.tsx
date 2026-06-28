"use client";

import { useState } from "react";
import { Check, Loader2, X, ChevronDown, ChevronRight } from "lucide-react";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

/** A single step in the thinking/execution process. */
interface ThinkingStep {
  /** Human-readable label, e.g. "Calling BuiltWith API" */
  label: string;
  /** Optional detail line, e.g. "GET https://api.builtwith.com/v21/..." */
  detail?: string;
  /** Current status of this step */
  status: "running" | "complete" | "error";
  /** Duration in milliseconds, shown when complete */
  duration_ms?: number;
  /** ISO timestamp of when the step was recorded */
  timestamp: string;
}

interface ThinkingBlockProps {
  /** Internal tool name, mapped to a human-readable display name */
  toolName: string;
  /** Domain being analyzed, e.g. "dell.com" */
  domain?: string;
  /** Ordered list of execution steps */
  steps?: ThinkingStep[];
  /** Whether the entire thinking block is finished */
  isComplete?: boolean;
  /** Total execution time in milliseconds */
  totalDuration?: number;
  /** Error message if the block-level execution failed */
  error?: string;
}

/** Maps internal tool names to user-facing display names. */
const TOOL_DISPLAY_NAMES: Record<string, string> = {
  get_company_profile: "Company Profile",
  get_tech_stack: "Technology Analysis",
  get_traffic_analysis: "Traffic Analysis",
  get_financial_data: "Public Financials",
  get_private_financials: "Private Financials",
  get_company_news: "Company News",
  get_hiring_intel: "Hiring Intelligence",
  get_social_intel: "Social Intelligence",
  get_investor_intel: "Investor Intelligence",
  get_partner_intel: "Partner Ecosystem",
  get_industry_benchmarks: "Industry Benchmarks",
  get_competitor_matrix: "Competitor Matrix",
  get_test_queries: "Test Queries",
  run_full_audit: "Full Intelligence Audit",
  get_audit_status: "Audit Status Check",
  get_browser_audit: "Browser Audit",
  get_factcheck_verdict: "Factcheck Gate",
  get_business_case: "Business Case",
  get_sales_plays: "Sales Plays",
  get_audit_report: "Audit Report",
  get_abx_campaign: "ABX Campaign",
  get_vertical_benchmarks: "Vertical Benchmarks",
  find_customer_evidence: "Customer Evidence Match",
  find_case_studies: "Case Studies",
  find_customer_quotes: "Customer Quotes",
};

/**
 * Formats a duration in milliseconds to a human-readable string.
 * Uses "ms" for values under 1000, "s" with one decimal for larger values.
 */
function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Returns the human-readable display name for a tool.
 * Falls back to a title-cased version of the tool name if not mapped.
 */
function getToolDisplayName(toolName: string): string {
  if (toolName in TOOL_DISPLAY_NAMES) {
    return TOOL_DISPLAY_NAMES[toolName];
  }
  // Fallback: convert snake_case to Title Case
  return toolName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/** Renders the icon for a single step based on its status. */
function StepIcon({ status }: { status: ThinkingStep["status"] }) {
  switch (status) {
    case "complete":
      return (
        <Check
          className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
          aria-hidden="true"
        />
      );
    case "running":
      return (
        <Loader2
          className="size-3.5 shrink-0 animate-spin text-[#003DFF]"
          aria-hidden="true"
        />
      );
    case "error":
      return (
        <X
          className="size-3.5 shrink-0 text-red-600 dark:text-red-400"
          aria-hidden="true"
        />
      );
  }
}

/**
 * ThinkingBlock — a collapsible execution transparency component.
 *
 * Shows what Prism is doing behind the scenes during tool execution.
 * Displays a summary line when collapsed and step-by-step progress when expanded.
 * Supports running, complete, and error states with appropriate visual treatment.
 */
export function ThinkingBlock({
  toolName,
  domain,
  steps = [],
  isComplete = false,
  totalDuration,
  error,
}: ThinkingBlockProps) {
  const [isOpen, setIsOpen] = useState(false);

  const displayName = getToolDisplayName(toolName);
  const hasError = Boolean(error);
  const isRunning = !isComplete && !hasError;

  // Build the summary line shown in the trigger
  function renderSummary(): string {
    if (hasError) {
      return `Analysis failed${error ? ` \u2014 ${error}` : ""}`;
    }
    if (isComplete) {
      const durationStr = totalDuration
        ? ` \u2014 ${formatDuration(totalDuration)}`
        : "";
      return `${displayName} complete${durationStr}`;
    }
    const target = domain ? ` ${domain}` : "";
    return `Analyzing${target}...`;
  }

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn(
        "my-2 w-full max-w-3xl rounded-lg border",
        "bg-[#F5F5F7] dark:bg-[#1E1E22]",
        "border-gray-200 dark:border-gray-700",
        hasError && "border-red-300 dark:border-red-700"
      )}
    >
      <CollapsibleTrigger
        className={cn(
          "flex w-full cursor-pointer items-center gap-2 px-3 py-2.5",
          "text-sm text-[#23263B] dark:text-gray-200",
          "rounded-lg transition-colors",
          "hover:bg-gray-100 dark:hover:bg-gray-800/50",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#003DFF]/50"
        )}
        aria-label={
          isOpen
            ? `Collapse ${displayName} details`
            : `Expand ${displayName} details`
        }
      >
        {/* Expand/collapse chevron */}
        {isOpen ? (
          <ChevronDown className="size-4 shrink-0 text-gray-500" aria-hidden="true" />
        ) : (
          <ChevronRight className="size-4 shrink-0 text-gray-500" aria-hidden="true" />
        )}

        {/* Status icon */}
        {hasError ? (
          <X className="size-4 shrink-0 text-red-600 dark:text-red-400" aria-hidden="true" />
        ) : isComplete ? (
          <Check className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
        ) : (
          <Loader2
            className="size-4 shrink-0 animate-spin text-[#003DFF]"
            aria-hidden="true"
          />
        )}

        {/* Summary text */}
        <span
          className={cn(
            "flex-1 text-left font-medium",
            hasError && "text-red-700 dark:text-red-400",
            isRunning && "animate-pulse"
          )}
        >
          {renderSummary()}
        </span>

        {/* Duration badge (shown in completed state) */}
        {isComplete && totalDuration != null && (
          <span className="shrink-0 rounded-full bg-gray-200 px-2 py-0.5 font-mono text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400">
            {formatDuration(totalDuration)}
          </span>
        )}
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="border-t border-gray-200 px-3 py-2 dark:border-gray-700">
          {steps.length === 0 && isRunning && (
            <div className="flex items-center gap-2 py-1 text-sm text-gray-500">
              <Loader2 className="size-3.5 animate-spin text-[#003DFF]" aria-hidden="true" />
              <span className="font-mono">Initializing...</span>
            </div>
          )}

          <ul className="space-y-1" role="list" aria-label={`${displayName} steps`}>
            {steps.map((step, index) => (
              <li key={`${step.timestamp}-${index}`} className="flex items-start gap-2 py-0.5">
                <div className="mt-0.5">
                  <StepIcon status={step.status} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span
                      className={cn(
                        "text-sm",
                        step.status === "error"
                          ? "text-red-700 dark:text-red-400"
                          : "text-[#23263B] dark:text-gray-200"
                      )}
                    >
                      {step.label}
                    </span>
                    {step.duration_ms != null && (
                      <span className="shrink-0 font-mono text-xs text-gray-400 dark:text-gray-500">
                        {formatDuration(step.duration_ms)}
                      </span>
                    )}
                  </div>
                  {step.detail && (
                    <p className="truncate font-mono text-xs text-gray-400 dark:text-gray-500">
                      {step.detail}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>

          {/* Error detail at the bottom of expanded view */}
          {hasError && error && (
            <div className="mt-2 rounded-md bg-red-50 px-2 py-1.5 font-mono text-xs text-red-700 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export type { ThinkingStep, ThinkingBlockProps };
