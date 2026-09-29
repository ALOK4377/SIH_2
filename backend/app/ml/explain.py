"""
explain.py — human-readable justification for every match decision.

Data stewards must not merge material masters on a black-box score. For each
scored pair this renders the three signals, the exact spec agreements /
conflicts, and the final verdict — so a reviewer can approve or reject in
seconds and an auditor can see *why* two codes were unified.
"""


def _fmt(v):
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def explain(a, b, f, auto=0.60, review=0.45):
    """`a`, `b` normalized records; `f` the dict from score.score_pair."""
    parts = [
        f"text {f['semantic']:.2f}",
        f"fuzzy {f['lexical']:.2f}",
    ]

    if f["attr_matches"]:
        agree = "/".join([f"{k}={_fmt(v)}" for k, v in f["attr_matches"]])
        parts.append(f"specs {f['attr_agree']} agree ({agree})")
    else:
        parts.append("specs 0 agree")

    parts.append("UOM ✓" if f["uom_match"] else "UOM ✗")

    if f["total"] >= auto:
        verdict = "DUPLICATE (auto)"
    elif f["total"] >= review:
        verdict = "REVIEW"
    else:
        verdict = "NOT A MATCH"

    reasons = []
    for k, x, y in f["attr_conflicts"]:
        reasons.append(f"{k} {_fmt(x)}≠{_fmt(y)}")
    if not f["uom_match"]:
        reasons.append(f"UOM {a['uom_std']}≠{b['uom_std']}")
    conflict = f"  ⚠ conflict: {', '.join(reasons)}" if reasons else ""

    header = f"[{a['clean_desc']}]  vs  [{b['clean_desc']}]"
    body = " · ".join(parts) + f"  →  {f['total']:.2f}  {verdict}{conflict}"
    return f"{header}\n    {body}"
