"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { usePrismStore } from "@/lib/store";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  Copy,
  Check,
  Sparkles,
  Mail,
  Video,
  UserCircle,
} from "lucide-react";
import type {
  ModuleResult,
  MEDDPICCItem,
  SPINQuestion,
  ObjectionHandler,
  PowerMapPerson,
  EmailStep,
  LinkedInMessage,
  BuyingCommitteeMember,
} from "@/lib/types";

/* ── Props ── */

interface TabProps {
  results: Record<string, ModuleResult>;
}

/* ── Helpers ── */

function getOutput(
  results: Record<string, ModuleResult>,
  moduleName: string,
): Record<string, unknown> | undefined {
  return results[moduleName]?.output as Record<string, unknown> | undefined;
}

/* ── Section wrapper with scroll-to and flash highlight ── */

function Section({
  id,
  highlightedSection,
  children,
}: {
  id: string;
  highlightedSection: string | null;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const activeSection = usePrismStore((s) => s.activeSection);

  useEffect(() => {
    if (activeSection === id && ref.current) {
      ref.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [activeSection, id]);

  return (
    <div
      ref={ref}
      id={id}
      className={cn(
        "mb-10 transition-all duration-700",
        highlightedSection === id &&
          "ring-2 ring-[#003DFF]/30 rounded-2xl ring-offset-4 ring-offset-[#F8F9FB]",
      )}
    >
      {children}
    </div>
  );
}

/* ── Empty state ── */

function EmptyState({ message }: { message: string }) {
  return (
    <div
      className="rounded-xl border border-dashed border-[#E5E7EB] px-6 py-10 text-center"
      style={{ background: "rgba(255,255,255,0.6)" }}
    >
      <p className="text-sm text-[#6B7280]">{message}</p>
    </div>
  );
}

/* ── Glassmorphism card wrapper ── */

function GlassCard({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn("rounded-2xl p-6", className)}
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: "20px",
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
      }}
    >
      {children}
    </div>
  );
}

/* ── Copy button component ── */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error("[SalesActionsTab] Failed to copy text:", err);
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="ml-2 inline-flex items-center justify-center rounded p-1 text-[#6B7280] hover:text-[#003DFF] hover:bg-[#003DFF]/5 transition-colors"
      aria-label="Copy to clipboard"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-green-600" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

/* ── LinkedIn SVG icon ── */

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

/* ── MEDDPICC letter badge color mapping ── */

const MEDDPICC_COLORS: Record<string, string> = {
  M: "#003DFF",
  E: "#5468FF",
  D: "#7C3AED",
  P: "#059669",
  I: "#D97706",
  C: "#DC2626",
};

function getMeddpiccColor(letter: string): string {
  return MEDDPICC_COLORS[letter.toUpperCase()] ?? "#6B7280";
}

/* ── SPIN category config ── */

const SPIN_CONFIG: Record<
  string,
  { label: string; color: string; bgColor: string }
> = {
  situation: { label: "Situation", color: "#6B7280", bgColor: "rgba(107,114,128,0.08)" },
  problem: { label: "Problem", color: "#DC2626", bgColor: "rgba(220,38,38,0.08)" },
  implication: { label: "Implication", color: "#D97706", bgColor: "rgba(217,119,6,0.08)" },
  need_payoff: { label: "Need-Payoff", color: "#059669", bgColor: "rgba(5,150,105,0.08)" },
};

/* ── Attitude badge config ── */

const ATTITUDE_CONFIG: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  champion: { bg: "rgba(5,150,105,0.12)", text: "#059669", label: "Champion" },
  supportive: { bg: "rgba(59,130,246,0.12)", text: "#3B82F6", label: "Supportive" },
  neutral: { bg: "rgba(107,114,128,0.12)", text: "#6B7280", label: "Neutral" },
  skeptical: { bg: "rgba(217,119,6,0.12)", text: "#D97706", label: "Skeptical" },
  blocker: { bg: "rgba(220,38,38,0.12)", text: "#DC2626", label: "Blocker" },
  unknown: { bg: "rgba(107,114,128,0.08)", text: "#9CA3AF", label: "Unknown" },
};

