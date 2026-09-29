// format.ts — presentation helpers (money in Indian units, %, and the CNMC
// structural split that powers the signature code chip).

export function pct(x: number | undefined, digits = 1): string {
  if (x === undefined || Number.isNaN(x)) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

/** Indian-format currency with lakh/crore suffixes (₹). */
export function inr(x: number | undefined): string {
  if (!x) return "₹0";
  if (x >= 1e7) return `₹${(x / 1e7).toFixed(2)} Cr`;
  if (x >= 1e5) return `₹${(x / 1e5).toFixed(2)} L`;
  return `₹${x.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function num(x: number | undefined): string {
  if (x === undefined) return "—";
  return x.toLocaleString("en-IN");
}

export interface CnmcParts {
  prefix: string;
  unspsc: string;
  serial: string;
  check: string;
  valid: boolean;
}

/** Split "IN-311516-0000011-6" into its four fields for segmented rendering. */
export function splitCnmc(cnmc: string): CnmcParts {
  const parts = (cnmc || "").split("-");
  if (parts.length === 4) {
    return {
      prefix: parts[0],
      unspsc: parts[1],
      serial: parts[2],
      check: parts[3],
      valid: true,
    };
  }
  return { prefix: cnmc, unspsc: "", serial: "", check: "", valid: false };
}

const CATEGORY_TONE: Record<string, string> = {
  BEARING: "#0E7C66",
  VALVE: "#2F6DB0",
  PUMP: "#7A5AB0",
  PIPE: "#B07A2F",
  CABLE: "#C0453B",
  FASTENER: "#3F7A5A",
  GASKET: "#9A6B12",
  OTHER: "#5A6B82",
};

export function categoryTone(cat: string | null | undefined): string {
  return CATEGORY_TONE[cat ?? "OTHER"] ?? CATEGORY_TONE.OTHER;
}
