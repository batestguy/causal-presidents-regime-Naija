# What the chat layer may refuse — Stage 9, the pre-retrieval intent gate

The retrieval layer answers "what is similar to this question?". A refusal needs a different question —
"can this corpus answer this question at all?" — and Stage 8c measured what happens when one similarity
score is asked to do both jobs: **out-of-scope refusal 0.25** and **refusal-with-reason recall 0.5**, against
declared targets of 1.0 (`docs/rag.md` §3). A 2030 forecast about a covered outcome embeds closer to the
corpus than some genuine questions do, so any threshold that refused it would refuse real questions with it.

This stage replaces the score with a **declared rule set applied before retrieval**. The gate reads the
question, decides one of three intents, and — for a refusal — pins the chunk the refusal must quote. It
computes no statistic, fits nothing and calls no model.

It is on **version 3**: a rule was changed twice, each time after a measurement missed a target, and each
change cost a new held-out set and a new freeze (§4, §5). The earlier numbers are kept in this page because
they are the reason the rules moved, not because they still describe the gate.

- **Spec:** `analysis/specs/intent_gate.yml` — the decision procedure, nine rules, the gates, the known gaps
- **Held-out set:** `analysis/specs/intent_gate_eval_v3.yml` — 49 questions, written **after** the v3 rules froze
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

`mentions_country` reads a committed vocabulary rather than a list written into the rules
(`registry/reference/countries.json`, ISO 3166-1 plus a short alias list), with Nigeria excluded when the
matcher is built. It matches on a variant of the declared normalisation in which the apostrophe becomes a
space: the declared form turns "Brazil's" into "brazils", and a country matcher looking for the word
"brazil" would miss a country in the possessive. No other rule sees that variant. The donor panel is the
second artifact — `registry/donors/2026-10-18/panel.json`, the 99 countries Stage 5 screened — and it is the
scope clause's justification rather than the rule's boundary: the corpus holds no series for a panel member
either, so a question about one is equally unanswerable. The verifier holds the two together by requiring
every panel member to appear in the vocabulary.

## 2. The nine rules

| Rule | Priority | Intent | What it catches | Route |
|---|---|---|---|---|
| G01 | 10 | `answerable` | "why can't you answer …" — questions *about* the corpus's limits | — |
| G02 | 20 | `out_of_scope` | forecast vocabulary ("forecast", "predict", "projection", "extrapolate"), excluding the corpus-scope and model-card frames | `scope:answer` |
| G03 | 30 | `out_of_scope` | the size of a population — the corpus carries no population series (X-09) — excluding the denominator / per-capita frame (v2) | `scope:answer` |
| G04 | 40 | `out_of_scope` | "should the government …" — a normative ask with a policy actor | `scope:answer` |
| G08 | 45 | `out_of_scope` | "recommend …", "advise …", "the best way to …" — an advice ask with no actor | `scope:answer` |
| G05 | 50 | `out_of_scope` | a year outside `[study_window.start, vintage]` | `scope:answer` |
| G09 | 55 | `out_of_scope` | a country other than Nigeria, named from the committed vocabulary (v3, closes KG01) | `scope:answer` |
| G06 | 60 | `refusal_with_reason` | a tenure comparison — "which administration did better" | `limitations.md` §1, by heading |
| G07 | 70 | `refusal_with_reason` | Design C asked for a causal answer it never produced | `result:C` |

G01 sits first because the same words appear in a question that must refuse: *"why can't you tell me whether
PDP or APC tenures did better?"* is answerable, while *"which president had the better record?"* is not. The
difference is the ask, not the topic.

G08 is evaluated before G05 (priority 45 against 50) because "what is the best way to allocate FAAC revenue
in 2030" is advice first and out-of-window second; both rules cite the same scope chunk, so the ordering
decides which rule is recorded on the artifact rather than which chunk is cited.

G09 sits after G05 because both cite the same scope chunk and the year rule is the more specific of the two.
The rule is deliberately **wider than the clause's wording**: it refuses a question about any country other
than Nigeria, panel member or not, because a panel member's series is just as absent. Nigeria is excluded
before matching, so a question about Nigeria's own record is never touched by it — which is what the authored
case C07 ("What was Nigeria's inflation rate in 2016?") exists to check.

## 3. Why a rule set, and not a classifier

A classifier trained on the eval set would score better on the eval set and mean less. Every rule names the
scope clause it implements and the project fact that justifies it, so a reviewer can argue with the rule
rather than with a probability. The limitation is published rather than discovered: the rules are **lexical**,
so a paraphrase that avoids the declared words is not detected (KG03). The alternative — a model — would
have to be measured on data that did not train it, and there is no such data here.

## 4. What was measured — version 3

### The held-out set — the generalisation estimate

**49 questions** built from sources that do not depend on the rules: **32 mechanical** questions whose
templates are filled from the artifacts (a card exists, so a card question is answerable; the corpus carries
no population series, so a population question is not), **16 authored** questions written to be hard —
answerable questions carrying a trigger word in a frame the rule must not fire on (including Nigeria's own
record and a possession of it), and out-of-scope questions worded unlike the published set's and v2's — and
**1 probe**. Composition: 22 answerable, 19 out of scope, 8 refusal-with-reason. 32 carry a gold chunk that
is scored; 8 carry a needle the cited chunk must contain.

| Metric | Measured | Target | Verdict |
|---|---|---|---|
| intent accuracy | **0.980** | 0.90 | met |
| out-of-scope refused | **0.947** | 0.90 | met |
| answerable kept | **1.000** | 1.0 | met |
| refusal route resolved | **1.000** | 1.0 | met |
| refusal reason cited | **1.000** | 1.0 | met |

