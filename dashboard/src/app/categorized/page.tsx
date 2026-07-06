import { listTemplates } from "@/lib/api";
import TemplateCard from "@/components/TemplateCard";

export const dynamic = "force-dynamic";

export default async function CategorizedPage() {
  const templates = await listTemplates("categorized");

  return (
    <div className="mx-auto max-w-5xl w-full px-5 py-8 flex-1">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="text-2xl" style={{ fontFamily: "var(--font-display)" }}>
          categorized
        </h1>
        <span className="text-[12px] text-[var(--ink-dim)]">
          {templates.length} template{templates.length === 1 ? "" : "s"}
        </span>
      </div>

      {templates.length === 0 ? (
        <div className="border border-dashed border-[var(--line)] py-16 text-center text-[var(--ink-dim)] text-[13px]">
          no templates categorized yet.
        </div>
      ) : (
        <div className="space-y-3">
          {templates.map((t) => (
            <TemplateCard key={t.cluster_id} template={t} showCategorizeForm />
          ))}
        </div>
      )}
    </div>
  );
}
