/**
 * IdentityAnchor — dark hero card at the top of any intel/profile section.
 * Tokens: font.*, color.dark.*, radius.2xl
 *
 * Sora weights: 300 (light) / 400 (regular) / 600 (semibold) only.
 * All font sizes ≥ 12px (Algolia minimum).
 */
"use client";

import { useState } from "react";
import { GridPatternBg } from "./grid-pattern-bg";
import { font, color, radius, shadow } from "@/lib/tokens";
import type { CompanyIntelOutput } from "@/lib/types";

function formatRevenue(value: number): string {
  if (value >= 1e12) return `~$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9)  return `~$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6)  return `~$${(value / 1e6).toFixed(0)}M`;
  return `~$${value.toLocaleString()}`;
}

function getInitials(name: string): string {
  return name.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

interface IdentityAnchorProps {
  output: CompanyIntelOutput;
}

export function IdentityAnchor({ output }: IdentityAnchorProps) {
  const [logoError, setLogoError] = useState(false);
  const companyName = output.common_name || output.legal_name;
  const initials    = getInitials(companyName);
  const yearsSince  = output.year_founded
    ? new Date().getFullYear() - output.year_founded
    : null;

  const badgePill: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    background: color.dark.badgeBg,
    border: `1px solid ${color.dark.badgeBorder}`,
    borderRadius: radius.pill,
    padding: "4px 12px",
    fontSize: font.caption,          // 12px
    fontWeight: font.weight.regular,
    color: color.dark.badgeText,
  };

  const statLabel: React.CSSProperties = {
    fontSize: font.caption,           // 12px — was 11px, fixed
    fontWeight: font.weight.semibold,
    textTransform: "uppercase",
    letterSpacing: "0.10em",
    color: color.dark.statLabel,
  };

  const statSource: React.CSSProperties = {
    fontSize: font.caption,           // 12px — was 10px, fixed
    fontWeight: font.weight.regular,
    color: color.dark.textGhost,
    fontStyle: "italic",
  };

  return (
    <div
      className="relative overflow-hidden"
      style={{
        background:   color.dark.bg,
        border:       `1px solid ${color.dark.border}`,
        borderRadius: radius["2xl"],
        boxShadow:    shadow.dark,
      }}
    >
      <GridPatternBg />

      {/* Parent company banner */}
      {output.parent_company && (
        <div
          style={{
            position: "relative",
            zIndex: 3,
            padding: "8px 28px",
            background: color.parent.bg,
            borderBottom: `1px solid ${color.parent.border}`,
            fontSize: font.small,      // 13px — was 11px, fixed
            color: color.parent.text,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span style={{ opacity: 0.6 }}>Subsidiary of:</span>
          <span style={{ fontWeight: font.weight.semibold }}>{output.parent_company}</span>
          {output.parent_domain && (
            <a
              href={`https://${output.parent_domain}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "rgba(255,210,100,0.70)", fontSize: font.caption, textDecoration: "none" }}
            >
              {output.parent_domain} ↗
            </a>
          )}
        </div>
      )}

      {/* Two-column grid */}
      <div
        style={{
          position: "relative",
          zIndex: 3,
          display: "grid",
          gridTemplateColumns: "55fr 45fr",
        }}
      >
        {/* Left: Identity */}
        <div style={{ padding: "28px 30px", borderRight: `1px solid ${color.dark.divider}` }}>
          {/* Logo / initials */}
          <div style={{ marginBottom: 14 }}>
            {!logoError ? (
              <div
                style={{
                  width: 56, height: 56,
                  borderRadius: radius.lg,
                  overflow: "hidden",
                  background: "white",
                  border: `1px solid ${color.dark.badgeBorder}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}
              >
                <img
                  src={`https://logo.clearbit.com/${output.domain}`}
                  alt={`${companyName} logo`}
                  style={{ width: "100%", height: "100%", objectFit: "contain", padding: 4 }}
                  onError={() => setLogoError(true)}
                />
              </div>
            ) : (
              <div
                style={{
                  width: 56, height: 56,
                  borderRadius: radius.lg,
                  background: color.blue,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: font.h4,
                  fontWeight: font.weight.semibold,
                  color: "white",
                }}
              >
                {initials}
              </div>
            )}
          </div>

          {/* Eyebrow */}
          <div
            style={{
              fontSize: font.small,            // 13px — was 11px, fixed
              fontWeight: font.weight.semibold,
              textTransform: "uppercase",
              letterSpacing: "0.13em",
              color: color.dark.textMuted,
              marginBottom: 8,
            }}
          >
            {output.sub_vertical ?? output.industry}
          </div>

          {/* Company name */}
          <div
            style={{
              fontSize: font.entityName,       // 26px
              fontWeight: font.weight.semibold,
              color: color.dark.text,
              letterSpacing: "-0.5px",
              lineHeight: 1.15,
              marginBottom: 16,
            }}
          >
            {companyName}
          </div>

          {/* Badge pills */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {output.headquarters && (
              <span style={badgePill}>📍 {output.headquarters}</span>
            )}
            {output.year_founded && (
              <span style={badgePill}>📅 Est. {output.year_founded}</span>
            )}
            {output.employee_count && (
              <span style={badgePill}>
                👥 {output.employee_count.toLocaleString()} employees
              </span>
            )}
            {output.is_public && output.ticker ? (
              <span
                style={{
                  ...badgePill,
                  background: color.ticker.bg,
                  border: `1px solid ${color.ticker.border}`,
                  color: color.ticker.text,
                  fontWeight: font.weight.semibold,
                }}
              >
                🏢 Public · {output.ticker}
              </span>
            ) : (
              <span style={badgePill}>🏢 Private</span>
            )}
          </div>
        </div>

        {/* Right: Stats 2×2 */}
        <div
          style={{
            padding: "28px 30px",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "20px 24px",
            alignContent: "start",
          }}
        >
          {output.revenue_estimate != null && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div style={{ fontSize: font.statValue, fontWeight: font.weight.semibold, color: color.dark.text, letterSpacing: "-0.3px" }}>
                {formatRevenue(output.revenue_estimate)}
              </div>
              <div style={statLabel}>Revenue</div>
              {output.revenue_source && <div style={statSource}>{output.revenue_source}</div>}
            </div>
          )}
          {output.employee_count != null && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div style={{ fontSize: font.statValue, fontWeight: font.weight.semibold, color: color.dark.text, letterSpacing: "-0.3px" }}>
                {output.employee_count.toLocaleString()}
              </div>
              <div style={statLabel}>Employees</div>
              {output.employee_count_source && <div style={statSource}>{output.employee_count_source}</div>}
            </div>
          )}
          {output.year_founded != null && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div style={{ fontSize: font.statValue, fontWeight: font.weight.semibold, color: color.dark.text, letterSpacing: "-0.3px" }}>
                {output.year_founded}
              </div>
              <div style={statLabel}>Founded</div>
              {yearsSince && <div style={statSource}>{yearsSince} years ago</div>}
            </div>
          )}
          {output.headquarters && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div style={{ fontSize: font.statValueSm, fontWeight: font.weight.semibold, color: color.dark.text, letterSpacing: "-0.3px", lineHeight: 1.2 }}>
                {output.headquarters.split(",")[0]}
              </div>
              <div style={statLabel}>Headquarters</div>
              <div style={statSource}>
                {output.headquarters.split(",").slice(1).join(",").trim()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
