import { ReactNode } from "react";

/** A single headline metric. Big tabular number, small label, optional trend. */
export function Stat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: "ink" | "verified" | "attention" | "conflict";
}) {
  const tone =
    accent === "verified"
      ? "text-verified"
      : accent === "attention"
        ? "text-[#9A6B12]"
        : accent === "conflict"
          ? "text-conflict"
          : "text-ink";
  return (
    <div className="card p-5">
      <div className="eyebrow">{label}</div>
      <div className={`mt-2 font-display text-3xl font-semibold tnum ${tone}`}>
        {value}
      </div>
      {sub && <div className="mt-1 text-sm text-steel">{sub}</div>}
    </div>
  );
}
