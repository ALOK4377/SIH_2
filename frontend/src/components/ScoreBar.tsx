/** Horizontal score bar, 0..1, tinted by how strong the score is. */
export function ScoreBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const tone =
    value >= 0.7 ? "bg-verified" : value >= 0.5 ? "bg-attention" : "bg-steel";
  return (
    <div className="h-1.5 w-full rounded-full bg-hairline overflow-hidden">
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
