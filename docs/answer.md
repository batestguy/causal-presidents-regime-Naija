# What an answer may contain — Stage 9, the answer layer

The intent gate decides whether the corpus may answer a question and, when it may not, which chunk the
refusal must quote. This layer does the rest: it retrieves passages, assembles an answer in the contract's
order, and runs the R-04 post-check **on its own output**. If any required part is missing, the answer is
replaced by the refusal template — the layer cannot ship a sentence the contract would not allow.

It is deliberately not a chat tab. `app/streamlit_app.py` has no chat surface, and the measurement below is
the reason the tab is still unbuilt: the contract is an **estimate** contract, and most questions the
retriever says are answerable cannot be answered with all three required parts.

- **Spec:** `analysis/specs/rag.yml#answer_contract` — the order, the post-check, the refusal template
- **Engine:** `app/answer_layer.py` — gate → BM25 retrieval → extractive assembly → post-check
- **Measurement:** `scripts/eval_answer.py` → `registry/rag/2026-10-18/answer_eval.json`
- **Verifier:** `tests/verify_answer.py` — re-checks every part, every quoted sentence and every number

## 1. What it does, in order

1. **Ask the gate.** An `out_of_scope` or `refusal_with_reason` decision ends the request: the layer returns
   the contract's refusal template with the rule's reason and the pinned chunk's citation. It never answers
   around a refusal.
2. **Retrieve.** Okapi BM25 over the corpus text, no stemming and no synonyms — the lexical scorer the
   retrieval evaluation measures as its baseline (`docs/rag.md`). **No embedding model is called**, so the
   layer imports no model, no database client, no network client and no fitting library. The committed
   vectors are used offline by `scripts/eval_rag.py`, not here.
3. **Assemble, extractively.** The top distinct parent documents are tried in rank order. From the parent
   that carries an estimate, three paragraphs are selected: the one with the 95 % interval, the identifying
   assumption, and what the design cannot rule out. If a part is missing there, it is borrowed from another
   retrieved chunk that carries it, and that chunk is cited too. Every sentence in the answer is a committed
   paragraph — nothing is paraphrased and no number is typed.
4. **Check the output.** The answer is labelled in the contract's order — question, estimate with interval,
   identifying assumption, what it cannot rule out, citation — and then the post-check runs. A missing part
   replaces the whole response with the refusal template (R-04).

Two relevance guards keep the assembly from lending a number to a question it does not answer, the same
failure the app's results tab prevents one layer up:

- **A question that names an outcome may only be answered from a passage about that outcome.** Without this,
  a design-level result that lists three other outcomes answered a fourth one with their coefficients.
- **"Effect" is an estimate word only when the question names the outcome.** On its own it is vague enough to
  pull a robustness paragraph about a different quantity.

## 2. What it measured

Two sets, 38 answerable questions: the 16 published answerable questions and the 22 answerable held-out
questions from the v2 intent set.

| Set | Questions | Answered | Declined by R-04 | Refused by the gate | Answer rate |
|---|---|---|---|---|---|
| published | 16 | 3 | 13 | 0 | **0.188** |
| held-out | 22 | 2 | 20 | 0 | **0.091** |
| all | 38 | 5 | 33 | 0 | **0.132** |

Every answered response carries all four parts — interval, assumption, cannot-rule-out and citation — and
**5 of 5** quote no number that is absent from their citations. The five answered questions are the two
Design A cards that carry a number (fatalities, incidents) plus the three questions about them: the
published `q01`, `q02`, `q03`, and held-out `B01` and `B03`.

### Why the rate is low, stated rather than tuned

R-04 requires an interval, an identifying assumption and what it cannot rule out **on every assembled
answer**. That is an estimate contract, and the corpus cannot satisfy it for most questions:

- **34 of the 36 cards carry no number**, by design (`docs/registry.md`). A question about those cards has no
  interval to carry, so the contract replaces the response with the refusal template — even though the corpus
  can say *why* there is no number.
- **A card's estimate and its caveats sit in different parts**, and the layer may only quote paragraphs that
  are committed. Borrowing fills some gaps, but a question whose retrieved passages never carry a
  cannot-rule-out is declined rather than answered with a fabricated caveat.
- **Coverage, status and date questions are declined by design**, because they ask for something an estimate
  answer cannot carry: "how many series were flagged", "which party governed in 2012", "what unit is u5mr in".

The rate is not a retrieval failure. BM25 recall@5 is 0.833 and the gold chunk is retrieved for most of these
questions; what fails is the contract's requirement that the *response* carry all three parts. Lowering the
requirement would be a spec change and a decision, not a fix, and it is not taken here. What would raise the
rate without weakening R-04 is a corpus that keeps each estimate, its assumption and its caveats in one
retrieved passage — a chunking question, not an answer-layer one.

## 3. What the verifier establishes

`tests/verify_answer.py` does not import the layer. It reads the artifact, the corpus and the intent
artifact, and requires:

- **The gate's decision is honoured** — every row's intent equals the intent artifact's, a `refused` row is
  one the gate refused, its route is the gate's pinned chunk, and its text is the contract's template.
- **Every answer carries the parts**, and the artifact's own `check` agrees with the text.
- **Every sentence is extractive** — the content after each label appears verbatim in a cited chunk. A
  sentence the corpus does not contain fails.
- **Every number is in its citation** — numbers are compared after comma normalisation, and the artifact's
  own `numbers_absent_from_citation` list is recomputed.
- **The counts recompute** from the artifact's rows.
- **The module imports no model, database or network client**, and it imports the gate rather than deciding
  for itself.

## 4. What it does not do

- **It does not generate prose.** The answer is a selection and a citation, which is the only kind R-04
  allows without an LLM in the path.
- **It does not verify relevance.** Retrieval is lexical; a passage can be a poor answer to the question and
  still satisfy the contract. The outcome guard above closes the worst case (a number lent to another
  outcome), not every case.
- **It does not serve the app.** No chat tab exists; wiring this layer into one would expose the 0.132 answer
  rate to a reader, which is a product decision with the numbers now in hand.
- **It does not replace RAGAS.** There is no generation step and no judge model, so faithfulness and answer
  relevance remain `not_run` (`docs/rag.md` §3).

## 5. Reproduction

```bash
py scripts/eval_answer.py     # rewrites registry/rag/<vintage>/answer_eval.json
py tests/verify_answer.py     # re-checks every part, sentence and citation
```

`scripts/validate_artifacts.py` also fails if the artifact describes a different corpus than the one beside
it, or a different `intent_eval.json` than the one the layer was measured against.
