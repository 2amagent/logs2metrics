import type { Template } from "@/lib/api";
import SeverityBadge from "./SeverityBadge";
import CategorizeForm from "./CategorizeForm";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function TemplateCard({
  template,
  showCategorizeForm,
}: {
  template: Template;
  showCategorizeForm?: boolean;
}) {
  return (
    <div
      className="border border-[var(--line)] bg-[var(--bg-raised)] hover:border-[var(--line-bright)] transition-colors"
      style={{ animation: "rise 0.3s ease-out both" }}
    >
      <div className="px-4 py-3 flex items-start justify-between gap-4 border-b border-[var(--line)]">
        <code className="text-[13px] text-[var(--ink)] break-all leading-relaxed">
          {template.template || <span className="text-[var(--ink-faint)] italic">(template pending reconciliation)</span>}
        </code>
        <SeverityBadge severity={template.severity} muted={template.muted} />
      </div>

      <div className="px-4 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[var(--ink-dim)] border-b border-[var(--line)]">
        <span>
          <span className="text-[var(--ink)]">{template.match_count}</span> matches
        </span>
        <span>cluster #{template.cluster_id}</span>
        <span>first seen {timeAgo(template.first_seen)}</span>
        <span>last seen {timeAgo(template.last_seen)}</span>
        {template.categorized_by && <span>by {template.categorized_by}</span>}
      </div>

      {template.sample_lines.length > 0 && (
        <div className="px-4 py-2.5 space-y-1 bg-[var(--bg-inset)]">
          {template.sample_lines.map((line, i) => (
            <div key={i} className="text-[11.5px] text-[var(--ink-faint)] truncate">
              {line}
            </div>
          ))}
        </div>
      )}

      {showCategorizeForm && (
        <div className="px-4 py-3">
          <CategorizeForm clusterId={template.cluster_id} />
        </div>
      )}
    </div>
  );
}
