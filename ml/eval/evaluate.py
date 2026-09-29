"""Evaluation harness (flowchart node: 'Metrics: precision / recall / F1').

Because the synthetic data ships with ground-truth groups, we can score the
engine honestly on the standard record-linkage metric: PAIRWISE precision /
recall / F1. A predicted cluster of k rows asserts k*(k-1)/2 "these are the
same" pair decisions; we compare that set against the true pair set.

    precision = correct merges / all merges we made      (did we over-merge?)
    recall    = correct merges / all true duplicates      (did we miss any?)
    F1        = harmonic mean
"""
import csv
from collections import defaultdict
from itertools import combinations


def _pair_set(groups) -> set:
    pairs = set()
    for members in groups:
        for a, b in combinations(sorted(members), 2):
            pairs.add((a, b))
    return pairs


def load_ground_truth(path) -> list:
    groups = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            groups[row["group_id"]].append(int(row["id"]))
    return list(groups.values())


def pairwise_prf(pred_clusters, truth_groups) -> dict:
    pred, truth = _pair_set(pred_clusters), _pair_set(truth_groups)
    tp = len(pred & truth)
    fp = len(pred - truth)
    fn = len(truth - pred)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1}
