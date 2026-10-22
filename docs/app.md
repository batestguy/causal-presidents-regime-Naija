# The app — what a reader sees before they see a number

This is the artifact the whole project exists to produce: pick an outcome, pick one of the three
identification designs, and get the assumption the design rests on, the adjustment set that assumption
implies, what the design cannot rule out, and then — separately, on the other side of the page — the published
number or the reason there is none.

It is read-only on purpose. **Nothing is fitted at render time**, nothing is fetched, nothing is re-derived.

- **App:** `app/streamlit_app.py` (Streamlit 1.60)
- **Registry reader:** `app/registry_data.py` — loads `registry/dags/index.json` and the 36 cards, refuses a
  card whose vintage is not the index's
- **Reads:** `registry/dags/` only (cards, index, graphs). No database, no network, no model.
- **Verifier:** `tests/verify_app.py` — renders all 36 cards in Streamlit's own test harness and compares the
  output against the card JSON
- **Run:** `/c/Users/TOSHIBA/ds-general/python.exe -m streamlit run app/streamlit_app.py`

## 1. What is on the page

Three tabs, in the order the questions come in.

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
embedded as SVG.

**Design-level results.** Design B's number is about the **national FAAC channel**, and on all nine B cards
FAAC is a mediator; Design C was not run. Both are published here, once, with their specifications, their
robustness support and the declared next step. The page shows them on a separate tab precisely so they are not
mistaken for a card's estimate — and the verifier checks that no B card ever displays B's coefficient.

**What this reads.** The file list, the vintage, the no-model-at-render-time rule, and the ratio below.

## 2. The ratio, stated before any single number

**2 of 36 model cards carry a published number.** The other 34 each carry a reason from a closed set:

| Reason | Cards |
|---|---|
| `outcome_series_absent` | 12 |
| `no_specification_declared` | 10 |
| `design_result_is_channel_level` | 9 |
| `design_not_run` | 3 |

That sentence is the first thing on the page, because a reader who scans one card cannot otherwise tell whether
the project estimated two things or failed to estimate thirty-four. A card whose number is missing says why in
its own words, and `tests/verify_app.py` fails if a single one of the 34 renders a code without its detail
sentence.

## 3. Why there is no chat tab yet

The retrieval half of the chat layer is built and measured (`docs/rag.md`): 441 attributed chunks, recall@5 of
0.944 for the embedding retriever. But two of its four gates fail — refusal-with-reason recall 0.5, out-of-scope
refusal 0.25 — because a question like *"what will inflation be in 2030?"* embeds closer to the corpus than
several genuine questions do. Similarity alone cannot refuse it.

Shipping the chat before that gate passes would produce exactly the failure the corpus exists to prevent: a
confident answer to a question this data cannot answer. **The gate and the answer layer are now built and measured.** On a held-out set the rules never saw, the
gate refuses 0.947 of out-of-scope questions, cites the reason 1.000 of the time and leaves every answerable
question alone (`docs/intent.md`); it is the first refusal decision in the project that is a policy rather
than a score. The answer layer then enforces the R-04 post-check on its own output (`docs/answer.md`) and the
measurement is the reason the tab is still unbuilt: it answers **3 of the 16 published answerable questions
(0.188)** and 2 of the 22 held-out ones, because R-04 is an estimate contract and 34 of the 36 cards carry no
number to put an interval on. What is left for a chat surface is a product decision with those numbers in
hand — not a missing component.

## 4. The rules the verifier enforces

`tests/verify_app.py` does not import `app/registry_data.py`; it formats the card JSON itself and requires the
page to match.

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

A deliberate consequence: the app holds no statistic of its own. If the page and the card ever disagree, the
card is right and the app is wrong.

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
  one (decision log, UI-08).

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
