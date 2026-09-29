import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Cluster } from "../lib/api";
import { pct, num, inr } from "../lib/format";
import { CnmcChip } from "../components/CnmcChip";
import { Spinner, Empty, ErrorNote } from "../components/Feedback";
import { PageHead } from "../components/Layout";

export function Clusters() {
  const qc = useQueryClient();
  const [status, setStatus] = useState("");
  const list = useQuery({
    queryKey: ["clusters", status],
    queryFn: () => api.clusters(status, true, 100),
  });

  const decide = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "approve" | "reject" }) =>
      api.decideCluster(id, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clusters"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
    },
  });

  return (
    <>
      <PageHead eyebrow="Resolved records" title="Material Families">
        <FilterTabs value={status} onChange={setStatus} />
      </PageHead>

      {list.isLoading ? (
        <Spinner label="Loading families…" />
      ) : list.isError ? (
        <ErrorNote error={list.error} />
      ) : (list.data?.length ?? 0) === 0 ? (
        <Empty
          title="No multi-source families"
          hint="Families that pool codes from more than one CPSE will appear here once a batch is resolved."
        />
      ) : (
        <div className="space-y-3">
          {list.data!.map((c) => (
            <FamilyCard
              key={c.id}
              c={c}
              busy={decide.isPending && decide.variables?.id === c.id}
              onDecide={(a) => decide.mutate({ id: c.id, action: a })}
            />
          ))}
        </div>
      )}
    </>
  );
}

function FamilyCard({
  c,
  busy,
  onDecide,
}: {
  c: Cluster;
  busy: boolean;
  onDecide: (a: "approve" | "reject") => void;
}) {
  const [open, setOpen] = useState(false);
  const canon = c.canonical;
  const prices = c.members.map((m) => m.price).filter((p) => p > 0);
  const spread = prices.length >= 2 ? Math.max(...prices) - Math.min(...prices) : 0;

  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {canon && <CnmcChip code={canon.cnmc} size="sm" />}
            <StatusPill status={c.status} />
          </div>
          <div className="mt-2 font-medium text-ink">
            {canon?.std_description ?? "—"}
          </div>
          <div className="mt-1 text-xs text-steel">
            {canon?.unspsc_title} · {canon?.uom} · confidence {pct(c.confidence)}
          </div>
        </div>
        <div className="flex items-center gap-4 text-right">
          <div>
            <div className="font-display text-xl font-semibold tnum text-ink">
              {num(c.size)}
            </div>
            <div className="text-[11px] text-steel">codes · {canon?.n_cpses} CPSEs</div>
          </div>
          {spread > 0 && (
            <div>
              <div className="font-display text-xl font-semibold tnum text-attention">
                {inr(spread)}
              </div>
              <div className="text-[11px] text-steel">price spread</div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <button
          className="text-sm font-medium text-verified hover:underline"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? "Hide" : "Show"} {c.members.length} member codes
        </button>
        {c.status === "proposed" && (
          <div className="flex gap-2">
            <button className="btn-danger" disabled={busy} onClick={() => onDecide("reject")}>
              Reject
            </button>
            <button className="btn-verified" disabled={busy} onClick={() => onDecide("approve")}>
              {busy ? "Saving…" : "Approve family"}
            </button>
          </div>
        )}
      </div>

      {open && (
        <div className="mt-3 overflow-x-auto">
          <table className="dt">
            <thead>
              <tr>
                <th>CPSE</th>
                <th>Local code</th>
                <th>Original description</th>
                <th className="text-right">Price</th>
              </tr>
            </thead>
            <tbody>
              {c.members.map((m) => (
                <tr key={m.raw_id}>
                  <td>{m.cpse ?? "—"}</td>
                  <td className="font-mono text-xs">{m.local_code}</td>
                  <td>{m.description}</td>
                  <td className="text-right tnum">{m.price ? inr(m.price) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: Cluster["status"] }) {
  if (status === "approved") return <span className="pill-verified">Approved</span>;
  if (status === "rejected") return <span className="pill-conflict">Rejected</span>;
  return <span className="pill-attention">Proposed</span>;
}

function FilterTabs({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const tabs = [
    { v: "", label: "All" },
    { v: "proposed", label: "Proposed" },
    { v: "approved", label: "Approved" },
  ];
  return (
    <div className="flex rounded-lg border border-hairline bg-surface p-0.5">
      {tabs.map((t) => (
        <button
          key={t.v}
          onClick={() => onChange(t.v)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            value === t.v ? "bg-ink text-white" : "text-steel hover:text-ink"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
