"""
cluster.py — constraint-aware grouping of matched pairs into entities (Stage 5).

Naive connected-components (plain Union-Find) over accepted edges is fragile:
one under-specified row (e.g. "CENTRIFUGAL PUMP SS" with the HP dropped) is
textually near-identical to BOTH a 2HP and a 10HP pump, so it transitively
chains two genuinely different items into one giant cluster.

We prevent that with cannot-link constraints. Each cluster carries a
consolidated attribute *profile*. Edges are merged strongest-first
(single-linkage order), but a merge is REJECTED if the two clusters' profiles
disagree on any discriminating spec (2HP vs 10HP). So the hp-less row attaches
to whichever item claims it first, and the incompatible one stays separate —
no bridge can fuse conflicting groups.

Records with no accepted, compatible edge remain singleton clusters
(legitimately unique materials).
"""
from .score import _DISCRIMINATING, _eq


def _profile(attrs):
    return {k: v for k, v in attrs.items() if k in _DISCRIMINATING}


def _compatible(pa, pb):
    for k, v in pa.items():
        if k in pb and not _eq(v, pb[k]):
            return False
    return True


def cluster(n_records, scored_edges, records):
    """
    scored_edges : iterable of (i, j, total) accepted duplicate pairs.
    records      : normalized records (for attribute profiles), index-aligned.
    Returns (clusters, label_of).
    """
    parent = list(range(n_records))
    rank = [0] * n_records
    profiles = [_profile(records[i]["attributes"]) for i in range(n_records)]

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for i, j, _t in sorted(scored_edges, key=lambda e: -e[2]):
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        if not _compatible(profiles[ri], profiles[rj]):
            continue                      # cannot-link: would fuse different items
        if rank[ri] < rank[rj]:
            ri, rj = rj, ri
        parent[rj] = ri
        if rank[ri] == rank[rj]:
            rank[ri] += 1
        merged = dict(profiles[ri])
        merged.update(profiles[rj])
        profiles[ri] = merged

    groups = {}
    for i in range(n_records):
        groups.setdefault(find(i), []).append(i)

    clusters = list(groups.values())
    label_of = [0] * n_records
    for c_idx, members in enumerate(clusters):
        for i in members:
            label_of[i] = c_idx
    return clusters, label_of
