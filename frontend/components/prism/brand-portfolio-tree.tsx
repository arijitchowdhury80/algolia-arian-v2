/**
 * BrandPortfolioTree — parent entity → subsidiary brand hierarchy.
 * Shows connecting lines, "THIS AUDIT" badge, portfolio opportunity callout.
 *
 * Tokens: font.label (brand names), font.caption (12px min for badges/domains)
 * Trigger: render when subsidiaries.length >= 1
 */
import { font, color, radius } from "@/lib/tokens";
import type { SubsidiarySeed } from "@/lib/types";

interface BrandPortfolioTreeProps {
  subsidiaries: SubsidiarySeed[];
  auditDomain:  string;
  parentCompany: string | null;
}

export function BrandPortfolioTree({ subsidiaries, auditDomain, parentCompany }: BrandPortfolioTreeProps) {
  if (subsidiaries.length === 0) {
    return (
      <div style={{ fontSize: font.small, color: color.ghost, fontStyle: "italic" }}>
        No distinct sub-brands identified
      </div>
    );
  }

  const auditBrandName = auditDomain.split(".")[0];
  const allBrands = [
    { name: auditBrandName, domain: auditDomain, isAudit: true },
    ...subsidiaries.map((s) => ({ name: s.name, domain: s.domain, isAudit: false })),
  ];

  const portfolioText =
    subsidiaries.length >= 2
      ? `${allBrands.length}-brand portfolio = ${allBrands.length}× search optimization surface`
      : `${allBrands.length} brands — full portfolio opportunity`;

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      {/* Parent label */}
      <div style={{ paddingBottom: 10 }}>
        <span
          style={{
            background: "rgba(0,0,0,0.05)",
            border: "1px solid rgba(0,0,0,0.09)",
            borderRadius: radius.sm,
            padding: "3px 8px",
            fontSize: font.caption,           // 12px — was 10px, fixed
            fontWeight: font.weight.semibold,
            textTransform: "uppercase",
            letterSpacing: "0.10em",
            color: color.muted,
          }}
        >
          {parentCompany ?? "Holding Company"}
        </span>
      </div>

      {/* Tree */}
      <div style={{ position: "relative", paddingLeft: 20 }}>
        {/* Vertical connector */}
        <div
          style={{
            position: "absolute",
            left: 8, top: 0, bottom: 24,
            width: 1,
            background: "rgba(0,0,0,0.12)",
          }}
        />

        {allBrands.map((brand, i) => (
          <div
            key={brand.name}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 0",
              position: "relative",
              borderBottom: i < allBrands.length - 1 ? `1px solid ${color.dividerSoft}` : "none",
            }}
          >
            {/* Horizontal connector */}
            <div
              style={{
                position: "absolute",
                left: 0, top: "50%",
                width: 16, height: 1,
                background: "rgba(0,0,0,0.12)",
              }}
            />

            {/* Avatar */}
            <div
              style={{
                width: 32, height: 32,
                borderRadius: radius.md,
                background: color.blue08,
                border: `1px solid ${color.blue15}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: font.small,          // 13px — was 12px
                fontWeight: font.weight.semibold,
                color: color.blue,
                flexShrink: 0,
                textTransform: "uppercase",
              }}
            >
              {brand.name[0]}
            </div>

            {/* Name + domain */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: font.label,        // 14px
                  fontWeight: font.weight.semibold,
                  color: color.navy,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  flexWrap: "wrap",
                }}
              >
                {brand.name}
                {brand.isAudit && (
                  <span
                    style={{
                      background: color.auditBadge.bg,
                      border: `1px solid ${color.auditBadge.border}`,
                      borderRadius: radius.sm,
                      padding: "2px 7px",
                      fontSize: font.caption,  // 12px — was 9px, fixed
                      fontWeight: font.weight.semibold,
                      textTransform: "uppercase",
                      letterSpacing: "0.10em",
                      color: color.auditBadge.text,
                    }}
                  >
                    THIS AUDIT
                  </span>
                )}
              </div>
              {brand.domain && (
                <a
                  href={`https://${brand.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: font.caption,    // 12px
                    color: color.blue,
                    textDecoration: "none",
                    opacity: 0.65,
                  }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLAnchorElement).style.opacity = "1")}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLAnchorElement).style.opacity = "0.65")}
                >
                  {brand.domain} ↗
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Portfolio opportunity callout */}
      {subsidiaries.length >= 2 && (
        <div
          style={{
            marginTop: 16,
            padding: "12px 14px",
            background: color.amber.bg,
            border: `1px solid ${color.amber.border}`,
            borderRadius: radius.lg,
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
          }}
        >
          <span style={{ fontSize: "16px" }}>💡</span>
          <div>
            <div style={{ fontSize: font.small, fontWeight: font.weight.semibold, color: color.amber.title, marginBottom: 2 }}>
              Portfolio Opportunity
            </div>
            <div style={{ fontSize: font.small, color: color.amber.body, lineHeight: 1.5 }}>
              {portfolioText}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
