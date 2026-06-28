"use client";

import { PanelGroup, Panel, PanelResizeHandle } from "react-resizable-panels";
import { LeftPanel } from "./left-panel";
import { CenterPanel } from "./center-panel";
import { RightPanel } from "./right-panel";

/**
 * ResizableShell — client-only three-panel layout with drag handles.
 * Loaded via dynamic import from AppShell to avoid SSR hydration issues.
 */
export function ResizableShell({ children }: { children: React.ReactNode }) {
  return (
    <PanelGroup direction="horizontal" className="flex-1 min-h-0">
      {/* Left panel */}
      <Panel defaultSize={18} minSize={14} maxSize={28}>
        <LeftPanel />
      </Panel>

      {/* Drag handle — left */}
      <PanelResizeHandle
        className="group relative w-[5px] flex items-center justify-center bg-transparent hover:bg-[#003DFF]/10 transition-colors"
      >
        <div className="w-[1px] h-full bg-[rgba(0,0,0,0.08)] group-hover:bg-[#003DFF]/30 transition-colors" />
      </PanelResizeHandle>

      {/* Center panel */}
      <Panel defaultSize={58} minSize={40}>
        <CenterPanel>{children}</CenterPanel>
      </Panel>

      {/* Drag handle — right */}
      <PanelResizeHandle
        className="group relative w-[5px] flex items-center justify-center bg-transparent hover:bg-[#003DFF]/10 transition-colors"
      >
        <div className="w-[1px] h-full bg-[rgba(0,0,0,0.08)] group-hover:bg-[#003DFF]/30 transition-colors" />
      </PanelResizeHandle>

      {/* Right panel */}
      <Panel defaultSize={24} minSize={18} maxSize={36}>
        <RightPanel />
      </Panel>
    </PanelGroup>
  );
}
