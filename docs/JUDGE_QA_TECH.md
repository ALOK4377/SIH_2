# Samanvay — Technology Q&A Bank for Judges

> Companion to `PITCH_SCRIPT.md` §4. That section has 8 broad questions. This document is the
> **deep technology bank** — 52 questions, grouped by how likely they are, each with a short
> answer to *say out loud* and the backing detail to use only if pressed.
>
> Every number here was re-verified against a live `python3 scripts/run_pipeline.py` run.

---

## 0. Three rules for answering a technical judge

1. **Answer in one sentence, then stop.** Let them ask for more. Long answers sound defensive.
2. **Never bluff a number.** "I don't have that figure, but I can tell you how we'd measure it"
   scores higher than a wrong number. Judges catch invented numbers and stop trusting everything.
3. **Own the limitation, then show the design that contains it.** Every weakness below has a
   containment story — the review queue, the veto, or the documented upgrade slot. Use it.

---

## 1. TIER 1 — the six you will almost certainly be asked

### Q1. Which AI model are you using?

> **Say:** "The matching engine is a hybrid scorer, not a single model. Sixty percent of the score
> is deterministic structured-attribute agreement, twenty-five percent is text similarity from
> TF-IDF vectors, fifteen percent is fuzzy string matching. We deliberately kept it dependency-free
> so it's reproducible and CPU-only, and transformer embeddings drop into one module when we want
> the recall boost."

- The weights are literal constants in `backend/app/ml/score.py`: `W_ATTR = 0.60`,
  `W_SEMANTIC = 0.25`, `W_LEXICAL = 0.15`.
- **Why this design is the strong answer:** the neural part is the *smallest* term. A judge who
  hears "we use an LLM" assumes a black box. You can say the opposite — the majority of your
  decision is inspectable engineering logic, which is what a government rollout actually needs.
- If they push on "so it's not really AI": entity resolution *is* a classical ML problem —
  blocking, pairwise scoring, and transitive clustering are the standard record-linkage pipeline
  used by census bureaus and banks. Naming it correctly is more credible than calling it an LLM.

### Q2. Your plan document mentions sentence-transformers. Is that what's running?

> **Say:** "No — and that's a deliberate choice we can defend. `requirements.txt` has MiniLM,
> pgvector and RapidFuzz commented out. We ship the TF-IDF baseline because it needs zero installs,
> it's fully deterministic so our metrics are exactly reproducible, and it already hits ninety
> percent precision. `embed.py` has the feature flag — `HAVE_ST` — so MiniLM is a one-line swap,
> not a rewrite."

- **This is your highest-risk question.** `docs/PROJECT_PLAN.md` §3 promises MiniLM, pgvector,
  RapidFuzz and XGBoost; none are installed. The pipeline banner literally prints
  `embeddings : tfidf-fallback` — a judge reading your terminal will see it.
- **Fix before the finale:** either align `PROJECT_PLAN.md` §3 with reality, or add one line noting
  the heavy stack is the documented production upgrade. Do not let them find the mismatch first.
- Honest framing that works: *"We chose to be able to prove our numbers over being able to claim a
  bigger model."*

### Q3. How do you know you aren't merging two genuinely different items?

> **Say:** "Two mechanisms. First, a hard conflict veto — if any discriminating spec disagrees, or
> the units of measure disagree, the score is capped at 0.25, which is far below our 0.70 merge
> gate. It cannot auto-merge, no matter how similar the text is. Second, the clustering carries
> cannot-link constraints, so a merge is rejected if it would pull an incompatible item into an
> existing family."

- The veto lives in `score.py` (`CONFLICT_CAP = 0.25`) over 20 discriminating attributes: thread,
  size_mm, schedule, rating, grade, material, csa, voltage, cores, insulation, hp, seal, code_no,
  btype, vtype, ptype, sub, ends, armour, finish, gtype.
- The clustering in `cluster.py` is a **constraint-aware Union-Find** that processes edges
  strongest-first and calls `_compatible()` on the two clusters' attribute profiles before merging.
