# The app — what a reader sees before they see a number

This is the artifact the whole project exists to produce: pick an outcome, pick one of the three
identification designs, and get the assumption the design rests on, the adjustment set that assumption
implies, what the design cannot rule out, and then — separately, on the other side of the page — the published
number or the reason there is none.

It is read-only on purpose. **Nothing is fitted at render time**, nothing is fetched, nothing is re-derived.

- **App:** `app/streamlit_app.py` (Streamlit 1.60)
- **Registry reader:** `app/registry_data.py` — loads `registry/dags/index.json` and the 36 cards, refuses a
  card whose vintage is not the index's
- **Answer layer:** `app/answer_layer.py` + `app/intent_gate.py` — the gate, the corpus and the answer
  contract, for the **Ask** tab
- **Reads:** `registry/dags/` (cards, index, graphs) and, for the Ask tab, `registry/rag/<vintage>/` (the
  corpus and the published questions), `analysis/specs/` (the gate's rules and the answer contract) and
  `docs/glossary.md`. No database, no network, no model.
- **Verifier:** `tests/verify_app.py` — renders all 36 cards in Streamlit's own test harness and compares the
  output against the card JSON, then asks the Ask tab the questions it offers and compares what comes back
  against the published measurement
- **Run:** `/c/Users/TOSHIBA/ds-general/python.exe -m streamlit run app/streamlit_app.py`

## 1. What is on the page

Four tabs, in the order the questions come in.

**Model card.** The sidebar picks `(outcome, design)`. The page then shows, left column first:

- the assumption, stated as a sentence rather than a symbol;
- the **adjustment set**, resolved by dagitty on the card's assumed graph and shown as `label (node_id)` —
  never hand-listed, so it cannot drift from the graph the estimate was produced under;
- the node the design assumes absent, and the cannot-rule-out list — anticipation, SUTVA, and the rest, copied
  from the card;
- the Stage 5 pre-check, including its blocker, because the diagnosis happened before the estimation and the
  reader is entitled to see what it said.

Right column: the number, its interval, p-value, sample and window, the verdict (`identified` /
`estimated_not_identified`) with the failed check that decided it, every field of the published specification
in an expander, and one line placing this specification in the Stage 7 grid. Below both: the assumed graph,
embedded as SVG, and then the outcome series the card is about.

**The outcome series, drawn from the base.** One static panel per outcome — **12 outcome panels**, published
at `registry/series/<vintage>/` by `analysis/R/07_series_figures.R` and reused by all three designs on that
outcome. The twelve panels together cover 4,008 outcome-months: **788 observed**, 1,826 interpolated by the
monthly spine, and 1,394 with no observation at all. An observed month is a dot, an interpolated month a
dotted segment, and a run of unobserved months is shaded and labelled — so a reader can see, without reading
a caption, that `u5mr` is 26 annual points across 275 interpolated months and that both education outcomes
stop in 2010. The figure is rendered at build time, never at request time, and its byte count is recorded in
the artifact so a panel that outlives its rows fails `scripts/validate_artifacts.py` rather than being noticed
by a reader.

**Design-level results.** Design B's number is about the **national FAAC channel**, and on all nine B cards
FAAC is a mediator; Design C's synthetic control published four windows and identified none. Both are published
here, once, with their specifications, their robustness support, the placebos and the declared next step. The
page shows them on a separate tab precisely so they are not mistaken for a card's estimate — and the verifier
checks that no B card ever displays B's coefficient.

**What this reads.** The file list, the vintage, the no-model-at-render-time rule, and the ratio below.

**Ask the registry.** The intent gate and the answer layer, in the reader's own words. Section 3.

## 2. The ratio, stated before any single number

**2 of 36 model cards carry a published number.** The other 34 each carry a reason from a closed set:

| Reason | Cards |
|---|---|
| `outcome_series_absent` | 12 |
| `no_specification_declared` | 10 |
| `design_result_is_channel_level` | 9 |
| `design_not_run` | 2 |
| `design_estimated_not_identified` | 1 |

That sentence is the first thing on the page, because a reader who scans one card cannot otherwise tell whether
the project estimated two things or failed to estimate thirty-four. A card whose number is missing says why in
its own words, and `tests/verify_app.py` fails if a single one of the 34 renders a code without its detail
sentence.

## 3. The Ask tab — the same rule, one level down

The **Ask** tab is the intent gate and the answer layer, in the reader's own words. A question goes to the
gate first. If the gate refuses it, the reader gets a refusal that carries four things: the rule that
refused (`G02`…`G09`), that rule's plain-English meaning out of `docs/glossary.md`, the passage that says why
it cannot be answered, and that passage's citation. If the gate allows it, the answer layer retrieves the
passages that answer it and assembles an extractive answer in the contract's order — an estimate with its
interval, a reason with the check that decided it, or the passage that says the thing asked about — and
every part of it cites the chunk it came from.

**Both halves are deterministic, and that is the point.** The retrieval is the same BM25 the retrieval
evaluation measures as its baseline; the assembly selects committed paragraphs rather than writing prose;
the plain-language reading is computed from the answer's own numbers. No model is called, no key is needed,
and the answer the tab gives is the answer the project measured: **36 of the 38 measured questions answered
(0.947)**, with 24 of the 25 published needles present in the answers that were supposed to carry them
(0.960 recall, 0.938 satisfaction — `docs/answer.md` §2). A generated answer could not be checked against
anything; this one is checked against the artifact on every build.

**The tab does not re-decide anything.** It offers four questions the project has already published and
measured — one that asks for a number, one that asks why a design was never run, one that asks a fact the
data-coverage record carries, and one the gate refuses — and the verifier asks each of them through the real
chat input and compares the answer with `intent_eval.json` and `answer_eval.json`. The tab reproduces the
measurement; it is not a second opinion on it.

**What it still cannot do.** BM25 is lexical, so a question phrased in words the corpus does not use is
declined rather than answered — 2 of the 38 measured questions were, and the refusal says so instead of
guessing. The embedding retriever's own refusal gates still fail (refusal-with-reason recall 0.5,
out-of-scope refusal 0.25 — `docs/rag.md`), which is why the tab uses the rule-based gate: similarity alone
cannot refuse *"what will inflation be in 2030?"*. The held-out question set is the project's own measurement
set, and the verifier fails if any held-out question reaches the page.

