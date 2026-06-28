"use client";

import { forwardRef, useImperativeHandle } from "react";
import { List, useListRef } from "react-window";
import type { CSSProperties, ReactElement } from "react";
import { AccountItem } from "./account-item";
import type { Account } from "./account-item";

interface AccountListProps {
  accounts: Account[];
  activeAccountId: string | null;
  onSelectAccount: (account: Account) => void;
}

export interface AccountListHandle {
  scrollToIndex: (index: number) => void;
}

interface RowExtraProps {
  accounts: Account[];
  activeAccountId: string | null;
  onSelectAccount: (account: Account) => void;
}

function AccountRow({
  index,
  style,
  accounts,
  activeAccountId,
  onSelectAccount,
}: {
  index: number;
  style: CSSProperties;
  ariaAttributes: {
    "aria-posinset": number;
    "aria-setsize": number;
    role: "listitem";
  };
  accounts: Account[];
  activeAccountId: string | null;
  onSelectAccount: (account: Account) => void;
}): ReactElement | null {
  const account = accounts[index];
  if (!account) return null;
  return (
    <AccountItem
      account={account}
      isActive={account.id === activeAccountId}
      style={style}
      onClick={onSelectAccount}
    />
  );
}

export const AccountList = forwardRef<AccountListHandle, AccountListProps>(
  function AccountList({ accounts, activeAccountId, onSelectAccount }, ref) {
    const listRefObj = useListRef(null);

    useImperativeHandle(ref, () => ({
      scrollToIndex: (index: number) => {
        listRefObj.current?.scrollToRow({ index, align: "start" });
      },
    }));

    if (accounts.length === 0) {
      return (
        <div className="flex items-center justify-center py-8">
          <p className="text-xs text-[var(--muted-text)]">No accounts found</p>
        </div>
      );
    }

    return (
      <List<RowExtraProps>
        listRef={listRefObj}
        rowCount={accounts.length}
        rowHeight={56}
        overscanCount={5}
        rowComponent={AccountRow}
        rowProps={{ accounts, activeAccountId, onSelectAccount }}
        style={{ height: "100%", width: "100%" }}
      />
    );
  }
);
