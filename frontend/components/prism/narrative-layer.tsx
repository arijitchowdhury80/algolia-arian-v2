/**
 * NarrativeLayer — section divider with a plain-language zone label.
 * Tokens: text-caption (12px), text-brand-muted (#6B7280)
 */

interface NarrativeLayerProps {
  label: string;
}

export function NarrativeLayer({ label }: NarrativeLayerProps) {
  return (
    <div className="flex items-center gap-3 my-2">
      <div className="flex-1 h-px" style={{ background: "rgba(0,0,0,0.09)" }} />
      <span
        className="select-none whitespace-nowrap text-brand-muted"
        style={{
          fontSize: "12px",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.14em",
          padding: "0 4px",
        }}
      >
        {label}
      </span>
      <div className="flex-1 h-px" style={{ background: "rgba(0,0,0,0.09)" }} />
    </div>
  );
}
