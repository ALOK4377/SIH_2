#!/usr/bin/env python3
"""
Samanvay synthetic data generator
==================================

The official CPSE dataset is "to be provided by participating CPSEs" and will
likely be unavailable/partial early on. This script fabricates *realistic,
messy* material-master rows across several CPSEs **with a known ground truth**
of which rows are the same physical item.

Why it matters:
  * gives us something to build the matcher on today, and
  * lets us report real precision / recall / F1 (a big credibility win).

Output (default `data/synthetic/`):
  materials.csv     id, cpse, sector, local_code, description, uom, category_raw, price
  ground_truth.csv  id, group_id            (rows sharing a group_id are the same item)
  canonicals.csv    group_id, category, canonical_desc, uom, base_price   (reference)

Deterministic given --seed. Pure standard library.

Usage:
  python3 scripts/gen_synthetic_data.py --groups 350 --seed 42
"""
import argparse
import csv
import json
import os
import random

# --------------------------------------------------------------------------
# CPSEs and their (heterogeneous) local material-code schemes
# --------------------------------------------------------------------------
CPSES = [
    ("CPCL", "Oil & Gas"),
    ("IOCL", "Oil & Gas"),
    ("BPCL", "Oil & Gas"),
    ("HPCL", "Oil & Gas"),
    ("ONGC", "Oil & Gas"),
    ("GAIL", "Oil & Gas"),
    ("SAIL", "Steel"),
    ("NTPC", "Power"),
    ("CIL",  "Mining"),
    ("BHEL", "Heavy Engineering"),
]


def local_code(rng, cpse):
    """Each CPSE mimics a different ERP numbering style."""
    d = lambda n: "".join(rng.choice("0123456789") for _ in range(n))
    styles = {
        "CPCL": lambda: "MAT" + d(7),
        "IOCL": lambda: d(9),
        "BPCL": lambda: "B-" + d(6),
        "HPCL": lambda: "H" + d(8),
        "ONGC": lambda: "ON" + d(7),
        "GAIL": lambda: d(6) + "-G",
        "SAIL": lambda: "S" + d(3) + "-" + d(4),
        "NTPC": lambda: "NT" + d(8),
        "CIL":  lambda: "CIL" + d(6),
        "BHEL": lambda: d(4) + "/" + d(4),
    }
    return styles.get(cpse, lambda: d(8))()


# --------------------------------------------------------------------------
# Category templates: attribute pools + how a "clean" description reads
# --------------------------------------------------------------------------
CATEGORIES = {
    "BEARING": {
        "uom": "EACH", "price": (120, 2600),
        "attrs": {
            "btype":  ["BALL", "ROLLER", "TAPER ROLLER", "SPHERICAL ROLLER"],
            "number": ["6003", "6204", "6205", "6206", "6305", "6307",
                       "22210", "30205", "30210", "NU309", "51110"],
            "seal":   ["ZZ", "2RS", "OPEN"],
        },
        "desc": lambda a: f"{a['btype']} BEARING {a['number']}"
                          + ("" if a["seal"] == "OPEN" else f" {a['seal']}"),
    },
    "VALVE": {
        "uom": "EACH", "price": (700, 16000),
        "attrs": {
            "vtype":    ["GATE", "GLOBE", "BALL", "BUTTERFLY", "CHECK"],
            "size":     ["25MM", "40MM", "50MM", "80MM", "100MM", "150MM", "200MM"],
            "rating":   ["PN16", "PN25", "CL150", "CL300"],
            "material": ["CAST IRON", "CARBON STEEL", "STAINLESS STEEL"],
            "ends":     ["FLANGED", "SCREWED", "WAFER"],
        },
        "desc": lambda a: f"{a['vtype']} VALVE {a['size']} {a['rating']} {a['material']} {a['ends']}",
    },
    "FASTENER": {
        "uom": "EACH", "price": (2, 70),
        "attrs": {
            "sub":    ["HEX BOLT", "HEX NUT", "STUD BOLT", "SPRING WASHER",
                       "PLAIN WASHER", "ALLEN BOLT"],
            "thread": ["M6", "M8", "M10", "M12", "M16", "M20", "M24"],
            "length": ["20MM", "25MM", "40MM", "50MM", "65MM", "80MM", "100MM"],
            "grade":  ["GRADE 4.6", "GRADE 8.8", "GRADE 10.9", "STAINLESS STEEL 304",
                       "STAINLESS STEEL 316"],
            "finish": ["GALVANIZED", "ZINC PLATED", "PLAIN", "BLACK"],
        },
        # nuts/washers have no length
        "desc": lambda a: (
            f"{a['sub']} {a['thread']}X{a['length']} {a['grade']} {a['finish']}"
            if "BOLT" in a["sub"]
            else f"{a['sub']} {a['thread']} {a['grade']} {a['finish']}"
        ),
    },
    "PIPE": {
        "uom": "METER", "price": (110, 3200),
        "attrs": {
            "ptype":    ["SEAMLESS", "ERW", "WELDED"],
            "size":     ["15MM", "25MM", "40MM", "50MM", "80MM", "100MM", "150MM"],
            "sched":    ["SCH20", "SCH40", "SCH80", "SCH160"],
            "material": ["CARBON STEEL", "STAINLESS STEEL 304", "STAINLESS STEEL 316",
                         "GALVANIZED IRON"],
        },
        "desc": lambda a: f"{a['ptype']} PIPE {a['size']} {a['sched']} {a['material']}",
    },
    "CABLE": {
        "uom": "METER", "price": (25, 1300),
        "attrs": {
            "cores":  ["1C", "2C", "3C", "3.5C", "4C"],
            "csa":    ["1.5", "2.5", "4", "6", "10", "16", "25", "35", "50"],
            "cond":   ["COPPER", "ALUMINIUM"],
            "ins":    ["XLPE", "PVC"],
            "armour": ["ARMOURED", "UNARMOURED"],
            "volt":   ["1.1KV", "3.3KV", "11KV"],
        },
        "desc": lambda a: f"CABLE {a['cores']}X{a['csa']} SQMM {a['cond']} {a['ins']} {a['armour']} {a['volt']}",
    },
    "PUMP": {
        "uom": "EACH", "price": (4500, 95000),
        "attrs": {
            "ptype":    ["CENTRIFUGAL", "SUBMERSIBLE", "GEAR", "SCREW"],
            "hp":       ["1HP", "2HP", "5HP", "7.5HP", "10HP", "15HP", "25HP"],
            "material": ["CAST IRON", "STAINLESS STEEL", "CARBON STEEL"],
        },
        "desc": lambda a: f"{a['ptype']} PUMP {a['hp']} {a['material']}",
    },
    "GASKET": {
        "uom": "EACH", "price": (30, 1600),
        "attrs": {
            "gtype":  ["SPIRAL WOUND", "CAF", "RING JOINT", "PTFE"],
            "size":   ["25MM", "50MM", "80MM", "100MM", "150MM"],
            "rating": ["CL150", "CL300", "PN16"],
        },
        "desc": lambda a: f"{a['gtype']} GASKET {a['size']} {a['rating']}",
    },
}

