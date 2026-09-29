export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-steel py-10 justify-center">
      <span
        className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-hairline border-t-verified"
        aria-hidden
      />
      <span className="text-sm">{label ?? "Loading…"}</span>
    </div>
  );
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="card p-10 text-center">
      <div className="font-display text-lg text-ink">{title}</div>
      {hint && <div className="mt-1 text-sm text-steel">{hint}</div>}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="card border-conflict/30 bg-conflict-soft p-4 text-sm text-conflict">
      <span className="font-semibold">Couldn't reach the service.</span> {msg}
      <div className="mt-1 text-conflict/80">
        Is the backend running on <code>{`${(import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000/api"}`}</code>?
      </div>
    </div>
  );
}
