"use client";

import { useState, useCallback } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { ExternalLink } from "lucide-react";

/**
 * CustomerProofCard — accordion-style case study showcase.
 * Renders proof points from real Algolia customers with measurable results.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CaseStudy {
  company: string;
  vertical?: string;
  result: string;
  product?: string;
  why?: string;
  url?: string;
}

interface CustomerProofCardProps {
  caseStudies: CaseStudy[];
  companyName?: string;
  isLoading?: boolean;
  error?: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const GRADIENTS = [
  "linear-gradient(145deg, #003DFF 0%, #5468FF 100%)",
  "linear-gradient(145deg, #5468FF 0%, #7B88FF 100%)",
  "linear-gradient(145deg, #0029CC 0%, #003DFF 100%)",
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive a plausible domain from a company name for favicon lookup. */
function deriveDomain(company: string): string {
  return company.toLowerCase().replace(/[^a-z0-9]/g, "") + ".com";
}

/** Extract up to two uppercase initials from a company name. */
function initials(company: string): string {
  return company
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CustomerProofSkeleton() {
  return (
    <div className="my-2">
      <Skeleton className="mb-1 h-4 w-40" />
      <Skeleton className="mb-1.5 h-7 w-56" />
      <Skeleton className="mb-6 h-4 w-72" />
      <div className="flex gap-2" style={{ height: 380 }}>
        {[0, 1, 2].map((i) => (
          <Skeleton
            key={i}
            className={cn("rounded-[14px]", i === 0 ? "flex-1" : "w-16")}
          />
        ))}
      </div>
    </div>
  );
}

function CollapsedSlab({
  company,
  gradient,
}: {
  company: string;
  gradient: string;
}) {
  const domain = deriveDomain(company);
  const [logoError, setLogoError] = useState(false);

  const handleImgError = useCallback(() => {
    setLogoError(true);
  }, []);

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
      {/* Favicon or monogram */}
      <div className="flex h-10 w-10 items-center justify-center">
        {!logoError ? (
          <img
            src={`https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://${domain}&size=64`}
            alt={`${company} logo`}
            width={32}
            height={32}
            className="rounded"
            onError={handleImgError}
          />
        ) : (
          <span
            className="select-none font-extrabold"
            style={{
              fontSize: 18,
              letterSpacing: 2,
              color: "rgba(255,255,255,0.6)",
            }}
          >
            {initials(company)}
          </span>
        )}
      </div>

      {/* Vertical company name */}
      <span
        className="max-h-48 select-none truncate font-bold uppercase"
        style={{
          writingMode: "vertical-rl",
          textOrientation: "mixed",
          transform: "rotate(180deg)",
          fontSize: 11,
          letterSpacing: "0.08em",
          color: "rgba(255,255,255,0.75)",
        }}
      >
        {company}
      </span>
    </div>
  );
}

function ExpandedContent({ study }: { study: CaseStudy }) {
  return (
    <div
      className="absolute inset-x-0 bottom-0 flex flex-col gap-1.5"
      style={{ padding: 24 }}
    >
      <span
        className="select-none font-bold uppercase"
        style={{
          fontSize: 10,
          letterSpacing: "0.1em",
          color: "rgba(255,255,255,0.6)",
        }}
      >
        {study.vertical ?? "Case Study"}
      </span>

      <span className="text-xl font-bold text-white">{study.company}</span>

      <span className="font-semibold" style={{ fontSize: 15, color: "#93c5fd" }}>
        {study.result}
      </span>

      {study.product && (
        <span
          className="mt-0.5 inline-block self-start rounded"
          style={{
            fontSize: 10,
            padding: "2px 8px",
            background: "rgba(255,255,255,0.15)",
            color: "rgba(255,255,255,0.8)",
          }}
        >
          {study.product}
        </span>
      )}

      {study.why && (
        <p
          className="mt-1"
          style={{
            fontSize: 12,
            lineHeight: 1.55,
            color: "rgba(255,255,255,0.75)",
          }}
        >
          {study.why}
        </p>
      )}

      {study.url && (
        <a
          href={study.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-flex items-center gap-1 font-semibold no-underline transition-colors hover:text-blue-300"
          style={{ fontSize: 12, color: "#60a5fa" }}
        >
          Read case study
          <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CustomerProofCard({
  caseStudies,
  companyName,
  isLoading,
  error,
}: CustomerProofCardProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (isLoading) return <CustomerProofSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">
          Customer proof unavailable
        </p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  if (caseStudies.length === 0) return null;

  return (
    <section className="my-2">
      {/* Section chrome */}
      <p
        className="mb-1 select-none font-semibold uppercase"
        style={{
          fontSize: 14,
          letterSpacing: "0.12em",
          color: "#003DFF",
        }}
      >
        Business Case &middot; Proof
      </p>
      <h2
        className="mb-1.5 font-semibold"
        style={{ fontSize: "1.75rem", color: "#23263B" }}
      >
        Customer Proof
      </h2>
      <p className="mb-6" style={{ fontSize: "0.9rem", color: "#6B7280" }}>
        {companyName
          ? `Selected for ${companyName}\u2019s vertical. Real results from comparable Algolia customers.`
          : "Real results from comparable Algolia customers."}
      </p>

      {/* Accordion */}
      <div className="flex gap-2" style={{ height: 380 }}>
        {caseStudies.map((study, idx) => {
          const isActive = idx === activeIndex;
          const gradient = GRADIENTS[idx % GRADIENTS.length];

          return (
            <div
              key={`${study.company}-${idx}`}
              className="relative overflow-hidden"
              style={{
                borderRadius: 14,
                flex: isActive ? "1 1 auto" : "0 0 64px",
                cursor: isActive ? "default" : "pointer",
                transition:
                  "flex 0.38s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.2s",
                border: "1.5px solid transparent",
              }}
              onClick={isActive ? undefined : () => setActiveIndex(idx)}
              onKeyDown={
                isActive
                  ? undefined
                  : (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setActiveIndex(idx);
                      }
                    }
              }
              role={isActive ? undefined : "button"}
              tabIndex={isActive ? undefined : 0}
              aria-label={
                isActive ? undefined : `Expand ${study.company} case study`
              }
            >
              {/* Background gradient */}
              <div
                className="absolute inset-0"
                style={{ background: gradient }}
                aria-hidden="true"
              />

              {/* Dark overlay */}
              <div
                className="absolute inset-0"
                style={{
                  background: isActive
                    ? "rgba(0,0,0,0.28)"
                    : "rgba(0,0,0,0.55)",
                  transition: "background 0.4s",
                }}
                aria-hidden="true"
              />

              {/* Collapsed slab — hidden when active */}
              <div
                style={{ display: isActive ? "none" : "block" }}
                className="absolute inset-0"
              >
                <CollapsedSlab company={study.company} gradient={gradient} />
              </div>

              {/* Expanded content */}
              <div
                style={{
                  opacity: isActive ? 1 : 0,
                  transform: isActive
                    ? "translateY(0)"
                    : "translateY(10px)",
                  transition:
                    "opacity 0.35s 0.15s, transform 0.35s 0.15s",
                  pointerEvents: isActive ? "auto" : "none",
                }}
              >
                <ExpandedContent study={study} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
