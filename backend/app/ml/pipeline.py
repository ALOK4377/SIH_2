"""
pipeline.py — end-to-end orchestration.

    normalize → embed(fit + vectorize) → block → score → cluster → canonicalize

Returns everything downstream consumers (the CLI, the API, the review UI, the
evaluator) need: normalized records, candidate stats, the full scored edge list
(for threshold sweeps), the human-review queue, the clusters, and the golden
records + code mappings.
"""
from .block import generate_candidates
from .canonical import canonicalize
from .cluster import cluster
from .embed import HAVE_ST, EmbeddingSpace
from .normalize import normalize_record
from .score import score_pair

AUTO_THRESHOLD = 0.70     # >= this (and no conflict) → auto-merge
REVIEW_LOW = 0.50         # [REVIEW_LOW, AUTO) (no conflict) → human review queue


def run(raw_rows, auto_threshold=AUTO_THRESHOLD, review_low=REVIEW_LOW):
    records = [normalize_record(r.get("description", ""),
                                r.get("uom", ""),
                                r.get("category_raw", "")) for r in raw_rows]

    space = EmbeddingSpace().fit([r["clean_desc"] for r in records])
    vectors = [space.vector(r["clean_desc"]) for r in records]

    pairs, block_stats = generate_candidates(records)

    edges_all = []          # (i, j, total, conflict) — every scored candidate
    accepted = []           # confident duplicate edges → clustering
    review_queue = []       # (i, j, features) needing a human
    for i, j in pairs:
        f = score_pair(records[i], records[j], vectors[i], vectors[j])
        t, conf = f["total"], f["conflict"]
        edges_all.append((i, j, t, conf))
        if not conf and t >= auto_threshold:
            accepted.append((i, j, t))
        elif not conf and t >= review_low:
            review_queue.append((i, j, f))

    clusters, label_of = cluster(len(records), accepted, records)
    canonicals, mappings = canonicalize(clusters, records, raw_rows)

    review_queue.sort(key=lambda x: -x[2]["total"])
    return {
        "records": records,
        "raw_rows": raw_rows,
        "vectors": vectors,
        "backend": "sentence-transformers" if HAVE_ST else "tfidf-fallback",
        "block_stats": block_stats,
        "edges_all": edges_all,
        "accepted_edges": accepted,
        "review_queue": review_queue,
        "clusters": clusters,
        "label_of": label_of,
        "canonicals": canonicals,
        "mappings": mappings,
        "params": {"auto_threshold": auto_threshold, "review_low": review_low},
    }
