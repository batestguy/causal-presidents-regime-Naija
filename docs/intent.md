# What the chat layer may refuse — Stage 9, the pre-retrieval intent gate

The retrieval layer answers "what is similar to this question?". A refusal needs a different question —
"can this corpus answer this question at all?" — and Stage 8c measured what happens when one similarity
score is asked to do both jobs: **out-of-scope refusal 0.25** and **refusal-with-reason recall 0.5**, against
declared targets of 1.0 (`docs/rag.md` §3). A 2030 forecast about a covered outcome embeds closer to the
corpus than some genuine questions do, so any threshold that refused it would refuse real questions with it.

This stage replaces the score with a **declared rule set applied before retrieval**. The gate reads the
question, decides one of three intents, and — for a refusal — pins the chunk the refusal must quote. It
computes no statistic, fits nothing and calls no model.

- **Spec:** `analysis/specs/intent_gate.yml` — the decision procedure, eight rules, the gates, the known gaps
- **Held-out set:** `analysis/specs/intent_gate_eval.yml` — 49 questions, written **after** the rules froze
- **Engine:** `app/intent_gate.py` (the decision), `scripts/eval_intent.py` (the measurement)
- **Artifact:** `registry/rag/2026-10-18/intent_eval.json`
- **Verifier:** `tests/verify_intent.py` — re-derives the questions, re-applies the rules with a second
  implementation, checks the freeze against git, and recomputes every metric and gate flag

## 1. The decision, in four steps

1. **Normalise** — lowercase, drop apostrophes, turn every other non-alphanumeric character into a space,
   collapse. No stemming and no synonyms: a rule has to be readable in the form it is matched in.
2. **Evaluate the rules in `priority` order.** The first rule whose conditions all hold decides. Priorities
   are unique, so the decision is total and deterministic — the same question always gets the same intent.
3. **No rule matches → `answerable`.** This is the safe default and it is deliberate: the gate may **add** a
   refusal; it may never **remove** one. A rule that misfires on an answerable question takes away an answer
   the corpus could have given, which is the worse failure.
4. **A refusal must resolve to a route.** A reason-bearing rule resolves its route (a chunk id or a
   documentation section found by its heading) against the corpus. If the route does not resolve to exactly
   one existing chunk, the intent falls back to `answerable` — the gate will not refuse without a citation.

`year_window` reads its bounds from the artifacts, not from the rules: `past` is before the quality report's
`study_window.start`, `future` is after the registry's `vintage_date`. The study window is open, so a question
about a 2025–2026 *value* is left answerable; the bound is the vintage year, and the cost is stated in the
spec rather than hidden.

## 2. The eight rules

| Rule | Priority | Intent | What it catches | Route |
|---|---|---|---|---|
| G01 | 10 | `answerable` | "why can't you answer …" — questions *about* the corpus's limits | — |
| G02 | 20 | `out_of_scope` | forecast vocabulary ("forecast", "predict", "projection", "extrapolate"), excluding the corpus-scope and model-card frames | `scope:answer` |
| G03 | 30 | `out_of_scope` | the size of a population — the corpus carries no population series (X-09) | `scope:answer` |
| G04 | 40 | `out_of_scope` | "should the government …" — a normative ask with a policy actor | `scope:answer` |
| G08 | 45 | `out_of_scope` | "recommend …", "advise …", "the best way to …" — an advice ask with no actor | `scope:answer` |
| G05 | 50 | `out_of_scope` | a year outside `[study_window.start, vintage]` | `scope:answer` |
| G06 | 60 | `refusal_with_reason` | a tenure comparison — "which administration did better" | `limitations.md` §1, by heading |
| G07 | 70 | `refusal_with_reason` | Design C asked for a causal answer it never produced | `result:C` |

G01 sits first because the same words appear in a question that must refuse: *"why can't you tell me whether
PDP or APC tenures did better?"* is answerable, while *"which president had the better record?"* is not. The
difference is the ask, not the topic.

G08 is evaluated before G05 (priority 45 against 50) because "what is the best way to allocate FAAC revenue
in 2030" is advice first and out-of-window second; both rules cite the same scope chunk, so the ordering
decides which rule is recorded on the artifact rather than which chunk is cited.

## 3. Why a rule set, and not a classifier

A classifier trained on the eval set would score better on the eval set and mean less. Every rule names the
scope clause it implements and the project fact that justifies it, so a reviewer can argue with the rule
rather than with a probability. The limitation is published rather than discovered: the rules are **lexical**,
so a paraphrase that avoids the declared words is not detected (KG03). The alternative — a model — would
have to be measured on data that did not train it, and there is no such data here.

## 4. What was measured

### The held-out set — the generalisation estimate

**49 questions** built from two sources that do not depend on the rules: **32 mechanical** questions whose
templates are filled from the artifacts (a card exists, so a card question is answerable; the corpus carries
no population series, so a population question is not), and **17 authored/probe** questions written to be
hard — answerable questions carrying a trigger word in a frame the rule must not fire on, and out-of-scope
questions worded unlike the published set's. Composition: 23 answerable, 18 out of scope, 8
refusal-with-reason. 32 carry a gold chunk that is scored; 8 carry a needle the cited chunk must contain.

| Metric | Measured | Target | Verdict |
|---|---|---|---|
| intent accuracy | **0.959** | 0.90 | met |
| out-of-scope refused | **0.944** | 0.90 | met |
| answerable kept | **0.957** | 1.0 | **not met** |
| refusal route resolved | **1.000** | 1.0 | met |
| refusal reason cited | **1.000** | 1.0 | met |

