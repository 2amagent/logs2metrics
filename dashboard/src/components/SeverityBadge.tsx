import type { Severity } from "@/lib/api";

const STYLES: Record<string, { fg: string; bg: string; label: string }> = {
  error: { fg: "var(--error)", bg: "var(--error-dim)", label: "error" },
  warning: { fg: "var(--warning)", bg: "var(--warning-dim)", label: "warning" },
  info: { fg: "var(--info)", bg: "var(--info-dim)", label: "info" },
  uncategorized: { fg: "var(--uncategorized)", bg: "var(--uncategorized-dim)", label: "uncategorized" },
};

export default function SeverityBadge({
  severity,
  muted,
}: {
  severity: Severity | null;
  muted?: boolean;
}) {
  const style = STYLES[severity ?? "uncategorized"];
  return (
    <span className="inline-flex items-center gap-1.5 shrink-0">
      <span
        className="px-2 py-0.5 text-[11px] uppercase tracking-wider font-medium"
        style={{ color: style.fg, background: style.bg }}
      >
        {style.label}
      </span>
      {muted && (
        <span
          className="px-1.5 py-0.5 text-[10px] uppercase tracking-wider border border-[var(--line-bright)] text-[var(--ink-faint)]"
          title="Counted but excluded from alerting"
        >
          muted
        </span>
      )}
    </span>
  );
}