# Raw category labels vary wildly across ERPs (part of the noise).
CATEGORY_RAW = {
    "BEARING":  ["BEARING", "BEARINGS", "BRG", "ANTI FRICTION BEARING", "BALL/ROLLER BRG"],
    "VALVE":    ["VALVE", "VALVES", "INDUSTRIAL VALVE", "VLV", "ISOLATION VALVE"],
    "FASTENER": ["FASTENER", "FASTENERS", "BOLT & NUT", "HARDWARE", "FIXING"],
    "PIPE":     ["PIPE", "PIPES", "TUBE", "PIPING", "MS/CS PIPE"],
    "CABLE":    ["CABLE", "CABLES", "POWER CABLE", "ELECT CABLE", "WIRE"],
    "PUMP":     ["PUMP", "PUMPS", "PUMPING UNIT", "PUMP ASSY"],
    "GASKET":   ["GASKET", "GASKETS", "SEAL", "JOINTING", "GSKT"],
}

# Words we deliberately abbreviate to create realistic noise.
ABBREV_INJECT = {
    "BEARING": ["BRG", "BER", "BRNG"],
    "STAINLESS STEEL": ["SS", "S.S.", "STAINLESS STL"],
    "CARBON STEEL": ["CS", "C.STEEL"],
    "CAST IRON": ["CI", "C.I."],
    "GALVANIZED": ["GALV", "GALVD"],
    "GALVANIZED IRON": ["GI", "G.I."],
    "HEXAGON": ["HEX"],
    "VALVE": ["VLV"],
    "GASKET": ["GSKT", "GKT"],
    "SEAMLESS": ["SMLS"],
    "CENTRIFUGAL": ["CENTRIF", "CENT"],
    "COPPER": ["CU"],
    "ALUMINIUM": ["AL", "ALU"],
    "PUMP": ["PMP"],
    "CABLE": ["CBL"],
    "ARMOURED": ["ARM", "ARMD"],
    "FLANGED": ["FLGD", "FLG"],
    "GRADE": ["GR", "GR."],
}

UOM_VARIANTS = {
    "EACH":  ["NOS", "NO", "EA", "PCS", "NOS.", "No", "Each", "UNIT"],
    "METER": ["MTR", "MTRS", "M", "MTS", "Mtr", "RMT", "Metre"],
}

VENDOR_NOISE = ["MAKE SKF", "MAKE FAG", "AS PER IS2062", "MAKE L&T", "MAKE KIRLOSKAR",
                "IS 1239", "MAKE AUDCO", "ASTM A106", "MAKE POLYCAB", "REF DWG"]


# --------------------------------------------------------------------------
# Noise helpers
# --------------------------------------------------------------------------
def apply_typo(rng, token):
    """Introduce one small typo into an alphabetic token."""
    if len(token) < 4 or not token.isalpha():
        return token
    i = rng.randrange(len(token) - 1)
    kind = rng.choice(["swap", "drop", "dup"])
    if kind == "swap":
        return token[:i] + token[i + 1] + token[i] + token[i + 2:]
    if kind == "drop":
        return token[:i] + token[i + 1:]
    return token[:i] + token[i] + token[i:]


