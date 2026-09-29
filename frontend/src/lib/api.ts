// api.ts — typed client for the Samanvay backend. One thin fetch wrapper +
// the response shapes that mirror backend/app/schemas/dto.py.

export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---- types ---------------------------------------------------------------
export interface Batch {
  id: number;
  name: string;
  source_file: string | null;
  n_rows: number;
  created_at: string;
}

export interface Metrics {
  has_ground_truth: boolean;
  precision?: number;
  recall?: number;
  f1?: number;
  tp?: number;
  fp?: number;
  fn?: number;
  blocking_recall?: number;
  pure_fraction?: number;
  groups_recovered_exactly?: number;
  truth_groups?: number;
}

export interface Job {
  id: number;
  batch_id: number;
  status: "pending" | "running" | "done" | "failed";
  params: Record<string, number>;
  metrics: Metrics;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface CategoryStat {
  category: string;
  raw: number;
  canonical: number;
}

export interface AnalyticsSummary {
  total_raw: number;
  total_canonical: number;
  duplicate_rows: number;
  duplication_rate: number;
  clusters_multi: number;
  clusters_total: number;
  review_pending: number;
  potential_savings: number;
  by_category: CategoryStat[];
  by_cpse: Record<string, number>;
  metrics: Metrics;
}

export interface Member {
  raw_id: number;
  cpse: string | null;
  local_code: string;
  description: string;
  clean_desc: string | null;
  price: number;
}

export interface Canonical {
  id: number;
  cluster_id: number;
  cnmc: string;
  category: string;
  unspsc_code: string;
  unspsc_title: string;
  std_description: string;
  uom: string;
  attributes: Record<string, string | number>;
  n_members: number;
  n_cpses: number;
}

export interface Cluster {
  id: number;
  status: "proposed" | "approved" | "rejected";
  size: number;
  confidence: number;
  canonical: Canonical | null;
  members: Member[];
}

export interface Material {
  id: number;
  cpse: string | null;
  local_code: string;
  description: string;
  uom: string | null;
  category_raw: string | null;
  price: number;
  clean_desc: string | null;
  uom_std: string | null;
  category: string | null;
  attributes: Record<string, string | number>;
  cnmc: string | null;
}

export interface ReviewPair {
  pair_id: number;
  total: number;
  semantic: number;
  lexical: number;
  attr_agree: number;
  attr_expected: number;
  conflict: boolean;
  status: string;
  a: Member;
  b: Member;
  explanation: string;
}

export interface CodeMapping {
  cnmc: string;
  cpse: string | null;
  local_code: string;
  description: string;
  category: string | null;
}

export interface AuditEntry {
  id: number;
  entity: string;
  entity_id: number | null;
  action: string;
  user: string;
  created_at: string;
}

export interface TopDup {
  cnmc: string;
  category: string;
  std_description: string;
  n_members: number;
  n_cpses: number;
}

// ---- endpoints -----------------------------------------------------------
export const api = {
  health: () => req<{ status: string }>("/health"),

  listBatches: () => req<Batch[]>("/ingest/batches"),
  loadSynthetic: () => req<Batch>("/ingest/load-synthetic", { method: "POST" }),
  uploadCsv: async (file: File): Promise<Batch> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/ingest/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error((await res.json()).detail ?? "upload failed");
    return res.json();
  },

  runPipeline: (batch_id: number, auto_threshold?: number, review_low?: number) =>
    req<Job>("/pipeline/run", {
      method: "POST",
      body: JSON.stringify({ batch_id, auto_threshold, review_low }),
    }),
  listJobs: () => req<Job[]>("/pipeline/jobs"),
  getJob: (id: number) => req<Job>(`/pipeline/jobs/${id}`),

  summary: (jobId?: number) =>
    req<AnalyticsSummary>(`/analytics/summary${jobId ? `?job_id=${jobId}` : ""}`),
  topDuplicated: (limit = 8) => req<TopDup[]>(`/analytics/top?limit=${limit}`),

  materials: (q = "", category = "", limit = 50) =>
    req<Material[]>(
      `/materials?limit=${limit}` +
        (q ? `&q=${encodeURIComponent(q)}` : "") +
        (category ? `&category=${encodeURIComponent(category)}` : ""),
    ),

  clusters: (status = "", multiOnly = true, limit = 50) =>
    req<Cluster[]>(
      `/clusters?multi_only=${multiOnly}&limit=${limit}` +
        (status ? `&status=${status}` : ""),
    ),
  cluster: (id: number) => req<Cluster>(`/clusters/${id}`),

  codes: (q = "", category = "", multiOnly = false, limit = 50) =>
    req<Canonical[]>(
      `/codes?limit=${limit}&multi_only=${multiOnly}` +
        (q ? `&q=${encodeURIComponent(q)}` : "") +
        (category ? `&category=${encodeURIComponent(category)}` : ""),
    ),
  codeMappings: (cnmc: string) =>
    req<CodeMapping[]>(`/codes/${encodeURIComponent(cnmc)}/mappings`),
  exportCsvUrl: () => `${API_BASE}/codes/export.csv`,

  reviewQueue: (limit = 40) => req<ReviewPair[]>(`/review/queue?limit=${limit}`),
  decidePair: (pairId: number, action: "approve" | "reject", reason?: string) =>
    req<{ pair_id: number; status: string; merged_into_cnmc: string | null }>(
      `/review/pairs/${pairId}/decision`,
      { method: "POST", body: JSON.stringify({ action, reason }) },
    ),
  decideCluster: (clusterId: number, action: "approve" | "reject", reason?: string) =>
    req<{ cluster_id: number; status: string }>(
      `/review/clusters/${clusterId}/decision`,
      { method: "POST", body: JSON.stringify({ action, reason }) },
    ),

  audit: (limit = 100) => req<AuditEntry[]>(`/audit?limit=${limit}`),
};
