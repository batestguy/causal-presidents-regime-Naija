# What an answer may contain — Stage 9, the answer layer

The intent gate decides whether the corpus may answer a question and, when it may not, which chunk the
refusal must quote. This layer does the rest: it retrieves passages, assembles an answer in the contract's
order, and runs the R-04 post-check **on its own output**. If any required part is missing, the answer is
replaced by the refusal template — the layer cannot ship a sentence the contract would not allow.

It is now the **Ask** tab of the app (`docs/app.md` §3). The tab is the same layer the measurement below
describes: it does not re-decide anything, and `tests/verify_app.py` asks the tab the questions it offers
and compares the answers with this artifact.

Every answer also carries a **plain-language reading** of the same evidence (`plain` on the artifact): the
sign of the estimate, whether the interval excludes zero, the sample it rests on, the assumption in one
sentence, the caveats as bullets, and the definitions of whatever technical words the answer uses. It is a
second reading of the contract answer, not a paraphrase of it, and it runs with **no LLM key** — the
retrieval is BM25 and the definitions are `docs/glossary.md`.

- **Spec:** `analysis/specs/rag.yml#answer_contract` — the order, the three shapes, the post-check, the
  refusal template
- **Engine:** `app/answer_layer.py` — gate → BM25 retrieval → extractive assembly → post-check
- **Measurement:** `scripts/eval_answer.py` → `registry/rag/2026-10-18/answer_eval.json`
- **Verifier:** `tests/verify_answer.py` — re-checks every part, every quoted sentence and every number

## 1. What it does, in order

1. **Ask the gate.** An `out_of_scope` or `refusal_with_reason` decision ends the request: the layer returns
   the contract's refusal template with the rule's reason, the rule's code and the pinned chunk's citation.
   It never answers around a refusal.
2. **Retrieve.** Okapi BM25 over the corpus text, no stemming and no synonyms — the lexical scorer the
   retrieval evaluation measures as its baseline (`docs/rag.md`). **No embedding model is called**, so the
   layer imports no model, no database client, no network client and no fitting library. The committed
   vectors are used offline by `scripts/eval_rag.py`, not here.
3. **Route by what the question asks for.** A question that asks for a published number goes down the number
   path; a question that asks for something else goes down the fact path. A question that asks for a number
   is answered with the card that carries one, and with the card's reason when the card carries none — which
   is why **34 of the 36 cards can be answered about at all**.
4. **Assemble, extractively.** Every sentence in the answer is a committed paragraph. Nothing is
   paraphrased and no number is typed: the layer selects passages and labels them in the contract's order,
   and every part it quotes is cited.
5. **Check the output.** The answer is checked against the requirements of its shape, and a missing part
   replaces the whole response with the refusal template (R-04).
6. **Read it back in plain words.** The layer extracts the coefficient and the interval's bounds from the
   quoted passage, says which direction they point and whether the range includes zero, states the sample,
   and shows the glossary entries for the words it used. It writes no number the citation does not carry.

### The three shapes, and why there are three

The contract had one shape — an estimate, an interval, an assumption, a caveat and a citation — and the
Stage 9 measurement showed what that cost. A question about one of the 34 cards that carries a reason
("what did the published estimate find for under-5 mortality under Design A?") was answered *"I don't have a
model for that"*, which is false: the project has a model card for that pair and the card says exactly why
there is no number. The refusal was refusing for the wrong reason, and 32 of the 38 answerable questions
were refused for it.

| Shape | Chosen when | Must carry | Must not carry |
|---|---|---|---|
| `estimate` | the question asks for a number, and the card carries one | interval, identifying assumption, what it cannot rule out, citation | — |
| `no_estimate` | the question asks for a number, and the card carries none | reason code, identifying assumption, what it cannot rule out, citation | an interval |
| `fact` | the question asks for neither | the passage, a citation | an interval |

Four relevance guards keep the assembly from lending a number to a question it does not answer, the same
failure the app's results tab prevents one layer up:

- **A question that names an outcome may only be answered from a passage about that outcome.** Without this,
  a design-level result that lists three other outcomes answered a fourth one with their coefficients.
- **The estimate paragraph itself must name the named outcome.** The parent-level check is not enough: a
  design-level result chunk holds several outcomes' intervals in one passage, and the first interval in it
  answered a fatalities question with an incidents number until the paragraph was checked too.
- **"Effect" is an estimate word only when the question names the outcome.** On its own it is vague enough to
  pull a robustness paragraph about a different quantity.