## 4. The rules the verifier enforces

`tests/verify_app.py` does not import `app/registry_data.py`; it formats the card JSON itself and requires the
page to match. It does not import `app/answer_layer.py` either: the answers the tab gives are compared with
the published artifacts, not with the code that produced them.

- **Every one of the 36 pairs renders** — a card the reader cannot reach is a card that does not exist.
- **The number on the page is the card's number** — coefficient, interval, p-value, sample, the coefficient's
  name and the verdict, all as the card carries them.
- **A verdict's failed check is shown with the number.** Coefficient without its verdict is the failure Stage 8
  exists to prevent.
- **A card without a number names its reason** and its detail.
- **The adjustment set is the card's**, node by node, resolved to labels.
- **No coefficient is typed into the app.** Every published coefficient is searched for in the app's source in
  full and 4-decimal form. The card wins; a literal in the UI is the defect.
- **Nothing can be fitted at render time** — the source is scanned for database clients, network clients and
  fitting libraries.
- **The Ask tab's answers are the measured answers** — each question the tab offers is asked through the real
  chat input, and the answer must carry the citation, the needles and the plain reading the measurement
  recorded.
- **A refusal must cite** — the rule, the glossary's meaning for it, and the passage it refuses for.
- **The held-out set does not leak** — a held-out question on the page fails the build.

A deliberate consequence: the app holds no statistic of its own. If the page and the card ever disagree, the
card is right and the app is wrong. The same holds for the tab: if an answer and `answer_eval.json` ever
disagree, the artifact is right and the app is wrong.

## 5. Limits

- **It renders; it does not explain.** A reader who does not know what a backdoor set is will not learn it
  here. `docs/design-memo.md` and `docs/limitations.md` are the explanation; the page links to neither yet.
- **A card cannot be linked.** The outcome and design live in widget state, not the URL, so "fatalities under
  Design A" has no address to send anyone. `st.query_params` fixes it; it is not done.
- **The graph is not interactive.** The SVG is the R-generated figure, drawn on the assumed graph, with the
  unobserved node labelled rather than hidden. Clicking a node to see which edge the assumption lives on is not
  built.
- **No tenure comparison, no forecast, no recommendation** — those are the three things readers ask for first,
  and the page says why the first one is not identifiable with 22–23 annual observations against four to five
  administrations.
- **The app is not deployed.** It runs locally against the committed registry; a hosted instance would need a
  decision about whether a stale vintage may ever be served, which is a governance question, not a packaging
  one (decision log, UI-08). **The static guided flow is deployed**, and answers that question the other way:
  `.github/workflows/verify.yml`'s `pages` job rebuilds from the same commit only after the static job has
  passed, and every page stamps the registry vintage (`site/build.py`, checked by `tests/verify_site.py`), so
  a reader can see which vintage they are being served rather than being told it is current.

## 6. Why Streamlit, and what that costs

The framework question was reopened on 2026-10-21 and settled on the record (`docs/decisions.md`, UI-01…UI-06).
The short version:

**Chosen because it is verifiable without a browser.** `streamlit.testing.v1.AppTest` renders the real script
and hands back the element tree in pure Python, so the 36-card contract check is a step in `verify.sh` and in
CI rather than a manual ritual. Every alternative — Dash, Shiny, React — needs a Selenium or Playwright
driver for the same evidence, and neither is installed here. A check nobody runs is a claim, not a check
(C-42).

**Also because the page has no state.** It is a pure function of the registry, so Streamlit's rerun-everything
model — the thing that makes it a poor fit for dashboards that hold a lot of state — has nothing to
desynchronise here. One Python process, no build step, no API layer, no keys, and the chat tab's streaming
and session state are native when it arrives.

**What it costs, honestly:** no URL routing per card (fixable with `st.query_params`), coarse layout control,
and the causal graph is a static SVG rather than a clickable object. None of those is a correctness problem;
the first is the one a reader will notice. The condition for leaving the framework is *the interactive graph
becoming the product*, not styling — at that point Plotly Dash is the smallest honest jump, and
`app/registry_data.py` (which is framework-free) would survive it unchanged.
