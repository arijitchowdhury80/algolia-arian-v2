"use client";

import { useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useAISDKRuntime } from "@assistant-ui/react-ai-sdk";
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { Thread } from "@/components/assistant-ui/thread";
import { usePrismStore } from "@/lib/store";
import {
  // Wave 1 — Intelligence
  GetCompanyProfileToolUI,
  GetTechStackToolUI,
  GetTrafficAnalysisToolUI,
  GetFinancialDataToolUI,
  GetPrivateFinancialsToolUI,
  GetCompanyNewsToolUI,
  GetHiringIntelToolUI,
  GetSocialIntelToolUI,
  GetInvestorIntelToolUI,
  GetPartnerIntelToolUI,
  GetIndustryBenchmarksToolUI,
  GetCompetitorMatrixToolUI,
  GetTestQueriesToolUI,
  // Wave 2 — Experience Audit
  GetBrowserAuditToolUI,
  // Wave 3 — Synthesis
  GetBusinessCaseToolUI,
  GetSalesPlaysToolUI,
  GetAuditReportToolUI,
  // Wave 4 — Activation
  GetAbxCampaignToolUI,
  // Wave 5 — Quality Gate
  GetFactcheckVerdictToolUI,
  // Wave 6 — Benchmarking
  GetVerticalBenchmarksToolUI,
  // Orchestration
  RunFullAuditToolUI,
  GetAuditStatusToolUI,
} from "./tool-renderers";

/**
 * PrismChat — AI-native chat interface for prospect intelligence.
 *
 * Now rendered in the right panel (340px). Bridges the AI SDK useChat
 * hook with assistant-ui's Thread component via useAISDKRuntime.
 * Tool renderers are registered as children of the AssistantRuntimeProvider.
 */
export function PrismChat() {
  // W-D: one brain = Hermes. Chat streams grounded report-QA from /api/hermes
  // (server-side proxy → Hermes /v1/responses). `domain` is read fresh per turn
  // so the report-QA plugin binds the account currently in view.
  const chat = useChat({
    id: "prism-chat",
    transport: new DefaultChatTransport({
      api: "/api/hermes",
      body: () => ({ domain: usePrismStore.getState().currentDomain }),
    }),
  });
  const runtime = useAISDKRuntime(chat);

  // Expose the chat sendMessage function so other components can trigger messages
  useEffect(() => {
    usePrismStore.getState().setSendChatMessage((text: string) => {
      chat.sendMessage({ text });
    });
  }, [chat]);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {/* Wave 1 — Intelligence (13 modules) */}
      <GetCompanyProfileToolUI />
      <GetTechStackToolUI />
      <GetTrafficAnalysisToolUI />
      <GetFinancialDataToolUI />
      <GetPrivateFinancialsToolUI />
      <GetCompanyNewsToolUI />
      <GetHiringIntelToolUI />
      <GetSocialIntelToolUI />
      <GetInvestorIntelToolUI />
      <GetPartnerIntelToolUI />
      <GetIndustryBenchmarksToolUI />
      <GetCompetitorMatrixToolUI />
      <GetTestQueriesToolUI />

      {/* Wave 2 — Experience Audit */}
      <GetBrowserAuditToolUI />

      {/* Wave 3 — Synthesis */}
      <GetBusinessCaseToolUI />
      <GetSalesPlaysToolUI />
      <GetAuditReportToolUI />

      {/* Wave 4 — Activation */}
      <GetAbxCampaignToolUI />

      {/* Wave 5 — Quality Gate */}
      <GetFactcheckVerdictToolUI />

      {/* Wave 6 — Benchmarking */}
      <GetVerticalBenchmarksToolUI />

      {/* Orchestration */}
      <RunFullAuditToolUI />
      <GetAuditStatusToolUI />

      {/* Chat thread */}
      <div className="flex h-full flex-col">
        <Thread />
      </div>
    </AssistantRuntimeProvider>
  );
}