def noisify(rng, clean_desc):
    """Turn a clean canonical description into one CPSE's messy version."""
    s = clean_desc

    # 1) inject abbreviations (multi-word first)
    for full, abbrs in sorted(ABBREV_INJECT.items(), key=lambda kv: -len(kv[0])):
        if full in s and rng.random() < 0.55:
            s = s.replace(full, rng.choice(abbrs))

    # 2) separator noise
    if rng.random() < 0.6:
        s = s.replace("X", rng.choice(["X", "x", "*", " X ", " x "]))
    if rng.random() < 0.4:
        s = s.replace("SQMM", rng.choice(["SQMM", "SQ MM", "SQ.MM", "MM2"]))
    if rng.random() < 0.3:
        s = s.replace("MM", rng.choice(["MM", "mm", " MM"]))

    tokens = s.split()

    # 3) drop a spec token (missing information)
    if len(tokens) > 3 and rng.random() < 0.22:
        del tokens[rng.randrange(1, len(tokens))]

    # 4) a typo somewhere
    if tokens and rng.random() < 0.35:
        j = rng.randrange(len(tokens))
        tokens[j] = apply_typo(rng, tokens[j])

    # 5) reorder tokens mildly
    if len(tokens) > 2 and rng.random() < 0.3:
        rng.shuffle(tokens)

    # 6) extra vendor / spec noise
    if rng.random() < 0.25:
        note = rng.choice(VENDOR_NOISE)
        tokens = (note.split() + tokens) if rng.random() < 0.5 else (tokens + note.split())

    out = " ".join(tokens)

    # 7) case noise
    r = rng.random()
    if r < 0.15:
        out = out.lower()
    elif r < 0.25:
        out = out.title()
    return out


def sample_attrs(rng, cat):
    pools = CATEGORIES[cat]["attrs"]
    return {k: rng.choice(v) for k, v in pools.items()}


# --------------------------------------------------------------------------
# Main generation
# --------------------------------------------------------------------------
def generate(groups, seed, min_variants, max_variants, singleton_rate):
    rng = random.Random(seed)
    cats = list(CATEGORIES.keys())

    materials, truth, canon = [], [], []
    seen_sig = set()
    rid = 0
    gid = 0

    attempts = 0
    while gid < groups and attempts < groups * 40:
        attempts += 1
        cat = rng.choice(cats)
        attrs = sample_attrs(rng, cat)
        sig = (cat, tuple(sorted(attrs.items())))
        if sig in seen_sig:
            continue
        seen_sig.add(sig)

        spec = CATEGORIES[cat]
        clean = spec["desc"](attrs)
        base_price = round(rng.uniform(*spec["price"]), 2)
        canon.append({
            "group_id": gid, "category": cat, "canonical_desc": clean,
            "uom": spec["uom"], "base_price": base_price,
        })

        # how many CPSEs carry this item
        if rng.random() < singleton_rate:
            n = 1
        else:
            n = rng.randint(min_variants, max_variants)
        chosen = rng.sample(CPSES, min(n, len(CPSES)))

        for cpse, sector in chosen:
            desc = noisify(rng, clean)
            uom = spec["uom"]
            if rng.random() < 0.6:
                uom = rng.choice(UOM_VARIANTS.get(uom, [uom]))
            price = round(base_price * rng.uniform(0.85, 1.18), 2)
            cat_raw = rng.choice(CATEGORY_RAW.get(cat, [cat]))
            materials.append({
                "id": rid, "cpse": cpse, "sector": sector,
                "local_code": local_code(rng, cpse), "description": desc,
                "uom": uom, "category_raw": cat_raw, "price": price,
            })
            truth.append({"id": rid, "group_id": gid})
            rid += 1
        gid += 1

    rng.shuffle(materials)  # rows arrive in no particular order
    return materials, truth, canon


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="Generate synthetic CPSE material data.")
    ap.add_argument("--groups", type=int, default=350)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-variants", type=int, default=2)
    ap.add_argument("--max-variants", type=int, default=6)
    ap.add_argument("--singleton-rate", type=float, default=0.15)
    ap.add_argument("--out", default=os.path.join("data", "synthetic"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    materials, truth, canon = generate(
        args.groups, args.seed, args.min_variants, args.max_variants, args.singleton_rate
    )

    write_csv(os.path.join(args.out, "materials.csv"), materials,
              ["id", "cpse", "sector", "local_code", "description", "uom", "category_raw", "price"])
    write_csv(os.path.join(args.out, "ground_truth.csv"), truth, ["id", "group_id"])
    write_csv(os.path.join(args.out, "canonicals.csv"), canon,
              ["group_id", "category", "canonical_desc", "uom", "base_price"])

    dup_groups = sum(1 for c in canon
                     if sum(1 for t in truth if t["group_id"] == c["group_id"]) > 1)
    print(f"Wrote {len(materials)} material rows across {len(canon)} groups "
          f"({dup_groups} with duplicates) to {args.out}/")
    print(f"  materials.csv · ground_truth.csv · canonicals.csv  (seed={args.seed})")


if __name__ == "__main__":
    main()
