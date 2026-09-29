"""
evaluate.py — measurable quality against a labelled ground truth.

The headline number in entity resolution is *pairwise* precision / recall / F1:
treat every pair of rows the system puts in the same cluster as a predicted
"duplicate", every pair sharing a ground-truth group as an actual duplicate,
and compare.

Also reported:
  * blocking recall — the ceiling recall the candidate generation allows
    (true pairs that survived blocking); if this is < 1.0, no scorer can
    recover the lost pairs.
  * cluster quality — how many predicted clusters are "pure" (no two different
    real items merged) and how many real groups were recovered exactly.
  * a threshold sweep — F1 across operating points, so we can pick/justify one.

All work is done in index space (0..n-1); `group_of` maps index → truth group.
"""
from itertools import combinations

from .cluster import cluster


def _pairs_within(groups):
    """groups: dict key -> list of indices. Returns set of frozenset pairs."""
    out = set()
    for members in groups.values():
        if len(members) > 1:
            out.update(frozenset(p) for p in combinations(sorted(members), 2))
    return out


def truth_pairs(group_of):
    groups = {}
    for idx, g in enumerate(group_of):
        groups.setdefault(g, []).append(idx)
    return _pairs_within(groups)


def cluster_pairs(clusters):
    return _pairs_within({k: v for k, v in enumerate(clusters)})


def prf(pred, truth):
    tp = len(pred & truth)
    fp = len(pred - truth)
    fn = len(truth - pred)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1}


def blocking_recall(candidate_pairs, truth):
    cand = {frozenset(p) for p in candidate_pairs}
    hit = len(cand & truth)
    return hit / len(truth) if truth else 1.0


def cluster_quality(clusters, group_of):
    pred_multi = [c for c in clusters if len(c) > 1]
    pure = 0
    for c in clusters:
        if len({group_of[i] for i in c}) == 1:
            pure += 1
    # real groups recovered exactly as one whole cluster
    truth_groups = {}
    for idx, g in enumerate(group_of):
        truth_groups.setdefault(g, set()).add(idx)
    cluster_sets = [set(c) for c in clusters]
    exact = sum(1 for members in truth_groups.values() if members in cluster_sets)
    return {
        "n_clusters": len(clusters),
        "n_multi_member": len(pred_multi),
        "pure_clusters": pure,
        "pure_fraction": pure / len(clusters) if clusters else 1.0,
        "truth_groups": len(truth_groups),
        "groups_recovered_exactly": exact,
    }


def sweep(edges_all, n_records, truth, thresholds, records):
    rows = []
    for t in thresholds:
        edges = [(i, j, total) for (i, j, total, conf) in edges_all if not conf and total >= t]
        clusters, _ = cluster(n_records, edges, records)
        m = prf(cluster_pairs(clusters), truth)
        rows.append((t, m["precision"], m["recall"], m["f1"]))
    return rows
