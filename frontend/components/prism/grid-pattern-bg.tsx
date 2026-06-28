"use client";

import { useId } from "react";

function genRandomPattern(length = 5): number[][] {
  return Array.from({ length }, () => [
    Math.floor(Math.random() * 4) + 7,
    Math.floor(Math.random() * 6) + 1,
  ]);
}

export function GridPatternBg() {
  const patternId = useId();
  const squares = genRandomPattern(5);

  return (
    <div
      className="pointer-events-none absolute inset-0"
      style={{
        maskImage: "linear-gradient(white, transparent)",
        WebkitMaskImage: "linear-gradient(white, transparent)",
        zIndex: 1,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(to right, rgba(255,255,255,0.03), rgba(255,255,255,0.01))",
          maskImage: "radial-gradient(farthest-side at top, white, transparent)",
          WebkitMaskImage:
            "radial-gradient(farthest-side at top, white, transparent)",
        }}
      >
        <svg
          aria-hidden="true"
          className="absolute inset-0 h-full w-full"
          style={{
            fill: "rgba(255,255,255,0.05)",
            stroke: "rgba(255,255,255,0.20)",
            mixBlendMode: "overlay",
          }}
        >
          <defs>
            <pattern
              id={patternId}
              width={20}
              height={20}
              patternUnits="userSpaceOnUse"
              x="-12"
              y="4"
            >
              <path d="M.5 20V.5H20" fill="none" />
            </pattern>
          </defs>
          <rect
            width="100%"
            height="100%"
            strokeWidth={0}
            fill={`url(#${patternId})`}
          />
          <svg x="-12" y="4" className="overflow-visible">
            {squares.map(([x, y], i) => (
              <rect
                key={i}
                strokeWidth={0}
                width={21}
                height={21}
                x={x * 20}
                y={y * 20}
              />
            ))}
          </svg>
        </svg>
      </div>
    </div>
  );
}
