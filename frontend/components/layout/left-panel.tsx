"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { PanelGroup, Panel, PanelResizeHandle } from "react-resizable-panels";
import { Plus, GripHorizontal } from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { AccountSearch } from "@/components/accounts/account-search";
import { AccountList } from "@/components/accounts/account-list";
import { AlphaIndex } from "@/components/accounts/alpha-index";
import { ROICalculator } from "@/components/prism/roi-calculator";
import { usePrismStore } from "@/lib/store";
import type { AccountListHandle } from "@/components/accounts/account-list";
import type { Account } from "@/components/accounts/account-item";

const isBypassAuth = process.env.NEXT_PUBLIC_BYPASS_AUTH === "true";

/** Response shape from GET /api/v1/accounts/{domain}/results */
interface AccountResultsResponse {
  domain: string;
  company_name: string | null;
  modules: Record<string, unknown>;
  last_audit_date: string | null;
  audit_status: string | null;
}

/**
 * Fetch all module results for a domain and populate the Zustand store.
 * Called when the user selects an account in the left panel.
 */
async function loadAccountResults(domain: string): Promise<void> {
  const apiUrl =
    process.env.NEXT_PUBLIC_PRISM_API_URL || "http://localhost:8000";

  try {
    const res = await fetch(
      `${apiUrl}/api/v1/accounts/${encodeURIComponent(domain)}/results`
    );

    if (!res.ok) {
      console.error("[left-panel] Failed to fetch account results", {
        domain,
        status: res.status,
      });
      return;
    }

    const data: AccountResultsResponse = await res.json();
    const store = usePrismStore.getState();

    store.clearResults();
    store.setCurrentDomain(domain);

    for (const [moduleName, output] of Object.entries(data.modules)) {
      if (output == null) continue;
      store.addResult(moduleName, {
        module_name: moduleName,
        module_version: "1.0.0",
        status: "success",
        output: output as Record<string, unknown>,
        sources: [],
        duration_ms: 0,
        errors: [],
        warnings: [],
      });
    }

    const moduleCount = Object.keys(data.modules).length;
    console.info("[left-panel] Loaded account results", {
      domain,
      moduleCount,
    });
  } catch (error) {
    console.error("[left-panel] Failed to load account results", {
      domain,
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

export function LeftPanel() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeAccountId, setActiveAccountId] = useState<string | null>(null);
  const accountListRef = useRef<AccountListHandle>(null);

  // Load accounts on mount
  useEffect(() => {
    async function loadAccounts() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_PRISM_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/v1/accounts/`);
        if (!res.ok) {
          console.warn("[LeftPanel] Backend returned", res.status, "— showing empty list");
          return;
        }
        const data: Account[] = await res.json();
        // Sort alphabetically
        data.sort((a, b) => a.company_name.localeCompare(b.company_name));
        // Deduplicate by domain (backend should already do this, but safety net)
        const seen = new Set<string>();
        const deduped = data.filter((a) => {
          const key = a.domain.toLowerCase();
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
        setAccounts(deduped);
      } catch (err) {
        console.error("[LeftPanel] Failed to load accounts:", err);
      }
    }
    loadAccounts();
  }, []);

  // Filter accounts by search
  const filteredAccounts = useMemo(() => {
    if (!searchQuery.trim()) return accounts;
    const q = searchQuery.toLowerCase();
    return accounts.filter(
      (a) =>
        a.company_name.toLowerCase().includes(q) ||
        a.domain.toLowerCase().includes(q)
    );
  }, [accounts, searchQuery]);

  // Compute which letters have accounts
  const availableLetters = useMemo(() => {
    const letters = new Set<string>();
    filteredAccounts.forEach((a) => {
      const first = a.company_name.charAt(0).toUpperCase();
      if (first >= "A" && first <= "Z") letters.add(first);
    });
    return letters;
  }, [filteredAccounts]);

  // Compute active letter from first visible item
  const activeLetter = useMemo(() => {
    if (filteredAccounts.length === 0) return null;
    return filteredAccounts[0].company_name.charAt(0).toUpperCase();
  }, [filteredAccounts]);

  const handleLetterClick = useCallback(
    (letter: string) => {
      const index = filteredAccounts.findIndex(
        (a) => a.company_name.charAt(0).toUpperCase() === letter
      );
      if (index >= 0) {
        accountListRef.current?.scrollToIndex(index);
      }
    },
    [filteredAccounts]
  );

  const handleSelectAccount = useCallback((account: Account) => {
    setActiveAccountId(account.id);

    // Update global store and fetch all module results for this account
    const store = usePrismStore.getState();
    store.clearResults();
    store.setCurrentDomain(account.domain);
    store.setCurrentCompanyName(account.company_name);
    store.setActiveTab("overview");

    // Load full audit data in the background
    loadAccountResults(account.domain);
  }, []);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  return (
    <div className="flex h-full flex-col bg-[var(--sidebar-bg)] border-r border-[var(--border-warm)]">
      <PanelGroup direction="vertical">
        {/* Top section: accounts */}
        <Panel defaultSize={60} minSize={30}>
          <div className="flex h-full flex-col">
            {/* New audit button */}
            <div className="px-3 pt-3 pb-2">
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-[#23263B] transition-colors hover:bg-[#EDEDF0]"
              >
                <Plus className="h-4 w-4" />
                New audit
              </button>
            </div>

            {/* Search */}
            <div className="px-3 pb-2">
              <AccountSearch
                totalCount={accounts.length}
                filteredCount={filteredAccounts.length}
                onSearch={handleSearch}
              />
            </div>

            {/* Account list + alpha index */}
            <div className="flex flex-1 min-h-0">
              <div className="flex-1 min-w-0 overflow-hidden">
                <AccountList
                  ref={accountListRef}
                  accounts={filteredAccounts}
                  activeAccountId={activeAccountId}
                  onSelectAccount={handleSelectAccount}
                />
              </div>
              <div className="shrink-0 border-l border-[var(--border-warm)] px-0.5">
                <AlphaIndex
                  availableLetters={availableLetters}
                  activeLetter={activeLetter}
                  onLetterClick={handleLetterClick}
                />
              </div>
            </div>
          </div>
        </Panel>

        {/* Vertical resize handle */}
        <PanelResizeHandle className="group relative flex h-px items-center justify-center bg-[var(--border-warm)] transition-colors hover:bg-[#5468FF]">
          <div className="z-10 flex h-3 w-6 items-center justify-center rounded-sm bg-white border border-[var(--border-warm)] opacity-0 group-hover:opacity-100 transition-opacity">
            <GripHorizontal className="h-3 w-3 text-[var(--muted-text)]" />
          </div>
        </PanelResizeHandle>

        {/* Bottom section: ROI Calculator */}
        <Panel defaultSize={40} minSize={15}>
          <div className="h-full overflow-y-auto">
            <ROICalculator compact />
          </div>
        </Panel>
      </PanelGroup>

      {/* User profile at bottom */}
      <div className="border-t border-[var(--border-warm)] px-3 py-3">
        <div className="flex items-center gap-2.5">
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
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-medium text-[#23263B]">
              Arijit Chowdhury
            </p>
            <p className="text-[10px] text-[var(--muted-text)]">Pro</p>
          </div>
        </div>
      </div>
    </div>
  );
}
