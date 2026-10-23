# What the chat layer is allowed to quote — Stage 8, the retrieval corpus

The registry is the app's data contract for numbers. This is its contract for *prose*: every sentence the
chat layer can produce is assembled from a chunk listed here, each chunk names the file and vintage it was
copied from, and the file's hash is checked on every verification run.

The layer exists because a RAG system is the one component that can undo this project's honesty argument in
a sentence. Retrieve the `+0.4793`, drop the `estimated_not_identified` verdict, and the answer is
authoritative-looking and wrong. Everything below is shaped by that.

- **Spec:** `analysis/specs/rag.yml` (chunk families, budget, retriever, refusal contract)
- **Eval set:** `analysis/specs/rag_eval.yml` (22 authored questions, declared before anything was measured)
- **Engine:** `scripts/build_rag_corpus.py` (text), `--embed` (vectors), `scripts/eval_rag.py` (retrieval)
- **Artifact:** `registry/rag/2026-10-18/` — `corpus.json`, `embeddings.npz`, `eval_set.json`,
  `retrieval_eval.json`
- **Verifier:** `tests/verify_rag.py` — re-hashes every source, rebuilds BM25 and the cosine ranking from
  stored data, and recomputes every published metric and gate flag

## 1. What is in it

**482 chunks from 53 attributed sources**, at vintage 2026-10-18 — the registry's vintage, not the build date,
so an answer that quotes a card is a statement about that data vintage whenever it is read.

| Family | Chunks | Parent documents |
|---|---|---|
| `model_card` | 179 | 36 — one per card, split into parts when the card exceeds the budget |
| `methodology` | 183 | 9 documents: design memo (34), estimates (23), robustness (19), events (22), registry (14), limitations (37), DAGs (29), glossary (3), licence register (2) |
| `data_dictionary` | 47 | 1 |
| `card_estimate` | 36 | 36 — one per card, the card's fields in one piece |
| `event_study` | 13 | 4 transitions + the artifact's `not_claimed` list |
| `published_result` | 12 | 3 — Designs A, B and C |
| `administration` | 5 | 5 seed rows |
| `shock` | 3 | 3 annotated bands |
| `coverage` | 2 | the quality gate counts and the registry's card counts |
| `scope` | 2 | the answer contract's own scope paragraph |

**No chunk is written by hand.** A model-card chunk is a serialisation of the card's fields — assumption,
adjustment set, cannot-rule-out, pre-check verdict, estimate block, Stage 7 summary — so it cannot disagree
with the card. A result chunk is serialised from the index's published result plus the estimates artifact's
own `design_name`. The tables come from the seeds, the events from the events artifact, and the narrative
from the committed markdown.

**A card is one document, not necessarily one chunk.** At a 950-character budget a card splits into 3–6
parts, each opening with `[title — part k of n]` and carrying the card's id in its own id
(`card:fatalities__A#p3`). That is a deliberate trade: keeping a card in one chunk would have meant either a
2,600-token chunk (silently truncated by any 512-token model) or dropping the coverage note and the
cannot-rule-out list. The estimate paragraph and its verdict sit in adjacent paragraphs and normally land in
the same part; when they do not, the retriever returns both.

**The `card_estimate` family is the same card in one piece**, because an answer has to quote the reason
beside the assumption it qualifies. A question about one of the 34 cards that carries a reason needs the
reason, the assumption and the caveat from a single passage; assembled from the split `model_card` parts it
lacked half of what the contract requires, and the answer layer declined. The family is therefore allowed a
declared **1,700-character** budget (`chunking.max_chars_by_family`) rather than the 950 every other family
takes. The number is the tokenizer's, not a preference: the longest card is 1,598 characters and 379 tokens
of the 512-token window, measured with the declared model's own tokenizer. `tests/verify_rag.py` reads the
per-family budget from the spec — before it did, it applied 950 to this family and reported 36 false
failures, which is how a verifier stops being read.

## 2. The budget is set by the model, and it caught two mistakes