- **A question that names a design is answered from that design.** "Design B specifications" answered from a
  Design A card is the same lending failure one level up, and the design id in the chunk's metadata is
  what catches it.

## 2. What it measured

Two sets, 38 answerable questions: the 16 published answerable questions and the 22 answerable held-out
questions from the v3 intent set.

| Set | Questions | Answered | Declined by R-04 | Refused by the gate | Answer rate |
|---|---|---|---|---|---|
| published | 16 | 16 | 0 | 0 | **1.000** |
| held-out | 22 | 20 | 2 | 0 | **0.909** |
| all | 38 | 36 | 2 | 0 | **0.947** |

The 36 answers are three shapes: **8 estimates, 14 reasons and 14 facts**. Every answered response carries
all the parts its shape requires, and **36 of 36** quote no number that is absent from their citations, in
the contract answer or in the plain reading.

**The needles.** The published eval set declares, per question, the strings the answer must carry — a
coefficient, an interval, a count. Of the **25** needles on the 16 published questions, **24** are present
(0.960 recall), and **15** of the 16 questions carry every needle they declare (0.938 satisfaction). The one
miss is a wording variant, not a missing fact: `q11` asks how many of the 36 cards carry a number and
declares the needle *"two `estimated` cards"*, while the answer carries the same fact as *"2 cards carry a
published estimate and 34 carry a reason instead"*. The published set is the only one that carries needles, so
the held-out figures for needles are not measured and are not reported.

**What the two declines are.** Both are held-out questions the layer declined with `L02` — no retrieved
passage matches the question closely enough to quote: *"What does the fatal crashes outcome measure?"* and
*"What was Nigeria's inflation rate in 2016?"*. Neither is a crash: the corpus carries no passage about a
fatal-crash outcome, and it carries no inflation series, so there is nothing to quote. An answer to either
would have been a paraphrase of something else.

### Why the rate moved, stated rather than tuned

The rate was **0.158** under the one-shape contract and is **0.947** under the three-shape contract. The
change is not a loosened post-check — every part R-04 requires is still required, and the verifier recomputes
the parts from the answers themselves. What changed is the contract's *shape*, which had been refusing for
the wrong reason: the corpus could say why there is no number, and the contract had no way to say it back.

What is still declined, and why:

- **Coverage, status and unit questions are answered as facts, not declined**, because the passage that says
  them exists and a fact answer can carry it. "How much of the monthly data series is observed rather than
  interpolated?" is answered from the data-quality record.
- **A question whose words the corpus does not use is declined rather than approximated.** The fact path
  requires the quoted passage to carry at least half the question's content words, weighted by how rare each
  word is in the corpus; below that the layer declines with `L02` rather than quote a passage that does not
  answer the question.

## 3. Plain language, and the key it does not need

The contract answer is precise and hard to read. `not statistically distinguishable from zero`, `standard
error`, `n = 3,456 state-months` and `p = 0.1129` are the right words for the record and the wrong words for
a reader. The plain reading is built from the same quoted passage:

- **Short answer** — the direction of the coefficient, whether the interval includes zero, and the sample,
  read out of the numbers the passage already contains.
- **The number / What it assumes / What it cannot tell you** — the estimate sentence, the identifying
  assumption in one sentence, and the caveats as bullets, all verbatim from the cited chunks.
- **What the words mean** — every term from `docs/glossary.md` that the answer actually uses, quoted from
  that page rather than rewritten in code. A term the page does not carry cannot appear.
- **For a refusal, the code and its meaning** — `docs/glossary.md` carries a plain-English line for every
  refusal code the contract declares (`L01`, `L02`, `G02`…`G09`), and a refusal that names its code without
  its meaning is a code the reader cannot use. The verifier fails if a code has no meaning, and if the
  glossary explains a code the contract does not declare.

The reading adds no evidence and no number. The verifier recomputes the sign, the interval's bounds, the
inclusion of zero and the sample from the artifact's own answer text, and fails if the plain reading
disagrees with them — so the plain view cannot drift away from the quoted answer it summarises.

**No LLM key is needed, and that is checked rather than claimed.** The layer's whole path is: declared rules
-> BM25 over committed text -> paragraph selection -> R-04 post-check -> plain reading -> glossary lookup.
Nothing is generated, so nothing needs a credential. `tests/verify_answer.py` runs the layer in a child
process with every key-shaped environment variable removed and requires an answer with a plain reading; a
requirement for a key would fail that step rather than surface as a broken demo. The answer-quality
measurement is the one thing here that does need a judge: it runs separately
(`scripts/eval_answer_quality.py`, `docs/rag.md` §3) and its key is never read by the app.

