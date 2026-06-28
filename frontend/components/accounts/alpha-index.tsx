"use client";

import { cn } from "@/lib/utils";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

interface AlphaIndexProps {
  availableLetters: Set<string>;
  activeLetter: string | null;
  onLetterClick: (letter: string) => void;
}

export function AlphaIndex({ availableLetters, activeLetter, onLetterClick }: AlphaIndexProps) {
  return (
    <div className="flex flex-col items-center py-1" role="navigation" aria-label="Alphabetic index">
      {LETTERS.map((letter) => {
        const isAvailable = availableLetters.has(letter);
        const isActive = activeLetter === letter;
        return (
          <button
            key={letter}
            type="button"
            disabled={!isAvailable}
            onClick={() => onLetterClick(letter)}
            className={cn(
              "h-[18px] w-5 text-center text-[9px] font-semibold leading-[18px] transition-colors rounded-sm",
              isActive
                ? "bg-[#003DFF] text-white"
                : isAvailable
                  ? "text-[#23263B] hover:bg-[#EDEDF0] cursor-pointer"
                  : "text-[var(--muted-text)]/40 cursor-default"
            )}
          >
            {letter}
          </button>
        );
      })}
    </div>
  );
}
