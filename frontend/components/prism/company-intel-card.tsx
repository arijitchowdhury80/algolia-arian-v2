"use client";

import { useState } from "react";
import type { ModuleResult, CompanyIntelOutput } from "@/lib/types";
import { font, color, radius, shadow, styles } from "@/lib/tokens";
import { IdentityAnchor } from "./identity-anchor";
import { NarrativeLayer } from "./narrative-layer";
import { StatChipGrid } from "./stat-chip-grid";
import { IntelRowHover } from "./intel-row-hover";
import { BrandPortfolioTree } from "./brand-portfolio-tree";
import { CompetitorCardGrid } from "./competitor-card-grid";

function formatRevenue(value: number): string {
  if (value >= 1e12) return `~$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `~$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `~$${(value / 1e6).toFixed(0)}M`;
  return `~$${value.toLocaleString()}`;
}

function castOutput(raw: Record<string, unknown>): CompanyIntelOutput {
  return {
    legal_name: (raw.legal_name as string) ?? "",
    common_name: (raw.common_name as string) ?? "",
    domain: (raw.domain as string) ?? "",
    headquarters: (raw.headquarters as string) ?? "",
    employee_count: (raw.employee_count as number | null) ?? null,
    employee_count_source: (raw.employee_count_source as string | null) ?? null,
    year_founded: (raw.year_founded as number | null) ?? null,
    business_model: (raw.business_model as string) ?? "",
    industry: (raw.industry as string) ?? "",
    sub_vertical: (raw.sub_vertical as string | null) ?? null,
    is_public: (raw.is_public as boolean) ?? false,
    ticker: (raw.ticker as string | null) ?? null,
    parent_company: (raw.parent_company as string | null) ?? null,
    parent_domain: (raw.parent_domain as string | null) ?? null,
    revenue_estimate: (raw.revenue_estimate as number | null) ?? null,
    revenue_source: (raw.revenue_source as string | null) ?? null,
    subsidiaries: (raw.subsidiaries as CompanyIntelOutput["subsidiaries"]) ?? [],
    executives: (raw.executives as CompanyIntelOutput["executives"]) ?? [],
    competitors: (raw.competitors as CompanyIntelOutput["competitors"]) ?? [],
    product_categories: (raw.product_categories as string[]) ?? [],
    company_linkedin_url: (raw.company_linkedin_url as string | null) ?? null,
    twitter_handle: (raw.twitter_handle as string | null) ?? null,
    youtube_url: (raw.youtube_url as string | null) ?? null,
    recent_headline: (raw.recent_headline as string | null) ?? null,
  };
}

const GLASS_CARD: React.CSSProperties = {
  ...styles.glassCard,
  padding: "32px 36px",   // generous — sections need to breathe
};

interface CompanyIntelCardProps {
  data: ModuleResult;
}

