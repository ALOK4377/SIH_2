#!/usr/bin/env python3
"""
run_pipeline.py — run the full de-duplication pipeline end-to-end and report.

    python3 scripts/run_pipeline.py                     # uses data/synthetic
    python3 scripts/run_pipeline.py --auto 0.60 --show 6
    python3 scripts/run_pipeline.py --data data/synthetic --out data/synthetic/out

If a ground_truth.csv sits alongside materials.csv, it prints pairwise
precision / recall / F1, blocking recall, cluster quality, and a threshold
sweep. It also prints sample match explanations (including spec-conflict vetoes)
and sample golden records with their assigned CNMC, and writes the outputs
(canonicals, code mapping, review queue) to the --out directory.

Pure standard library — runs offline with zero installs.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml import evaluate as ev          # noqa: E402
from app.ml import explain as explain_mod  # noqa: E402
from app.ml import pipeline as pl          # noqa: E402
from app.ml.score import score_pair        # noqa: E402


def load_materials(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["id"] = int(r["id"])
        r["price"] = float(r["price"]) if r.get("price") else 0.0
    return rows


def load_truth(path, rows):
    with open(path, newline="") as f:
        gt = {int(r["id"]): int(r["group_id"]) for r in csv.DictReader(f)}
    return [gt[r["id"]] for r in rows]      # index-aligned


def bar(title):
    print("\n" + "═" * 72)
    print(f"  {title}")
    print("═" * 72)


def pct(x):
    return f"{100 * x:5.1f}%"


def sample_explanations(res, show):
    records, vectors = res["records"], res["vectors"]
    edges = res["edges_all"]

    accepted = sorted([e for e in edges if not e[3] and e[2] >= res["params"]["auto_threshold"]],
                      key=lambda e: -e[2])
    conflicts = sorted([e for e in edges if e[3]], key=lambda e: -e[2])

    bar("SAMPLE AUTO-MERGES (highest confidence)")
    seen_cat = set()
    shown = 0
    for i, j, _t, _c in accepted:
        cat = records[i]["category"]
        if cat in seen_cat and shown >= show:
            break
        seen_cat.add(cat)
        f = score_pair(records[i], records[j], vectors[i], vectors[j])
        print(explain_mod.explain(records[i], records[j], f, res["params"]["auto_threshold"], res["params"]["review_low"]))
        shown += 1
        if shown >= show:
            break

    bar("SAMPLE SPEC-CONFLICT VETOES (text looks similar, specs differ)")
    shown = 0
    for i, j, _t, _c in conflicts:
        f = score_pair(records[i], records[j], vectors[i], vectors[j])
        if f["semantic"] < 0.45:
            continue
        print(explain_mod.explain(records[i], records[j], f, res["params"]["auto_threshold"], res["params"]["review_low"]))
        shown += 1
        if shown >= show:
            break

    if res["review_queue"]:
        bar("SAMPLE HUMAN-REVIEW QUEUE (ambiguous band)")
        for i, j, f in res["review_queue"][:show]:
            print(explain_mod.explain(records[i], records[j], f, res["params"]["auto_threshold"], res["params"]["review_low"]))


def sample_golden(res, show):
    bar("SAMPLE GOLDEN RECORDS + COMMON NATIONAL MATERIAL CODE")
    by_cnmc = {}
    for m in res["mappings"]:
        by_cnmc.setdefault(m["cnmc"], []).append(m)
    multi = sorted([c for c in res["canonicals"] if c["n_members"] >= 3],
                   key=lambda c: -c["n_members"])
    for c in multi[:show]:
        print(f"\n  {c['cnmc']}   [{c['category']} · UNSPSC {c['unspsc_code']} {c['unspsc_title']}]")
        print(f"    canonical : {c['canonical_desc']}  ({c['uom']})")
        print(f"    unifies {c['n_members']} codes across {c['n_cpses']} CPSEs:")
        for m in by_cnmc[c["cnmc"]][:6]:
            print(f"      - {m['cpse']:5} {m['local_code']:14} | {m['description']}")


def write_outputs(res, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "canonicals.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cnmc", "category", "unspsc_code", "unspsc_title",
                    "canonical_desc", "uom", "n_members", "n_cpses", "member_ids"])
        for c in res["canonicals"]:
            w.writerow([c["cnmc"], c["category"], c["unspsc_code"], c["unspsc_title"],
                        c["canonical_desc"], c["uom"], c["n_members"], c["n_cpses"],
                        "|".join(map(str, c["member_ids"]))])

    with open(os.path.join(out_dir, "code_mapping.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "cpse", "local_code", "cnmc", "description"])
        for m in res["mappings"]:
            w.writerow([m["id"], m["cpse"], m["local_code"], m["cnmc"], m["description"]])

    with open(os.path.join(out_dir, "review_queue.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id_a", "id_b", "total", "semantic", "lexical",
                    "attr_agree", "desc_a", "desc_b"])
        for i, j, ft in res["review_queue"]:
            ra, rb = res["records"][i], res["records"][j]
            w.writerow([res["raw_rows"][i]["id"], res["raw_rows"][j]["id"],
                        ft["total"], ft["semantic"], ft["lexical"], ft["attr_agree"],
                        ra["clean_desc"], rb["clean_desc"]])
    print(f"\n  → wrote canonicals.csv, code_mapping.csv, review_queue.csv to {out_dir}/")


def main():
    ap = argparse.ArgumentParser(description="Run the Samanvay de-duplication pipeline.")
    ap.add_argument("--data", default=os.path.join("data", "synthetic"))
    ap.add_argument("--auto", type=float, default=pl.AUTO_THRESHOLD)
    ap.add_argument("--review-low", type=float, default=pl.REVIEW_LOW)
    ap.add_argument("--show", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    mats_path = os.path.join(args.data, "materials.csv")
    gt_path = os.path.join(args.data, "ground_truth.csv")
    rows = load_materials(mats_path)

    bar("SAMANVAY · MATERIAL DE-DUPLICATION PIPELINE")
    print(f"  input        : {mats_path}  ({len(rows)} rows)")

    res = pl.run(rows, auto_threshold=args.auto, review_low=args.review_low)
    bs = res["block_stats"]
    print(f"  embeddings   : {res['backend']}")
    print(f"  blocking     : {bs['n_candidate_pairs']:,} candidate pairs "
          f"(vs {bs['n_all_pairs']:,} all-pairs · {pct(bs['reduction_ratio'])} reduction)")
    print(f"  thresholds   : auto ≥ {args.auto:.2f}   review [{args.review_low:.2f}, {args.auto:.2f})")
    print(f"  clusters     : {len(res['clusters']):,}   "
          f"review queue: {len(res['review_queue']):,}   "
          f"canonical codes: {len(res['canonicals']):,}")

    if os.path.exists(gt_path):
        group_of = load_truth(gt_path, rows)
        truth = ev.truth_pairs(group_of)
        pred = ev.cluster_pairs(res["clusters"])
        m = ev.prf(pred, truth)
        br = ev.blocking_recall([(i, j) for (i, j, _t, _c) in res["edges_all"]], truth)
        q = ev.cluster_quality(res["clusters"], group_of)

        bar(f"EVALUATION vs GROUND TRUTH  (operating point: auto ≥ {args.auto:.2f})")
        print(f"  duplicate pairs in truth : {len(truth):,}")
        print(f"  precision : {pct(m['precision'])}   (TP={m['tp']:,}  FP={m['fp']:,})")
        print(f"  recall    : {pct(m['recall'])}   (FN={m['fn']:,})")
        print(f"  F1        : {pct(m['f1'])}")
        print(f"  blocking recall (ceiling): {pct(br)}")
        print(f"  clusters  : {q['n_clusters']:,} total · {q['n_multi_member']:,} multi-member · "
              f"{pct(q['pure_fraction'])} pure")
        print(f"  groups recovered exactly : {q['groups_recovered_exactly']:,} / {q['truth_groups']:,}")

        bar("THRESHOLD SWEEP  (precision / recall / F1)")
        ths = [round(0.40 + 0.02 * k, 2) for k in range(26)]
        rows_sw = ev.sweep(res["edges_all"], len(res["records"]), truth, ths, res["records"])
        best = max(rows_sw, key=lambda r: r[3])
        print("   thr    precision   recall     F1")
        for t, p, r, f1 in rows_sw:
            star = "  ← best F1" if (t, p, r, f1) == best else ""
            if abs(t - args.auto) < 1e-9 or star or int(round(t * 100)) % 6 == 0:
                print(f"   {t:.2f}    {pct(p)}     {pct(r)}    {pct(f1)}{star}")
        print(f"\n  best F1 = {pct(best[3])} at threshold {best[0]:.2f} "
              f"(precision {pct(best[1])}, recall {pct(best[2])})")

    sample_explanations(res, args.show)
    sample_golden(res, args.show)

    if args.out:
        write_outputs(res, args.out)

    print()


if __name__ == "__main__":
    main()
