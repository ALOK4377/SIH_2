import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, Canonical } from "../lib/api";
import { num } from "../lib/format";
import { CnmcChip } from "../components/CnmcChip";
import { Spinner, Empty, ErrorNote } from "../components/Feedback";
import { PageHead } from "../components/Layout";

const CATEGORIES = ["", "BEARING", "VALVE", "PUMP", "PIPE", "CABLE", "FASTENER", "GASKET", "OTHER"];

export function Codes() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [multiOnly, setMultiOnly] = useState(false);

  const list = useQuery({
    queryKey: ["codes", q, cat, multiOnly],
    queryFn: () => api.codes(q, cat, multiOnly, 100),
  });

  return (
    <>
      <PageHead eyebrow="The deliverable" title="National Code Registry">
        <a href={api.exportCsvUrl()} className="btn-primary">Export CSV</a>
      </PageHead>

      {/* Controls */}
      <div className="card mb-4 flex flex-wrap items-center gap-3 p-4">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search description or CNMC…"
          className="flex-1 min-w-[200px] rounded-lg border border-hairline bg-surface px-3 py-2 text-sm"
        />
        <select
          value={cat}
          onChange={(e) => setCat(e.target.value)}
          className="rounded-lg border border-hairline bg-surface px-3 py-2 text-sm"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c || "All categories"}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-steel">
          <input
            type="checkbox"
            checked={multiOnly}
            onChange={(e) => setMultiOnly(e.target.checked)}
            className="accent-verified"
          />
          Multi-CPSE only
        </label>
      </div>

      {list.isLoading ? (
        <Spinner label="Loading registry…" />
      ) : list.isError ? (
        <ErrorNote error={list.error} />
      ) : (list.data?.length ?? 0) === 0 ? (
        <Empty title="No codes match" hint="Try a broader search or clear the filters." />
      ) : (
        <div className="space-y-2">
          {list.data!.map((c) => (
            <CodeRow key={c.cnmc} c={c} />
          ))}
        </div>
      )}
    </>
  );
}

function CodeRow({ c }: { c: Canonical }) {
  const [open, setOpen] = useState(false);
  const mappings = useQuery({
    queryKey: ["mappings", c.cnmc],
    queryFn: () => api.codeMappings(c.cnmc),
    enabled: open,
  });
  const attrs = Object.entries(c.attributes ?? {}).filter(([, v]) => v !== "" && v != null);

  return (
    <div className="card p-4">
      <button
        className="flex w-full items-center justify-between gap-4 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="min-w-0 flex-1">
          <CnmcChip code={c.cnmc} size="sm" />
          <div className="mt-1.5 font-medium text-ink">{c.std_description}</div>
          <div className="mt-0.5 text-xs text-steel">
            {c.unspsc_title} · UNSPSC {c.unspsc_code} · {c.uom}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-display text-lg font-semibold tnum text-ink">
            {num(c.n_members)}
          </div>
          <div className="text-[11px] text-steel">
            {c.n_cpses} {c.n_cpses === 1 ? "CPSE" : "CPSEs"}
          </div>
        </div>
      </button>

      {attrs.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {attrs.map(([k, v]) => (
            <span key={k} className="pill-steel">
              {k}: <span className="ml-1 font-mono normal-case">{String(v)}</span>
            </span>
          ))}
        </div>
      )}

      {open && (
        <div className="mt-3 border-t border-hairline pt-3">
          <div className="eyebrow mb-2">Local code crosswalk</div>
          {mappings.isLoading ? (
            <Spinner />
          ) : (
            <div className="overflow-x-auto">
              <table className="dt">
                <thead>
                  <tr>
                    <th>CPSE</th>
                    <th>Local code</th>
                    <th>Original description</th>
                  </tr>
                </thead>
                <tbody>
                  {mappings.data?.map((m, i) => (
                    <tr key={`${m.cpse}-${m.local_code}-${i}`}>
                      <td>{m.cpse ?? "—"}</td>
                      <td className="font-mono text-xs">{m.local_code}</td>
                      <td>{m.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
