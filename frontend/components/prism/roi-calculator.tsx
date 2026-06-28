"use client";

import { useState, useCallback, useMemo } from "react";
import NumberFlow from "@number-flow/react";
import { Copy } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types & Constants
// ---------------------------------------------------------------------------

const LEVER_CONFIG = [
  {
    key: "conversionLift",
    label: "Conversion Lift",
    min: 0,
    max: 100,
    default: 15,
    suffix: "%",
    proof: {
      company: "Decathlon & Harry Rosen",
      result: "Decathlon saw +50% lift. Harry Rosen saw +360% lift.",
    },
  },
  {
    key: "aovIncrease",
    label: "AOV Increase",
    min: 0,
    max: 30,
    default: 5,
    suffix: "%",
    proof: {
      company: "Intrend & Oh Polly",
      result: "Intrend saw +19% increase. Oh Polly saw +172%.",
    },
  },
  {
    key: "bounceReduction",
    label: "Bounce Reduction",
    min: 0,
    max: 50,
    default: 10,
    suffix: "%",
    proof: {
      company: "Lacoste & JadoPado",
      result: "Lacoste saw an 88% reduction. JadoPado saw a 17% decrease.",
    },
  },
  {
    key: "noResultsRecovery",
    label: "No-Results Recovery",
    min: 0,
    max: 80,
    default: 30,
    suffix: "%",
    proof: {
      company: "Ubisoft",
      result: "Ubisoft reduced zero-results from 20% to <5%.",
    },
  },
] as const;