The base spec named `all-MiniLM-L6-v2`. That model caps at **256 tokens**, so the first build would have
truncated every chunk past ~1,000 characters — the tail of a card would have been unreachable while the
artifact still looked complete. The corpus declares `multi-qa-MiniLM-L6-cos-v1` instead: same 384 dimensions,
same CPU cost, **512 tokens**, and trained for question-to-passage retrieval.

The first character budget (1,800) then failed its own tokenizer check: a table-heavy chunk needed **935
tokens**. So `--embed` counts the model's own tokens for every chunk and fails the build rather than
truncating. At 950 characters the densest text in this corpus (0.53 tokens/character) uses 504 tokens.

This is recorded rather than quietly fixed because it is the failure class the project keeps finding: a
budget that was right for prose, silently wrong for tables, and invisible in every artifact until something
measures it.

## 3. What was measured, and what was not

22 questions, authored before any number was read: 16 answerable (the published estimates, the channel,
Design C's status, coverage, quality, the event study, the tables), 2 refusals that must cite a reason, and
4 genuinely out of scope (a forecast, a 1960 fact, a current city population, a policy recommendation).

| Metric | Embeddings | BM25 baseline | Gate |
|---|---|---|---|
| recall@5 | **0.944** | 0.833 | ≥ 0.90 — **met** for embeddings, not for the baseline |
| gold coverage@5 | 0.418 | 0.383 | — |
| MRR | 0.715 | 0.657 | — |
| refusal-with-reason recall | **0.5** | 0.0 | 1.0 — **not met** |
| out-of-scope refused | **0.25** | n/a | 1.0 — **not met** |
| answerable kept (not refused) | 1.0 | n/a | 1.0 — met |

The embeddings beat the lexical baseline on every retrieval measure, which is the only reason to keep a
model in the path at all: if BM25 had matched it, the corpus would have been keyword-addressable and the
model would have been decoration.

### The two failures, stated rather than tuned away

**Refusal-with-reason recall is 0.5.** One of the two refusal questions — "Can the synthetic control tell me
whether Buhari's tenure caused the fall in under-5 mortality?" — retrieves `docs/estimates.md` §1 (the tenure
question is unanswerable) instead of the Design C passage, because §1 is a better lexical match for the words
"tenure" and "Buhari". The corpus contains the right answer in `result:C` and in §2's Design C subsection;
the retriever ranks the wrong passage. A reranker or a hybrid score would likely fix it. It is published as
a miss because the alternative — editing the question until it passed — would have measured the edit.

**Out-of-scope refusal is 0.25.** Only the "How many people live in Kano today?" probe falls below the
threshold. The others — a 2030 inflation forecast, a 1960 population, a normative recommendation — embed
*closer* to the corpus than some genuine questions do (0.39, 0.32, 0.42 against answerable questions at 0.37
and 0.42). That is the finding: **similarity alone cannot refuse a question that is out of scope but on
topic.** Any threshold that refused the forecast would refuse real questions with it. The replacement is the
pre-retrieval intent gate built in Stage 9 (`docs/intent.md`): a declared rule set that decides the intent
from the question's own words before retrieval and pins the chunk a refusal must quote. Measured on a
held-out set the rules never saw (v3), it refuses **0.947** of out-of-scope questions and cites the reason
**1.000** of the time, while keeping **1.000** of answerable questions — the one miss, a country reached only
through its capital city, is published rather than tuned away (`docs/intent.md`). On this eval set, out-of-scope refusal goes
**0.25 → 1.000** and reason-citation **0.5 → 1.000**, with answerable recall unchanged.

The refusal threshold is `0.291464`, derived as 0.5 × the median answerable top-1 similarity (0.5829). It is
calibrated on the eval set, so the refusal number is optimistic; that caveat travels in the artifact.

### Not measured, and why

- **RAGAS** (faithfulness, answer relevance, context precision/recall) needs a generation step and a judge
  model. There is no LLM key in this repository, so the artifact says `not_run` with that reason. The eval set
  carries a `reference_answer` per question, i.e. the ground-truth column a RAGAS run needs, so wiring it is
  a key and one script away — not a rebuild.
  This is a limit on the *measurement*, not on the system: retrieval, the intent gate and the answer layer
  all run with **no key at all** (`docs/answer.md` §3), and `tests/verify_answer.py` proves it by running the
  layer in a child process with every key-shaped variable stripped. Nothing here generates text, which is
  why nothing here needs a credential and why faithfulness has nothing to judge yet.
