import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Batch, Job } from "../lib/api";
import { num, pct } from "../lib/format";
import { Spinner, ErrorNote } from "../components/Feedback";
import { PageHead } from "../components/Layout";

export function Ingest() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  const batches = useQuery({ queryKey: ["batches"], queryFn: api.listBatches });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["batches"] });
    qc.invalidateQueries({ queryKey: ["jobs"] });
    qc.invalidateQueries({ queryKey: ["summary"] });
  };

  const loadSynthetic = useMutation({
    mutationFn: api.loadSynthetic,
    onSuccess: (b: Batch) => {
      setSelected(b.id);
      setMsg(`Loaded sample catalogue "${b.name}" — ${num(b.n_rows)} rows.`);
      invalidate();
    },
  });

  const upload = useMutation({
    mutationFn: (f: File) => api.uploadCsv(f),
    onSuccess: (b: Batch) => {
      setSelected(b.id);
      setMsg(`Uploaded "${b.name}" — ${num(b.n_rows)} rows.`);
      invalidate();
    },
  });

  const run = useMutation({
    mutationFn: (batchId: number) => api.runPipeline(batchId),
    onSuccess: (j: Job) => {
      setMsg(
        j.status === "done"
          ? `Resolution complete — job #${j.id}.`
          : `Job #${j.id} finished with status ${j.status}.`,
      );
      invalidate();
    },
  });

  const busy = loadSynthetic.isPending || upload.isPending || run.isPending;
  const anyError = loadSynthetic.error || upload.error || run.error;

  return (
    <>
      <PageHead eyebrow="Data intake" title="Ingest & Run" />

      {anyError && (
        <div className="mb-4">
          <ErrorNote error={anyError} />
        </div>
      )}
      {msg && !anyError && (
        <div className="mb-4 card border-verified/30 bg-verified-soft p-3 text-sm text-verified">
          {msg}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Source */}
        <div className="card p-5">
          <div className="eyebrow">1 · Choose a source</div>
          <p className="mt-2 text-sm text-steel">
            Start from the built-in multi-CPSE sample, or upload your own catalogue
            CSV (columns: <code>cpse, local_code, description, uom, category, price</code>).
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              className="btn-primary"
              onClick={() => loadSynthetic.mutate()}
              disabled={busy}
            >
              {loadSynthetic.isPending ? "Loading…" : "Load sample catalogue"}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) upload.mutate(f);
                e.target.value = "";
              }}
            />
            <button
              className="btn-ghost"
              onClick={() => fileRef.current?.click()}
              disabled={busy}
            >
              {upload.isPending ? "Uploading…" : "Upload CSV"}
            </button>
          </div>
        </div>

        {/* Run */}
        <div className="card p-5">
          <div className="eyebrow">2 · Resolve into national codes</div>
          <p className="mt-2 text-sm text-steel">
            Runs normalization, hybrid matching, constraint-aware clustering, and
            CNMC assignment over the selected batch.
          </p>
          <div className="mt-4 flex items-center gap-2">
            <select
              className="rounded-lg border border-hairline bg-surface px-3 py-2 text-sm"
              value={selected ?? ""}
              onChange={(e) => setSelected(Number(e.target.value) || null)}
            >
              <option value="">Select a batch…</option>
              {batches.data?.map((b) => (
                <option key={b.id} value={b.id}>
                  #{b.id} · {b.name} ({num(b.n_rows)})
                </option>
              ))}
            </select>
            <button
              className="btn-verified"
              disabled={!selected || busy}
              onClick={() => selected && run.mutate(selected)}
            >
              {run.isPending ? "Resolving…" : "Run resolution"}
            </button>
          </div>
        </div>
      </div>

      {/* Jobs history */}
      <div className="card mt-4 p-5">
        <div className="eyebrow">Resolution jobs</div>
        {jobs.isLoading ? (
          <Spinner />
        ) : jobs.data && jobs.data.length > 0 ? (
          <div className="mt-3 overflow-x-auto">
            <table className="dt">
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Batch</th>
                  <th>Status</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1</th>
                  <th>Finished</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.map((j) => (
                  <tr key={j.id}>
                    <td className="tnum">#{j.id}</td>
                    <td className="tnum">{j.batch_id}</td>
                    <td><JobStatus status={j.status} /></td>
                    <td className="tnum">{pct(j.metrics?.precision)}</td>
                    <td className="tnum">{pct(j.metrics?.recall)}</td>
                    <td className="tnum font-semibold">{pct(j.metrics?.f1)}</td>
                    <td className="text-steel">
                      {j.finished_at ? new Date(j.finished_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-2 text-sm text-steel">No jobs run yet.</p>
        )}
      </div>
    </>
  );
}

function JobStatus({ status }: { status: Job["status"] }) {
  if (status === "done") return <span className="pill-verified">Done</span>;
  if (status === "failed") return <span className="pill-conflict">Failed</span>;
  return <span className="pill-steel">{status}</span>;
}