## 4. What the verifier establishes

`tests/verify_answer.py` does not import the layer. It reads the artifact, the corpus and the intent
artifact, and requires:

- **The gate's decision is honoured** — every row's intent equals the intent artifact's, a `refused` row is
  one the gate refused, its route is the gate's pinned chunk, and its text is the contract's template.
- **Every answer carries the parts** its shape requires and none its shape forbids, and the artifact's own
  `check` agrees with the text.
- **The sections appear in the contract's order**, read from the contract rather than from a list in the
  verifier.
- **Every sentence is extractive** — the content after each label appears verbatim in a cited chunk. A
  sentence the corpus does not contain fails.
- **Every number is in its citation** — numbers are compared after comma normalisation, and the artifact's
  own `numbers_absent_from_citation` list is recomputed.
- **The counts recompute** from the artifact's rows, including the shape counts and the needle counts.
- **The module imports no model, database or network client**, and it imports the gate rather than deciding
  for itself.
- **The plain reading is derived, not written** — its coefficient, bounds, zero-crossing, direction and
  sample recompute from the answer's own quoted numbers; every definition it prints is a line from
  `docs/glossary.md`; and it quotes no number its citations do not carry.
- **Every refusal code has a meaning and every refusal carries one** — in the contract, in the glossary and
  on the answer.
- **It runs with no LLM key** — a child process with the key-shaped variables stripped must answer and
  produce a plain reading.
- **The prose quotes the artifact** — this page must carry the measured rates and needle counts, or the
  build fails.

`tests/verify_app.py` closes the last gap: it asks the app's **Ask** tab the questions the tab offers and
requires the answers to carry the citation, the needles and the plain reading the artifact recorded, and a
refusal to carry its rule, its meaning and the passage it cites.

## 5. What it does not do

- **It does not generate prose.** The answer is a selection and a citation, which is the only kind R-04
  allows without an LLM in the path.
- **It does not verify relevance.** Retrieval is lexical; a passage can be a poor answer to the question and
  still satisfy the contract. The outcome guard above closes the worst case (a number lent to another
  outcome), not every case.
- **It does not paraphrase.** A question phrased in words the corpus does not use is declined rather than
  answered approximately. That is the cost of the deterministic path, and it is published rather than tuned.
- **Selection was tested before it was changed, and the test said no.** Two reader-shaped probes fail and
  both look like ranking defects: "can I republish the ACLED rows?" is answered from the coverage table in
  `docs/limitations.md`, which matches the words *ACLED* and *rows* but says nothing about licences, and
  "what did the event study find for 2010?" declines even though the 2010 event chunk is the retriever's
  top-ranked one. The obvious fix was implemented as a probe rather than shipped: let the highest-ranked
  document that covers the question be the answer document, and gate on the quoted paragraphs together
  instead of on the first paragraph alone. On the published eval set it **lost more than it gained** —
  correct answers moved off their administration record, their registry paragraph and their card and onto
  narrative pages, because trusting the retriever's document order gives up the paragraph-level check that
  keeps a passage about another subject from answering. It was not shipped. The probes have three different
  causes, not one: a vocabulary gap (*republish* vs *redistribution*, *caveats* vs *cannot rule out*) in two,
  and a generic frame (*event study*, *find*) wrapped around a specific year in the third. The honest fix is
  a declared routing and vocabulary layer, measured on a held-out question set written after it — the same
  order the intent gate used — not an ordering change made after reading three probes.
- **It does not generate, so it needs no judge.** Faithfulness and answer relevancy are measured separately
  by `scripts/eval_answer_quality.py` (faithfulness 1.000, answer relevancy 0.800 — `docs/rag.md` §3), and
  that measurement is the four RAGAS definitions implemented here, not the `ragas` library. The keyless run
  above still proves something the measurement does not: the system answers without a key at all.

## 6. Reproduction

```bash
py scripts/eval_answer.py     # rewrites registry/rag/<vintage>/answer_eval.json
py tests/verify_answer.py     # re-checks every part, sentence and citation
py tests/verify_app.py        # asks the app's Ask tab the same questions
```

`scripts/validate_artifacts.py` also fails if the artifact describes a different corpus than the one beside
it, or a different `intent_eval.json` than the one the layer was measured against.
