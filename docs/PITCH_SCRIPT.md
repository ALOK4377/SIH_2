# Samanvay — Judge Pitch Script & Deck Outline

**Problem Statement 26099** · Ministry of Petroleum & Natural Gas → Chennai Petroleum Corporation Limited (CPCL)
**Tagline:** One Nation · One Material Code

> Every number in this script is taken from the running product (the dashboard, families,
> review queue, and registry you just demoed). Nothing here is invented — say it with confidence.

---

## 0. How to use this document

- **Section 1** — the 30-second elevator version (for corridors, or if your slot gets cut).
- **Section 2** — the full pitch, written **slide-by-slide** (spoken words + stage directions + timing).
- **Section 3** — the live-demo runbook (exact click path, what to say, and a fallback).
- **Section 4** — Q&A prep, including how to answer the hard/honest questions.
- **Section 5** — speaker tips + roles.
- **Section 6** — the PPT slide outline that mirrors Section 2.

Total run time as written: **~8 minutes** speaking + demo. Trim guidance is in Section 6.

---

## 1. The 30-second elevator pitch

> "Across India's CPSEs, the *same physical item* is stored under dozens of different codes — in our
> demo data, one bearing appears **9 times across 8 companies.** That means duplicate stock, blocked
> capital, and the same part bought at wildly different prices. **Samanvay** is an AI platform that
> reads every CPSE's material master, finds the true duplicates, and assigns **one Common National
> Material Code** — while keeping a mapping to every original code. On real benchmarks it cuts the
> catalogue by **66%** at **90% precision**, and every merge is explained and auditable. One Nation,
> One Material Code."

---

## 2. The full pitch — slide by slide

### SLIDE 1 · Title  *(0:00–0:25)*
> **"Namaste. We're [Team Name], and this is Samanvay** — the Sanskrit word for *harmony*, for
> bringing things into coordination. That is exactly our mission: **One Nation, One Material Code.**
> We built it for Problem Statement 26099, for the Ministry of Petroleum & Natural Gas and CPCL."

