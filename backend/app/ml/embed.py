"""
embed.py — semantic vectorization (Stage 2).

Default: a pure-stdlib TF-IDF space over word tokens + character n-grams, with
cosine similarity. Short technical strings ("HEX BOLT M10X50 GRADE 8.8") don't
need a transformer to be separated well, and IDF down-weights ubiquitous words
like "VALVE"/"PIPE" so the *discriminating* tokens dominate the score.

Upgrade path (documented, not required to run):
    A sentence-transformers backend (all-MiniLM-L6-v2, 384-d) drops in behind
    the same `EmbeddingSpace` interface — `fit()` becomes a no-op and
    `vector()` returns the model encoding. pgvector then stores the 384-d
    vectors and does ANN blocking in Postgres. `HAVE_ST` reports availability.
"""
import math
import re
from collections import Counter

try:                                    # optional heavy backend
    from sentence_transformers import SentenceTransformer  # noqa: F401
    HAVE_ST = True
except Exception:
    HAVE_ST = False

_CHAR_N = (3, 4)
_CHAR_W = 0.5          # char n-grams weighted below whole words


def _features(text):
    feats = Counter()
    toks = text.split()
    for t in toks:
        feats[f"w:{t}"] += 1.0
    squash = re.sub(r"\s+", "", text)
    for n in _CHAR_N:
        for i in range(len(squash) - n + 1):
            feats[f"c:{squash[i:i+n]}"] += _CHAR_W
    return feats


class EmbeddingSpace:
    """TF-IDF cosine space. `fit` on the corpus, then `vector` per document."""

    def __init__(self):
        self.idf = {}
        self.n_docs = 0

    def fit(self, texts):
        self.n_docs = len(texts)
        df = Counter()
        for t in texts:
            for f in set(_features(t)):
                df[f] += 1
        self.idf = {f: math.log((1 + self.n_docs) / (1 + c)) + 1.0
                    for f, c in df.items()}
        return self

    def vector(self, text):
        feats = _features(text)
        vec = {f: tf * self.idf.get(f, math.log(1 + self.n_docs) + 1.0)
               for f, tf in feats.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {f: v / norm for f, v in vec.items()}


def cosine(a, b):
    """Cosine of two pre-normalized sparse vectors (dicts)."""
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(f, 0.0) for f, w in a.items())