function getAttitudeConfig(attitude: string): { bg: string; text: string; label: string } {
  return (
    ATTITUDE_CONFIG[attitude.toLowerCase()] ??
    ATTITUDE_CONFIG["unknown"]
  );
}

/* ── Email step labels ── */

const STEP_LABELS = ["Hook", "Insight", "Proof", "ROI", "Ask"] as const;

/* ══════════════════════════════════════════════════════════════
   6.1 MEDDPICC Section
   ══════════════════════════════════════════════════════════════ */

function MEDDPICCSection({
  items,
  highlightedSection,
}: {
  items: MEDDPICCItem[];
  highlightedSection: string | null;
}) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <Section id="meddpicc" highlightedSection={highlightedSection}>
      <p className="text-sm font-bold uppercase tracking-wide text-[#003DFF] mb-1">
        MEDDPICC
      </p>
      <h2 className="text-[1.75rem] font-semibold text-[#23263B] mb-4">
        Qualification Framework
      </h2>

      {items.length === 0 ? (
        <EmptyState message="Run sales plays to populate MEDDPICC" />
      ) : (
        <GlassCard className="p-0 overflow-hidden">
          {items.map((item, idx) => {
            const isOpen = openIndex === idx;
            const color = getMeddpiccColor(item.letter);
            const hasData =
              item.person.trim() !== "" ||
              item.evidence.trim() !== "" ||
              item.approach.trim() !== "";

            return (
              <div
                key={`${item.letter}-${idx}`}
                style={{
                  borderBottom:
                    idx < items.length - 1 ? "1px solid #E5E7EB" : "none",
                }}
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : idx)}
                  className="flex items-center gap-3 w-full px-5 py-4 text-left hover:bg-[#F8F9FB]/60 transition-colors"
                >
                  {/* Letter badge */}
                  <span
                    className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full text-white text-xs font-bold"
                    style={{ background: color }}
                  >
                    {item.letter}
                  </span>

                  {/* Name */}
                  <span className="flex-1 text-sm font-medium text-[#23263B]">
                    {item.name}
                  </span>

                  {/* Status indicator */}
                  {!hasData && (
                    <span className="text-xs italic text-[#9CA3AF]">
                      Not yet identified
                    </span>
                  )}

                  {/* Chevron */}
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 text-[#6B7280] transition-transform duration-200",
                      isOpen && "rotate-180",
                    )}
                  />
                </button>

                {isOpen && (
                  <div className="px-5 pb-4 pt-0 ml-11 space-y-2">
                    {hasData ? (
                      <>
                        {item.person.trim() !== "" && (
                          <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                              Person
                            </span>
                            <p className="text-sm text-[#23263B] mt-0.5">
                              {item.person}
                            </p>
                          </div>
                        )}
                        {item.evidence.trim() !== "" && (
                          <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                              Evidence
                            </span>
                            <p className="text-sm text-[#23263B] mt-0.5">
                              {item.evidence}
                            </p>
                          </div>
                        )}
                        {item.approach.trim() !== "" && (
                          <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                              Approach
                            </span>
                            <p className="text-sm text-[#23263B] mt-0.5">
                              {item.approach}
                            </p>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-sm italic text-[#9CA3AF]">
                        Not yet identified -- run sales plays to populate this field.
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </GlassCard>
      )}
    </Section>
  );
}

/* ══════════════════════════════════════════════════════════════
   6.2 SPIN Questions Section
   ══════════════════════════════════════════════════════════════ */

function SPINQuestionsSection({
  questions,
  highlightedSection,
}: {
  questions: SPINQuestion[];
  highlightedSection: string | null;
}) {
  const grouped: Record<string, SPINQuestion[]> = {
    situation: [],
    problem: [],
    implication: [],
    need_payoff: [],
  };

  for (const q of questions) {
    if (grouped[q.category]) {
      grouped[q.category].push(q);
    }
  }

  const categories = ["situation", "problem", "implication", "need_payoff"] as const;

  return (
    <Section id="spin-questions" highlightedSection={highlightedSection}>
      <p className="text-sm font-bold uppercase tracking-wide text-[#003DFF] mb-1">
        SPIN Questions
      </p>
      <h2 className="text-[1.75rem] font-semibold text-[#23263B] mb-4">
        Discovery Questions
      </h2>

      {questions.length === 0 ? (
        <EmptyState message="Run sales plays to generate SPIN questions" />
      ) : (
        <div className="space-y-4">
          {categories.map((cat) => {
            const config = SPIN_CONFIG[cat];
            const catQuestions = grouped[cat];
            if (catQuestions.length === 0) return null;

            return (
              <GlassCard key={cat} className="p-0 overflow-hidden">
                {/* Category header */}
                <div
                  className="px-5 py-3 flex items-center gap-2"
                  style={{ background: config.bgColor }}
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ background: config.color }}
                  />
                  <span
                    className="text-sm font-semibold uppercase tracking-wider"
                    style={{ color: config.color }}
                  >
                    {config.label}
                  </span>
                  <span className="text-xs text-[#9CA3AF] ml-auto">
                    {catQuestions.length} question{catQuestions.length !== 1 ? "s" : ""}
                  </span>
                </div>

                {/* Questions */}
                <div className="divide-y divide-[#E5E7EB]">
                  {catQuestions.map((q, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2 px-5 py-3 group"
                    >
                      <p className="flex-1 text-sm text-[#23263B] leading-relaxed">
                        {q.question}
                      </p>
                      <CopyButton text={q.question} />
                    </div>
                  ))}
                </div>
              </GlassCard>
            );
          })}
        </div>
      )}
    </Section>
  );
}

/* ══════════════════════════════════════════════════════════════
   6.3 Objection Handling Section
   ══════════════════════════════════════════════════════════════ */

function ObjectionHandlingSection({
  handlers,
  highlightedSection,
}: {
  handlers: ObjectionHandler[];
  highlightedSection: string | null;
}) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <Section id="objection-handling" highlightedSection={highlightedSection}>
      <p className="text-sm font-bold uppercase tracking-wide text-[#003DFF] mb-1">
        Objection Handling
      </p>
      <h2 className="text-[1.75rem] font-semibold text-[#23263B] mb-4">
        Common Objections
      </h2>

      {handlers.length === 0 ? (
        <EmptyState message="Run sales plays to generate objection handlers" />
      ) : (
        <div className="space-y-3">
          {handlers.map((handler, idx) => {
            const isOpen = openIndex === idx;

            return (
              <GlassCard key={idx} className="p-0 overflow-hidden">
                <button
                  onClick={() => setOpenIndex(isOpen ? null : idx)}
                  className="flex items-center gap-3 w-full px-5 py-4 text-left hover:bg-[#F8F9FB]/60 transition-colors"
                >
                  <span
                    className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                    style={{
                      background: "rgba(220,38,38,0.1)",
                    }}
                  >
                    <span className="text-xs font-bold text-[#DC2626]">!</span>
                  </span>
                  <span className="flex-1 text-sm font-medium text-[#23263B]">
                    {handler.objection}
                  </span>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 text-[#6B7280] transition-transform duration-200",
                      isOpen && "rotate-180",
                    )}
                  />
                </button>

                {isOpen && (
                  <div className="px-5 pb-4 pt-0 ml-9 space-y-3 border-t border-[#E5E7EB] pt-3 mx-5">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-[#059669]">
                        Counter
                      </span>
                      <p className="text-sm text-[#23263B] mt-0.5 leading-relaxed">
                        {handler.counter}
                      </p>
                    </div>
                    {handler.evidence.trim() !== "" && (
                      <div>
                        <span className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                          Evidence
                        </span>
                        <p className="text-sm text-[#23263B] mt-0.5 leading-relaxed">
                          {handler.evidence}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </GlassCard>
            );
          })}
        </div>
      )}
    </Section>
  );
}

/* ══════════════════════════════════════════════════════════════
   6.4 Buying Committee Section
   ══════════════════════════════════════════════════════════════ */

function BuyingCommitteeSection({
  powerMap,
  buyingCommittee,
  highlightedSection,
}: {
  powerMap: PowerMapPerson[];
  buyingCommittee: BuyingCommitteeMember[];
  highlightedSection: string | null;
}) {
  /* Merge power map and buying committee into a unified list */
  const combinedRows: {
    name: string;
    title: string;
    attitude: string;
    approach: string;
  }[] = [];

  for (const pm of powerMap) {
    combinedRows.push({
      name: pm.person,
      title: pm.title,
      attitude: pm.attitude,
      approach: pm.approach,
    });
  }

  /* Add buying committee members that are not already in the power map */
  const powerMapNames = new Set(powerMap.map((p) => p.person.toLowerCase()));
  for (const bc of buyingCommittee) {
    if (!powerMapNames.has(bc.name.toLowerCase())) {
      combinedRows.push({
        name: bc.name,
        title: bc.title,
        attitude: "unknown",
        approach: bc.approach,
      });
    }
  }

  return (
    <Section id="buying-committee" highlightedSection={highlightedSection}>
      <p className="text-sm font-bold uppercase tracking-wide text-[#003DFF] mb-1">
        Buying Committee
      </p>
      <h2 className="text-[1.75rem] font-semibold text-[#23263B] mb-4">
        Power Map
      </h2>

      {combinedRows.length === 0 ? (
        <EmptyState message="Run sales plays or hiring intel to map the buying committee" />
      ) : (
        <GlassCard className="p-0 overflow-hidden">
          {/* Table header */}
          <div
            className="grid gap-3 px-5 py-3 text-xs font-semibold uppercase tracking-wider text-[#6B7280]"
            style={{
              gridTemplateColumns: "1.2fr 1.5fr 100px 2fr",
              background: "#F8F9FB",
              borderBottom: "1px solid #E5E7EB",
            }}
          >
            <span>Name</span>
            <span>Title</span>
            <span>Attitude</span>
            <span>Approach</span>
          </div>

          {/* Table rows */}
          {combinedRows.map((row, idx) => {
            const attCfg = getAttitudeConfig(row.attitude);
            const isEven = idx % 2 === 0;

            return (
              <div
                key={`${row.name}-${idx}`}
                className="grid items-center gap-3 px-5 py-3"
                style={{
                  gridTemplateColumns: "1.2fr 1.5fr 100px 2fr",
                  background: isEven ? "white" : "#F8F9FB",
                  borderBottom:
                    idx < combinedRows.length - 1
                      ? "1px solid #E5E7EB"
                      : "none",
                }}
              >
                <span className="text-sm font-medium text-[#23263B] flex items-center gap-2">
                  <UserCircle className="h-4 w-4 text-[#6B7280]" />
                  {row.name}
                </span>
                <span className="text-sm text-[#6B7280]">{row.title}</span>
                <span
                  className={cn(
                    "inline-flex items-center justify-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase",
                    row.attitude === "unknown" && "border border-dashed border-[#9CA3AF]",
                  )}
                  style={{
                    background: attCfg.bg,
                    color: attCfg.text,
                  }}
                >
                  {attCfg.label}
                </span>
                <span className="text-sm text-[#23263B] leading-relaxed">
                  {row.approach}
                </span>
              </div>
            );
          })}
        </GlassCard>
      )}
    </Section>
  );
}

/* ══════════════════════════════════════════════════════════════
   6.5 Outreach Sequence Section
   ══════════════════════════════════════════════════════════════ */

function OutreachSequenceSection({
  emailSequence,
  linkedinMessages,
  loomScript,
  highlightedSection,
}: {
  emailSequence: EmailStep[];
  linkedinMessages: LinkedInMessage[];
  loomScript: string;
  highlightedSection: string | null;
}) {
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [showLinkedIn, setShowLinkedIn] = useState(false);
  const [showLoom, setShowLoom] = useState(false);

  const hasData =
    emailSequence.length > 0 ||
    linkedinMessages.length > 0 ||
    loomScript.trim() !== "";

  return (
    <Section id="outreach-sequence" highlightedSection={highlightedSection}>
      <p className="text-sm font-bold uppercase tracking-wide text-[#003DFF] mb-1">
        Outreach Sequence
      </p>
      <h2 className="text-[1.75rem] font-semibold text-[#23263B] mb-4">
        Multi-Channel Campaign
      </h2>

      {!hasData ? (
        <EmptyState message="Run ABX campaign to generate outreach sequence" />
      ) : (
        <div className="space-y-5">
          {/* ── Email Stepper ── */}
          {emailSequence.length > 0 && (
            <GlassCard>
              <div className="flex items-center gap-2 mb-4">
                <Mail className="h-4 w-4 text-[#003DFF]" />
                <span className="text-sm font-semibold text-[#23263B]">
                  Email Sequence
                </span>
              </div>

              {/* Horizontal stepper */}
              <div className="flex items-center gap-0 mb-4 overflow-x-auto">
                {emailSequence.map((step, idx) => {
                  const isActive = expandedStep === idx;
                  const label =
                    STEP_LABELS[idx] ?? step.label ?? `Step ${step.step}`;

                  return (
                    <div key={step.step} className="flex items-center">
                      <button
                        onClick={() =>
                          setExpandedStep(isActive ? null : idx)
                        }
                        className={cn(
                          "flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors min-w-[80px]",
                          isActive
                            ? "bg-[#003DFF]/10"
                            : "hover:bg-[#F8F9FB]",
                        )}
                      >
                        <span
                          className={cn(
                            "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors",
                            isActive
                              ? "bg-[#003DFF] text-white"
                              : "bg-[#E5E7EB] text-[#6B7280]",
                          )}
                        >
                          {step.step}
                        </span>
                        <span
                          className={cn(
                            "text-[11px] font-medium",
                            isActive
                              ? "text-[#003DFF]"
                              : "text-[#6B7280]",
                          )}
                        >
                          {label}
                        </span>
                      </button>
                      {idx < emailSequence.length - 1 && (
                        <div className="w-6 h-px bg-[#E5E7EB] flex-shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Expanded email content */}
              {expandedStep !== null && emailSequence[expandedStep] && (
                <div
                  className="rounded-lg border border-[#E5E7EB] bg-white p-4 space-y-2"
                >
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                      Subject
                    </span>
                    <p className="text-sm font-medium text-[#23263B] mt-0.5">
                      {emailSequence[expandedStep].subject}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                      Body
                    </span>
                    <p className="text-sm text-[#23263B] mt-0.5 leading-relaxed whitespace-pre-wrap">
                      {emailSequence[expandedStep].body}
                    </p>
                  </div>
                </div>
              )}
            </GlassCard>
          )}

          {/* ── LinkedIn Messages ── */}
          {linkedinMessages.length > 0 && (
            <Collapsible open={showLinkedIn} onOpenChange={setShowLinkedIn}>
              <GlassCard className="p-0 overflow-hidden">
                <CollapsibleTrigger className="flex items-center gap-2 w-full px-5 py-4 text-left hover:bg-[#F8F9FB]/60 transition-colors">
                  <LinkedInIcon className="h-4 w-4 text-[#0A66C2]" />
                  <span className="flex-1 text-sm font-semibold text-[#23263B]">
                    LinkedIn Messages
                  </span>
                  <span className="text-xs text-[#9CA3AF] mr-2">
                    {linkedinMessages.length} recipient{linkedinMessages.length !== 1 ? "s" : ""}
                  </span>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 text-[#6B7280] transition-transform duration-200",
                      showLinkedIn && "rotate-180",
                    )}
                  />
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="divide-y divide-[#E5E7EB] border-t border-[#E5E7EB]">
                    {linkedinMessages.map((msg, idx) => (
                      <div key={idx} className="px-5 py-4 space-y-3">
                        <div className="flex items-center gap-2">
                          <UserCircle className="h-4 w-4 text-[#6B7280]" />
                          <span className="text-sm font-medium text-[#23263B]">
                            {msg.recipient_name}
                          </span>
                          <span className="text-xs text-[#9CA3AF]">
                            {msg.recipient_title}
                          </span>
                        </div>
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wider text-[#0A66C2]">
                            Connection Request
                          </span>
                          <p className="text-sm text-[#23263B] mt-0.5 leading-relaxed">
                            {msg.connection_message}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                            Follow-up
                          </span>
                          <p className="text-sm text-[#23263B] mt-0.5 leading-relaxed">
                            {msg.follow_up_message}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CollapsibleContent>
              </GlassCard>
            </Collapsible>
          )}

          {/* ── Loom Script ── */}
          {loomScript.trim() !== "" && (
            <Collapsible open={showLoom} onOpenChange={setShowLoom}>
              <GlassCard className="p-0 overflow-hidden">
                <CollapsibleTrigger className="flex items-center gap-2 w-full px-5 py-4 text-left hover:bg-[#F8F9FB]/60 transition-colors">
                  <Video className="h-4 w-4 text-[#7C3AED]" />
                  <span className="flex-1 text-sm font-semibold text-[#23263B]">
                    Loom Video Script
                  </span>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 text-[#6B7280] transition-transform duration-200",
                      showLoom && "rotate-180",
                    )}
                  />
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="px-5 pb-4 pt-0 border-t border-[#E5E7EB]">
                    <p className="text-sm text-[#23263B] leading-relaxed whitespace-pre-wrap pt-3">
                      {loomScript}
                    </p>
                  </div>
                </CollapsibleContent>
              </GlassCard>
            </Collapsible>
          )}
        </div>
      )}
    </Section>
  );
}

/* ══════════════════════════════════════════════════════════════
   Deliverable Composer Placeholder
   ══════════════════════════════════════════════════════════════ */

const DELIVERABLE_SECTIONS = [
  { id: "meddpicc", label: "MEDDPICC Framework" },
  { id: "spin-questions", label: "SPIN Questions" },
  { id: "objection-handling", label: "Objection Handlers" },
  { id: "buying-committee", label: "Buying Committee" },
  { id: "outreach-sequence", label: "Outreach Sequence" },
] as const;

const TEMPLATE_OPTIONS = [
  "Customer Leave-Behind",
  "Google Slides",
  "Microsite",
] as const;

function DeliverableComposer() {
  const [checkedSections, setCheckedSections] = useState<Set<string>>(
    new Set(),
  );
  const [selectedTemplate, setSelectedTemplate] = useState<string>(
    TEMPLATE_OPTIONS[0],
  );
  const [showToast, setShowToast] = useState(false);

  const toggleSection = useCallback((sectionId: string) => {
    setCheckedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  }, []);

  const handleGenerate = useCallback(() => {
    console.log("[DeliverableComposer] Generate deliverable", {
      sections: Array.from(checkedSections),
      template: selectedTemplate,
    });
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  }, [checkedSections, selectedTemplate]);

  return (
    <Dialog>
      {/* Floating trigger button */}
      <DialogTrigger
        className={cn(
          "fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full px-5 py-3",
          "text-sm font-semibold text-white shadow-lg transition-all hover:scale-105",
        )}
        style={{
          background: "linear-gradient(135deg, #003DFF, #5468FF)",
          boxShadow:
            "0 4px 14px rgba(0,61,255,0.35), 0 1px 3px rgba(0,0,0,0.1)",
        }}
      >
        <Sparkles className="h-4 w-4" />
        Create Deliverable
      </DialogTrigger>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Deliverable</DialogTitle>
          <DialogDescription>
            Select sections and a template to generate a deliverable package.
          </DialogDescription>
        </DialogHeader>

        {/* Section checkboxes */}
        <div className="space-y-2 py-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-[#6B7280] mb-1">
            Include Sections
          </p>
          {DELIVERABLE_SECTIONS.map((section) => (
            <label
              key={section.id}
              className="flex items-center gap-2 cursor-pointer rounded px-2 py-1.5 hover:bg-[#F8F9FB] transition-colors"
            >
              <input
                type="checkbox"
                checked={checkedSections.has(section.id)}
                onChange={() => toggleSection(section.id)}
                className="h-4 w-4 rounded border-[#E5E7EB] text-[#003DFF] focus:ring-[#003DFF]/20"
              />
              <span className="text-sm text-[#23263B]">{section.label}</span>
            </label>
          ))}
        </div>

        {/* Template dropdown */}
        <div className="py-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-[#6B7280] mb-1">
            Choose a Template
          </p>
          <select
            value={selectedTemplate}
            onChange={(e) => setSelectedTemplate(e.target.value)}
            className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-2 text-sm text-[#23263B] focus:outline-none focus:ring-2 focus:ring-[#003DFF]/20"
          >
            {TEMPLATE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        <DialogFooter>
          <Button
            onClick={handleGenerate}
            className="w-full sm:w-auto"
            style={{
              background: "linear-gradient(135deg, #003DFF, #5468FF)",
              color: "white",
            }}
          >
            <Sparkles className="h-3.5 w-3.5 mr-1.5" />
            Generate
          </Button>
        </DialogFooter>

        {/* Toast */}
        {showToast && (
          <div
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 rounded-lg px-4 py-2 text-xs font-medium text-white shadow-lg"
            style={{ background: "#23263B" }}
          >
            Coming soon -- deliverable generation is under development
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/* ══════════════════════════════════════════════════════════════
   SalesActionsTab — main export
   ══════════════════════════════════════════════════════════════ */

export function SalesActionsTab({ results }: TabProps) {
  const highlightedSection = usePrismStore((s) => s.highlightedSection);

  /* ── Extract data from module outputs ── */
  const salesPlaysOutput = getOutput(results, "synth-sales-plays");
  const hiringOutput = getOutput(results, "intel-hiring");
  const campaignOutput = getOutput(results, "campaign-abx");

  /* Sales plays data */
  const meddpicc = (salesPlaysOutput?.meddpicc as MEDDPICCItem[] | undefined) ?? [];
  const spinQuestions = (salesPlaysOutput?.spin_questions as SPINQuestion[] | undefined) ?? [];
  const objectionHandlers =
    (salesPlaysOutput?.objection_handlers as ObjectionHandler[] | undefined) ?? [];
  const powerMap = (salesPlaysOutput?.power_map as PowerMapPerson[] | undefined) ?? [];

  /* Hiring data for buying committee */
  const buyingCommittee =
    (hiringOutput?.buying_committee as BuyingCommitteeMember[] | undefined) ?? [];

  /* Campaign data */
  const emailSequence =
    (campaignOutput?.email_sequence as EmailStep[] | undefined) ?? [];
  const linkedinMessages =
    (campaignOutput?.linkedin_messages as LinkedInMessage[] | undefined) ?? [];
  const loomScript = (campaignOutput?.loom_script as string | undefined) ?? "";

  return (
    <div className="relative px-1 py-6" style={{ background: "#F8F9FB" }}>
      {/* 6.1 MEDDPICC */}
      <MEDDPICCSection
        items={meddpicc}
        highlightedSection={highlightedSection}
      />

      {/* 6.2 SPIN Questions */}
      <SPINQuestionsSection
        questions={spinQuestions}
        highlightedSection={highlightedSection}
      />

      {/* 6.3 Objection Handling */}
      <ObjectionHandlingSection
        handlers={objectionHandlers}
        highlightedSection={highlightedSection}
      />

      {/* 6.4 Buying Committee */}
      <BuyingCommitteeSection
        powerMap={powerMap}
        buyingCommittee={buyingCommittee}
        highlightedSection={highlightedSection}
      />

      {/* 6.5 Outreach Sequence */}
      <OutreachSequenceSection
        emailSequence={emailSequence}
        linkedinMessages={linkedinMessages}
        loomScript={loomScript}
        highlightedSection={highlightedSection}
      />

      {/* Deliverable Composer floating button + modal */}
      <DeliverableComposer />
    </div>
  );
}
