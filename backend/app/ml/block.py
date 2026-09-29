"""
block.py — candidate generation / blocking (Stage 3).

Comparing every row against every other is O(n^2) and unscalable. Blocking
restricts comparisons to rows that share a coarse key, so we only score pairs
that could plausibly match.

MVP key: the detected `category`. All true duplicates share a category
(a bearing is never a valve), so category blocking keeps recall high while
cutting the pair count by ~1/n_categories.

Upgrade path: at CPSE scale, replace/augment this with ANN over the 384-d
embeddings (pgvector `<=>` or FAISS) — top-k nearest neighbours per row — which
also catches items whose category was mis-detected. Same output contract:
a list of (i, j) index pairs to score.
"""
from itertools import combinations


def generate_candidates(records):
    """Return (pairs, stats). `pairs` is a list of (i, j) index tuples."""
    blocks = {}
    for i, r in enumerate(records):
        blocks.setdefault(r["category"], []).append(i)

    pairs = []
    for cat, idxs in blocks.items():
        pairs.extend(combinations(idxs, 2))

    total = len(records)
    max_pairs = total * (total - 1) // 2 if total > 1 else 1
    stats = {
        "n_records": total,
        "n_blocks": len(blocks),
        "block_sizes": {c: len(v) for c, v in sorted(blocks.items())},
        "n_candidate_pairs": len(pairs),
        "n_all_pairs": max_pairs,
        "reduction_ratio": 1.0 - (len(pairs) / max_pairs) if max_pairs else 0.0,
    }
    return pairs, stats
