"use client";

import { useRef, useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { Mail, Video, ChevronDown, Calendar } from "lucide-react";
import type { ModuleResult, CampaignResult } from "@/lib/types";

/**
 * CampaignCard -- 5-email ABX sequence as horizontal stepper,
 * LinkedIn messages, Loom script, collateral schedule.
 * Glassmorphism container with Algolia audit SPA styling.
 */

const STEP_LABELS = ["Hook", "Insight", "Proof", "ROI", "Ask"] as const;

interface CampaignCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

/** LinkedIn SVG icon at 14x14 */
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

export function CampaignCard({ data, isLoading, error }: CampaignCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [showLoom, setShowLoom] = useState(false);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const angle =
      Math.atan2(e.clientY - cy, e.clientX - cx) * (180 / Math.PI) + 90;
    card.style.setProperty("--glow-angle", `${angle}deg`);
  }, []);

  if (isLoading) return <CampaignSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">
          Campaign unavailable
        </p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<CampaignResult>;
  const output = {
    email_sequence: raw.email_sequence ?? [],
    linkedin_messages: raw.linkedin_messages ?? [],
    loom_script: raw.loom_script ?? null,
    collateral_schedule: raw.collateral_schedule ?? [],
  };
  const emails = output.email_sequence ?? [];

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className="my-2"
      style={
        {
          "--glow-angle": "0deg",
          background: "rgba(255,255,255,0.72)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.85)",
          borderRadius: "20px",
          boxShadow:
            "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
          padding: "26px 28px",
        } as React.CSSProperties
      }
    >
      {/* Eyebrow + version */}
      <div className="flex items-center justify-between mb-4">
        <div
          className="flex items-center gap-2"
          style={{
            fontSize: "10px",
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#6B7280",
          }}
        >
          <Mail className="h-3.5 w-3.5" />
          ABX CAMPAIGN
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      {/* ── Email Sequence — Horizontal Stepper ── */}
      {emails.length > 0 && (
        <div className="mb-4">
          <span
            style={{
              fontSize: "10px",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              color: "#6B7280",
            }}
            className="mb-3 block"
          >
            Email Sequence
          </span>

          {/* Stepper row */}
          <div className="flex items-start mb-3">
            {emails.map((email, i) => {
              const isActive = expandedStep === i;
              const isPast =
                expandedStep !== null && i < expandedStep;
              return (
                <div
                  key={email.step}
                  className="flex items-center"
                  style={{ flex: i < emails.length - 1 ? 1 : undefined }}
                >
                  {/* Circle + label column */}
                  <div className="flex flex-col items-center">
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedStep(expandedStep === i ? null : i)
                      }
                      aria-label={`Email step ${i + 1}: ${STEP_LABELS[i] ?? `Step ${i + 1}`}`}
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        fontSize: "12px",
                        fontWeight: 700,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        border: "none",
                        cursor: "pointer",
                        transition: "background 0.15s, color 0.15s",
                        background: isActive || isPast
                          ? "#003DFF"
                          : "#F5F5F7",
                        color: isActive || isPast ? "#fff" : "#23263B",
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive && !isPast) {
                          (e.currentTarget as HTMLButtonElement).style.background =
                            "rgba(0,61,255,0.10)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive && !isPast) {
                          (e.currentTarget as HTMLButtonElement).style.background =
                            "#F5F5F7";
                        }
                      }}
                    >
                      {i + 1}
                    </button>
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 600,
                        color: "#6B7280",
                        textAlign: "center",
                        marginTop: "6px",
                      }}
                    >
                      {STEP_LABELS[i] ?? `Step ${i + 1}`}
                    </span>
                  </div>

                  {/* Connecting line */}
                  {i < emails.length - 1 && (
                    <div
                      style={{
                        height: 2,
                        flex: 1,
                        alignSelf: "center",
                        marginTop: "-18px",
                        background:
                          expandedStep !== null && i < expandedStep
                            ? "#003DFF"
                            : "#E5E7EB",
                        transition: "background 0.15s",
                      }}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Expanded email content */}
          {expandedStep !== null && emails[expandedStep] && (
            <div
              style={{
                border: "1px solid #E5E7EB",
                borderRadius: "8px",
                padding: "16px 20px",
                background: "#F8F9FF",
              }}
            >
              {/* Badge */}
              <span
                style={{
                  fontSize: "9px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  padding: "2px 8px",
                  borderRadius: "20px",
                  background: "#EEF2FF",
                  color: "#003DFF",
                  display: "inline-block",
                  marginBottom: "8px",
                }}
              >
                {emails[expandedStep].label}
              </span>

              {/* Subject */}
              <div style={{ marginBottom: "8px" }}>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    color: "#6B7280",
                  }}
                >
                  Subject:{" "}
                </span>
                <span
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: "#23263B",
                  }}
                >
                  {emails[expandedStep].subject}
                </span>
              </div>

              {/* Body */}
              <p
                style={{
                  fontSize: "14px",
                  color: "#23263B",
                  lineHeight: 1.7,
                  whiteSpace: "pre-wrap",
                  fontFamily: "'Sora', sans-serif",
                  margin: 0,
                }}
              >
                {emails[expandedStep].body}
              </p>
            </div>
          )}
        </div>
      )}

      <Separator className="mb-4" />

      {/* ── LinkedIn Messages ── */}
      {output.linkedin_messages.length > 0 && (
        <div className="mb-4">
          <span
            className="mb-2 flex items-center gap-1.5 block"
            style={{
              fontSize: "10px",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              color: "#0A66C2",
            }}
          >
            <LinkedInIcon className="h-3.5 w-3.5" />
            LinkedIn Messages
          </span>
          <div className="space-y-1.5">
            {output.linkedin_messages.map((lm, i) => (
              <Collapsible key={i}>
                <CollapsibleTrigger className="flex items-center gap-2 w-full py-1 text-left group">
                  <ChevronDown className="h-3 w-3 text-[#0A66C2] transition-transform group-data-[state=open]:rotate-180" />
                  <span className="text-[11px] font-semibold text-[#23263B]">
                    {lm.recipient_name}
                  </span>
                  <span className="text-[10px] text-[#6B7280]">
                    {lm.recipient_title}
                  </span>
                </CollapsibleTrigger>
                <CollapsibleContent className="pl-5 pb-1">
                  <div
                    style={{
                      background: "#EEF2FF",
                      borderRadius: "6px",
                      padding: "12px 14px",
                      marginBottom: "6px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "9px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        color: "#0A66C2",
                        display: "block",
                        marginBottom: "4px",
                      }}
                    >
                      Connect
                    </span>
                    <p className="text-[11px] text-[#23263B] m-0">
                      {lm.connection_message}
                    </p>
                  </div>
                  <div
                    style={{
                      background: "#EEF2FF",
                      borderRadius: "6px",
                      padding: "12px 14px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "9px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        color: "#0A66C2",
                        display: "block",
                        marginBottom: "4px",
                      }}
                    >
                      Follow-up
                    </span>
                    <p className="text-[11px] text-[#23263B] m-0">
                      {lm.follow_up_message}
                    </p>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            ))}
          </div>
        </div>
      )}

      {/* ── Loom Script ── */}
      {output.loom_script && (
        <div className="mb-4">
          <Collapsible open={showLoom} onOpenChange={setShowLoom}>
            <CollapsibleTrigger className="flex items-center gap-2 w-full text-left group">
              <Video className="h-3.5 w-3.5" style={{ color: "#7C3AED" }} />
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  letterSpacing: "0.12em",
                  color: "#7C3AED",
                }}
              >
                Loom Script
              </span>
              <ChevronDown className="h-3 w-3 text-[#7C3AED] transition-transform group-data-[state=open]:rotate-180 ml-auto" />
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              <div
                style={{
                  background: "#F5F3FF",
                  borderRadius: "8px",
                  padding: "14px 16px",
                  border: "1px solid #DDD6FE",
                }}
              >
                <p
                  style={{
                    fontSize: "11px",
                    color: "#23263B",
                    lineHeight: 1.7,
                    whiteSpace: "pre-wrap",
                    margin: 0,
                  }}
                >
                  {output.loom_script}
                </p>
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      )}

      <Separator className="mb-4" />

      {/* ── Collateral Schedule ── */}
      {output.collateral_schedule.length > 0 && (
        <div>
          <span
            className="mb-2 flex items-center gap-1.5"
            style={{
              fontSize: "10px",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              color: "#6B7280",
            }}
          >
            <Calendar className="h-3.5 w-3.5" />
            Collateral Schedule
          </span>
          <div
            style={{
              borderRadius: "8px",
              border: "1px solid #E5E7EB",
              overflow: "hidden",
            }}
          >
            {output.collateral_schedule.map((cs, i) => (
              <div
                key={i}
                className="flex items-center gap-3 px-3 py-2"
                style={{
                  fontSize: "11px",
                  background: i % 2 === 0 ? "#fff" : "#FAFAFA",
                }}
              >
                {/* Week pill */}
                <span
                  style={{
                    fontSize: "9px",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "20px",
                    background:
                      i === 0
                        ? "#DBEAFE"
                        : i === 1
                          ? "#D1FAE5"
                          : i === 2
                            ? "#FEF3C7"
                            : "#EDE9FE",
                    color:
                      i === 0
                        ? "#1D4ED8"
                        : i === 1
                          ? "#059669"
                          : i === 2
                            ? "#B45309"
                            : "#6D28D9",
                    flexShrink: 0,
                  }}
                >
                  Week {cs.week}
                </span>
                <span style={{ color: "#23263B", flex: 1 }}>{cs.action}</span>
                <span
                  style={{
                    color: "#6B7280",
                    textAlign: "right",
                    flexShrink: 0,
                  }}
                >
                  {cs.channel}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {(data.warnings?.length ?? 0) > 0 && (
        <div className="mt-3 text-[10px] text-amber-600">
          {(data.warnings ?? []).map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function CampaignSkeleton() {
  return (
    <div
      className="my-2"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: "20px",
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
        padding: "26px 28px",
      }}
    >
      <div className="flex justify-between mb-4">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-4 w-16" />
      </div>
      {/* Stepper skeleton */}
      <div className="flex items-center gap-0 mb-3">
        {[1, 2, 3, 4, 5].map((n) => (
          <div key={n} className="flex items-center" style={{ flex: n < 5 ? 1 : undefined }}>
            <div className="flex flex-col items-center">
              <Skeleton className="h-8 w-8 rounded-full" />
              <Skeleton className="h-2 w-8 mt-1.5" />
            </div>
            {n < 5 && <Skeleton className="h-0.5 flex-1 mx-1" />}
          </div>
        ))}
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-16 w-full rounded-lg" />
      </div>
    </div>
  );
}