- **Live proof you can show:** the pipeline's own "SPEC-CONFLICT VETOES" section prints real
  examples, e.g. a 6 SQMM PVC unarmoured cable vs a 2.5 SQMM XLPE armoured cable — fuzzy similarity
  0.66, but scored 0.25 and blocked with the reason `csa 6≠2.5, insulation PVC≠XLPE`.

### Q4. Why is recall only 80%? That means you're missing a fifth of the duplicates.

> **Say:** "Correct, and that's the deliberate operating point. In this domain a false merge is far
> more expensive than a missed merge — a wrong merge sends the wrong spare part to a refinery, a
> missed merge just leaves a duplicate code we catch next pass. So we tuned precision-first, and the
> 873 pairs we're unsure about go to a human rather than being silently dropped."

- Full sweep from the live run:

  | Gate | Precision | Recall | F1 |
  |---|---|---|---|
  | 0.60 | 85.5% | 83.7% | 84.6% |
  | **0.70 (shipped)** | **90.2%** | **80.5%** | **85.1%** |
  | 0.72 | 92.1% | 79.4% | 85.3% |
  | **0.76 (best F1)** | **96.9%** | **77.5%** | **86.1%** |
  | 0.84 | 98.3% | 63.0% | 76.8% |
  | 0.90 | 98.6% | 38.8% | 55.7% |

- **Be ready for the follow-up:** "then why aren't you at 0.76?" Your shipped gate is *not*
  F1-optimal. Honest answer: *"0.76 is our precision-first configuration and it's one config value.
  We shipped 0.70 to surface more candidates into the review queue for the demo, since the human
  loop is part of what we're showing."* Better still — change it to 0.76 before the finale and
  quote 96.9% precision.

### Q5. This is synthetic data. Doesn't that make the accuracy meaningless?

> **Say:** "It's the opposite — synthetic data with planted ground truth is the only way we can
> report *measured* precision and recall instead of just claiming accuracy. Real CPSE material
> masters are commercially sensitive and we couldn't obtain multi-CPSE data with a verified answer
> key. Our generator applies seven stacked corruptions modelled on real ERP patterns, at a fixed
> seed, so anyone can reproduce our exact numbers."

- `scripts/gen_synthetic_data.py`, seed 42. Corruptions include abbreviation swaps, case scrambling,
  vendor-noise injection, unit-spelling drift, token dropping at p=0.22 and full token shuffle at
  p=0.30.
- The answer key is in a **separate file** (`ground_truth.csv`) that the pipeline never reads — it's
  only opened afterwards to score. Structurally the model cannot peek. Say this; it's a strong point.
- **The honest caveat to volunteer:** *"Real data will have failure modes our generator didn't
  invent — multilingual entries, vendor part numbers as descriptions, legacy encodings. That's
  exactly why the human review queue isn't optional in our design."*

### Q6. What happens when you're wrong?

> **Say:** "Three layers. Anything below 0.70 but above 0.50 never auto-merges — it goes to the
> review queue with a plain-English explanation. A steward approves or rejects in one click, and the
> mapping to every original local code is preserved, so a merge is always reversible. And every
> action is written to an audit log."

- Nothing is destructive: `code_mapping` retains all 1,274 original local codes permanently.
- `POST /review/clusters/{id}/split` exists to undo a bad merge. **Note:** it currently has no
  frontend wrapper, so don't promise you can demo the split — say "the API supports it."

---

## 2. TIER 2 — algorithm internals

### Q7. Walk me through the pipeline stage by stage.

> Normalize → Embed → Block → Score → Threshold → Cluster → Golden record + code. Six stages, all
> under `backend/app/ml/`, roughly 900 lines of pure standard-library Python.

### Q8. What does normalization actually do?