Per family, every mechanical family is exact: card 1.000, forecast 1.000, population 1.000, past year 1.000,
tenure 1.000, Design C 1.000. The authored family is 0.938 and the probe 0.000.

**The `answerable kept` target is missed, and the miss is the finding.** A16 — *"Is the population
denominator for the per-capita axis built?"* — is answerable: the data dictionary says the denominator is
typed and empty and that X-09 is an unmade decision. G03 refuses it, because it matches the same word
("population") as the question about how many people live in Lagos. The gate cannot currently tell a question
**about the denominator** from a question about **the size of a population**. That is the worst direction for
this gate to fail in, which is why the question is in the set and why its number is published rather than
tuned away.

The rules are **not** edited to catch A16. They were frozen at commit `30afc23` before the held-out questions
existed, and `tests/verify_intent.py` reads the rule spec as of that commit and fails if the file on disk
differs. Changing the rules now would mean the held-out numbers no longer measure what they say they measure;
the fix is a rule excluding the denominator frame (`\bpopulation denominator\b`, `\bper capita\b`) **together
with a new held-out set and a new freeze** — which is the next change, not this one.

### The published set — the set the rules were written against

The 22 published questions from `registry/rag/2026-10-18/eval_set.json`, measured under the gate for
comparability with the numbers that failed:

| Metric | Under the score (Stage 8c) | Under the gate |
|---|---|---|
| out-of-scope refused | 0.25 | **1.000** |
| refusal-with-reason recall | 0.5 | **1.000** |
| refusal route matches the declared citation | — | **1.000** |
| answerable kept | 1.0 | **1.000** |
| answerable recall@5 | 0.944 (all gold-bearing questions) | **1.000** (answerable subset) |

The last row is the important one: the gate is a **refusal** gate, so it must not change what is retrieved.
Every answerable published question is still answerable and still finds its gold chunk in the top 5, and the
verifier recomputes the cosine from the committed vectors to check it rather than trusting the artifact. The
recall figures are not like-for-like — 0.944 is over all gold-bearing questions, 1.000 is over the answerable
subset, and only the subset is the gate's business.

These numbers are **not** a generalisation estimate. The published set is the set the rules were written
against, including the pair (q09, r01) that forced the G01/G06 ordering. They are reported as "what the gate
does on the questions it was built from", and the held-out set is the estimate that can be argued with.

### One metric that is easy to misread

`route_matches_gold` is **0.625** — 20 of 32 scored golds. All 12 misses are the mechanical card questions.
The gate returns no route for an `answerable` decision by design: choosing *which* chunk answers an answerable
question is the retriever's job, and the gold is a card chunk the retriever is measured on in `docs/rag.md`.
Read against the 20 questions that actually carry a route, the gate cites the expected chunk **20 of 20**:
`scope:answer` for all 12 out-of-window and population questions, `limitations.md` §1 for the four tenure
questions, and `result:C` for the four Design C questions. The metric is published as computed, with this
paragraph as its reading — the alternative is deleting a metric after seeing it, which is the practice the
gates above exist to prevent.

## 5. What the gate does not detect

Four gaps are declared on the spec and carried onto the artifact rather than left to a reader's surprise:

- **KG01 — countries outside the donor panel.** P01 (*"What is the under-5 mortality rate in Chad?"*) is
  expected out of scope and is **not refused**; that is the measured cost of the gap. The country list lives
  in a gitignored acquisition artifact, so a rule built on it would behave differently on a fresh clone and
  the published number would not be reproducible. Closing it means committing the donor pool's membership as
  a registry artifact.
- **KG02 — the answer-shape post-check.** The gate decides an intent and a citation; it does not assemble an
  answer, so it cannot check one for an interval, an identifying assumption and a citation (R-04). That
  belongs to the answer layer, which is not built.
- **KG03 — the rules are lexical.** A paraphrase that avoids the declared words is missed. Accepted, with the
  reason above; closing it means a paraphrased held-out set published beside the lexical one.
- **KG04 — a value inside the window but past the outcome series.** 2025–2026 values are left answerable
  because the study window is open and the registry's own state in those years is answerable. Closing it means
  reading each outcome's own end month off the cards and accepting the risk of refusing a question about the
  registry's own contents.

## 6. What this does not do

- **It does not answer anything.** It returns `{intent, rule_id, route, route_status, reason}`; the answer
  layer that would quote the pinned chunk is not built.
- **It does not gate the app yet.** `app/streamlit_app.py` has no chat tab, so nothing calls the gate at
  request time today. The module is framework-free and importable from the app when that tab exists.
- **It does not earn the tab by itself.** The gate passes the out-of-scope and reason-citation targets on the
  held-out set; it misses `answerable kept` at 0.957, and the chat tab remains unbuilt. What the numbers change
  is that the refusal decision is now a policy with a measurement behind it rather than a similarity score.

## 7. Reproduction

```bash
py scripts/eval_intent.py     # rewrites registry/rag/<vintage>/intent_eval.json
py tests/verify_intent.py     # re-derives the questions, re-applies the rules, recomputes every number
```

The artifact records the sha256 of both specs and of the corpus, and the commit that froze the rules. A spec
edited after the measurement fails the verifier on the hash; a rule edited after the questions were written
fails it on the freeze. `scripts/validate_artifacts.py` additionally fails if the artifact describes a
different corpus than the one beside it.
