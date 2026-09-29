"""
score.py — hybrid pairwise similarity (Stage 4).

Three independent signals are combined into one confidence:

  attribute — agreement over structured specs parsed by normalize     weight 0.60
  semantic  — TF-IDF cosine over text (embed.cosine)                   weight 0.25
  lexical   — SequenceMatcher ratio + token-set Jaccard                weight 0.15

The attribute signal leads, because for short technical strings the parsed
specs are the identity and the free text is noisy. It carries a HARD veto: if
ANY spec both rows declare disagrees (M10 vs M12, BALL vs ROLLER, CENTRIFUGAL
vs SUBMERSIBLE, ARMOURED vs UNARMOURED, SCH40 vs SCH80, or the UOM), the pair
is capped at CONFLICT_CAP no matter how similar the text is. This stops
textually-near but physically-different items from merging.

The attribute component is COUNT-AWARE: `agree / expected_keys[category]`, so a
single coincidental spec match cannot by itself push a pair over threshold —
which (with Union-Find transitivity) is what caused runaway mega-clusters.

Upgrade path: swap `lexical` for RapidFuzz and replace the fixed weights with a
classifier (LogisticRegression / XGBoost) trained on accumulated review labels;
the same feature dict feeds both.
"""
from difflib import SequenceMatcher

from . import embed

W_ATTR = 0.60
W_SEMANTIC = 0.25
W_LEXICAL = 0.15
CONFLICT_CAP = 0.25

# structured specs that must never silently disagree within a match
_DISCRIMINATING = {
    "thread", "size_mm", "schedule", "rating", "grade", "material",
    "csa", "voltage", "cores", "insulation", "hp", "seal", "code_no",
    "btype", "vtype", "ptype", "sub", "ends", "armour", "finish", "gtype",
}

# how many identifying specs a fully-described item of each category carries;
# the attribute score is agree / this, so partial matches score proportionally.
_EXPECTED = {
    "BEARING": 3, "VALVE": 4, "PUMP": 3, "PIPE": 3,
    "CABLE": 4, "FASTENER": 3, "GASKET": 3, "OTHER": 2,
}


def _lexical(a_desc, b_desc, a_tokens, b_tokens):
    ratio = SequenceMatcher(None, a_desc, b_desc).ratio()
    sa, sb = set(a_tokens), set(b_tokens)
    jac = len(sa & sb) / len(sa | sb) if (sa or sb) else 0.0
    return 0.5 * ratio + 0.5 * jac


def _eq(x, y):
    if isinstance(x, float) or isinstance(y, float):
        return abs(float(x) - float(y)) < 1e-6
    return x == y


def _attribute_agreement(a_attrs, b_attrs):
    shared = set(a_attrs) & set(b_attrs) & _DISCRIMINATING
    matches, conflicts = [], []
    for k in shared:
        if _eq(a_attrs[k], b_attrs[k]):
            matches.append((k, a_attrs[k]))
        else:
            conflicts.append((k, a_attrs[k], b_attrs[k]))
    return matches, conflicts


def score_pair(a, b, va, vb):
    """`a`, `b` are normalized records; `va`, `vb` their embedding vectors."""
    semantic = embed.cosine(va, vb)
    lexical = _lexical(a["clean_desc"], b["clean_desc"], a["tokens"], b["tokens"])
    matches, conflicts = _attribute_agreement(a["attributes"], b["attributes"])
    uom_match = a["uom_std"] == b["uom_std"]

    expected = _EXPECTED.get(a["category"], _EXPECTED["OTHER"])
    attr_component = min(1.0, len(matches) / expected)
    total = W_ATTR * attr_component + W_SEMANTIC * semantic + W_LEXICAL * lexical

    conflict = bool(conflicts) or not uom_match
    if conflict:
        total = min(total, CONFLICT_CAP)

    return {
        "semantic": round(semantic, 4),
        "lexical": round(lexical, 4),
        "attr_agree": len(matches),
        "attr_expected": expected,
        "attr_shared": len(matches) + len(conflicts),
        "attr_matches": matches,
        "attr_conflicts": conflicts,
        "uom_match": uom_match,
        "conflict": conflict,
        "total": round(total, 4),
    }