- Uppercase, split glued tokens (`3.5CX6` → `3.5C X 6`), unify `SQ MM`/`MM2` → `SQMM`.
- Strip vendor noise by regex: `MAKE SKF`, `AS PER`, `REF DWG`, `IS 1239`, `ASTM A106`.
- Expand 56 abbreviations from `data/reference/abbreviations.json` (`BRG`→`BEARING`, `SMLS`→`SEAMLESS`).
- Map 32 UOM spellings down to 8 canonical units via `uom_map.json`.
- Extract structured attributes by category-aware regex, then match type words **fuzzily** at a 0.8
  cutoff so typos still resolve — that's why `SUBMERISBLE` and `SPHHERICAL` are handled.

### Q9. Why fuzzy-match the type words? Give an example.

> Your own dataset contains `SPHHERICAL ROLLER BEARING 6003` and `TAPER ROLLEER BRG 6206`. Exact
> matching would extract no bearing type at all from those rows and they'd fall out of their family.
> `_present()` in `normalize.py` uses `difflib.SequenceMatcher` at ratio ≥ 0.8 on tokens of length ≥ 4.

### Q10. What is blocking and why do you need it?

> **Say:** "Comparing every row to every other row is quadratic. With 1,274 rows that's 810,901
> pairs; at a million rows it's five hundred billion. So we only compare items in the same detected
> category. That cuts us to 118,405 pairs — an 85.4% reduction — while still keeping 97.9% of the
> true duplicate pairs reachable."

- The 97.9% figure is your **blocking recall ceiling**: the best recall any scorer could achieve
  given what blocking discarded. Quoting a ceiling shows you understand the cost of your own
  optimization — judges notice this.

### Q11. What are you losing in that 2.1%?

> Items whose category was misdetected — typically rows so corrupted that no category keyword or
> spec survived, which land in `OTHER`. It's a bounded, measured loss, and it caps our recall at
> 97.9% before scoring even begins.

### Q12. Explain your scoring formula.

```
total = 0.60 × attribute_agreement
      + 0.25 × semantic_similarity     (TF-IDF cosine)
      + 0.15 × lexical_similarity      (difflib ratio + Jaccard, averaged)

if any discriminating spec conflicts, or UOM differs:
    total = min(total, 0.25)           # hard veto
```

- `attribute_agreement` is **count-aware**, not binary: `min(1.0, matches / expected[category])`,
  where expected is BEARING 3, VALVE 4, PUMP 3, PIPE 3, CABLE 4, FASTENER 3, GASKET 3, OTHER 2.
- **Why count-aware matters:** two items agreeing on 1 of 4 expected cable specs score much lower
  than two agreeing on all 4. A binary "specs match" flag would treat those identically.

### Q13. Where did the weights 0.60 / 0.25 / 0.15 come from?

> **Say honestly:** "They're hand-set from domain reasoning, not learned — structured specs are the
> real identity of an industrial part, so they dominate. We validated the choice by threshold sweep
> rather than by fitting the weights, because with 350 groups we'd risk overfitting. The documented
> next step is a classifier trained on the steward decisions we're already collecting."

- Do **not** claim they were tuned or learned. "Hand-set, then validated" is defensible; "trained"
  is falsifiable in one question.

### Q14. Why TF-IDF with character n-grams instead of just words?

> Word-level TF-IDF fails on this data because tokens are corrupted. Character 3- and 4-grams still
> match `BEARING` to `BRNG` and `BRG` through shared substrings. `embed.py` combines both, weighting
> char n-grams at 0.5 (`_CHAR_N = (3,4)`, `_CHAR_W = 0.5`).

### Q15. How does clustering turn pair scores into families?

> **Say:** "Union-Find with constraints. We sort all merge-worthy edges by score descending and
> merge strongest-first, but before each merge we check the two clusters' attribute profiles are
> compatible. If merging would create a conflict, we skip that edge."

- Standard single-linkage would chain A–B–C even when A and C conflict. The compatibility check is
  what prevents that transitive over-merge.

### Q16. Why strongest-edge-first rather than arbitrary order?

> Because the cannot-link check makes the result order-dependent. Processing highest-confidence
> merges first means the most reliable evidence shapes the cluster before weaker evidence can
> distort it — the same greedy logic as Kruskal's algorithm.

### Q17. How do you pick the canonical description for a family?

