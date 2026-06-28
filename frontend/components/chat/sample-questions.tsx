"use client";

import { useState } from "react";
import { Sparkles, ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useComposerRuntime } from "@assistant-ui/react";

const SAMPLE_QUESTIONS = [
  // Company Intelligence
  { label: "Company Profile", prompt: "Tell me about ", hint: "e.g. dell.com" },
  { label: "Tech Stack", prompt: "What tech stack does ", hint: "e.g. nike.com" },
  { label: "Traffic Analysis", prompt: "Show me traffic analytics for ", hint: "e.g. costco.com" },
  { label: "Public Financials", prompt: "What are the financials and revenue trends for ", hint: "e.g. Dell" },
  { label: "Private Financials", prompt: "Estimate revenue for ", hint: "e.g. patagonia.com" },
  { label: "Company News", prompt: "What's in the news about ", hint: "e.g. Home Depot" },

  // People Intelligence
  { label: "Hiring Intel", prompt: "Who is hiring at ", hint: "e.g. nordstrom.com" },
  { label: "Social Intel", prompt: "What are executives saying on LinkedIn at ", hint: "e.g. Nike" },
  { label: "Investor Intel", prompt: "What did the CEO say on earnings calls at ", hint: "e.g. Dell" },

  // Market Intelligence
  { label: "Competitor Matrix", prompt: "Compare competitors across all dimensions for ", hint: "e.g. Dell vs HP vs Lenovo" },
  { label: "Industry Benchmarks", prompt: "What are the benchmarks for ", hint: "e.g. retail ecommerce" },
  { label: "Partner Ecosystem", prompt: "What's the partner ecosystem for ", hint: "e.g. bestbuy.com" },

  // Audit & Analysis
  { label: "Quick Lookup", prompt: "Quick lookup on ", hint: "e.g. jewson.co.uk" },
  { label: "Full Audit", prompt: "Run a full audit on ", hint: "e.g. nike.com" },
  { label: "Test Queries", prompt: "Generate test search queries for ", hint: "e.g. dell.com" },
  { label: "Browser Audit", prompt: "Test the live search experience on ", hint: "e.g. bestbuy.com" },

  // Sales Enablement
  { label: "Business Case", prompt: "Build the business case and ROI for ", hint: "e.g. dell.com" },
  { label: "Sales Plays", prompt: "Generate MEDDPICC sales plays for ", hint: "e.g. nordstrom.com" },
  { label: "Audit Report", prompt: "Generate the full audit report for ", hint: "e.g. dell.com" },
  { label: "ABX Campaign", prompt: "Create an email campaign for ", hint: "e.g. costco.com" },

  // Benchmarks
  { label: "Vertical Benchmarks", prompt: "Show vertical benchmarks for ", hint: "e.g. Consumer Electronics" },
  { label: "Factcheck", prompt: "Factcheck all claims from the latest audit", hint: "" },
];

export function SampleQuestions() {
  const [isOpen, setIsOpen] = useState(false);
  const composerRuntime = useComposerRuntime();

  const handleSelect = (prompt: string) => {
    composerRuntime.setText(prompt);
    // Focus the composer input so user can immediately type their argument
    requestAnimationFrame(() => {
      const input = document.querySelector<HTMLTextAreaElement>(".aui-composer-input");
      if (input) {
        input.focus();
        // Place cursor at the end of the text
        const len = prompt.length;
        input.setSelectionRange(len, len);
      }
    });
  };

  return (
    <div className="relative w-full">
      {/* Expandable panel — above the button */}
      {isOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-[var(--border-warm)] bg-white shadow-lg z-50">
          <div className="p-3 max-h-[60vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-1.5 min-w-0">
              {SAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q.label}
                  type="button"
                  onClick={() => {
                    handleSelect(q.prompt);
                    setIsOpen(false);
                  }}
                  className={cn(
                    "flex flex-col items-start gap-0.5 rounded-lg px-3 py-2 text-left transition-colors min-w-0 overflow-hidden",
                    "hover:bg-[#003DFF]/5 hover:border-[#003DFF]/20",
                    "border border-transparent"
                  )}
                >
                  <span className="text-[11px] font-semibold text-[#003DFF]">
                    {q.label}
                  </span>
                  <span className="text-[11px] text-[var(--muted-text)] leading-snug line-clamp-1 italic">
                    {q.hint || q.prompt}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Toggle button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "mx-auto flex items-center gap-1.5 rounded-full border px-4 py-1.5 text-xs font-medium transition-all",
          isOpen
            ? "border-[#003DFF]/30 bg-[#003DFF]/5 text-[#003DFF]"
            : "border-[var(--border-warm)] bg-white text-[var(--muted-text)] hover:border-[#003DFF]/30 hover:text-[#003DFF]"
        )}
      >
        <Sparkles className="h-3.5 w-3.5" />
        Sample Questions
        {isOpen ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronUp className="h-3 w-3" />
        )}
      </button>
    </div>
  );
}
