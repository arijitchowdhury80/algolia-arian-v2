"use client";

import { UserButton } from "@clerk/nextjs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Diamond } from "lucide-react";
import Image from "next/image";
import { usePrismStore } from "@/lib/store";

const isBypassAuth = process.env.NEXT_PUBLIC_BYPASS_AUTH === "true";

/**
 * TopBar — dark navy header spanning full width above all three panels.
 *
 * Left:   Algolia logo + divider + "PRISM" label
 * Center: current account name + domain (if selected)
 * Right:  user avatar/name
 */
export function Header() {
  const currentDomain = usePrismStore((s) => s.currentDomain);
  const companyName = usePrismStore((s) => s.currentCompanyName);

  return (
    <header className="h-[50px] bg-[#1C1E26] flex items-center px-5 shrink-0 border-b-2 border-[rgba(0,61,255,0.1)] relative z-50">
      {/* Loading progress bar animation */}
      <div className="absolute bottom-[-2px] left-0 h-[2px] bg-[#003DFF] animate-[loadProgress_1.5s_ease-out_forwards]" />

      {/* Left: Algolia logo + PRISM */}
      <div className="flex items-center gap-3">
        <Image
          src="/algolia-logo.svg"
          alt="Algolia"
          width={80}
          height={19}
          className="brightness-0 invert"
          priority
        />
        <div className="w-px h-5 bg-white/20" />
        <div className="flex items-center gap-1.5">
          <Diamond className="h-3.5 w-3.5 text-[#5468FF]" />
          <span className="text-[13px] font-semibold text-white tracking-tight">
            PRISM
          </span>
        </div>
      </div>

      {/* Center: current account */}
      <div className="flex-1 flex items-center justify-center">
        {currentDomain ? (
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-semibold text-white">
              {companyName ?? currentDomain}
            </span>
            {companyName && (
              <span className="text-[11px] text-white/40">
                {currentDomain}
              </span>
            )}
          </div>
        ) : (
          <span className="text-[11px] text-white/40">
            Light goes in, intelligence comes out
          </span>
        )}
      </div>

      {/* Right: user avatar */}
      <div className="flex items-center gap-3">
        {isBypassAuth ? (
          <Avatar className="h-7 w-7">
            <AvatarFallback className="bg-[#003DFF] text-white text-[11px] font-medium">
              AC
            </AvatarFallback>
          </Avatar>
        ) : (
          <UserButton
            appearance={{
              elements: {
                avatarBox: "h-7 w-7",
              },
            }}
          />
        )}
      </div>
    </header>
  );
}

/**
 * AI Disclaimer Footer — sliding ticker warning that AI can make mistakes.
 */
export function DisclaimerFooter() {
  return (
    <div className="h-[28px] bg-[#1C1E26] border-t border-[rgba(0,61,255,0.1)] overflow-hidden relative shrink-0">
      <span className="absolute top-1/2 -translate-y-1/2 whitespace-nowrap text-[15px] font-semibold text-[#DC2626] animate-[ticker_240s_linear_infinite]">
        ⚠ All data elements are source-linked. Always double-check and verify before using. AI can make mistakes.
      </span>
      <style jsx>{`
        @keyframes ticker {
          0%   { left: 100%; opacity: 1; }
          5%   { opacity: 1; }
          45%  { left: -100%; opacity: 1; }
          50%  { left: -100%; opacity: 0; }
          51%  { left: 100%; opacity: 0; }
          55%  { opacity: 1; }
          100% { left: 100%; opacity: 1; }
        }
      `}</style>
    </div>
  );
}
