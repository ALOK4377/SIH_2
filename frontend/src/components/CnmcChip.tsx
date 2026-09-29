import { splitCnmc } from "../lib/format";

/**
 * The signature element: a Common National Material Code rendered as a
 * segmented "license plate" — the IN prefix as a national tab, the UNSPSC
 * class and per-class serial as dividered fields, and the mod-11 check digit
 * verified in teal. This is the one artifact the whole platform produces.
 */
export function CnmcChip({
  code,
  size = "md",
}: {
  code: string;
  size?: "sm" | "md" | "lg";
}) {
  const p = splitCnmc(code);
  const scale =
    size === "lg"
      ? "text-base"
      : size === "sm"
        ? "text-xs [&>span]:px-1.5 [&>span]:py-0.5"
        : "text-sm";

  if (!p.valid) {
    return <span className={`cnmc ${scale}`}><span className="cnmc-seg">{code}</span></span>;
  }
  return (
    <span className={`cnmc ${scale}`} title={`CNMC ${code}`}>
      <span className="cnmc-prefix">{p.prefix}</span>
      <span className="cnmc-seg" title="UNSPSC class">{p.unspsc}</span>
      <span className="cnmc-seg tnum" title="Per-class serial">{p.serial}</span>
      <span className="cnmc-check" title="Check digit (mod-11)">{p.check}</span>
    </span>
  );
}