> The member with the most extracted attributes, breaking ties on longest cleaned description —
> `_pick_representative()` in `canonical.py`. The intuition is that the most *specific* record is
> the most complete one.
>
> **Known weakness to own:** it picks the most specific *surviving* description, which can still be
> a corrupted one. Your own output has `TAPER ROLLEER BEARING 6206 ZZ` and `GEAR PUMP 10HP CCAST
> IRON` as canonical text. If a judge spots a typo in a golden record, say: *"Representative
> selection is extractive today — we pick the best existing row. Generating clean canonical text
> from the extracted attributes is a straightforward next step."*

### Q18. Explain the national code format.

> `IN-311516-0000011-6` — country prefix `IN`, six-digit UNSPSC commodity class `311516`
> (Bearings and bushings), a seven-digit serial, and a **mod-11 check digit**.

- Check digit uses weights `[2,3,4,5,6,7]` cycling right-to-left, `k = (11 - total mod 11) mod 11`,
  emitting `0` when k is 10. Implemented in `canonical.py::_check_digit`.
- **Why include a check digit:** it catches single-digit typos and most transpositions when a code is
  keyed into an ERP by hand. This is a genuinely good detail — it shows you designed for the field,
  not just the demo.

### Q19. What is UNSPSC and are you using the real thing?

> **Say:** "UNSPSC is the UN Standard Products and Services Code, the global commodity taxonomy —
> using it means our codes interoperate with GeM and international catalogues instead of being a
> private scheme. We ship an eight-class subset covering our seven categories; the full taxonomy is
> a data-file swap, not a code change."

- Be upfront that `data/reference/unspsc_subset.json` has 8 entries. If you imply full UNSPSC
  coverage and they ask how many classes UNSPSC has, you're exposed.

### Q20. Are the explanations real or templated?

> Generated from the actual score components in `explain.py` — each says which specs agreed, the
> text and fuzzy scores, whether UOM matched, and on a veto, exactly which attribute conflicted and
> with what values. The reason string is derived from the decision, not written alongside it.

---

## 3. TIER 3 — accuracy and evaluation

### Q21. Define your precision and recall. Precision of what, exactly?

> **Pairwise.** Ground truth defines 2,184 pairs of rows that are genuinely the same item. We
> produced 1,948 merge pairs, of which 1,758 were correct (TP) and 190 wrong (FP), and we missed 426
> (FN). Precision 90.2%, recall 80.5%, F1 85.1%.

- **Know why pairwise:** cluster-level accuracy hides partial credit. If a true family of 6 splits
  into two 3s, cluster accuracy calls it a total failure while pairwise correctly gives you the 6
  pairs you did get right. Say this if asked why not cluster accuracy.

### Q22. What's cluster purity, and why report it separately?

> 92.4% of our 435 clusters contain rows from only one true group. Purity measures over-merging
> specifically; pairwise F1 blends over- and under-merging into one number. Reporting both tells you
> *which* error you're making.

### Q23. How many families did you get exactly right?

> 228 of 350 — 65%. Exact recovery is the strictest possible measure: every member present, no
> extras. It's the number to quote if someone accuses you of cherry-picking a flattering metric.

### Q24. Are these numbers hardcoded?