- **The answer-shape post-check** (interval + assumption + citation, R-04) is now enforced by
  `app/answer_layer.py` and measured in `docs/answer.md`: every assembled answer is checked, and a missing
  part is replaced by the refusal template. The eval set's `must_contain` needles remain the retrieval
  layer's inputs.

Neither is reported as satisfied. A skipped check printed as a pass is the defect this project keeps
finding.

## 4. What the corpus refuses, and how

`analysis/specs/rag.yml` declares the answer contract: question → estimate with interval → identifying
assumption → what it cannot rule out → citation. A response missing any of the three required parts is
replaced by the refusal template, whatever the model produced (R-04).

Two refusal paths, measured separately:

- **Nothing relevant** — top-1 below the declared threshold, or the top-1 chunk is `scope:answer`.
- **A reason the data cannot answer** — the question retrieves a limitations or Design-C passage, and the
  answer must cite it. This is why `docs/limitations.md` is in the corpus at all: it is where "I don't have a
  model for that" gets a citation instead of a shrug.

## 5. Rebuilding it

The text half needs only Python and PyYAML, so CI can rebuild and check the corpus without torch:

```bash
python scripts/build_rag_corpus.py            # corpus.json + eval_set.json
python scripts/eval_rag.py                    # BM25 only if there are no embeddings
python tests/verify_rag.py
```

The vector half needs the ingestion environment's torch install, which lives in its own conda env on this
machine (no network service, no GPU):

```bash
/c/conda-envs/drlca-rag/python.exe scripts/build_rag_corpus.py --embed
```

`sentence-transformers==5.1.2`, `torch==2.14.1+cpu`, `numpy 2.4.6`; the model is `multi-qa-MiniLM-L6-cos-v1`
(384 dims, 512 tokens). The first `--embed` downloads ~90 MB into the Hugging Face cache; after that the run
is ~20 seconds for 482 chunks.

**Then rebuild whenever a source changes.** The corpus records the sha256 of all 51 sources and
`tests/verify_rag.py` fails when one no longer matches, with the rebuild command in the message. That is the
mechanism the project kept asking for: a document edited without its corpus is caught by a check rather than
by a reader noticing that the chat layer contradicts the page.

## 6. What this does not claim

- Not that retrieval alone is good enough to ship a chat box: two of four semantic gates fail, for the
  reasons in §3, which is why the tab built in Stage 9 puts the declared intent gate in front of retrieval,
  not a similarity threshold.
- Not that the corpus is complete: the donor panel, the raw quality report and the robustness grid are
  summarised, not chunked. A question that needs a specific donor's value or a specific robustness cell will
  refuse, and that is the correct behaviour until those artifacts are added as families.
- Not that adding a document is the same as making its questions answerable. The glossary and the licence
  register were added in the 2026-10-23 rebuild (5 chunks in total, with every retrieval metric unchanged), and the effect is
  partial and stated: "what does G02 mean?" now quotes the glossary's refusal table, while "can I republish
  the ACLED rows?" still resolves to the coverage table in `docs/limitations.md`, because the fact path
  chooses the passage with the most of the question's words and a licence table row is short. The corpus
  gain is real; the selection gain is not, and it is measured here rather than assumed.
- Not that `docs/decisions.md` is in the corpus. It was tried in the 2026-10-23 rebuild and rejected on
  the numbers: at 210 chunks — more than the registry itself — recall@5 stayed at 0.944 but MRR fell from 0.715 to 0.687 and
  gold coverage from 0.418 to 0.379. A session log that dilutes every ranking to answer a few "why was that
  chosen" questions is a corpus that quotes the project's diary before its findings. It stays out until it
  is summarised into a declared artefact.
- Not that RAGAS has been run. It has not, and it is the only stage that would need a key.
- Not that this corpus is what answers a reader's question on its own. The corpus is the quotable text; the
  intent gate and the answer layer (`docs/intent.md`, `docs/answer.md`) decide what may be asked and how a
  passage becomes an answer.
