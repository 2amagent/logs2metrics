"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { categorizeTemplate, type Severity } from "@/lib/api";

const OPTIONS: { value: Severity; label: string }[] = [
  { value: "error", label: "error" },
  { value: "warning", label: "warning" },
  { value: "info", label: "info" },
];

export default function CategorizeForm({ clusterId }: { clusterId: number }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [severity, setSeverity] = useState<Severity | null>(null);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  function submit() {
    if (!severity) {
      setError("choose a severity first");
      return;
    }
    setError(null);
    startTransition(async () => {
      try {
        await categorizeTemplate(clusterId, { severity, muted });
        setDone(true);
        router.refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "categorize failed");
      }
    });
  }

  if (done) {
    return (
      <div className="text-[12px] text-[var(--accent)] py-2">
        ✓ categorized — moving to categorized view
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 pt-1">
      <div className="flex border border-[var(--line-bright)]">
        {OPTIONS.map((opt, i) => (
          <button
            key={opt.value}
            onClick={() => setSeverity(opt.value)}
            disabled={isPending}
            className={`px-3 py-1.5 text-[12px] uppercase tracking-wide transition-colors cursor-pointer ${
              i > 0 ? "border-l border-[var(--line-bright)]" : ""
            } ${
              severity === opt.value
                ? "bg-[var(--ink)] text-[var(--bg)]"
                : "text-[var(--ink-dim)] hover:text-[var(--ink)] hover:bg-[var(--bg-inset)]"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <label className="flex items-center gap-1.5 px-2 text-[12px] text-[var(--ink-dim)] cursor-pointer select-none">
        <input
          type="checkbox"
          checked={muted}
          onChange={(e) => setMuted(e.target.checked)}
          className="accent-[var(--accent)]"
        />
        mute
      </label>

      <button
        onClick={submit}
        disabled={isPending}
        className="px-3 py-1.5 text-[12px] uppercase tracking-wide bg-[var(--accent-dim)] text-[var(--accent)] border border-[var(--accent)]/30 hover:border-[var(--accent)] transition-colors disabled:opacity-50 cursor-pointer"
      >
        {isPending ? "saving…" : "categorize"}
      </button>

      {error && <span className="text-[12px] text-[var(--error)]">{error}</span>}
    </div>
  );
}