> **Say:** "No — they're recomputed from ground truth on every run. Run `python3
> scripts/run_pipeline.py` yourself; it needs no installs and no database. `evaluate.py` computes
> them, and the threshold sweep in the output would be impossible to fake consistently."

- Offer to run it live. Willingness to run it in front of them is itself the proof.

### Q25. What's your biggest source of error?

> **This is your best answer in the whole document — see §7 Q44.** 33 of your 435 clusters are
> impure, and the 12 provable ones all share a single root cause you can name precisely.

---

## 4. TIER 4 — the data

### Q26. How big is your dataset?

> 1,274 rows, 8 columns, 10 CPSEs across 5 sectors, resolving to 350 true items — a 3.6× duplication
> factor. Companion files: `ground_truth.csv` (1,274×2) and `canonicals.csv` (350×5).

### Q27. How messy is it really? Quantify it.

- **17 different UOM spellings** for 8 real units (EACH, Each, EA, UNIT, NO, No, NOS, NOS., PCS…).
- **34 category labels** for 7 real categories (`PUMPING UNIT`, `PUMP ASSY`, `PUMPS` all mean pump).
- Only **18 of 1,274 descriptions are exact duplicates** — 98.6% are textually unique. So exact
  matching or `GROUP BY description` would find almost nothing. **Quote this number when someone
  asks why they can't just use SQL.**

### Q28. Why only 7 categories?

> They're the highest-volume MRO families in a refinery context — bearings, valves, pumps, pipes,
> cables, fasteners, gaskets. Adding a category is a controlled-vocabulary entry in `normalize.py`
> plus an `expected_keys` count, not an architectural change.

### Q29. Can it handle a category you've never seen?

> **Say honestly:** "It degrades gracefully rather than failing — unknown items land in `OTHER`,
> which expects only 2 attribute agreements, so matching leans more on text similarity and the
> pairs are more likely to route to human review. It won't match them as well, and it won't
> confidently merge them wrongly either."

### Q30. What if descriptions are in Hindi or mixed script?

> Not handled today — our normalization assumes Latin-script uppercase. Character n-grams are
> script-agnostic in principle so the embedding layer would still function, but the abbreviation
> dictionary and spec regexes would need per-language versions. Worth flagging as a real gap for a
> national rollout.

---

## 5. TIER 5 — architecture, stack, scale

### Q31. What's your stack?

> **Frontend:** React 18.3 + TypeScript 5.5 + Vite 5.3, Tailwind 3.4, React Router 6.24, TanStack
> Query 5.51 for server state, Recharts 2.12 for the dashboard.
> **Backend:** FastAPI 0.141 on Uvicorn, SQLAlchemy 2.0 ORM, Pydantic 2.13 for validation.
> **Data:** SQLite for the demo, PostgreSQL 16 + pgvector for production, both via one env var.
> **Ops:** Docker Compose — backend, frontend on nginx, Postgres, Redis.

### Q32. Is this MERN? Django?

> **Neither.** No Mongo, no Django. It's React + FastAPI + Postgres — closest named acronym is
> "FARM" but that specifies Mongo, so just name the components. Say the layers, not an acronym.

### Q33. Why FastAPI over Django or Flask?

> Three reasons: native async so the pipeline can move to background workers without rewriting the
> API layer; Pydantic validation on every request and response, which matters when ingesting
> untrusted CSVs; and auto-generated OpenAPI docs at `/docs` — which is also a nice thing to show a
> judge live. Django's ORM and admin would be weight we don't use.

### Q34. Why SQLite in the demo? Isn't that a toy?

> It's zero-configuration for a laptop demo, and it's one environment variable to Postgres —
> `SAMANVAY_DATABASE_URL`. The SQLAlchemy models are database-agnostic. Docker Compose already
> brings up Postgres 16 with pgvector.

### Q35. Will it scale to millions of rows?

> **Say:** "The pipeline is quadratic within a block, so the honest answer is that blocking is what
> makes it scale, and beyond a few hundred thousand rows exact category blocking isn't enough. The
> documented path is pgvector approximate-nearest-neighbour to generate candidates instead of full
> within-category pairing, plus Celery workers to parallelise scoring by block, which shards
> naturally because blocks are independent."

- **Do the arithmetic if pushed:** 1,274 rows → 810,901 possible pairs. One million rows → about
  5×10¹¹. Blocking's 85% reduction is not enough at that size; you need ANN. Saying this unprompted
  is far more impressive than claiming it already scales.
- **Do not claim Celery is working.** It's in `docker-compose.yml` and Redis runs, but nothing
  consumes it. Say "documented scale path", never "we have workers".

### Q36. How long does a run take?

> **3.8 seconds** for 1,274 rows on a laptop — single-threaded pure Python, scoring 118,405 pairs,
> no GPU anywhere in the system. Quote the real number; it's more impressive than a vague one.

### Q37. Why is the pipeline synchronous?

> Because at demo scale it finishes inside an HTTP request and synchronous code is easier to reason
> about and debug. `pipeline_service.py` is the single seam where it becomes a Celery task — the API
> already returns a `job` record with status, so the async contract exists.

### Q38. Do you have tests?

> **Say honestly:** "No unit tests — `backend/app/tests/` is empty, and that's a real gap. What we
> have instead is a full-pipeline regression harness: `run_pipeline.py` recomputes precision, recall
> and F1 against ground truth on every run, so any change that breaks matching shows up immediately
> as a metric drop. That's caught real regressions during the build, but it's not a substitute."

- If you have time before the finale, adding even three tests (check digit, UOM normalization, the
  conflict veto) converts this from a weakness into a non-issue. High value for the effort.

### Q39. How is the frontend talking to the backend?

> REST over nine router groups, with TanStack Query handling caching, refetch and loading states on
> the client. API base is configurable via `VITE_API_BASE`. Every response is a Pydantic-validated
> schema, so the TypeScript types mirror real contracts.

---

## 6. TIER 6 — security, governance, deployment

### Q40. Who can approve a merge? Is there authentication?

> **Say honestly:** "Not yet — auth is our next sprint. The `User` model and the role concept exist,
> but there are no login routes, so the audit log currently attributes every action to a single
> `steward` identity. The audit plumbing is real and complete; wiring JWT and populating the actor
> from the token is the remaining work."

- **Do not say roles are enforced.** The `users` table has 0 rows and the actor string is hardcoded.
  If they check, that's the credibility hit you can't recover from in a Q&A.

### Q41. What's in the audit log?

> Entity type, entity id, action, actor, timestamp, and a JSON detail blob — for merges, splits,
> review decisions, pipeline runs and ingests. It's append-only and queryable via `/audit`.

### Q42. Is this deployable in a government environment?

> Fully containerised via Docker Compose, no external API calls, no cloud dependency, and the
> matching engine is pure standard-library Python — so it runs completely air-gapped. For CPSE data
> that never leaves the premises, that's a design requirement, not an accident. **This is a
> genuinely strong point; make it.**

### Q43. How would a CPSE actually integrate this with SAP?

> **Say:** "Today, CSV in and CSV out — which is exactly how these teams already exchange material
> master extracts, so it works on day one with no integration project. The roadmap item is a direct
> SAP adapter reading MARA and MAKT, but I'd argue CSV first is the right sequencing: it gets a CPSE
> to value without a six-month IT engagement."

- Naming the actual SAP tables (`MARA` = material master general data, `MAKT` = material
  descriptions) signals you've thought about the real system.

---

## 7. TIER 7 — the trap questions

These are where you can actually lose marks. Know them cold.

### Q44. ⚠️ "Are all nine of those bearings really the same item?"

**This is the most dangerous question you can be asked, because the answer is no** — and it targets
the family your pitch opens with.

`IN-311516-0000011-6` (`ROLLER ZZ 30210 BEARING`, 9 codes / 8 CPSEs), the hook in `PITCH_SCRIPT.md`
Slide 2, is an **over-merge**. It mixes three distinct true groups: the sealed `30210 ZZ` bearing
(5 rows) and two unsealed `30210` groups (4 rows). Same for the Review Queue demo pair —
`IN-311516-0000006-0` (`TAPER ROLLEER BEARING 6206 ZZ`, 7 codes) mixes the sealed and unsealed 6206.

Ground truth caps a real family at 6 members, so **every family in your output with 7+ members is
provably an over-merge** — there are 12 of them.

**The root cause, and it is beautifully consistent — all 12 share it:**

> The conflict veto only fires on **declared disagreement**. When one record says `ZZ` and the other
> says nothing about sealing, no conflict is registered, so the veto never triggers and the strong
> text similarity carries the merge through.

Every one of the 12 is an attribute present in one record and absent in the other — seal on five
bearing families, HP on three pump families, size or schedule on two pipe families, material on one
pump family, and one cable family where `XLPE` was corrupted to `*LPE` so insulation extraction
failed.

**If asked, say this:**

> "Not quite — that family is over-merged, and I can tell you exactly why. Our veto fires when two
> records *disagree* on a spec, but not when one record is simply silent. A `30210 ZZ` and a plain
> `30210` don't contradict each other, so the text similarity carries the merge. The fix is an
> asymmetric specificity rule: if one record declares a discriminating attribute and the other
> declares nothing, that's not agreement — it should cap the score into the review band. All twelve
> of our over-merges have this single cause, which is why I'm confident it's one rule, not twelve
> patches."

Naming your own dominant failure mode precisely, with a count and a fix, will land better with a
technical judge than any clean number. **But you must not be the second person to notice it.**

**Two things to do before the finale:**

1. **Change your demo hook** to a clean family. `IN-401015-0000040-0`
   (`SUBMERSIBLE PUMP 2HP STAINLESS STEEL`) is **pure and complete** — 6 codes, 6 CPSEs, all one
   true group, nothing missing. Prices run ₹20,045.78 (SAIL) to ₹27,467.44 (CPCL): a **₹7,422 gap
   between cheapest and dearest**, and **₹23,410 of total excess** across the six buyers if they'd
   all paid SAIL's price. It makes the same point without the vulnerability — and unlike the
   bearing, it survives a judge checking it.
2. **Avoid searching `6205` on stage.** It returns the over-merged `IN-311516-0000030-2` sitting
   right beside a singleton `MAKE POLYCAB BAALL BEARING 6205` — an over-merge and an under-merge
   adjacent on one screen.

### Q45. ⚠️ "Where does the ₹18.6 lakh savings figure come from?"

> **Say:** "It's the sum, over families bought by more than one CPSE, of each member's price minus
> that family's lowest price — so it's the price spread on items we've identified as identical. I'd
> call it indicative rather than a forecast, for two reasons: our dataset has prices but no
> quantities, so it isn't volume-weighted; and any over-merged family inflates it by comparing prices
> of items that aren't actually the same."

- **The real numbers:** the pipeline reports ₹1,862,961.05, but the ground-truth ceiling — the same
  calculation on *correct* families — is ₹1,258,074.59. So the figure is **148.1% of the true
  maximum**, and half of it (₹937,655.27, across the 33 impure families) comes from over-merges.
- Worst single case: `IN-401015-0000015-9`, where an under-specified `submersible pump ci` at
  ₹20,948 was merged into a 2HP family priced ₹69,376–₹89,999, fabricating ₹166,432 of "savings"
  on its own.
- **Fix it if you can:** excluding families whose members have subset attribute profiles removes most
  of the inflation. Otherwise, say "indicative" every single time you say the number, and never
  extrapolate it to crores in front of a technical judge.

### Q46. ⚠️ "You have 144 single-member codes but ground truth says 52. Why?"

> That's the mirror image of the over-merge problem — under-merging. 92 items that should have joined
> a family stayed alone, mostly rows so corrupted that too few attributes survived to clear the 0.70
> gate. They're the visible face of our 80.5% recall, and they're exactly what the review queue is
> designed to recover.

### Q47. ⚠️ "Your dashboard says 873 pending but the queue shows 40."

> 873 is the full backlog; the view is paginated to the top 40 by score for triage. Already covered
> in `PITCH_SCRIPT.md` — just don't be surprised by it.

### Q48. ⚠️ "Why does `material_raw` have 2,548 rows when your dataset is 1,274?"

> Because the sample catalogue got loaded twice — the loader appends rather than replaces, so
> there's a second batch of 1,274 rows with no pipeline job attached. It doesn't affect the results,
> which all belong to the processed batch, but **clean it before you demo**:
>
> ```bash
> cd ~/Documents/sih2 && rm backend/samanvay.db && python scripts/seed_db.py
> ```
>
> And don't click "Load sample catalogue" twice on stage.

### Q49. ⚠️ "What does `data/synthetic/clusters.json` say?"

> A stale artefact from an early run — 233 rows, cutoff 0.58, different metrics entirely. Nothing
> reads it. **Delete it before the finale** so it can't contradict your live numbers.

### Q50. "Does the human feedback actually improve the model?"

> **Say honestly:** "Not yet. Every steward decision is persisted in the `review` table as a labelled
> pair, so we're accumulating exactly the training set a supervised matcher would need — but the
> pipeline doesn't consume those labels yet. Re-running today reproduces the same metrics. The label
> store is built; closing the loop is next."

- Do not claim it learns. If a judge approves a pair in your demo and then asks whether the numbers
  moved, the answer is visibly no.

### Q51. "What would you do with three more months?"

> Rank them and be specific — this is a chance to show judgement:
> 1. Fix the specificity gap in the veto (Q44) — biggest accuracy win available, and it's one rule.
> 2. Train the scorer on steward labels instead of hand-set weights, closing the feedback loop.
> 3. pgvector ANN candidate generation plus Celery workers, to get past a few hundred thousand rows.
> 4. JWT auth with real steward identities in the audit trail — the gate for any government pilot.
> 5. A live SAP adapter on MARA/MAKT.

### Q52. "What's the one thing you'd want us to remember?"

> "That we can tell you our error rate, and where the errors come from. Most systems in this space
> report a duplicate count. We report precision, recall, cluster purity, a threshold sweep, and our
> dominant failure mode — because for a national code registry, knowing when to *not* merge is worth
> more than merging aggressively."

---

## 8. Numbers to memorise

| Fact | Number |
|---|---|
| Input rows / columns | 1,274 × 8 |
| CPSEs / sectors | 10 / 5 |
| True items (ground truth) | 350 |
| National codes produced | 435 |
| Catalogue reduction | 65.9% |
| Precision / Recall / F1 | 90.2% / 80.5% / 85.1% |
| TP / FP / FN | 1,758 / 190 / 426 |
| True duplicate pairs | 2,184 |
| Best-F1 gate | 0.76 → 96.9% P, 77.5% R, 86.1% F1 |
| Merge gate / review band | ≥ 0.70 / 0.50–0.70 |
| Pairs before / after blocking | 810,901 → 118,405 (85.4% ↓) |
| Blocking recall ceiling | 97.9% |
| Cluster purity | 92.4% (33 of 435 impure) |
| Provable over-merges (7+ members) | 12 |
| Output singletons vs true | 144 vs 52 (92 under-merged) |
| Families exactly recovered | 228 / 350 |
| Review queue size | 873 |
| Full pipeline runtime | 3.8 s, single-threaded, no GPU |
| Score weights | 0.60 attr / 0.25 semantic / 0.15 lexical |
| Conflict cap | 0.25 |
| Exact-duplicate descriptions | 18 of 1,274 (1.4%) |
| UOM spellings / categories collapsed | 17→8 / 34→7 |

## 9. Phrasing

**Use these:**
- "Measured, not claimed."
- "That's a real limitation. Here's the mechanism that contains it."
- "Precision-first, because a wrong merge is more expensive than a missed one."
- "It's a documented upgrade slot, not a rewrite."
- "I'd call that indicative rather than a forecast."

**Avoid these:**
- "It's basically 100% accurate" — you have exact numbers; use them.
- "We use AI/ML" — name the technique.
- "It scales infinitely" — say what breaks and at what size.
- "We have Celery workers" / "roles are enforced" / "it learns from feedback" — all currently false.
- Extrapolating the savings figure to crores in front of a technical judge.

## 10. Pre-finale checklist

- [ ] Reset the DB (`rm backend/samanvay.db && python scripts/seed_db.py`) — fixes the 2,548 rows
- [ ] Delete `data/synthetic/clusters.json`
- [ ] Change the Slide 2 hook from the 30210 bearing to the `submersible` pump family
- [ ] Decide on gate 0.70 vs 0.76 and make the docs agree with the code
- [ ] Align `PROJECT_PLAN.md` §3 with the TF-IDF reality
- [ ] Add 3 unit tests (check digit, UOM map, conflict veto) if time allows
- [ ] Rehearse Q2, Q5, Q44, Q45 out loud — those four are where marks are won or lost
