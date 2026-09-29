"""
canonical.py — golden record + Common National Material Code (Stage 6).

For each cluster we build ONE canonical ("golden") record and assign a stable
Common National Material Code (CNMC), while preserving the mapping from every
original CPSE local code to that CNMC (nothing is thrown away — legacy codes
stay traceable).

CNMC format:  IN-<CCCCCC>-<NNNNNNN>-<K>
    IN        country prefix
    CCCCCC    6-digit UNSPSC commodity/class code (from category)
    NNNNNNN   7-digit zero-padded serial, allocated per UNSPSC class
    K         mod-11 check digit over the 13 numeric digits (self-validating)

e.g.  IN-311516-0000001-4   (a bearing)

Golden record = the cluster member with the most parsed attributes (tie-break:
longest description) — i.e. the least-noised, most-complete row — plus the
consolidated attribute set.
"""
import json
from pathlib import Path

_REF = Path(__file__).resolve().parents[3] / "data" / "reference"
UNSPSC = json.loads((_REF / "unspsc_subset.json").read_text())


def _check_digit(digits):
    weights = [2, 3, 4, 5, 6, 7]
    total = sum(int(d) * weights[i % len(weights)]
                for i, d in enumerate(reversed(digits)))
    k = (11 - (total % 11)) % 11
    return "0" if k == 10 else str(k)


def make_cnmc(unspsc_code, serial):
    body = f"{unspsc_code}{serial:07d}"
    return f"IN-{unspsc_code}-{serial:07d}-{_check_digit(body)}"


def _pick_representative(members, records):
    return max(members, key=lambda i: (len(records[i]["attributes"]),
                                        len(records[i]["clean_desc"])))


def _mode(values):
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def canonicalize(clusters, records, raw_rows):
    """
    clusters : list of index-lists (from cluster.cluster)
    records  : normalized records (index-aligned)
    raw_rows : original rows with id/cpse/local_code (index-aligned)

    Returns (canonicals, mappings).
    """
    ordered = sorted(clusters, key=lambda c: min(c))   # deterministic serials
    serials = {}
    canonicals, mappings = [], []

    for members in ordered:
        rep = _pick_representative(members, records)
        category = _mode([records[i]["category"] for i in members])
        info = UNSPSC.get(category, UNSPSC["OTHER"])
        code = info["code"]

        serials[code] = serials.get(code, 0) + 1
        cnmc = make_cnmc(code, serials[code])

        canonicals.append({
            "cnmc": cnmc,
            "category": category,
            "unspsc_code": code,
            "unspsc_title": info["title"],
            "canonical_desc": records[rep]["clean_desc"],
            "uom": _mode([records[i]["uom_std"] for i in members]),
            "attributes": records[rep]["attributes"],
            "member_ids": sorted(raw_rows[i]["id"] for i in members),
            "n_members": len(members),
            "n_cpses": len({raw_rows[i]["cpse"] for i in members}),
        })
        for i in members:
            mappings.append({
                "id": raw_rows[i]["id"],
                "cpse": raw_rows[i]["cpse"],
                "local_code": raw_rows[i]["local_code"],
                "description": raw_rows[i]["description"],
                "cnmc": cnmc,
            })

    return canonicals, mappings
