"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Search, X } from "lucide-react";

interface AccountSearchProps {
  totalCount: number;
  filteredCount: number;
  onSearch: (query: string) => void;
}

export function AccountSearch({ totalCount, filteredCount, onSearch }: AccountSearchProps) {
  const [value, setValue] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const debouncedSearch = useCallback(
    (query: string) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        onSearch(query);
      }, 150);
    },
    [onSearch]
  );

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const q = e.target.value;
    setValue(q);
    debouncedSearch(q);
  }

  function handleClear() {
    setValue("");
    onSearch("");
  }

  return (
    <div className="space-y-1">
      <div className="relative">
        <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-[var(--muted-text)]" />
        <input
          value={value}
          onChange={handleChange}
          placeholder="Search accounts..."
          className="h-7 w-full rounded-md bg-[#EDEDF0] pl-8 pr-7 text-xs text-[#23263B] placeholder:text-[var(--muted-text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-warm)]"
        />
        {value && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2 top-1.5 rounded p-0.5 text-[var(--muted-text)] hover:text-[#23263B]"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
      <p className="px-1 text-[10px] text-[var(--muted-text)]">
        {filteredCount === totalCount
          ? `${totalCount} accounts`
          : `${filteredCount} of ${totalCount} accounts`}
      </p>
    </div>
  );
}
