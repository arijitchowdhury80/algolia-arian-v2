"use client";

import dynamic from "next/dynamic";
import { Header, DisclaimerFooter } from "./header";
import { CenterPanel } from "./center-panel";
import { RightPanel } from "./right-panel";

// Both panels use react-resizable-panels — load client-only to avoid SSR hydration mismatch
const LeftPanel = dynamic(() => import("./left-panel").then((m) => m.LeftPanel), { ssr: false });

// Resizable three-panel shell — loaded client-only for same reason
const ResizableShell = dynamic(
  () => import("./resizable-shell").then((m) => m.ResizableShell),
  { ssr: false }
);

/**
 * AppShell — Three-panel layout with resizable side panels.
 *
 * Left (default 18%, min 14%): Account list + ROI calculator
 * Center (default 58%, flex):  Intelligence dashboard with tabbed content
 * Right (default 24%, min 18%): aRRIe chat panel
 *
 * All three panels are user-resizable via drag handles.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col">
      <Header />
      <ResizableShell>
        {children}
      </ResizableShell>
      <DisclaimerFooter />
    </div>
  );
}
