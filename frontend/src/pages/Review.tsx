import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ReviewPair, Member } from "../lib/api";
import { pct } from "../lib/format";
import { ScoreBar } from "../components/ScoreBar";
import { Spinner, Empty, ErrorNote } from "../components/Feedback";
import { PageHead } from "../components/Layout";

export function Review() {
  const qc = useQueryClient();
  const queue = useQuery({ queryKey: ["review"], queryFn: () => api.reviewQueue(40) });

  const decide = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "approve" | "reject" }) =>
      api.decidePair(id, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["clusters"] });
    },
  });

  if (queue.isLoading) return <Spinner label="Loading review queue…" />;
  if (queue.isError) return <ErrorNote error={queue.error} />;
  const pairs = queue.data ?? [];

  return (
    <>
      <PageHead eyebrow="Human in the loop" title="Review Queue">
        <span className="pill-attention">{pairs.length} pending</span>
      </PageHead>

      {pairs.length === 0 ? (
        <Empty
          title="Queue is clear"
          hint="Every borderline match has been decided. New ambiguous pairs will appear here after the next resolution run."
        />
      ) : (
        <div className="space-y-4">
          {pairs.map((p) => (
            <PairCard
              key={p.pair_id}
              p={p}
              busy={decide.isPending && decide.variables?.id === p.pair_id}
              onDecide={(action) => decide.mutate({ id: p.pair_id, action })}
            />
          ))}
        </div>
      )}
    </>
  );
}

function PairCard({
  p,
  busy,
  onDecide,
}: {
  p: ReviewPair;
  busy: boolean;
  onDecide: (a: "approve" | "reject") => void;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="eyebrow">Possible match</span>
            {p.conflict && <span className="pill-conflict">Attribute conflict</span>}
          </div>
          <p className="mt-2 text-sm text-ink/90">{p.explanation}</p>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-display text-2xl font-semibold tnum text-ink">
            {pct(p.total)}
          </div>
          <div className="text-[11px] uppercase tracking-wide text-steel">
            match score
          </div>
        </div>
      </div>

      {/* Side-by-side candidates */}
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <MemberPanel m={p.a} />
        <MemberPanel m={p.b} />
      </div>

      {/* Score breakdown — attribute agreement leads (0.60 of the score). */}
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <ScoreRow
          label={`Attributes (${p.attr_agree}/${p.attr_expected})`}
          v={Math.min(1, p.attr_agree / Math.max(1, p.attr_expected))}
        />
        <ScoreRow label="Semantic" v={p.semantic} />
        <ScoreRow label="Lexical" v={p.lexical} />
      </div>

      <div className="mt-4 flex items-center justify-end gap-2">
        <button className="btn-danger" disabled={busy} onClick={() => onDecide("reject")}>
          Keep separate
        </button>
        <button className="btn-verified" disabled={busy} onClick={() => onDecide("approve")}>
          {busy ? "Saving…" : "Confirm same item"}
        </button>
      </div>
    </div>
  );
}

function MemberPanel({ m }: { m: Member }) {
  return (
    <div className="rounded-lg border border-hairline bg-paper/50 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="pill-steel">{m.cpse ?? "—"}</span>
        <span className="font-mono text-xs text-steel">{m.local_code}</span>
      </div>
      <div className="mt-2 text-sm text-ink">{m.description}</div>
      {m.clean_desc && (
        <div className="mt-1 font-mono text-[11px] text-steel">{m.clean_desc}</div>
      )}
    </div>
  );
}

function ScoreRow({ label, v }: { label: string; v: number }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-steel">{label}</span>
        <span className="tnum font-medium text-ink">{pct(v)}</span>
      </div>
      <div className="mt-1">
        <ScoreBar value={v} />
      </div>
    </div>
  );
}