export function CompanyIntelCard({ data }: CompanyIntelCardProps) {
  const [bioExpanded, setBioExpanded] = useState(false);
  const output = castOutput(data.output);

  const yearsSince = output.year_founded
    ? new Date().getFullYear() - output.year_founded
    : null;

  const statChips = [
    output.revenue_estimate != null
      ? { icon: "💰", label: "Revenue", value: formatRevenue(output.revenue_estimate), source: output.revenue_source ?? undefined }
      : null,
    output.employee_count != null
      ? { icon: "👥", label: "Employees", value: output.employee_count.toLocaleString(), source: output.employee_count_source ?? undefined }
      : null,
    output.headquarters
      ? { icon: "📍", label: "Headquarters", value: output.headquarters }
      : null,
    output.year_founded != null
      ? { icon: "📅", label: "Founded", value: String(output.year_founded), source: yearsSince ? `${yearsSince} years ago` : undefined }
      : null,
  ].filter((c): c is NonNullable<typeof c> => c !== null);

  const hasFootprint = output.subsidiaries.length > 0 || output.competitors.length > 0;

  const socialLinks = [
    output.domain
      ? { icon: "🔗", label: output.domain, href: `https://${output.domain}` }
      : null,
    output.company_linkedin_url
      ? { icon: "in", label: "LinkedIn", href: output.company_linkedin_url }
      : null,
    output.twitter_handle
      ? { icon: "@", label: `@${output.twitter_handle}`, href: `https://twitter.com/${output.twitter_handle}` }
      : null,
    output.youtube_url
      ? { icon: "▶", label: "YouTube", href: output.youtube_url }
      : null,
  ].filter((l): l is NonNullable<typeof l> => l !== null);

  const hasOnlinePresence =
    output.product_categories.length > 0 ||
    socialLinks.length > 0 ||
    !!output.recent_headline;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>  {/* 28px — sections breathe */}
      {/* Layer 0: Identity Anchor */}
      <IdentityAnchor output={output} />

      {/* Layer 1: WHO ARE THEY? */}
      {(output.business_model || statChips.length > 0) && (
        <>
          <NarrativeLayer label="WHO ARE THEY?" />
          <div style={GLASS_CARD}>
            {output.business_model && (
              <div
                style={{
                  borderLeft: `3px solid ${color.blue20}`,
                  paddingLeft: 16,
                  marginBottom: statChips.length > 0 ? 28 : 0,
                }}
              >
                <div
                  style={{
                    fontSize: font.body,
                    fontWeight: font.weight.regular,
                    color: color.text,
                    lineHeight: 1.7,
                    display: bioExpanded ? "block" : "-webkit-box",
                    WebkitLineClamp: bioExpanded ? undefined : 3,
                    WebkitBoxOrient: "vertical",
                    overflow: bioExpanded ? "visible" : "hidden",
                  }}
                >
                  {output.business_model}
                </div>
                {output.business_model.length > 200 && (
                  <button
                    onClick={() => setBioExpanded((v) => !v)}
                    style={{
                      marginTop: 8,
                      fontSize: font.small,
                      fontWeight: font.weight.semibold,
                      color: color.blue,
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: 0,
                      opacity: 0.75,
                    }}
                  >
                    {bioExpanded ? "Show less" : "Read more"}
                  </button>
                )}
              </div>
            )}
            {statChips.length > 0 && <StatChipGrid chips={statChips} />}
          </div>
        </>
      )}

      {/* Layer 2: WHO'S IN CHARGE? */}
      {output.executives.length > 0 && (
        <>
          <NarrativeLayer label="WHO'S IN CHARGE?" />
          <div style={GLASS_CARD}>
            <IntelRowHover executives={output.executives} />
          </div>
        </>
      )}

      {/* Layer 3: THEIR FOOTPRINT */}
      {hasFootprint && (
        <>
          <NarrativeLayer label="THEIR FOOTPRINT" />
          <div style={{ ...GLASS_CARD, padding: 0, overflow: "hidden" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  output.subsidiaries.length > 0 && output.competitors.length > 0
                    ? "1fr 1fr"
                    : "1fr",
              }}
            >
              {output.subsidiaries.length > 0 && (
                <div
                  style={{
                    padding: "32px 28px 32px 32px",
                    borderRight: output.competitors.length > 0 ? `1px solid ${color.divider}` : "none",
                  }}
                >
                  <div style={styles.eyebrow}>Brand Portfolio</div>
                  <BrandPortfolioTree
                    subsidiaries={output.subsidiaries}
                    auditDomain={output.domain}
                    parentCompany={output.parent_company}
                  />
                </div>
              )}
              {output.competitors.length > 0 && (
                <div style={{ padding: "32px 32px 32px 28px" }}>
                  <div style={styles.eyebrow}>Competitors</div>
                  <CompetitorCardGrid competitors={output.competitors} />
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Layer 4: ONLINE PRESENCE */}
      {hasOnlinePresence && (
        <>
          <NarrativeLayer label="ONLINE PRESENCE" />
          <div style={{ ...GLASS_CARD, background: "rgba(255,255,255,0.50)" }}>
            {output.product_categories.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: socialLinks.length > 0 || output.recent_headline ? 20 : 0 }}>
                {output.product_categories.map((cat) => (
                  <span
                    key={cat}
                    style={{
                      background: color.blue07,
                      border: `1px solid ${color.blue15}`,
                      borderRadius: radius.sm,
                      padding: "4px 10px",
                      fontSize: font.caption,       // 12px — was 10px, fixed
                      fontWeight: font.weight.semibold,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: color.blue,
                    }}
                  >
                    {cat}
                  </span>
                ))}
              </div>
            )}
            {socialLinks.length > 0 && (
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: output.recent_headline ? 20 : 0 }}>
                {socialLinks.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={link.label}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "6px 14px",
                      background: color.blue06,
                      border: `1px solid ${color.blue12}`,
                      borderRadius: radius.md,
                      fontSize: font.small,         // 13px — was 12px
                      fontWeight: font.weight.semibold,
                      color: color.blue,
                      textDecoration: "none",
                    }}
                  >
                    <span style={{ fontSize: font.label }}>{link.icon}</span>
                    {link.label}
                  </a>
                ))}
              </div>
            )}
            {output.recent_headline && (
              <div style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: font.small, color: color.text, lineHeight: 1.6, fontStyle: "italic" }}>
                <span>🗞</span>
                <span>{output.recent_headline}</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
