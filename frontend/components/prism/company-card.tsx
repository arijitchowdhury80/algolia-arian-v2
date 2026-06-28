"use client";

import { useRef, useState, useCallback } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import type { ModuleResult, CompanyProfileResult } from "@/lib/types";

/**
 * CompanyCard — company profile intelligence rendered inline in chat.
 * Pattern: glassmorphism `.ov-tile` bento tile from Algolia Audit SPA.
 */

interface CompanyCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

export function CompanyCard({ data, isLoading, error }: CompanyCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const { ref: inViewRef, inView } = useInView({ triggerOnce: true, threshold: 0.2 });

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    card.style.setProperty("--ov-x", `${x}px`);
    card.style.setProperty("--ov-y", `${y}px`);
  }, []);

  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
  }, []);

  if (isLoading) return <CompanySkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Company profile unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = data.output as unknown as Partial<CompanyProfileResult>;
  const output: CompanyProfileResult = {
    legal_name: raw.legal_name ?? "",
    common_name: raw.common_name ?? "",
    domain: raw.domain ?? "",
    headquarters: raw.headquarters ?? "",
    employee_count: raw.employee_count ?? null,
    employee_count_source: raw.employee_count_source ?? null,
    year_founded: raw.year_founded ?? null,
    business_model: raw.business_model ?? "",
    motto: raw.motto ?? null,
    industry: raw.industry ?? "",
    sub_vertical: raw.sub_vertical ?? null,
    is_public: raw.is_public ?? false,
    ticker: raw.ticker ?? null,
    parent_company: raw.parent_company ?? null,
    revenue_estimate: raw.revenue_estimate ?? null,
    revenue_source: raw.revenue_source ?? null,
    executives: raw.executives ?? [],
    competitors: raw.competitors ?? [],
    recent_news: raw.recent_news ?? [],
    recent_blog_posts: raw.recent_blog_posts ?? [],
    has_search_bar: raw.has_search_bar ?? null,
    product_categories: raw.product_categories ?? [],
    search_experience_description: raw.search_experience_description ?? null,
  };

  const companyName = output.common_name || output.legal_name;
  const revenueDisplay = output.revenue_estimate ?? "Unknown";
  const ecommercePlatform = output.sub_vertical ?? output.industry ?? "N/A";

  // Determine search vendor info from the data
  const searchVendor = output.search_experience_description ?? null;
  const isDisplacementTarget = searchVendor != null && !searchVendor.toLowerCase().includes("algolia");

  return (
    <div
      ref={(node) => {
        (cardRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
        inViewRef(node);
      }}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="ov-tile my-2"
      style={
        {
          "--ov-x": "50%",
          "--ov-y": "50%",
        } as React.CSSProperties
      }
    >
      <style jsx>{`
        .ov-tile {
          position: relative;
          background: rgba(255, 255, 255, 0.72);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.85);
          border-radius: 20px;
          padding: 26px 28px;
          box-shadow:
            0 2px 4px rgba(0, 0, 0, 0.03),
            0 6px 16px rgba(0, 0, 0, 0.06),
            0 16px 36px rgba(0, 0, 0, 0.07),
            inset 0 1px 0 rgba(255, 255, 255, 0.95);
          isolation: isolate;
          overflow: hidden;
          transition: transform 0.2s ease;
        }
      `}</style>

      {/* Spotlight layer */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "inherit",
          background:
            "radial-gradient(600px circle at var(--ov-x, 50%) var(--ov-y, 50%), rgba(71,85,105, 0.07) 0%, transparent 65%)",
          opacity: isHovered ? 1 : 0,
          transition: "opacity 0.3s ease",
          pointerEvents: "none",
          zIndex: 1,
        }}
      />

      {/* Top shimmer */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: "10%",
          right: "10%",
          height: "1px",
          background:
            "linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent)",
          opacity: isHovered ? 1 : 0,
          transition: "opacity 0.3s ease",
          pointerEvents: "none",
          zIndex: 2,
        }}
      />

      {/* Content — above spotlight */}
      <div style={{ position: "relative", zIndex: 3 }}>
        {/* Eyebrow */}
        <div
          style={{
            fontSize: "10px",
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#6B7280",
            marginBottom: "10px",
          }}
        >
          Who is this?
        </div>

        {/* Company name */}
        <h3
          style={{
            fontSize: "22px",
            fontWeight: 800,
            color: "#23263B",
            letterSpacing: "-0.5px",
            marginBottom: "14px",
            lineHeight: 1.2,
          }}
        >
          {companyName}
        </h3>

        {/* Info rows */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "18px" }}>
          {/* Revenue row */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "8px",
                background: "rgba(0,61,255,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "13px",
                flexShrink: 0,
              }}
            >
              💰
            </div>
            <div>
              <span style={{ fontSize: "12px", color: "#6B7280", fontWeight: 500 }}>Revenue</span>
              <span style={{ fontSize: "13px", color: "#23263B", fontWeight: 600, marginLeft: "8px" }}>
                {typeof revenueDisplay === "number" && inView ? (
                  <NumberFlow
                    value={revenueDisplay}
                    format={{ style: "currency", currency: "USD", notation: "compact" }}
                  />
                ) : (
                  String(revenueDisplay)
                )}
              </span>
            </div>
          </div>

          {/* Ecommerce platform row */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "8px",
                background: "rgba(0,61,255,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "13px",
                flexShrink: 0,
              }}
            >
              🛒
            </div>
            <div>
              <span style={{ fontSize: "12px", color: "#6B7280", fontWeight: 500 }}>Platform</span>
              <span style={{ fontSize: "13px", color: "#23263B", fontWeight: 600, marginLeft: "8px" }}>
                {ecommercePlatform}
              </span>
            </div>
          </div>

          {/* Search vendor row */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "8px",
                background: "rgba(0,61,255,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "13px",
                flexShrink: 0,
              }}
            >
              {isDisplacementTarget ? "🎯" : "✅"}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "12px", color: "#6B7280", fontWeight: 500 }}>Search</span>
              <span style={{ fontSize: "13px", color: "#23263B", fontWeight: 600 }}>
                {searchVendor ?? "Unknown"}
              </span>
              {isDisplacementTarget && (
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "#DC2626",
                    background: "rgba(220,38,38,0.10)",
                    padding: "2px 7px",
                    borderRadius: "3px",
                  }}
                >
                  Target
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Bottom navigation link */}
        <div
          style={{
            borderTop: "1px solid rgba(0,0,0,0.07)",
            paddingTop: "14px",
            marginTop: "4px",
          }}
        >
          <a
            href="#research"
            className="ov-tile-nav"
            style={{
              fontSize: "11px",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#94A3B8",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              transition: "color 0.2s ease",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "#003DFF";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "#94A3B8";
            }}
          >
            Research
            <span style={{ fontSize: "13px" }}>&rarr;</span>
          </a>
        </div>
      </div>

      {/* Warnings */}
      {(data.warnings?.length ?? 0) > 0 && (
        <div
          style={{
            position: "relative",
            zIndex: 3,
            marginTop: "8px",
            fontSize: "10px",
            color: "#D97706",
          }}
        >
          {(data.warnings ?? []).map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function CompanySkeleton() {
  return (
    <div
      className="my-2"
      style={{
        background: "rgba(255, 255, 255, 0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255, 255, 255, 0.85)",
        borderRadius: "20px",
        padding: "26px 28px",
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
      }}
    >
      <Skeleton className="h-3 w-24 mb-3" />
      <Skeleton className="h-7 w-48 mb-4" />
      <div className="space-y-3 mb-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-7 w-7 rounded-lg" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex items-center gap-3">
          <Skeleton className="h-7 w-7 rounded-lg" />
          <Skeleton className="h-4 w-40" />
        </div>
        <div className="flex items-center gap-3">
          <Skeleton className="h-7 w-7 rounded-lg" />
          <Skeleton className="h-4 w-36" />
        </div>
      </div>
      <Separator />
      <Skeleton className="h-3 w-20 mt-4" />
    </div>
  );
}