*[On screen: logo, tagline, the CNMC chip. Calm, clear open. Don't rush.]*

---

### SLIDE 2 · The problem — the hook  *(0:25–1:35)*
> **"Let me show you one bearing."** *[point to the dashboard's Most-Duplicated list — ROLLER ZZ
> 30210 BEARING, ×9, 8 CPSEs]* **"This exact bearing is stored nine different ways, across eight
> different public-sector companies. Nine codes. One physical item.**
>
> Now multiply that across a material master with lakhs of rows — which is the reality inside every
> large CPSE. You get duplicate inventory, working capital locked in things another unit already has
> on the shelf, emergency purchases of parts that already exist, and the *same item* bought at very
> different prices. In our sample, a single pump family has a price spread of **₹76,000** for what is
> the same pump.
>
> The root cause is simple: **there is no common language for materials across CPSEs.**"

*[On screen: the ×9 bearing, and one or two big price-spread numbers. This slide must land emotionally — it's the "why should I care" moment.]*

---

### SLIDE 3 · Why this is hard  *(1:35–2:20)*
> **"You cannot fix this with find-and-replace.** Descriptions are short and messy — 'BEARING'
> becomes 'BRNG', the grade '316' hides inside free text, units differ, spellings differ across
> companies.
>
> And here's the dangerous part: two items can look **95% identical and still be different items.**
> A 6205 bearing is not a 6206. Merge them, and you hand a refinery the wrong spare part. So our AI
> has to do two opposite things at once — **match aggressively, and never over-merge.**"

*[On screen: two near-identical descriptions side by side, one subtle spec difference highlighted.]*

---

### SLIDE 4 · The solution  *(2:20–3:00)*
> **"Samanvay ingests every CPSE's material master, understands each item, groups the true
> duplicates, and assigns one Common National Material Code** — while keeping a full mapping back to
> every original local code, so **nothing is ever lost.**
>
> This is that code." *[point to a CNMC chip]* **"IN, a UNSPSC category, a unique serial, and a
> check digit — `IN-311516-0000011-6`. A real, verifiable coding scheme, not a random ID."**

*[On screen: the CNMC chip broken into its four segments with labels.]*

---

### SLIDE 5 · How it works — the engine  *(3:00–4:00)*
> **"Five stages, and every one is real code.**
> - **Normalize** — expand abbreviations, standardize units, and extract structured specs like bore,
>   seal type, voltage, material grade.
> - **Block** — only compare items in the same family. That drops **85% of comparisons** while
>   keeping **98% of true matches.**
> - **Match** — a hybrid score: **60% structured attributes, 25% meaning, 15% spelling** — with a
>   hard **veto**. If two items conflict on a critical spec, they can *never* auto-merge.
> - **Cluster** — link the strongest matches first, always respecting those conflicts.
> - **Golden record** — pick the cleanest description, classify it, and mint the national code.
>
> And critically — **every decision comes with a plain-English reason.**"

*[On screen: a clean 5-step pipeline diagram, left to right.]*

---

### SLIDE 6 · LIVE DEMO  *(4:00–6:15)*
*[Switch to the browser. Follow the runbook in Section 3. This is the heart of the pitch — spend your time here, not on slides.]*

---

### SLIDE 7 · Results — measured, not claimed  *(6:15–6:55)*
> **"These numbers are recomputed from ground truth on every single run — measured, not claimed.**
> On 1,274 codes across 10 CPSEs:
> - **Precision 90%. Recall 80%. F1 85%.**
> - We collapsed the catalogue by **66%** — 1,274 down to **435** national codes.
> - And we didn't guess on the hard cases — we routed **873 uncertain pairs to a human** for review."

*[On screen: the three big metrics + the 1,274→435 funnel. Same numbers the judges just saw live.]*

---

### SLIDE 8 · Trust & governance  *(6:55–7:25)*
> **"For a government rollout, accuracy alone isn't enough — you need trust.**
> - Every proposed merge is **explainable.**
> - A data steward **approves or rejects in one click.**
> - Every action is **audited** — who, what, when.
> - And the veto means the system **fails safe**: when it's unsure, it asks. It does not merge."

*[On screen: the review card + the audit trail, side by side.]*

---

### SLIDE 9 · Architecture & scale  *(7:25–7:50)*
> **"This is a real product, not a notebook.** React front end, FastAPI back end, a clean REST API
> with nine endpoint groups, SQLite for the demo and **PostgreSQL with pgvector** for scale — all
> containerized with Docker. The matching engine runs today on **pure standard-library Python**, so
> it runs anywhere. And every heavy component has a documented upgrade slot: transformer embeddings,
> RapidFuzz, and Celery workers for millions of rows."

*[On screen: a simple architecture diagram + the tech-stack logos.]*

---

### SLIDE 10 · Impact & roadmap  *(7:50–8:05)*
> **"We built this CPCL-first — but the design is national.** The same engine that harmonizes
> petroleum CPSEs works for steel, coal, and power — for every CPSE in India. Next on our roadmap: a
> live SAP connector, role-based access, and a feedback loop that learns from every steward decision."

---

### SLIDE 11 · Close  *(8:05–8:20)*
> **"Duplicate codes cost crores, lock up working capital, and hide savings in plain sight. Samanvay
> gives India's CPSEs one shared language for materials — accurate, explainable, and auditable.
> One Nation. One Material Code.** Thank you — we'd love your questions."

---

## 3. Live-demo runbook (~2 min 15s)

**Before you present:** start the backend and frontend 5 minutes early. Have `localhost:5173` open on
the Dashboard, and keep the deck's demo screenshots ready as a fallback in case Wi-Fi/servers fail.

Follow this exact path — five moves:

1. **Dashboard** *(start here)*
   > "1,274 local codes, down to 435 national codes — 66% fewer. Quality up here: 90, 80, 85. And
   > there's our nine-times bearing." *[point to Most-Duplicated]*

2. **Families → open ROLLER ZZ 30210 BEARING**
   > "Proposed family: 9 codes, 8 CPSEs, confidence 79%." *[click "Show 9 member codes"]* "Same
   > physical bearing, eight different local codes from eight different companies — and every original
   > code is preserved. Look at the price spread on shared items."

3. **Review Queue → the TAPER ROLLER 6206 pair**
   > "This is the AI explaining itself: text 0.69, fuzzy 0.85, two specs agree, unit matches → score
   > 0.70, auto-duplicate. A steward reads that reason and confirms in one click." *[optionally click
   > "Confirm same item" so a judge sees it move]*

4. **Code Registry → search a spec (the 'we don't over-merge' beat)**
   > *[type "bearing" or a code number]* "Here's the discipline: the 30210 bearing and the 6206
   > bearing are **separate national codes** — different bore, different item. The attribute veto
   > keeps them apart. And each code carries its structured specs — seal, type, size."

5. **Code Registry → Export CSV, then Audit Trail**
   > "This is the deliverable — the National Code Registry. Search it, filter it, and **export the
   > full crosswalk** from every local code to its national code." *[click Export CSV]* "And every
   > action is logged in the Audit Trail — full governance."

**Fallback line if anything breaks:** "Let me show you this from our captured run" → switch to the
screenshots baked into the deck. Never debug live in front of judges.

---

## 4. Q&A preparation

**Q: Is this real CPSE data?**
> "It's synthetic but realistic — generated with real UNSPSC categories, real abbreviation patterns,
> and deliberate hard cases like 6205-vs-6206 bearings. Because we control the ground truth, we can
> measure accuracy honestly. And it ingests a real SAP/ERP export today via CSV."

**Q: Why is recall only 80%? Why not 100%?**
> "By design. We tuned it precision-first — we'd rather miss a merge and let a human catch it than
> wrongly merge two different parts. It's a dial: at a stricter gate we reach ~97% precision. The 873
> uncertain pairs in the review queue are exactly where humans recover the rest."

**Q: The dashboard says 873 pending, but the queue shows 40 — why?**
> "873 is the full backlog of uncertain pairs. The queue view shows the top 40 by priority for
> triage; it's paginated in production."

**Q: How is this different from SAP MDG or existing MDM tools?**
> "Those need humans to pre-define match rules and a clean taxonomy first. Samanvay *learns* the match
> from the data, explains every decision, refuses to over-merge, and outputs a national code with full
> traceability — not just a 'possible duplicate' flag."

**Q: You use TF-IDF, not a large language model. Isn't that weak?**
> "We deliberately shipped a zero-dependency engine so it runs anywhere and our metrics are perfectly
> reproducible. Transformer embeddings (MiniLM) drop into a single module for a recall boost — the
> architecture already supports pgvector for that."

**Q: Will it scale to millions of rows?**
> "Yes. Blocking keeps it near-linear within each category. The scale path is documented: PostgreSQL +
> pgvector for search, and Celery + Redis workers for parallel batch matching. The API is already
> structured for async jobs."

**Q: Who is allowed to approve merges? Is it secure?**
> "Roles exist in the data model — steward, admin, viewer. JWT authentication is our next sprint. The
> audit trail is already live, so every decision is attributable."

**Q: What's the actual money saved?**
> "On this 1,274-row sample we can already see ~₹18.6 lakh of price spread on shared items — the same
> item bought at different prices. Extrapolated across CPSE material masters in the millions of rows,
> the addressable opportunity is in the hundreds of crores. We're careful to call that illustrative,
> but the mechanism is real and visible in the demo."

---

## 5. Speaker tips & roles

- **Two people:** one **driver** (controls the screen) and one **narrator** (speaks). Rehearse the
  handoff into the demo.
- **Lead with the bearing.** The "one item, nine codes" image is your strongest hook — open on it.
- **Say "measured, not claimed"** at least once. Judges hear inflated numbers all day; this line
  earns trust.
- **Keep the demo to the five moves.** Resist clicking around. Every extra click risks a stumble.
- **End on the tagline**, not on a feature. "One Nation. One Material Code." is your last line.
- **Don't read the slides.** Slides are for the judges' eyes; the script is for their ears.
- **Time it.** Rehearse to fit your slot with ~30s buffer. Know which slide you drop if you're short
  (drop Slide 3 or compress Slide 9).

---

## 6. PPT slide outline

Mirror Section 2. Keep each slide to **one message + one visual + ≤4 short bullets.** Judges skim.

| # | Slide | One-line message | Visual to use |
|---|-------|------------------|---------------|
| 1 | **Title** | Samanvay · One Nation, One Material Code | Logo, tagline, CNMC chip |
| 2 | **The Problem** | One item, nine codes, eight companies | Dashboard's Most-Duplicated + a price spread |
| 3 | **Why it's hard** | Match hard, but never over-merge | Two near-identical items, one spec differs |
| 4 | **The Solution** | One national code, full traceability | CNMC chip split into its 4 parts |
| 5 | **How it works** | Normalize → Block → Match → Cluster → Code | 5-step pipeline diagram |
| 6 | **Live Demo** | (screen) | Demo, or the 5 runbook screenshots as backup |
| 7 | **Results** | 66% fewer codes at 90% precision — measured | 3 big metrics + 1,274→435 funnel |
| 8 | **Trust & Governance** | Explainable, one-click review, audited, fail-safe | Review card + audit trail |
| 9 | **Architecture** | A real, scalable product | Architecture diagram + stack |
| 10 | **Impact & Roadmap** | CPCL-first, built for the nation | CPSE logos across sectors + roadmap arrows |
| 11 | **Close** | One Nation. One Material Code. | Tagline, team, thank you |

**Trim guide by time slot:**
- **~10 min (grand-finale style):** use all 11 slides as written; spend 2.5 min on the demo.
- **~5 min:** Title → Problem → Solution → **Demo** → Results → Close (6 slides). Demo is 90s.
- **~3 min lightning:** Problem (the bearing) → Solution + CNMC → 60s demo → Results → tagline.

**Design note:** reuse the product's own identity so the deck and the app look like one thing — paper
background `#F4F6F9`, navy ink `#12233D`, verified-teal `#0E7C66` for the "harmonized" numbers,
saffron `#E0A32E` for duplication/attention. Fonts: Space Grotesk for titles, Inter for body, IBM
Plex Mono for codes. The CNMC chip is your signature — put it on the title and closing slides.