Per family: card, forecast, population, past year, tenure, Design C and the authored family are all exact at
1.000. The probe family is 0.000, and it is the one miss: **P03** — *"How did Accra's economy grow between
2010 and 2015?"* — is expected out of scope and is left answerable, because the question reaches a country
only through its capital city and the vocabulary is country names. It is scored and labelled rather than
excluded, so the lexical remainder has a measured cost.

### The regression block — the cases the two rule changes were made for

Twenty-three previously published questions are re-checked after the changes and reported **beside** the
held-out numbers, never inside them: a question the rules were changed with in view cannot also measure the
change. The block is the sixteen v2 authored questions, the v2 probe P02, and the six v2 checks:

| Case | Question | Expected | Result |
|---|---|---|---|
| R01 | Is the population denominator for the per-capita axis built? | answerable | answerable |
| R02 | How many inhabitants does Lagos have? | out of scope | out of scope |
| R03 | What was the population in 1960? | out of scope | out of scope |
| R04 | How many people live in Kano today? | out of scope | out of scope |
| R05 | Which president had the better record? | refusal with reason | refusal with reason |
| R06 | Does the corpus publish a forecast for inflation? | answerable | answerable |
| P02 | How did Brazil's under-5 mortality compare with Nigeria's? | out of scope | out of scope |

**Regression accuracy 1.000** — P02 is now refused, which is the gap v3 closes, and the denominator and
population questions the v2 exclusion sits beside are unchanged.

### Why version 3 exists, and what it cost

v2 was frozen at `8b9ba3b` and measured on 49 questions. It hit every declared target on the held-out set,
but it missed its one probe: **P02**, a question about a country, left answerable because no rule owned the
class and no committed artifact named a country. KG01 declared that gap from the first freeze; v3 closes it.

The change was made the right way round: the donor panel and the country vocabulary were committed and the
rule was **frozen at `3dcb555`** first, and this held-out set was written afterwards, from a new path. The
cost is stated on the spec: the v2 authored questions are spent, the mechanical families survive because
they are filled from artifacts, and the v2 questions become the regression block above rather than held-out
questions a second time. The v2 set is retained at `analysis/specs/intent_gate_eval_v2.yml`, and its
measurement stays on the record: intent accuracy 0.980, out-of-scope refusal 0.947, answerable kept 1.000,
reason cited 1.000.

`tests/verify_intent.py` enforces the order: it reads the rule spec **as of `3dcb555`**, fails if the file
on disk differs, and fails if the v3 eval set existed at that commit. A rule changed now would require a v4
set and a fourth freeze.

### Why version 2 exists, and what it cost

v1 was frozen at commit `30afc23` and measured on 49 questions. It missed one target: `answerable kept`
**0.957**, because G03 refused A16 (*"is the population denominator for the per-capita axis built?"*) on the
word "population". The rules were **not** edited then — the measurement had been made, and editing the rule
would have tuned it to the set that measured it (S9-05). The v1 set is retained at
`analysis/specs/intent_gate_eval.yml`, and its measurement stays on the record: intent accuracy 0.959,
out-of-scope refusal 0.944, answerable kept 0.957, reason cited 1.000.

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
verifier recomputes the cosine from the committed vectors to check it rather than trusting the artifact.

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

- **KG01 — countries outside the donor panel. Closed by G09 in version 3.** The panel's 99 members and the
  ISO 3166-1 names are committed registry artifacts, so the rule decides the class from files every clone
  has; P02 is refused on the regression block. The remainder is lexical: a country named only by a city
  (P03), an abbreviation the alias list lacks, or a misspelling is not detected — that is KG03, and it is
  measured rather than assumed.
- **KG02 — the answer-shape post-check.** The gate decides an intent and a citation; it does not assemble an
  answer, so it cannot check one for an interval, an identifying assumption and a citation (R-04). That
  belongs to the answer layer, which is now built (`docs/answer.md`): it enforces the post-check on its own
  output and declines 13 of the 16 published answerable questions, because R-04 is an estimate contract and
  34 of the 36 cards carry no number.
- **KG03 — the rules are lexical.** A paraphrase that avoids the declared words is missed, and so is a
  country reached through a city or a demonym. Accepted, with the reason above; closing it means a
  paraphrased held-out set published beside the lexical one.
- **KG04 — a value inside the window but past the outcome series.** 2025–2026 values are left answerable
  because the study window is open and the registry's own state in those years is answerable. Closing it means
  reading each outcome's own end month off the cards and accepting the risk of refusing a question about the
  registry's own contents.

## 6. What this does not do

- **It does not answer anything.** It returns `{intent, rule_id, route, route_status, reason}`; quoting the
  pinned chunk is the answer layer's job, and that layer's measured answer rate is **0.158** over the 38
  answerable questions it was run on (`docs/answer.md` §2).
- **It does not gate the app yet.** `app/streamlit_app.py` has no chat tab, so nothing calls the gate at
  request time today. The module is framework-free and importable from the app when that tab exists.
- **It does not replace the answer contract.** A question the gate leaves answerable can still be refused by
  the R-04 post-check if the retrieved passages do not carry an interval, an assumption and a citation —
  which is what happens to 32 of the 38 questions the layer was measured on.

## 7. Reproduction

```bash
py scripts/eval_intent.py     # rewrites registry/rag/<vintage>/intent_eval.json
py tests/verify_intent.py     # re-derives the questions, re-applies the rules, recomputes every number
```

The artifact records the sha256 of both specs and of the corpus, and the commit that froze the rules. A spec
edited after the measurement fails the verifier on the hash; a rule edited after the questions were written
fails it on the freeze. `scripts/validate_artifacts.py` additionally fails if the artifact describes a
different corpus than the one beside it.
