"use client";

import { motion } from "framer-motion";
import { Diamond, Search, BarChart3, Zap, Target } from "lucide-react";

/**
 * WelcomeMessage — animated welcome state for empty chat.
 * Pattern: adapted from 21st.dev animated-ai-chat component,
 * restyled for Algolia light branding.
 */

const suggestions = [
  {
    icon: <Search className="h-4 w-4" />,
    label: "Analyze tech stack",
    query: "What technology does dell.com use?",
  },
  {
    icon: <BarChart3 className="h-4 w-4" />,
    label: "Run full audit",
    query: "Run a full audit on nordstrom.com",
  },
  {
    icon: <Target className="h-4 w-4" />,
    label: "Check search vendor",
    query: "Check the search vendor for target.com",
  },
  {
    icon: <Zap className="h-4 w-4" />,
    label: "Audit status",
    query: "What's the status of my last audit?",
  },
];

interface WelcomeMessageProps {
  onSuggestionClick?: (query: string) => void;
}

export function WelcomeMessage({ onSuggestionClick }: WelcomeMessageProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 relative">
      <motion.div
        className="relative z-10 space-y-10 w-full max-w-lg"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        {/* Logo + heading */}
        <div className="text-center space-y-3">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="flex items-center justify-center"
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#003DFF]/10 shadow-lg shadow-[#003DFF]/5">
              <Diamond className="h-7 w-7 text-[#003DFF]" />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            <h1 className="text-2xl font-semibold tracking-tight text-[#23263B]">
              Welcome to Prism
            </h1>
            <motion.div
              className="mx-auto mt-2 h-px bg-gradient-to-r from-transparent via-[#003DFF]/20 to-transparent"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: "60%", opacity: 1 }}
              transition={{ delay: 0.5, duration: 0.8 }}
            />
          </motion.div>

          <motion.p
            className="text-sm text-[var(--muted-text)]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            Light goes in. Intelligence comes out.
          </motion.p>
        </div>

        {/* Suggestion buttons — animated-ai-chat pattern */}
        <div className="grid grid-cols-2 gap-2">
          {suggestions.map((suggestion, index) => (
            <motion.button
              key={suggestion.query}
              type="button"
              onClick={() => onSuggestionClick?.(suggestion.query)}
              className="group relative flex items-center gap-3 rounded-xl border border-[var(--border-warm)] bg-white px-4 py-3.5 text-left transition-all hover:border-[#003DFF]/20 hover:bg-[#F8F9FF] hover:shadow-sm"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + index * 0.1, duration: 0.4 }}
              whileHover={{ scale: 1.01, y: -1 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#F5F5F7] text-[var(--muted-text)] group-hover:bg-[#003DFF]/10 group-hover:text-[#003DFF] transition-colors">
                {suggestion.icon}
              </div>
              <div className="min-w-0">
                <p className="text-[13px] font-medium text-[#23263B] group-hover:text-[#003DFF] transition-colors">
                  {suggestion.label}
                </p>
                <p className="truncate text-[11px] text-[var(--muted-text)]">
                  {suggestion.query}
                </p>
              </div>
              {/* Hover border glow */}
              <motion.div
                className="absolute inset-0 rounded-xl border border-[#003DFF]/0 group-hover:border-[#003DFF]/15 transition-colors"
                initial={false}
              />
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
