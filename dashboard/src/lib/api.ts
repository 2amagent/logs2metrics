export type Severity = "error" | "warning" | "info";
export type TemplateStatus = "pending" | "categorized";

export interface Template {
  cluster_id: number;
  template: string;
  severity: Severity | null;
  muted: boolean;
  status: TemplateStatus;
  match_count: number;
  sample_lines: string[];
  first_seen: string;
  last_seen: string;
  categorized_by: string | null;
  categorized_at: string | null;
}

export interface CategorizeInput {
  severity: Severity;
  muted: boolean;
  actor?: string;
}

// Server Components call the FastAPI service directly (no network hop through
// our own proxy route needed on the server side); the browser-side mutation
// in CategorizeForm goes through /api/... so it stays same-origin and can
// later carry auth cookies/headers without the API needing to know about them.
const API_URL = process.env.LOGTRIAGE_API_URL ?? "http://localhost:8000";

export async function listTemplates(status: TemplateStatus): Promise<Template[]> {
  const res = await fetch(`${API_URL}/api/templates?status=${status}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to load ${status} templates: ${res.status}`);
  }
  return res.json();
}

export async function categorizeTemplate(
  clusterId: number,
  input: CategorizeInput,
): Promise<Template> {
  const res = await fetch(`/api/templates/${clusterId}/categorize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Categorize failed: ${res.status}`);
  }
  return res.json();
}