type SliderKey = (typeof LEVER_CONFIG)[number]["key"];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ROICalculatorProps {
  baseRevenue?: number;
  /** Compact mode — shows only total value in a simplified view */
  compact?: boolean;
  /** Pre-populate lever values */
  presets?: Partial<Record<SliderKey, number>>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${Math.round(value).toLocaleString()}`;
  }
  return `$${Math.round(value)}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ROICalculator({
  baseRevenue = 10_000_000,
  compact = false,
  presets: externalPresets,
}: ROICalculatorProps) {
  const defaultLevers: Record<SliderKey, number> = {
    conversionLift: 15,
    aovIncrease: 5,
    bounceReduction: 10,
    noResultsRecovery: 30,
  };

  const [levers, setLevers] = useState<Record<SliderKey, number>>(
    externalPresets ? { ...defaultLevers, ...externalPresets } : defaultLevers
  );
  const [baselineRevenue, setBaselineRevenue] = useState(baseRevenue);
  const [baselineConvRate, setBaselineConvRate] = useState(2.5);
  const [baselineAOV, setBaselineAOV] = useState(120);
  const [copied, setCopied] = useState(false);

  const handleLeverChange = useCallback((key: SliderKey, value: number) => {
    setLevers((prev) => ({ ...prev, [key]: value }));
  }, []);

  // Calculation per the SPA formula
  const calculations = useMemo(() => {
    const convRate = baselineConvRate / 100;
    const aov = baselineAOV;

    const searchRevenue = baselineRevenue * 0.15;
    const searchTraffic = searchRevenue / aov / convRate;

    const conversionLift = levers.conversionLift / 100;
    const aovIncrease = levers.aovIncrease / 100;
    const bounceReduction = levers.bounceReduction / 100;
    const noResultsRecovery = levers.noResultsRecovery / 100;

    const newConvRate = convRate * (1 + conversionLift);

    const conversionImpact =
      searchTraffic * newConvRate * aov - searchRevenue;
    const aovImpact =
      searchTraffic * newConvRate * (aov * (1 + aovIncrease) - aov);
    const bounceImpact =
      searchTraffic * 0.3 * bounceReduction * newConvRate * (aov * (1 + aovIncrease));
    const noResultsImpact =
      searchTraffic * 0.1 * noResultsRecovery * newConvRate * (aov * (1 + aovIncrease));

    const total = conversionImpact + aovImpact + bounceImpact + noResultsImpact;

    return {
      conversionImpact: Math.round(conversionImpact),
      aovImpact: Math.round(aovImpact),
      bounceImpact: Math.round(bounceImpact),
      noResultsImpact: Math.round(noResultsImpact),
      total: Math.round(total),
    };
  }, [levers, baselineRevenue, baselineConvRate, baselineAOV]);

  const handleExport = useCallback(async () => {
    const lines = LEVER_CONFIG.map(
      (cfg) =>
        `${cfg.label}: ${levers[cfg.key]}% → ${formatCurrency(
          cfg.key === "conversionLift"
            ? calculations.conversionImpact
            : cfg.key === "aovIncrease"
              ? calculations.aovImpact
              : cfg.key === "bounceReduction"
                ? calculations.bounceImpact
                : calculations.noResultsImpact
        )}`
    );
    const summary = [
      "PRISM ROI Estimate",
      `Annual Digital Revenue: $${baselineRevenue.toLocaleString()}`,
      `Baseline Conv Rate: ${baselineConvRate}%`,
      `Average Order Value: $${baselineAOV}`,
      "",
      ...lines,
      "",
      `Total Annual Revenue Impact: ${formatCurrency(calculations.total)}`,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may fail in some contexts
    }
  }, [levers, calculations, baselineRevenue, baselineConvRate, baselineAOV]);

  // -------------------------------------------------------------------------
  // Compact mode — minimal summary
  // -------------------------------------------------------------------------
  if (compact) {
    return (
      <div className="rounded-lg bg-gradient-to-r from-[#090e24] to-[#1a2356] p-4 text-white">
        <p className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">
          Estimated Annual Revenue Impact
        </p>
        <div className="text-2xl font-semibold">
          $<NumberFlow value={calculations.total} />
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Full two-panel layout
  // -------------------------------------------------------------------------
  return (
    <div
      className="w-full bg-white rounded-lg overflow-hidden border border-gray-200 mb-6"
      style={{ boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px]">
        {/* ---- Left Panel: Builder ---- */}
        <div className="p-6 lg:border-r border-gray-200">
          {/* Description */}
          <p className="text-sm text-gray-500 mb-5">
            Adjust the baseline inputs and value levers below to model the
            revenue impact of upgrading your site search with Algolia.
          </p>

          {/* Baseline inputs row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6 pb-5 border-b border-gray-200">
            {/* Annual Digital Revenue */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-1.5">
                Annual Digital Rev
              </label>
              <div className="relative">
                <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 font-semibold text-sm">
                  $
                </span>
                <input
                  type="text"
                  value={baselineRevenue.toLocaleString()}
                  onChange={(e) => {
                    const raw = e.target.value.replace(/[^0-9]/g, "");
                    if (raw) setBaselineRevenue(Number(raw));
                  }}
                  className="w-full py-2 pl-6 pr-2.5 border border-gray-200 rounded text-[15px] font-semibold text-[#23263B] focus:border-[#5468FF] focus:ring-2 focus:ring-[#5468FF]/15 outline-none transition-colors"
                  style={{ fontFamily: "'Sora', sans-serif" }}
                />
              </div>
            </div>

            {/* Baseline Conv Rate */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-1.5">
                Baseline Conv Rate
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={baselineConvRate}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    if (!isNaN(val) && val >= 0 && val <= 100)
                      setBaselineConvRate(val);
                    if (e.target.value === "") setBaselineConvRate(0);
                  }}
                  className="w-full py-2 px-2.5 pr-7 border border-gray-200 rounded text-[15px] font-semibold text-[#23263B] focus:border-[#5468FF] focus:ring-2 focus:ring-[#5468FF]/15 outline-none transition-colors"
                  style={{ fontFamily: "'Sora', sans-serif" }}
                />
                <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 font-semibold text-sm">
                  %
                </span>
              </div>
            </div>

            {/* Average Order Value */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-1.5">
                Average Order Value
              </label>
              <div className="relative">
                <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 font-semibold text-sm">
                  $
                </span>
                <input
                  type="text"
                  value={baselineAOV.toLocaleString()}
                  onChange={(e) => {
                    const raw = e.target.value.replace(/[^0-9.]/g, "");
                    const val = parseFloat(raw);
                    if (!isNaN(val)) setBaselineAOV(val);
                    if (raw === "") setBaselineAOV(0);
                  }}
                  className="w-full py-2 pl-6 pr-2.5 border border-gray-200 rounded text-[15px] font-semibold text-[#23263B] focus:border-[#5468FF] focus:ring-2 focus:ring-[#5468FF]/15 outline-none transition-colors"
                  style={{ fontFamily: "'Sora', sans-serif" }}
                />
              </div>
            </div>
          </div>

          {/* Value Levers header */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-base font-normal text-[#23263B]">
              Value Levers
            </span>
            <span className="bg-[#7C3AED] text-white px-2 py-1 text-[9px] font-semibold uppercase tracking-wide rounded">
              15 Case Studies Verified
            </span>
          </div>

          {/* Lever rows */}
          <div className="space-y-3">
            {LEVER_CONFIG.map((cfg) => {
              const impactValue =
                cfg.key === "conversionLift"
                  ? calculations.conversionImpact
                  : cfg.key === "aovIncrease"
                    ? calculations.aovImpact
                    : cfg.key === "bounceReduction"
                      ? calculations.bounceImpact
                      : calculations.noResultsImpact;

              return (
                <div
                  key={cfg.key}
                  className="bg-[#F5F5F7] border border-gray-200 rounded-md p-4"
                >
                  {/* Header row */}
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-semibold text-sm text-[#23263B]">
                      {cfg.label}
                    </span>
                    <span className="text-sm font-bold text-[#003DFF] bg-[#EEF2FF] px-2 py-0.5 rounded-xl">
                      +{levers[cfg.key]}%
                    </span>
                  </div>

                  {/* Range slider */}
                  <input
                    type="range"
                    min={cfg.min}
                    max={cfg.max}
                    value={levers[cfg.key]}
                    onChange={(e) =>
                      handleLeverChange(cfg.key, Number(e.target.value))
                    }
                    className="w-full h-1 appearance-none rounded-full bg-gray-300 cursor-pointer
                      [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#003DFF] [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-[0_1px_4px_rgba(0,0,0,0.2)]
                      [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-[#003DFF] [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:shadow-[0_1px_4px_rgba(0,0,0,0.2)]"
                  />

                  {/* Proof point */}
                  <div className="mt-3 border border-dashed border-gray-300 rounded px-3 py-2 flex items-start gap-2">
                    <span className="shrink-0 bg-[#7C3AED] text-white text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded mt-0.5">
                      Case Study
                    </span>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      <span className="font-bold text-[#23263B]">
                        {cfg.proof.company}
                      </span>
                      {" — "}
                      {cfg.proof.result}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Copy button */}
          <button
            onClick={handleExport}
            className="mt-4 flex items-center justify-center gap-1.5 w-full py-2 border border-gray-200 rounded text-xs text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <Copy className="h-3 w-3" />
            {copied ? "Copied!" : "Copy Summary"}
          </button>
        </div>

        {/* ---- Right Panel: Summary ---- */}
        <div
          className="p-6 lg:p-[30px_24px] flex flex-col justify-center text-white"
          style={{
            background: "linear-gradient(135deg, #090e24, #1a2356)",
          }}
        >
          {/* Total */}
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-2">
            Total Annual Revenue Impact
          </p>
          <div className="text-4xl font-semibold text-white mb-8">
            $<NumberFlow value={calculations.total} />
          </div>

          {/* Breakdown */}
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-4">
            Impact Breakdown
          </p>
          <div className="space-y-2">
            {[
              { label: "Conversion Lift", value: calculations.conversionImpact },
              { label: "AOV Increase", value: calculations.aovImpact },
              { label: "Bounce Reduction", value: calculations.bounceImpact },
              {
                label: "No-Results Recovery",
                value: calculations.noResultsImpact,
              },
            ].map((row, i) => (
              <div
                key={row.label}
                className={cn(
                  "flex items-center justify-between pb-2",
                  i < 3 && "border-b border-white/10"
                )}
              >
                <span className="text-xs text-slate-300">{row.label}</span>
                <span className="text-sm font-semibold text-white">
                  {formatCurrency(row.value)}
                </span>
              </div>
            ))}
          </div>

          {/* Formula note */}
          <p className="text-[10px] text-slate-500 leading-snug mt-8">
            Estimates assume 15% of digital revenue flows through site search.
            Bounce rate base: 30% of search traffic. No-results base: 10% of
            search queries. Actual results vary by implementation.
          </p>
        </div>
      </div>
    </div>
  );
}
