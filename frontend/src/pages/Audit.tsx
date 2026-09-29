import { useQuery } from "@tanstack/react-query";
import { api, AuditEntry } from "../lib/api";
import { Spinner, Empty, ErrorNote } from "../components/Feedback";
import { PageHead } from "../components/Layout";

const ACTION_TONE: Record<string, string> = {
  approve: "pill-verified",
  approve_cluster: "pill-verified",
  reject: "pill-conflict",
  reject_cluster: "pill-conflict",
  split: "pill-attention",
  merge: "pill-attention",
};

export function Audit() {
  const log = useQuery({ queryKey: ["audit"], queryFn: () => api.audit(150) });

  return (
    <>
      <PageHead eyebrow="Governance" title="Audit Trail" />

      {log.isLoading ? (
        <Spinner />
      ) : log.isError ? (
        <ErrorNote error={log.error} />
      ) : (log.data?.length ?? 0) === 0 ? (
        <Empty
          title="No activity recorded"
          hint="Every ingest, resolution run, and review decision is logged here for traceability."
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="dt">
            <thead>
              <tr>
                <th>When</th>
                <th>Action</th>
                <th>Entity</th>
                <th>By</th>
              </tr>
            </thead>
            <tbody>
              {log.data!.map((e: AuditEntry) => (
                <tr key={e.id}>
                  <td className="whitespace-nowrap text-steel">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td>
                    <span className={ACTION_TONE[e.action] ?? "pill-steel"}>
                      {e.action.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td>
                    <span className="text-ink">{e.entity}</span>
                    {e.entity_id != null && (
                      <span className="ml-1 font-mono text-xs text-steel">#{e.entity_id}</span>
                    )}
                  </td>
                  <td className="text-steel">{e.user}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
