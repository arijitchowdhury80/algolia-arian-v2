"use client";

import { cn } from "@/lib/utils";

export interface Account {
  id: string;
  company_name: string;
  domain: string;
  status: "complete" | "running" | "pending" | "none";
  last_audit: string | null;
  score: number | null;
}

interface AccountItemProps {
  account: Account;
  isActive: boolean;
  style: React.CSSProperties;
  onClick: (account: Account) => void;
}

const statusColors: Record<Account["status"], string> = {
  complete: "bg-green-500",
  running: "bg-amber-400 animate-pulse",
  pending: "bg-blue-400 animate-pulse",
  none: "bg-zinc-300",
};

export function AccountItem({ account, isActive, style, onClick }: AccountItemProps) {
  return (
    <div
      style={style}
      role="button"
      tabIndex={0}
      onClick={() => onClick(account)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick(account);
        }
      }}
      className={cn(
        "flex items-center gap-2.5 px-3 py-1.5 cursor-pointer transition-colors mx-1 rounded-lg",
        isActive
          ? "bg-[#003DFF]/10 border border-[#003DFF]/20"
          : "hover:bg-[#EDEDF0] border border-transparent"
      )}
    >
      {/* Status dot */}
      <div className={cn("h-2 w-2 shrink-0 rounded-full", statusColors[account.status])} />

      {/* Name + domain */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium text-[#23263B]">
          {account.company_name}
        </p>
        <p className="truncate text-[10px] text-[var(--muted-text)]">
          {account.domain}
        </p>
      </div>

      {/* Score */}
      {account.score !== null && (
        <span
          className={cn(
            "shrink-0 text-[11px] font-mono font-semibold",
            account.score < 4
              ? "text-red-500"
              : account.score < 6
                ? "text-amber-500"
                : "text-green-500"
          )}
        >
          {account.score.toFixed(1)}
        </span>
      )}

      {/* Status label */}
      {account.status !== "none" && (
        <span className="shrink-0 text-[9px] font-medium uppercase text-[var(--muted-text)]">
          {account.status}
        </span>
      )}
    </div>
  );
}
