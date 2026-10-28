# Progress log — causal-presidents-regime-Naija

**Last updated:** 2026-10-28 (nineteenth session) · **Stage:** 9 — **Design C (stage 8h) fitted and closed as
not identified**, the gate re-frozen at v4, and the whole chain re-run · **verified at vintage 2026-10-18**:
dbt build (165/165), every R stage, the corpus, both evals and all **twenty-three** verifiers, one step at a time
with `HF_HUB_OFFLINE=1` and the RAG interpreter; `all checks passed`

**This session, in one line:** the last declared design that had never been run — **Design C, a synthetic
control on under-5 mortality** — was specified, fitted, broken on purpose and published, and its honest verdict
is **estimated, not identified**: four windows, rank p 0.17–0.50, and a pre-fit gate that turned out not to
discriminate at all (304 of 396 placebos clear it).

- **The spec was written before a weight was fitted** (`analysis/specs/design_c.yml`, stated in its own
  `stamp`): the windows are Stage 5's declared ones, read from `diagnostics.yml` rather than retyped; a year
  belongs to the administration in office on **1 July**; the estimator is the gate's own simplex QP on the
  pre-treatment path, and `Synth`'s V search is *not* used because it returned a fit worse than the best single
  donor on every window.
- **The verdict rule is three conditions, fixed in advance:** pre-fit ratio ≤ 0.10, in-space rank p ≤ 0.05, and
  every runnable in-time placebo under half the estimated gap. Nothing was added after the numbers were read.
- **The result, and it is a refusal.** yaradua, jonathan, buhari and tinubu estimated (obasanjo refused: 0 pre
  years inside the 1999-onward window); **none identified**. In-space p = 0.50 / 0.32 / 0.17 / 0.33; the
  in-time placebo fails where it can run (buhari's backdated windows return gaps of 0.9–11.6 against a 9.4
  estimate, one of them larger than the estimate). **304 of 396 placebo fits also clear the 0.10 pre-fit
  gate**, which is the measured form of the warning Stage 5 wrote in prose: on a 99-donor pool the gate is
  interpolation, not validation.
- **The verifier found the estimator is underdetermined, and that is now published.** 99 donors against 8–24
  pre-years leaves a face of equally optimal weights; the QP returns one vertex and SLSQP returns another with
  the same pre-fit and a different post gap. The artifact therefore publishes the vertex **and** a unique
  ridge refit beside it, plus the leave-one-donor-out range. For yaradua the two disagree in sign (+2.1 against
  −2.6 deaths per 1,000) — the estimate belongs to the solver, and the artifact says so rather than picking one.
- **`tests/verify_design_c.py` refits it with a different solver** (22s): the published weights reproduce every
  path, gap and ratio; SLSQP cannot improve the declared objective; the ridge solution is recomputed and
  matched; the rank p is arithmetic on the shipped distribution; the verdict is re-derived from the declared
  rule; and the in-time/LOO fields are re-checked. It is in the chain.
- **No gap reached a card, and the reason is a contract, not an oversight.** A synthetic control has no
  sampling distribution, so the honesty layer's "no point estimate without an interval" rule keeps it off the
  card. The `u5mr`×C card now carries **`design_estimated_not_identified`** — a fifth reason code — with the
  gap range, the rank range and the artifact path in its detail. **2 of 36 cards still carry a number**; the
  reason split moved 3/0 → 2/1 for the two Design C codes.
- **`estimates.json` no longer claims Design C is `not_run`.** Stage 6 reads the stage-8h artifact and carries
  its status, counts and per-window summary; the chain runs 8h **before** Stage 6 so the block cannot describe
  a design that has since been fitted. `docs/estimates.md`, `limitations.md` §7, `registry.md`,
  `robustness.md`, `design-memo.md` §4 and `app.md` were moved onto the artifact's own numbers.
- **The design screen prints C by year, never by name** — 2007–2009, 2010–2014, 2015–2022 — with the placebo
  p and the ridge gap beside each, and the note that a synthetic control has no interval. The surname guard
  covers the new block like every other page.
- **The gate had to be re-frozen, and the process was followed.** G07's reason sentence ("Design C was never
  run") became false the moment the design was fitted. The rule was edited and **frozen at `613ccf5`** before
  `intent_gate_eval_v4.yml` existed; the v4 set uses **new rotations** of every mechanical family (the harness
  now reads `indices`, `design_offset` and `admin_indices` from the spec instead of hard-coding them) and
  sixteen **new** authored questions, with the seventeen v3 authored cases as the regression block. Measured on
  v4: intent accuracy **0.980**, out-of-scope refusal **0.947**, answerable kept **1.000**, route resolved
  **1.000**, reason cited **1.000**; the one miss is the new probe **P04** (a country reached through its
  currency), and the regression block is 0.941 with the v3 probe P03 still answerable — the declared KG03
  remainder.
- **The retrieval and answer measurements were re-run, not carried forward.** The corpus grew to **488 chunks**
  (the new card reason and the new §7 text), recall@5 **0.944**, gold coverage **0.432**, MRR **0.718**; the
  answer layer answers **36 of 38 (0.947)** with **10 estimates, 14 facts and 12 no-estimate readings**, and
  needles **22 of 25 (0.880)**. One published example is now **declined** — *"what did its placebos find?"* is
  not the corpus's vocabulary ("in-space rank p") and BM25 is lexical — so `verify_app.py` grew a branch that
  requires the tab to reproduce a **measured decline** rather than an answer.
- **The answer-quality measurement was re-scored against the new corpus** (15 answered questions, 30 judge
  calls): faithfulness **0.965**, answer relevancy **0.833**, context precision **1.000**, context recall
  **0.850**. Still the four RAGAS definitions in house, `library: false`, judge noise published as a range.
- **The stat work still not done is now only the blocked kind:** per-capita dose axis (X-09 and a state
  denominator), D2 (IGR), monthly CPI, security after 2024-12, DHIS2, and a real-library RAGAS run. Design C was
  the last declared design with no estimate, and it now has one — a verdict of refusal, with its placebos.

**Then, same session — page 1 of the final layout, the navigation, and the methodology draft.** The requester
asked for the cover to state scope rather than the failure ratio, a nav bar with About and a Methodology page,
and party emblems on the portrait strip.

- **The cover band now reads scope:** *36 models compared*, the three methods, and *3 identification designs ·
  117 fitted specifications · 1999–2026*. Every part is a fill from the registry (`models`, `designs`,
  `specifications`, `first_year`/`last_year`); `verify_site.py` fails if any drifts. The ratio is not deleted —
  it moved into **About this study** and the verifier still requires it (P-08 supersedes P-06's placement only).
- **Five portraits in one row**, 3 + 2 centred on tablet and 2-up on a phone with the last card centred; the
  header, cards and footer share the 1180 px measure; the CTA sits above the fold; full white on the flag green
  (4.6:1) replaces the 88 % alpha that measured ~3.9:1.
- **A primary nav on every page** (`Home · About · Methodology`), with the current page marked by
  `aria-current` and links resolved from each page's own URL — the rule that caught the 404ing figures in the
  previous pass. **About** ships as a declared frame with a "still to come" list (author, funding, citation,
  licences, changelog) rather than invented biography (P-10).
- **Methodology is drafted in full**: the problem; four strands of prior work (synthetic control; staggered DiD
  and local projections; specification curves; Nigeria/region); six paragraphs on what this project does
  differently, each anchored to a measured fact; what it does not claim; how it is checked; eleven references.
  The references were **checked against the Crossref API on 2026-10-28** — venue, volume, pages and DOI — which
  is the check the design spec §18 said had to happen before a public methodology page existed. DOIs are printed
  as text, not links, because the site makes no network request; `verify_site.py` requires every reference and
  each derived number on the page.
- **Party emblems are drawn, not copied**: a line-art umbrella for the PDP and broom for the APC beside the code
  in the portrait strip. Copying the official marks would raise a trademark question and read as an endorsement
  on an analysis about presidencies; the shapes are public-domain objects and the drawing is this project's
  (P-09). The full party name remains on the strip's `title`, and the emblem is `aria-hidden`.
- **The site is now 10 pages** and `verify_site.py` covers the new ones: nav on every page, the About frame, the
  five methodology sections, every reference, and each derived number on the page.

**Then, same session — Technical details, and a shorter Methodology.** The requester asked where the variable
dictionary, the model table and the equations should live, and whether that should shorten the methodology.

- **A separate page, not a dropdown.** `/technical/` carries four reference tables: the **25 catalogue
  variables** (id, meaning, unit, direction, source, coverage — read from `raw_metric_catalogue.csv` at build
  time), the **design variables** (dose, per-capita axis, IGR share, UCDP counts, Brent, donor weights), the
  **model table** (A, B, C and the grid: estimator, outcome, treatment, controls, inference, artifact path,
  with estimator/treatment strings read from `estimation.yml`), and the **equations** with every symbol
  defined. Equations are typeset from the spec's own plain notation (`x_{s,t}` → subscript), so the spec stays
  reviewable and the page stays readable.
- **Methodology is now brief**: five sections became four — the problem, prior work, what this project does
  differently (four items), and what it does not claim. The "how it is checked" section folded into the
  data-honesty item, which still carries the verifier count. The page says where the reference material is.
- **`analysis/specs/technical.yml`** is the new declared source for the reference page: the equations, the term
  definitions and the design-variable meanings. The variable and model tables are generated, not retyped, and
  `verify_site.py` fails if a metric id, an estimator string, an equation title or a term symbol is missing
  (P-11).



**This session, in one line:** **Screen 6b — the design-level results** (`site/build.py` → `/designs/`, from
`registry/estimates`, `registry/robustness` and `registry/events`), because the three figures Stage 8 published
were reachable from **no page at all** — and building the reader for them found two defects, one of which the
published site had been serving since the day the flow went up.

- **The screen reads; it does not compute.** Each section is the artifact's own fields: the figure and its
  `layout` sentence, Design A's verdict and the check that decided it (the lead-shift p, the 24-month placebo),
  its three published rows, Design B's number with the grid's support counts and the five sign-flip levels,
  Design C's reason and next step, and the transition study's eight verdicts with the rule they were read
  against and four `not_claimed` statements. `analysis/specs/guide.yml` gained a `design_results` section, so
  every sentence on the page is declared wording or an artifact string. No new stage, no new number.
- **It is not a flow step, and that is deliberate.** It is not per-outcome, so putting it between two outcome
  screens would either break the selection carried in the URL or imply the reader's outcomes change it. It is
  linked from the estimate screen — where a card with no number already names the design's result — and from the
  Ask footer, which is the "go deeper" the spec declared and never built.
- **The transitions are shown by month, never by name.** The event artifact carries surnames in its `label`
  fields; the page prints none of them. This is the one screen where a per-president reading would be easiest to
  produce by accident, and `verify_site.py`'s surname guard now covers it like every other page.
- **The site was serving 404s for every figure on `/chart/` and `/graph/`.** Figure paths were written
  `src="assets/…"` on pages served one directory down, so the browser requested `/chart/assets/…` and got nothing
  — while the verifier stayed green, because it proved the file existed in `dist/assets/` and never that the
  markup pointed at it. Found by opening the page in a browser, not by reading it. Every `src` and `href` on
  every page is now resolved from that page's own URL; the three design figures return 200 over HTTP.
- **The robustness curve's byte count was platform-dependent, and the new check caught it.** `04_robustness.R`
  recorded `file.info()$size` — raw bytes on this Windows checkout — so it published **94,502** for a file whose
  canonical (LF) size is **93,677**. `03_estimate.R` had recorded canonical bytes since the forest plot's own
  contract was fixed; `verify_stage7.py` never checked the number, so nothing failed. The engine now uses the
  same `canonical_bytes()` rule, the vintage was regenerated in place, and a field-by-field diff of the artifact
  before and after shows **only `figure.bytes` and `generated_at` moved** — no coefficient, count or verdict.
- **Six mutations, six caught, every file restored byte-for-byte** (`.probe/break_designs.py`, gitignored): the
  curve dropped from the page, A's failed check dropped, C's next step dropped, all transition rows dropped, the
  support count stripped of its positive tally, and the forest plot's recorded size moved by one byte.
- **Two verifier defects were found while writing the check, not by reading it.** `plain()` stripped tags
  *after* resolving entities, so a literal `<` in the artifact prose (`p <= 0.05`) ate the rest of the sentence;
  and the transition regex swallowed `0.6102` plus the next row's `2007-05` once tags were removed. Both are
  fixed by making the check stricter, not looser.
- **Left standing, and recorded rather than fixed:** the forest plot's right-hand labels are clipped at the
  SVG's own edge (`B — oil to state allocations (114 national months, 2016-12 to 2026-0…`). That is a layout
  question for `03_estimate.R`, and fixing it means re-rendering Stage 6 and everything whose bytes it records —
  a separate decision, not a side effect of this page.
- **Not done:** the chat still cannot point at a panel (no `figure` answer shape, no figure chunks in the
  corpus), and the Model card and What-this-reads halves of the "go deeper" screens remain unbuilt.

**Then, same session — the cover's five empty frames, and a deploy that had never happened.** The requester asked
for photographs of all five presidents with their party flag behind them. The cover had shipped placeholders by
design (`docs/portraits.md`), so this was a licence task before it was a design task.

- **Five Commons portraits, each licence read on its own file page.** Obasanjo is public domain (Helene C.
  Stikkel); Yar'Adua and Jonathan are CC BY-SA 2.0 (World Economic Forum); Buhari and Tinubu are CC BY-SA 4.0
  (Bayo Omoboriowo; Nosa Asemota). Each is recorded twice, as `docs/portraits.md` requires: a row in
  `docs/licences.md` with the licence URL and the attribution string, and an entry in
  `site/assets/presidents/manifest.json` with the `sha256`, source, author, retrieval date and crop note.
  `scripts/build_administrations.py` was re-run rather than hand-edited, so `portrait_status` is `supplied`
  because the files exist.
- **The party backdrop is an override, and it is written down.** `docs/portraits.md` §1 excludes "campaign or
  party-branded imagery" because a portrait on an analysis is not an endorsement. The requester asked for the
  flag and accepted the override; it is recorded in `docs/decisions.md` as **P-02**, with the colours declared in
  `guide.yml` from the parties' Wikipedia infobox swatches (PDP `#006903`/white/`#F0001C`; APC
  `#87BEEB`/`#39944A`/white/`#E52B33`) rather than sampled from a logo.
- **Crop and resize only, so the bands are a matte, not a silhouette.** Every file is 600 × 800 (the frame is
  `aspect-ratio: 3 / 4`, which the procedure's 600 × 750 row contradicted — **P-03** corrects it), JPEG q85,
  EXIF stripped, 76–101 KB each, and the photograph itself is never cut out (**P-04**).
- **The manifest is now enforced rather than decorative.** None of the five invariants `docs/portraits.md` §4
  declared had ever been implemented. `tests/verify_site.py` now checks the file exists, its `sha256` matches,
  the slug names an administration marked `supplied`, exactly one `docs/licences.md` row permits redistribution,
  and the attribution text appears in the cover footer — so a swapped image fails on the hash and an unlicensed
  one fails on the register.
- **The deployed site had never existed.** `https://batestguy.github.io/causal-presidents-regime-Naija/`
  returned GitHub Pages' 404: the repository had no Pages site at all, so the `pages` job had nothing to deploy
  to. Pages is now enabled with `build_type: workflow` (C-74) — the deploy still only happens from a green chain,
  and this commit is the first one that can reach it.
- **The full chain was run after the design screen and is green end-to-end:** `scripts/verify.sh` → **`all checks
  passed`** (exit 0), including the corpus and both evals, with `verify_site.py` reporting 8 pages and
  `verify_answer_js.py` reproducing **38 of 38** measured answers field for field.

**Then, same session — the visual pass: dropdown, tenancy bands, flag, green.** Nine changes asked for in one
message; three were decisions (flag vs party strip, where the failure ratio lives, how to shade the charts) and
are answered above; the rest are here.

- **The study screen is a category dropdown plus its outcomes.** `<select id="domain-select">` filters the four
  declared domains, and all twelve checkboxes stay in the HTML, so the site verifier still sees every outcome and
  the flow still carries a selection across screens.
- **The causal graphs are full width.** `render_graph` puts the SVG above the written assumption instead of in a
  half column, on a `wide_page` that raises the flow to 1240 px; the height is capped at 68 vh so a card cannot
  become a mile long.
- **Every outcome chart now shades the tenures.** `08_comparisons.R` and `09_changepoints.R` draw a light band per
  administration with the president's name, from `dim_administration`'s half-open spans (comparisons) and
  `administrations.json` (changepoints). Both specs declare the decoration (`figures.tenure_bands`), including the
  22 % headroom reserved above the data and the legend moved outside the plot region — the first attempt put the
  names and the legend on top of each other, and the second clipped the legend at the device edge.
- **The site is green-and-white with a flag behind the presidents.** The palette is the Nigerian green
  (`#008751`) on a green-tinted paper with white cards; the cover's header is a green panel, and a large
  green-white-green `flag-band` sits behind the portrait grid at 16 % opacity. The colours are declared in
  `guide.yml` (`national_flag`, `parties`), not typed into the stylesheet.
- **The carousel is a grid.** Four portraits to a row, so the fifth — Tinubu — sits on a row of his own, as asked;
  the arrows and the auto-advance are gone, which also removes the one piece of JavaScript the cover needed.
- **The copy is shorter and the tagline changed.** "Read the assumption before the number" became "Causal models
  have assumptions. Study them before you read the numbers"; the cover's three long paragraphs became two
  sentences, and the study, compare, designs and ask intros lost their throat-clearing.
- **The failure ratio now appears once.** `2 of 36 model cards carry a published number` stays in the cover footer
  only, per the requester, and is not repeated on the way to the estimate page where the absent number is met.
- **Re-verified end to end.** `scripts/verify.sh` over the regenerated figures: **`all checks passed`** (exit 0),
  including `verify_comparisons.py` (every group mean and caption recomputed) and `verify_changepoints.py`
  (8 series refitted independently, month for month), then `verify_site.py` on the new grid, flag and dropdown.
  The three decisions that shaped this pass are recorded in `docs/decisions.md` as P-05 (grid + flag), P-06 (the
  ratio stated once) and P-07 (tenancy bands drawn in R, not overlaid).

**Then, same session — Stage 8g: describing a tenure without calling it an effect.** The requester asked for the
closest thing to an estimate *between presidents* that carries fewer assumptions. That is a **descriptive
contrast**: the difference between two tenures' mean deviation from a trend fitted without knowing who was in power.

- **Why not interrupted time series.** ITS/segmented regression is a quasi-experimental design whose coefficients
  are read as effects (Wagner 2002; Bernal 2017). Putting one on a page labelled "descriptive" is the failure this
  repository exists to prevent. The changepoint stage already owns "the series changes here"; this stage answers a
  different question — "was the series above or below its own path during this window?"
- **The method.** LOESS, degree 1, on **native observations only**, over a declared span grid of 0.5/0.75/1.0.
  Each tenure's deviation is reported as a **range across the three spans** — the range of an analyst choice, not a
  confidence interval. `analysis/specs/tenure.yml` declares the method, the windows (the base's half-open spans),
  the refusals and the forbidden fields (`p_value`, `standard_error`, `confidence_interval`, `effect`,
  `significance`).
- **The estimate between presidents.** `difference = mean deviation(a) - mean deviation(b)`, in outcome units, with
  its range across spans. Its only assumption is that the tenure-blind smoother is a fair description of the long-run
  path — no parallel trends, no ignorability, no counterfactual. 68 contrasts are published across 8 outcomes.
  The largest for conflict: **Jonathan − Yar'Adua = +202.9 fatalities** (range +106.5 to +282.0); for under-5
  mortality **Obasanjo − Yar'Adua = +3.8 per 1,000** (range +0.8 to +8.0); for growth **Jonathan − Buhari = +2.8 pp**
  (range +1.8 to +3.5).
- **Two refusals keep it honest.** Four outcomes have < 20 native points and are refused with the count (8, 8, 9, 9).
  A tenure holding < 3 native points publishes *"insufficient points"* rather than a deviation — the preview showed
  a two-year administration on an annual series has two points, and a mean of two residuals describes the smoother.
- **The verifier found three bugs before the artifact shipped.** A window boundary off by one month (Yar'Adua read
  33 points where the artifact said 32), a coverage denominator counted on a different month convention, and the
  incumbent's band running to **9999-12** because `end_date_effective` is a sentinel. All three were arithmetic, not
  judgement; `tests/verify_tenure.py` recomputes every deviation from the published trend and every contrast from
  the two deviations.
- **The surname guard was made precise, not removed.** The chart's tenure table names presidents as period labels,
  and the Ask page's autocomplete offers the project's own published questions, some of which name a president. The
  verifier now allows a surname in those two blocks only, and fails on any verdict word inside the tenure table.
- **The Ask page autocompletes to a measured question.** Typing offers the published question set, and on submit the
  field snaps to the closest match by word overlap, so the layer is only ever asked a question it was measured on.
- **The bootstrap was dropped.** A residual bootstrap on break dates was considered and abandoned: an interval on a
  date invites "the change is significant", which is the reading the descriptive stage exists to refuse. Recorded in
  `analysis/specs/changepoints.yml` so the next reader does not re-propose it.
- **Not done from the same brief:** the cover primer on causal inference and methods, the ≤100-word answer cap (a
  contract change that needs re-measurement), and the role-coloured DAG nodes.
- **Re-verified end to end and shipped.** `scripts/verify.sh` → **`all checks passed`** (exit 0) over the new stage,
  with `verify_tenure.py` recomputing every deviation from the published trend and every contrast from the two
  deviations; deployed from CI (`7cfa9a7`, `64df7f3`) and the tenure table renders on the live chart page.

**Statistical work still not run, in the order it could move a number.** (No declared specification is left
unfitted — all 12 Stage 6 specifications and Design C are fitted. Each row below is a new estimand whose input
is missing.)

| Estimand | Blocked on | Where it is recorded |
|---|---|---|
| Per-capita dose axis | the population-denominator decision (**X-09**); `d1_faac_per_capita` is 0 of 12,358 rows | `robustness.json → unbuilt_axes` |
| D2, FAAC as a share of state revenue | NBS state IGR parsed (same parser family as FAAC) | same |
| Monthly CPI for the 2023 window | monthly NBS CPI is a parser; annual is landed | `limitations.md` §13 |
| Monthly security after 2024-12 | the UCDP archive ends there; ACLED is not wired | same |
| Monthly sub-national health | DHIS2 credentials were never obtained | same |
| RAGAS with the real library | a judge model; the four definitions are implemented in house and labelled `library: false` | `answer_quality_eval.json` |
| An identified synthetic counterfactual | a donor pool that cannot interpolate an 8-to-24-year pre-period, or a different fit window | `registry/design_c/` (measured, not pending) |


**Previous session, in one line:** the **outcome panels** — `analysis/specs/series_figures.yml`,
`analysis/R/07_series_figures.R`, `registry/series/2026-10-18/` (12 SVGs + `index.json`) and
`tests/verify_series_figures.py` — so that a card's reason is shown beside the series it is about, and the
series is the reason: **764 of the 3,008 outcome-months are observations; 1,826 are interpolated; 1,418 have
no observation at all.**

- **The figure is a contract, not a decoration.** Observed months are dots, interpolated months are dotted
  segments (the imputation rule made visible), and a run of three or more unobserved months — plus every
  trailing run — is shaded and labelled "no observation". A reader can now see that `u5mr` is 26 annual points
  across 275 interpolated months, that `skilled_birth` has 8 points in 27 years, and that `ner_primary` and
  `primary_completion` stop in 2010 and cannot see any APC tenure.
- **Nothing is typed.** Counts, window, first/last observation, unit, native frequency, the Stage 3 status and
  the definition breaks are read from the base (`fact_metric`, `fact_observation_native`, `dim_metric`,
  `dim_definition_break`); the outcome's identity comes from `analysis/specs/outcomes.yml`. The caption is
  assembled from those fields, so it cannot disagree with the panel.
- **The verifier re-derives all of it from DuckDB** — every count, the native observation count (excluding the
  World Bank's valueless 2025 row, which would have overstated coverage by one month per year), the breaks,
  the byte count, and the required strings inside the rendered SVG. Seven mutations were applied and caught:
  a count moved by one, a caption's count, a byte count, a flipped Stage 3 status, a moved window, a dropped
  definition break, and a label cut out of the SVG; each file restored byte-for-byte.
- **The panel is on every card and the app verifier checks it.** `app/registry_data.py` loads the series index
  under the same vintage contract as the cards and refuses a family that is missing or from another vintage;
  the card tab renders the SVG and the artifact's caption. Removing the heading, or replacing the caption with
  a literal, fails `tests/verify_app.py` on all 36 cards.
- **One inconsistency surfaced and was left standing.** `outcomes.yml` still marks `literacy_youth`
  `declared_gap` (probe date 2026-10-10) while the base now carries 7 observations to 2024. The panel draws
  what the base holds and the caption says so; the registry's `coverage_status` is a separate claim and
  changing it would regenerate all 36 cards, so it is recorded here as an open question rather than edited.
- **The chain's corpus step needed the cached model, and that is recorded rather than glossed.**
  `scripts/build_rag_corpus.py --embed` failed on a Hugging Face lookup for
  `sentence-transformers/multi-qa-MiniLM-L6-cos-v1` although the snapshot is cached; `HF_HUB_OFFLINE=1` loads
  it (384 dims) and every downstream step passes. The chain was not declared green as one uninterrupted run:
  stages 0–8d ran through `verify.sh`, then 8c–9 and the sixteen verifiers were run separately against the
  rebuilt corpus. Retrieval is unchanged (recall@5 0.944, coverage 0.418, MRR 0.715).
- **Not done:** the figure and its caption are on the card only — the chat layer still cannot point at a
  panel (no `figure` answer shape, no figure chunks in the corpus), and the three design-level figures
  (forest plot, specification curve, event study) still have no tab.

**Previous session, late, in one line:** `ragas: not_run` is closed — the four RAGAS metric definitions are
**implemented here** (the package is not installed), judged by `gemini-3.5-flash-lite`, and published as
faithfulness **1.000**, answer relevancy **0.800**, context precision **0.990**, context recall **0.863** over
the 16 answered questions.

- **The library is not run, and the artifact says so in its own fields.** `ragas` is installed in none of the
  machine's seven environments, and installing it would add a dependency tree to a project whose answering
  path deliberately has none. `scripts/eval_answer_quality.py` implements the same four definitions, records
  `library: false`, the judge model, the prompt's sha256, and the sentence that matters: **these scores are
  not comparable to a `ragas` library run**.
- **One judge call per question, because the free tier is the binding constraint.** `gemini-2.5-flash` allows
  20 requests per window on this key, which a per-statement design exhausts on the second question; the
  judgement is one structured call per question plus one batched embedding call (32–36 calls for 16 questions
  instead of ~200). That is recorded as a working-paper difference, not hidden.
- **The measurement is honest about itself.** Faithfulness is 1.000 *by construction* — the answer is a
  selection of quoted paragraphs — so it confirms the contract, not retrieval. Context recall 0.863 is the
  number with content: `q04_oil_to_states` and `q05_design_b_robust` score 0.500, i.e. the right document was
  quoted without the paragraph that carries the reference's claim.
- **The judge is noisy and that is published, not averaged away.** Five runs of the same measurement gave
  faithfulness 0.964–1.000, answer relevancy 0.800–0.834, context precision 0.885–1.000 and context recall
  0.801–0.863. A lite model at temperature 0 is not deterministic; the next step on this metric is a stronger
  judge or several runs published as a range.
- **Two verifier catches, both real.** `tests/verify_answer_quality.py` (new, in the chain) found an
  unparseable judge reply that had been written through as null scores — the script now retries, and refuses
  to record a judgement that did not happen, leaving the run `partial` instead — and the schema found a cosine
  of 1.0000000000000002, which is correct arithmetic and an invalid metric value, now clamped and rounded.
- **The artifact fingerprints content, not files.** The chain rewrites the corpus and eval artifacts on every
  run, changing their bytes and not their content, so `inputs` carries content hashes (chunk text, answered
  rows, questions + reference answers). Without that, the measurement would have gone stale every time the
  chain verified it.
- **What was not done:** no dependency was installed and no key is committed — the run reads
  `GOOGLE_API_KEY` from the environment, and the verifier fails if a key-shaped string appears in the
  artifact.

**This session, in one line:** the **verification chain was red and is now green** — `tests/verify_rag.py`
failed with 41 problems at the end of the chat-tab session, and the header above had said zero failures —
and the corpus was extended with the glossary and the licence register, **measured before it was kept**.

- **The chain was red, and two of the three causes were the verifier's own.** The spec's hash had moved
  since the corpus was built (the `card_estimate` family was added after it), `family_to_type` had no entry
  for that family, and the budget check applied the 950-character default to every family while the spec
  declares `max_chars_by_family: {card_estimate: 1700}` — **36 of the 41 failures were that third defect**, a
  verifier reporting the family's declared design as a violation. It now reads the declared budget, maps the
  family, and asserts one `card_estimate` parent per card. A verifier that fails for its own reason is how
  the real drift beside it stays unread.
- **The corpus was rebuilt with `--embed`**, so the spec hash, the chunks and the vectors describe the same
  build; `docs/rag.md` still carried 441 chunks and the pre-`card_estimate` coverage and MRR, and was moved
  onto the artifact.
- **Then the corpus grew, and the growth was measured before it was kept.** `docs/glossary.md` and
  `docs/licences.md` were added — 5 chunks — because "what does this word mean" and "what may be
  republished" had no chunk to quote. Every retrieval metric is unchanged: recall@5 **0.944**, gold coverage
  **0.418**, MRR **0.715**. `docs/decisions.md` was tried and **rejected on the numbers**: at ~210 chunks it
  held recall at 0.944 but moved MRR to 0.687 and coverage to 0.379 — the passages stayed in the top five and
  sank within it. The rejection is recorded in the spec, where the next rebuild reads it.
- **The gain is partial, and the page says so.** "What does G02 mean?" now quotes the glossary's refusal
  table; "can I republish the ACLED rows?" still resolves to the coverage table in `docs/limitations.md`,
  because the fact path selects the passage carrying the most of the question's words and a licence row is
  short. Content was added; selection was not fixed, and `docs/rag.md` §6 states both.
- **Every dependent artifact was re-measured on the new corpus** rather than left describing the old one:
  `eval_rag`, `eval_intent` (it records the corpus hash) and `eval_answer` — the answer rate is unchanged at
  **36 of 38 (0.947)**, 16 of 16 published and 20 of 22 held out. `scripts/validate_artifacts.py` caught the
  two stale dependents in order: an `intent_eval.json` describing a different corpus, then an
  `answer_eval.json` measured against a different intent artifact.
- **Current numbers:** 482 chunks from 53 attributed sources at vintage 2026-10-18, three of the four
  retrieval gates still as they were — recall@5 0.944 met; refusal-with-reason 0.5 and out-of-scope 0.25
  still failing and still published, with the intent gate in front of them.

**This session, in one line:** the **chat tab** (`app/streamlit_app.py`'s fourth tab, on `app/answer_layer.py`
and `app/intent_gate.py`) — the first surface a reader can ask a question of — and the **three-shape answer
contract** that made it worth building: the layer now answers **36 of the 38 measured questions (0.947)**
because 34 of the 36 cards carry a *reason* rather than a number, and a contract that could carry nothing but
an interval was refusing for the wrong reason.

- **The contract got a shape, and the refusals stopped being wrong.** The one-shape contract required an
  interval, an identifying assumption and what the design cannot rule out on *every* answer, so a question
  about one of the 34 cards that carries a reason — "what did the published estimate find for under-5
  mortality under Design A?" — was answered *"I don't have a model for that"*, which is false: the card says
  exactly why there is no number. The contract now has three shapes (**estimate**, **no_estimate**,
  **fact**), each with its own required parts and its own forbidden ones, and the post-check is unchanged:
  a missing part still replaces the whole response with the refusal template. The rate moved from **0.158**
  to **0.947** because the contract stopped refusing for the wrong reason — not because the check was
  loosened, and the verifier recomputes every part from the answers themselves.
- **The tab is the same layer, and the verifier asks it questions.** `tests/verify_app.py` now drives the
  real `st.chat_input` with the four questions the tab offers and compares what comes back with
  `intent_eval.json` and `answer_eval.json`: the citation, the needles and the plain reading must all be
  there. The tab reproduces the measurement; it is not a second opinion on it. A break-test — dropping the
  plain reading from the rendered answer — turns the verifier red with five problems, so the check is not
  vacuous.
- **A refusal is an argument with a source.** A refused question shows the rule that refused it (`G02`…`G09`),
  that rule's plain-English meaning out of `docs/glossary.md`, the passage that says why it cannot be
  answered, and that passage's citation. `docs/glossary.md` now carries a line for every refusal code the
  contract declares, and the verifier fails if a code has no meaning — or if the glossary explains a code the
  contract does not declare.
- **The deterministic path is the one that can be checked.** The answer is a *selection of committed
  paragraphs* plus a citation, so every sentence can be re-derived from the artifact and every number
  checked against its citation. A generated answer could only be checked by a judge model, which is the
  RAGAS measurement this project already publishes as `not_run` for want of a key. The tab calls no model and
  needs no key.
- **The example questions are the project's own.** The app reads their text from the published evaluation
  set and types only their ids, so an example cannot drift from the question the measurement was run on. The
  verifier fails if an offered example is not a published, measured question.
- **The held-out set does not leak.** The held-out questions are the project's own measurement set, so a
  held-out question reaching the page would mean the measurement could no longer be scored. The verifier
  fails if one appears anywhere on the page.
- **What this does not do:** it does not paraphrase. BM25 is lexical, so a question phrased in words the
  corpus does not use is declined with `L02` rather than approximated — 2 of the 38 measured questions were,
  and both are published as declines rather than smoothed over. The embedding retriever's own refusal gates
  still fail (0.5 and 0.25 — `docs/rag.md`), which is why the tab uses the rule-based gate: similarity alone
  cannot refuse "what will inflation be in 2030?".

**Previous session, in one line:** the **intent gate** (`app/intent_gate.py`, a held-out set frozen after the
rules, `scripts/eval_intent.py`, `tests/verify_intent.py`, `docs/intent.md`) — which turns the corpus's two
failed refusal gates (0.25 out-of-scope, 0.5 reason-cited) into **0.944 and 1.000 on questions the rules never
saw** — then the **A16 closure** that cost a new held-out set and a second freeze, and the **answer layer**
(`app/answer_layer.py`, `docs/answer.md`) that enforces the R-04 post-check and measures **what the contract
actually permits: 5 of 38 answerable questions**.

**The gate exists because the retriever was answering the wrong question.** Stage 8c measured the failure:
a 2030 forecast about a covered outcome embeds closer to the corpus than some genuine questions do, so any
similarity threshold that refused it would refuse real questions with it. "What is similar to this text?"
and "can this corpus answer this question at all?" are different questions, and the second has to be asked
before retrieval, from the question's own words, by rules the project declares and can defend.

- **The decision is total and deterministic.** Eight rules, unique priorities, first match decides, and
  **no match means `answerable`** — the gate may add a refusal and may never remove one. A refusal must
  resolve its route to exactly one existing chunk; an unresolved route falls back to `answerable`, because a
  refusal without a citation is the failure this project is built to avoid (R-04 applied to the gate itself).
  The year bounds are read from the artifacts — the quality report's study window and the registry's vintage —
  so no number is typed into the rules.
- **The rules were frozen before the questions existed, and the verifier checks that against git.** The v1
  held-out set was written after commit `30afc23`; `tests/verify_intent.py` reads the rule spec **as of that
  commit** and fails if the file on disk differs, and fails if the eval spec existed at the freeze. Changing
  a rule therefore requires a new held-out set and a new freeze — which is the point, and which is exactly
  what the A16 closure cost.
- **The held-out set is mechanical where it can be.** 32 of the 49 questions are templates filled from the
  artifacts (one per card, six forecasts, three population questions, three past-year questions, four tenure
  comparisons, four Design C questions), so their expected intent is derived rather than opined. The other
  17 are authored hard cases — answerable questions carrying a trigger word in a frame the rule must not fire
  on ("which check should I read", "what does the specification predict") — plus one probe.
- **The numbers, on v2 questions the rules never saw:** intent accuracy **0.980**, out-of-scope refusal
  **0.947**, answerable kept **1.000**, refusal route resolved **1.000**, refusal reason cited **1.000**.
  Every mechanical and authored family is exact; the one miss is the probe KG01 declares. On the 22 published
  questions — the set the rules were written against, so not a generalisation estimate — out-of-scope refusal
  goes **0.25 → 1.000** and reason-citation **0.5 → 1.000**, while answerable recall@5 stays **1.000**: the
  gate changes what is refused, not what is retrieved.
- **The one v1 miss was closed the expensive way, on purpose.** A16 — "Is the population denominator for the
  per-capita axis built?" — is answerable, and v1's G03 refused it on the word "population". The rules were
  **not** edited then (the measurement had been made); instead G03 got a denominator-frame exclusion, was
  **frozen at `8b9ba3b` before any new question existed**, and a new held-out set was written from a new
  path. The seen denominator/population questions became a declared **regression block — 6 of 6 correct**,
  reported beside the held-out numbers and never inside them (S9-08, `docs/intent.md` §4).
- **KG01 was closed by committing its inputs, not by narrowing the claim.** P02 ("How did Brazil's
  under-5 mortality compare with Nigeria's?") was the v2 miss: a country question, and no artifact the rule
  could read. The donor panel's 99 members and the ISO 3166-1 names are now committed registry artifacts and
  G09 refuses a question naming any country other than Nigeria, frozen at `3dcb555` **before** the v3 set
  existed. On the 49 v3 held-out questions: intent accuracy **0.980**, out-of-scope refusal **0.947**,
  answerable kept **1.000**, route resolved **1.000**, reason cited **1.000**, and the 23 seen cases at
  **1.000**. The one miss is P03, a country reached only through a capital city — the lexical remainder the
  gate declares (KG03), measured rather than assumed.
- **One metric is published with its reading rather than deleted.** `route_matches_gold` is 0.625 — 20 of 32 —
  and all 12 misses are the card questions, where an answerable decision returns no route by design. Read
  against the 20 questions that carry a route, the gate cites the expected chunk 20 of 20.
- **The answer layer enforces R-04 on its own output, and the contract now has three shapes.** `app/answer_layer.py`
  gates, retrieves lexically (BM25 — no model at request time), assembles extractively and then checks the
  answer against the requirements of its shape. The one-shape contract required an interval on every answer,
  so a question about one of the 34 cards that carries a *reason* was refused for the wrong reason; the
  contract now has **estimate**, **no_estimate** and **fact** shapes, and the rate moved from **0.158** to
  **0.947** — 16 of the 16 published answerable questions (1.000) and 20 of the 22 held-out ones (0.909),
  2 declined, none answered around a refusal. The post-check is unchanged: a missing part still replaces the
  whole response with the refusal template, and the verifier recomputes every part from the answers.
- **Every answer now has a plain-language reading, built from its own numbers.** `plain` on the artifact (and
  on the `Answer`) gives the direction of the coefficient, whether the interval includes zero, the sample,
  the assumption in one sentence, the caveats as bullets, and the meanings of the technical words the answer
  actually uses — each definition quoted from `docs/glossary.md`, each figure copied out of the cited
  passage. The verifier recomputes the sign, bounds, zero-crossing and sample from the answer's own text and
  fails if the reading disagrees, so the plain view cannot drift from the contract answer it summarises.
- **No LLM key is needed, and the verifier proves it.** Rules, BM25, paragraph selection, the R-04 check and
  the glossary are all local. `tests/verify_answer.py` runs the layer in a child process with every
  key-shaped environment variable removed and requires an answer with a plain reading. RAGAS stays `not_run`
  because it needs a judge model — that is the *measurement* that needs a key, not the system that answers.
- **Four lending guards keep a coefficient off questions it does not answer.** A question naming an outcome
  may only be answered from a passage about that outcome; the estimate paragraph itself must name that
  outcome (a design-level result lists several intervals in one passage); a question naming a design must be
  answered from that design; and the scope chunk is never borrowed from, because it contains the words
  "identifying assumption" only because the contract is described there. Without these, a design-level
  result answered a fourth outcome with three others' numbers, and a fatalities question got an incidents
  coefficient — the same failure the app's results tab prevents, one layer down.
- **The chain measures both on every run.** `scripts/verify.sh` re-runs `scripts/eval_intent.py` and
  `scripts/eval_answer.py` (no model, no key, no network) and then `tests/verify_intent.py` and
  `tests/verify_answer.py`, which re-derive the questions, re-apply the rules with a second implementation,
  check the freeze against git, recompute every metric, require every quoted sentence and number to appear
  in its citation, and require `docs/intent.md`/`docs/answer.md` to quote the artifacts' own numbers.
- **What this does not do:** it does not build the chat tab — `docs/app.md` §3 and `PHASES.md` Stage 9 record
  it as unbuilt, and the reason is now measured rather than assumed: a surface built on this layer would
  refuse four questions in five.

**Previous session, in one line:** the **read-only app** — `app/streamlit_app.py`, a `docs/app.md` that states
the ratio it leads with, and `tests/verify_app.py`, which renders **all 36 cards** through Streamlit's own test
harness and compares the page against the card JSON — followed by the framework question itself, reopened
and **settled on the record** rather than left implicit.

**"Must it be Streamlit?" — asked and answered, in the decision log (UI-01…UI-08).** It was chosen, not forced,
so the reason is now written down where a reversal would be visible. **UI-01: Streamlit**, because `AppTest`
renders the real app **without a browser**, which is what makes the 36-card contract check a step in
`verify.sh` and CI instead of a manual ritual — Dash, Shiny and React all need a Selenium/Playwright driver
for the same evidence, and neither is installed here. **UI-05: the costs are accepted explicitly** — no
per-card URL (`st.query_params` is the fix, not done), coarse layout, a static SVG rather than a clickable
graph. **UI-06: the alternatives are recorded with the condition that would revive each** — static export if
the deliverable becomes "publish a page", Dash if the interactive graph becomes the product, React if someone
else maintains it as one. What makes the decision cheap to reverse is that `app/registry_data.py` is
framework-free: the loader and the assertions survive a port unchanged.

**What this session built, and the two checks that had to be sharpened before they meant anything.**

- **The page leads with the ratio, not a coefficient:** *2 of 36 model cards carry a published number; the rest
  say why not.* A reader who opens one card otherwise cannot tell whether the project estimated two things or
  failed to estimate thirty-four — and the four reason codes (12 `outcome_series_absent`, 10
  `no_specification_declared`, 9 `design_result_is_channel_level`, 3 `design_not_run`) are listed with their
  counts on the third tab.
- **Left column is the argument, right column is the number.** Assumption → backdoor adjustment set resolved
  from the card's own nodes to `label (node_id)` → the node assumed absent → cannot-rule-out → the Stage 5
  pre-check, including its blocker. Only then the estimate, its interval, its verdict *and the check that
  decided the verdict*, the full specification in an expander, one Stage 7 grid line, and the SVG graph.
- **Design-level results get their own tab, and the verifier keeps them there.** B's channel-level number and
  C's non-run are shown once, with their specifications, support counts and declared next step. The check
  only became real after it was sharpened: pointing the *results* tab at a different design while each B card
  renders is what proves the number is not being lent to a card — before that, a B coefficient found on the
  page could have come from the results tab, where it belongs.
- **Two verifier misses found by breaking it, not by reading it.** (1) The failed-check needle was satisfied
  by the results tab repeating Design A's verdict sentence, so a card could lose that sentence and still
  pass; the needle now carries the `Failed check:` prefix and the results tab is pointed elsewhere. (2) The
  first harness addressed widgets by position — and tabs register their widgets on every run, so index 0 was
  the results tab's radio, and 24 of the 36 cards were being checked against a page showing a different
  design. Widgets now carry keys, and the loop drives them by key.
- **Seven break-tests, all caught, files restored byte-for-byte** (`.probe/break_app.py`, gitignored): a
  typed coefficient, a dropped adjustment set, a reason code without its detail, a verdict without its
  failed check, a `duckdb` import, a drifted ratio in `docs/app.md`, and a drifted count in its reason
  table — the last added because the table's four numbers are prose too, and prose that is not derived from
  the index is prose that drifts.
- **The app was not shipped with a chat tab.** Out-of-scope refusal measures 0.25, so a 2030 forecast about a
  covered outcome is not refused by similarity alone; building the tab now would ship the failure the corpus
  exists to prevent. `docs/app.md` §3 says so where a reader will find it, and the eval set is ready to judge
  the intent gate when it exists.
- **Environment:** `streamlit==1.60.0` added to `requirements.txt` (the verifier renders the app, so the
  verified environment has to carry the framework) and `app/*.py` added to the compile gate in `verify.sh` and
  CI.

**Two sessions back, in one line:** the **RAG corpus, its eval set and the measured retrieval numbers** — 441
chunks from 51 attributed sources, embedding recall@5 **0.944** against a BM25 baseline's 0.833, and **two of
four refusal gates failing, published rather than tuned away**.

**What this session changed, and the two defects it found before they shipped.**

- **The corpus is generated, never authored.** `scripts/build_rag_corpus.py` serialises the cards, the three
  design results, the seeds and the narrative into chunks and records the sha256 of all 51 sources; a source
  edited without a rebuild fails `tests/verify_rag.py`. A card is one *document*, split into parts at the
  embedding budget, and every part opens with its parent and part number.
- **The model the base spec named would have silently truncated every chunk.** `all-MiniLM-L6-v2` caps at
  **256 tokens** — about 1,000 characters — so a 1,800-character chunk would have been indexed with its tail
  dropped and nothing in the artifact would have said so. The corpus uses `multi-qa-MiniLM-L6-cos-v1` (512
  tokens, same 384 dims), and `--embed` counts the model's own tokens and **fails the build** rather than
  truncating. It caught a 935-token table chunk on the first run; the budget is now 950 characters, chosen
  from the measured 0.53 tokens/character of the densest text.
- **Two refusal rules, not one.** The first harness applied a single similarity threshold to both kinds of
  refusal and reported 0 of 2 reason-bearing questions as "refused" while the reason chunk ranked **first** —
  which is what a good refusal looks like. The rules are now separate: reason-bearing refusals are measured
  by whether the reason chunk is retrieved and cited, and only out-of-scope questions use the threshold.
- **The numbers.** Embedding recall@5 **0.944**, gold coverage 0.432, MRR 0.724; BM25 0.833 / 0.364 / 0.676.
  The model earns its place. **Refusal-with-reason recall 0.5** — one compound question ("did Buhari's tenure
  cause the fall in under-5 mortality") retrieves the tenure-limitations passage instead of the Design C one.
  **Out-of-scope refusal 0.25** — a 2030 forecast and a policy recommendation embed closer to the corpus
  than some genuine questions do, so similarity alone cannot refuse an on-topic out-of-scope question; the
  app needs an intent gate. Both are published as misses; editing the questions until they passed would have
  measured the edit.
- **RAGAS is declared `not_run`, not faked.** It needs a generation step and a judge model; there is no LLM
  key, so the artifact says so and the eval set already carries the `ground_truth` column a RAGAS run needs.
- **A destructive path was closed.** A plain (non-`--embed`) rebuild on a machine without torch would have
  overwritten a corpus that had vectors with one that did not, leaving the published retrieval numbers
  describing a corpus nobody could reproduce. The builder now refuses that without `--allow-embedding-drop`,
  and the harness refuses to overwrite embedding metrics with a BM25-only run.
- **`docs/rag.md` is checked as claims**, not prose: the verifier requires the page to quote the chunk count,
  source count, eval-set size, both recalls, coverage, MRR, the refusal numbers and the threshold — all
  derived from the artifact, so the page cannot drift from the corpus the way two documents had by
  2026-10-20.
- **Break-tested before publishing.** Six mutations — a source edited without a rebuild, a chunk edited after
  it was built, a published recall moved to 0.999, a gate's `met` flipped, a chunk dropped, and the vintage
  changed — each failed `tests/verify_rag.py`, and each file was restored byte-for-byte
  (`.probe/break_rag.py`, gitignored; the mutations are described here so the record survives it).
- **The push was checked on a clone of the pushed commit**, not only in the working tree: the LF checkout
  reproduces all 51 source hashes, every chunk hash and the forest plot's recorded size. Those were the last
  two contracts that only held on this Windows checkout, and both are now canonical-byte based.

**This session, in one line:** the **forest plot** — the last figure Stage 8 asked for, with the checks
that make it an artifact rather than a picture — and **the limitations narrative**, written before the
findings it constrains and wired into three verifiers as derived claims, which immediately caught two
stale prose facts (the events cell split and the memo's old observed share).

**This session, in one line:** two things were built — **the transition event study** (`docs/events.md`:
did conflict move after each swearing-in?) and **a widened Design C donor pool** (`docs/design-memo.md` §4:
13 → 99 candidates, which took the design from `infeasible` to passing its pre-fit gate on `u5mr`). Both
were declared before they were fitted, both are independently verified, and both changed a published
verdict — which is why the whole chain was re-run at the new vintage rather than left describing the old
one.

**One-line status:** specification complete; ingestion working and provenance-verified on **five**
sources — **238 retrievals at the newest vintage of each source** (174 FAAC documents, 22 World Bank
national series, 40 donor requests, Brent, UCDP GED) — the newest being **UCDP GED**, whose bulk archive
turned out to be keyless (C-45), so the state-attributed security outcome exists. **Stage 6 has published
its first estimates** (`docs/estimates.md`, `registry/estimates/2026-10-18/`): the fiscal transmission
channel is estimated (**a 10 % Brent move reaches the states as ~5 % more money two to three months
later**, C-48), and the state dose-response question is **estimated but not identified** (C-47) — with the
numbers and the failing check both on the record. Ingestion, plus the older status: the FAAC monthly
disbursement workbook — **the fiscal dose is landed and gated** (174 documents, 114 months × 36 states,
2016-12 → 2026-06; 37 series through the Stage 3 gates with the result travelling on the panel); the
causal-graph (DAG) assumption layer is built — 36 graphs (12 outcomes × 3 identification designs); Stage
3's five quality gates run over all **672** landed series (357 `ok`, 313 `flagged`, 2 `empty` — the FAAC
dose, the UCDP scopes and the monthly prices are flagged on movements the whole panel shares, and the two
empty series are Eritrea's and Somalia's CPI, which the source has no data for); Stage 4's analytical base
exists — one monthly table, **8,350 rows (25 metrics × 334 months, 1999-01 → 2026-10)**, held by 136 data
tests; and **Stage 5 has decided what the data can support before anything is estimated**. Every one of
the **36 (outcome × design) cards carries a pre-check verdict, and one passes** — `u5mr` under Design C —
with 14 fail, 9 degraded and 12 not attempted, **re-run at vintage 2026-10-18** after the donor pool was
widened. The totals moved on both later re-runs while the reasons moved on all of them: Family A is still
dropped, now because its dose is absent **on the per-capita axis the estimand is written on** (the nominal
dose is landed and gated) rather than for want of an outcome; Family B is degraded (annual grain, FAAC
present as data but absent from the catalogue, a 38–99 SD detectable effect); Family C is no longer
infeasible — it is a `candidate`, and `u5mr` passes 3 of its 4 runnable windows against a 99-candidate pool. **No
credential gates anything now** — FRED's key is set, UCDP's archive is keyless, and ACLED is simply not
wired. The recurring constraint is the one Stage 4 measured: **the monthly spine is only 16.2 % observed**,
and on the native grain the study is ~26 annual observations.


**Last action (2026-10-18, fifth session): Stage 8 — the registry. The app's data contract exists, and it
carries two numbers, not twelve.**

Stage 9 has to be buildable without opening R (PHASES.md Stage 8), so every number the app can show has to be
on a card, beside the assumption it rests on, with the artifact it was copied from named. Stage 6 published
12 specifications and the registry has 36 cards — and the two do not line up:

- **2 cards carry a published number, 34 say why not**, and the ratio is enforced rather than reported. Both
  Design A cards that can carry one do (fatalities +0.4793, incidents +0.5460, each with its interval, its
  `estimated_not_identified` verdict and the check that decided it); the third Design A specification lives
  on an outcome with no card (`fatalities_civilians` is a UCDP item inside the `fatalities` outcome) and is
  carried on the index as a declared gap rather than dropped (C-55).
- **No Design B card carries a number, and that is the point of the layer.** Stage 6's nine B specifications
  measure the **national FAAC channel**; on every B card FAAC is a *mediator* node, not the outcome. The
  result is published once, on the index, with `result_is_card_level: false` — showing it nine times would
  have been the most misleading thing this layer could do.
- **Every card with no number names a reason from a closed set** — `outcome_series_absent` (12),
  `no_specification_declared` (10), `design_result_is_channel_level` (9), `design_not_run` (3) — so the
  absence of an estimate is never silent, and the verifier recomputes which reason each card should carry.
- **The index no longer claims the registry holds no estimates.** Its `layer` string said exactly that until
  this stage; the app would have read the strongest claim in the repository and been wrong.
- **The engine found the omission before publication.** The first assembly wrote 2 of 3 Design A numbers and
  reported success, because the declared expectation counted *published specifications* rather than *cards*.
  The count that matters is now declared separately and checked in both directions (S8-02, C-55).

**Current action (2026-10-20, seventh session): the forest plot, and the stale figure it caught on the way in.**

The figure Stage 8 still owed. Declared in `analysis/specs/estimation.yml`, rendered by
`analysis/R/03_estimate.R` from the artifact's own `specifications` rows — nothing is typed and no estimate
is recomputed for the picture, so the figure cannot disagree with the table beside it.

- **Two panels, not one axis.** Design A's coefficient is a state-month elasticity and Design B's is a
  national cumulative response at a horizon. Both are log-points and a shared axis would invite a
  comparison the artifact never makes, so each panel takes its x-limits from its own rows.
- **The decisive check is drawn hollow beside each estimate** — Design A's 24-month mis-timed dose
  (+0.302, nearly the size of the published +0.479) and Design B's 6-month lead placebo (+0.095 against a
  peak of +0.518). A forest plot of estimates alone would show a number the artifact says is *not
  identified* without showing the number that decided it. Design B's declared peak band (h = 2–4) is
  shaded on the panel rather than described in a caption.
- **`svglite`, not the base `svg()` device Stage 8b's panels use.** Cairo converts text to glyph outlines:
  the file renders identically and contains no searchable label, so a row that never got drawn could not be
  detected. The spec requires every published specification's label as text, and the verifier asserts it —
  all 12 labels plus the recomputed verdict string.
- **The artifact records the figure's byte count**, and `tests/verify_stage6.py` compares it to the file on
  disk: a figure one re-fit behind fails instead of being noticed by a reader. `scripts/validate_artifacts.py`
  now carries the same invariant (path, presence, real SVG, recorded bytes vs disk, a figure for zero
  specifications), which is the cheap cross-artifact check the Stage 7 curve already had.
- **The re-run was necessary, not cosmetic.** The working copy's `estimates.json` had been rewritten by a
  probe in a different serialisation and carried **no figure block**, while `report.md` beside it carried a
  fresh timestamp — the artifact and its narrative one edit apart. `scripts/verify.sh` re-ran the engine at
  2026-10-20T03:14 and the artifact now carries the block; the new contract check names this failure rather
  than trusting that the two files were written by the same run.
- **Break-tested, and restored byte-for-byte each time.** A label cut out of the SVG, a byte count moved by
  one, a wrong figure path — all three caught by the contract test; a dropped row label, a stale byte count,
  a figure with no text elements — all caught by the verifier (`.probe/break_forest.py`,
  `.probe/break_artifact_figure.py`, gitignored; the mutations they apply are described here so the record
  survives them).
- **`docs/estimates.md` retargeted to the 2026-10-18 artifacts** after checking that all 12 specifications'
  coefficients are identical across the two vintages — the pointer had still been to 2026-10-17, and the
  figure's path is now in the header paragraph.

**Then, same session — the limitations, written before the findings, and checked as claims.**

Base spec §19 asks for the limitations to be drafted before the findings and to outrun them in length.
`docs/limitations.md` is that page: 14 sections, every count traced to an artifact, and the findings
reduced to a single short section at the end. It is deliberately longer than `docs/estimates.md`.

- **What it says, in order:** the tenure question is arithmetically unanswerable (22–23 annual rows per
  outcome, Tier-3 MDE 35–99 residual SDs); the spine is **1,349 of 8,350 rows observed (16.2 %)** and three
  frequency gaps are declared; coverage limits node by node (FAAC begins 2016-12, `dose_status` observed on
  4,104 of 12,358 state-months, per-capita **0 rows**, UCDP ends 2024-12, ACLED unwired, education series
  stop in 2010, no monthly NGN/USD); **313 of 672 series flagged** and 8 definition breaks; Design A
  published as `estimated_not_identified` with an interval that crosses zero on its own (+0.4793,
  [−0.1132, +1.0718], p = 0.113), a 24-month placebo at +0.3021 and 8 of 60 mis-timed doses at least as
  large (p = **0.133**); Design B's channel with only h = 2 and h = 3 excluding zero and a timing bound of
  **p = 0.0625**; Design C as permission, not result; the inference floors; the **45 positive / 36
  negative** grid result and the 24-of-24 sign survival for B; reproduction limits including the expired
  OAGF certificate and R-less CI.
- **The claims are derived, not typed.** `tests/verify_registry.py` now computes its needles from the
  estimates and robustness artifacts (support counts, the published coefficient, the lead-shift p and its
  8-of-60 count, the 34 cards carrying a reason); `tests/verify_events.py` derives the cell-status counts
  from the verdicts it just re-derived; `tests/verify_stage5.py` derives the observed share from the base
  and requires the memo to quote it. A literal typed into a verifier only catches a document that
  changed — deriving it catches an artifact moving under a document that did not, which is the failure
  this repository has actually had (C-44, C-49).
- **It found two drifts immediately, both in prose that every verifier had passed:** `docs/events.md`
  claimed **four** cells fail the pre-trend where the artifact has **three** failing, **two** that cannot be
  checked (Yar'Adua, 100 of the required 120 months) and one showing no shift; and `docs/design-memo.md`
  still described the spine as **10.1 % observed (775 of 7,682)** from the pre-FAAC base. Both corrected
  here, and both are now registered so the next drift fails rather than being re-read.
- **Break-tested.** Five mutations — the events count, Design A's split, the lead-shift p, the Stage 7
  count and the memo's grain — each failed the verifier that owns the claim, each restored byte-for-byte
  (`.probe/break_narrative.py`, gitignored).

**Previous action (2026-10-18, sixth session): comparing tenures, and the donor pool that unblocked Design C.**

Two builds, both declared before anything was fitted, and both because the previous session's write-ups ended
with a stated next step rather than a silent gap.

- **Stage 8b — the transition event study** (`analysis/specs/events.yml`, `analysis/R/06_events.R`,
  `registry/schema/events.schema.json`, `tests/verify_events.py`, `docs/events.md`). The tenure question needs
a counterfactual and has none; its **timing** half is answerable on the one monthly outcome. Four in-window
transitions, 96 pre-months each, post windows of 12 and 24 months truncated at the successor, inference by
**exhaustive placebo assignment** over 58 eligible months — enumerated, not sampled, so there is no seed.
**2 of 8 event-outcome cells survive both the placebo and the pre-trend check** (2010 incidents +391 %,
2023 fatalities +77 %, each p = 0.017, the floor at 58 placebo months); four fail the pre-trend placebo,
including the largest shift in the series (2015 fatalities −67 %); one event cannot be checked at all and
says so. **No party comparison is published** — two events against two events has no sampling distribution.
- **Design C's donor pool, widened from 13 countries to 99** (`ingestion/flows/pull_worldbank_donors.py`,
  `analysis/specs/diagnostics.yml`, `analysis/R/02_diagnostics.R`). Stage 5's `infeasible` verdict was always
about the pool, so the pool was rebuilt on declared groups (West African neighbours, oil exporters, African
comparators, large lower-middle-income countries) screened on oil dependence, region/income band and
coverage. The gate moved: **`u5mr` passes 3 of its 4 runnable windows** (ratios 0.0014–0.0042 against the
declared 0.10), `gdp_growth` 1 of 4, `cpi_yoy` 0 of 4 — under a rollup rule that is now **declared** as a
strict majority of the runnable windows, where the old rule ("any window passes") was undeclared and would
have credited `gdp_growth` on one window of four (S5-12). Design C is still not estimated: the estimator and
the placebos are the next build, and the pass carries the warning that a 99-donor simplex can fit almost any
pre-period (C-59).
- **Everything was re-run at vintage 2026-10-18** because the donor vintage changed the base, and the
discipline is that a published number names the vintage it was computed on: quality (672 series now, up from
242), dbt, Stage 5, Stage 6, Stage 7, the registry and Stage 8b. **All 10 verifiers pass, 41 registry
documents validate against their schemas, and the two break-test suites catch all six mutations they apply**
(5 on the events artifact, 1 on the newly declared Design C rollup).
- Three defects were found by the chain rather than by review and are recorded with their causes: the
**`dataset_id` join** that silently emptied the donor panel under a green `dbt build` (C-61), a Stage 3
**coverage count** that described a request shape rather than the data (S5-14), and the **undeclared
gate rollup** itself (S5-12). Each one is the same failure class this project keeps finding: a claim that was
true when written and quietly false later.

**Previous action (2026-10-18, fourth session): Stage 7 — robustness and the multiverse. The grid was fitted,
and it turned one design's verdict into a different one.**

Stage 6 published two estimates. Stage 7 asks whether either survives the choices it did not pin down:
**105 specifications** fitted and published (81 Design A, 24 Design B), every one declared in
`analysis/specs/robustness.yml` before any of them ran, with the specification curve drawn and the support
counts computed rather than typed.

- **Design B survives, with a named weak part.** All **24 of 24** specifications are positive and all 24
  intervals exclude zero; the pre-registered cell reproduces Stage 6 to 4.3e-12. Its *magnitude* is a
  choice (the coefficient at h=2 spans +0.3968 to +2.3976, and the spread is mostly the shock definition —
  a three-month average is a smoother regressor) and its **timing is weaker than its sign**: the in-time
  placebo, 48 shifted alignments, returns **p = 0.0625**. That number is published as a bound rather than
  widened until it passed (S7-04).
- **Design A does not survive, and that is the finding.** **45 of 81 specifications are positive and 36
  negative.** Five axis levels have a majority on the opposite side of zero from the pre-registered
  specification — including the preferred `outcome = fatalities` level itself (14 of 27), and 6 of the 105
  specifications sit inside the declared ±0.02 near-zero band and are counted as such — and the sharpest
  is the **dose lag**: with the dose lagged one month and state and month effects, the estimate is negative
  in all three windows while the pre-registered same-month estimate is +0.479. The 36 leave-one-state-out
  refits do **not** flip the sign ([0.1234, 0.6254], 0 flips), so the fragility is the identification and
  the timing rather than one unit; dropping Delta/Bayelsa/Rivers raises the estimate to 0.6663 (C-47 restated).
  Stage 6's `estimated_not_identified` was therefore the *milder* of the two true statements: this number is
  not a direction (C-50).
- **What the grid cannot vary is declared rather than dropped.** Four of the design spec's eight axes have
  no live variant here (imputation handling, index anchor, donor pool, event window) and each carries its
  reason; the **per-capita dose axis is live in principle and unbuilt in fact** — `d1_faac_per_capita` is
  0 of 12,358 rows because X-09 is unmade — so the curve is a curve over the nominal dose and says so.
- **Sensitivity, reported in the case it is actually in.** Oster's delta is negative for both designs
  (Design B −44.04: the controls move the estimate away from zero; Design A's linear analogue −1.53: the
  control set flips its sign, −0.1023 to +0.0882), so the artifact carries `delta_interpretable`, a
  sign-flip flag and beta* at delta = 1 rather than a bare number that reads like a certification.
  **Rosenbaum bounds are declared not applicable** (continuous treatment, no matching) with the reason, and
  the HAC bandwidth moves the Design B interval only from 0.1609 to 0.1723, so its width is the sample.
- **The engine found a real bug and the pre-registered check caught it before publication.** `data.table`'s
  `shift(x, -h, type = "lead")` is a *lag* — the sign and the type cancel — and the first grid run produced
  a Design B coefficient 0.408 away from Stage 6's. The engine refuses to write when the pre-registered cell
  disagrees with the estimate artifact, which is exactly the class of error that check exists for (C-52).
  Two more were found the same session: a rank-deficient state-slope design made the verifier's clustered SE
  disagree by 97 % while the coefficient agreed to 1e-10, and `lm`'s silent drop of the first lagged month had
  to be reproduced explicitly so the two implementations compare the same sample.

**Previous action (2026-10-17, third session): the verification became one command, and the documentation was
put back onto the artifacts.**

What this session found is that the project's *claims* drifted faster than its artifacts: three of them
(C-42, C-44, C-49) were true when written and silently false later, and the verifiers were only ever run
by hand — so a green verifier on disk was a convention, not a check.

- **`scripts/verify.sh` and `.github/workflows/verify.yml`.** One command runs compile, the artifact
  contracts, acquisition when nothing is landed, Stage 3, dbt, Stage 6 and all seven verifiers, and returns
  the first failure's status; CI runs it from `requirements.txt` on a clean runner. Run today: **exit 0 —
  `all checks passed`**.
- **`scripts/validate_artifacts.py`, the contract test.** Every landed payload must be readable by the
  reader its **extension** declares — an unregistered extension fails rather than being skipped — the
  newest gate report's own label must be a date and agree with its directory, Stage 5 must describe that
  report, and every registry JSON must validate against its schema. Today: 203 payloads, 37 documents, 0
  unreadable. Three mutations confirmed each check can fail, on the real raw layer (§4).
- **C-49 — two numbers in the Stage 5 report were typed into the prose, and one was worse than stale.** It
  printed the *modal* dose status under the words "on every row", so a panel that is now 4,104 observed
  rows out of 12,358 still described itself as entirely declared gaps; the observed share was the literal
  "10.1%". Both are now computed (`grain_decision.observed_fraction`), the report was regenerated at
  vintage 2026-10-17 and the 36 cards re-emitted — and each card's own `estimate.note` was fixed too, since
  it promised estimates from a stage that has already run (G-07, narrowed).
- **The documentation was put back onto the artifacts**, and checked by a script against
  `data/analytics.duckdb`, the quality report and `estimates.json` rather than by eye: 7,682 → **8,350**
  rows, 23 → **25** metrics, 92 → **136** data tests, 125 → **242** gated series, 3 → **5** provenance
  sources, 10.1 % → **16.2 %** observed, and "five published estimates" → the **12 specifications** that are
  actually in `estimates.json`. Dated session logs and decisions were left as written; only the
  current-state claims moved.

**Previous action (2026-10-17, second session): the security outcome landed, and Stage 6 ran.**

The blocker that mattered was a credential — `fatalities` and `incidents` were recorded as needing a UCDP
token or an ACLED OAuth app (C-14/C-13), and Family A had no state-attributed outcome at all. Both halves
turned out to be one probe away: **UCDP's API is token-gated and its bulk archive is not** (401 on three
API versions, a plain 200 on a 29 MB zip), and it is CC-BY, unlike ACLED. So the security domain stopped
being blocked rather than being unblocked, and the state-month outcome exists.

- **Landed and gated**: 7,418 Nigeria events, 1990-09 → 2024-12, state-attributed via `adm_1`. 117 new
gated series (38 scopes × 3 items + national), the national series on the monthly spine from 1999-01, and
the state outcome on the panel — with `security_status` distinguishing a **recorded zero** (80 % of
state-months) from a month the archive does not cover at all.
- **A decision the landing forced**: a count series must never be interpolated. The spine would otherwise
  have carried **25 fabricated fatality-months** (1999-2009) between months the archive covers and months
  it does not (S6-05).
- **Stage 6** (`analysis/R/03_estimate.R`, 12 specifications, every number recomputed by
  `tests/verify_stage6.py` to within 1e-12): Design B is **estimated** — cumulative elasticity of state
  FAAC to a Brent shock of −0.160 at h=0, **+0.518 at h=2**, +0.470 at h=3, with a 6-month lead placebo of
  +0.095 — and Design A is **estimated, not identified**: the dose's post-fixed-effect variation is 0.50 in
  the oil-producing states against 0.11 elsewhere, and 8 of 60 mis-timed doses return an estimate at least
  as large (C-47). Both are published, each with the check that decided it.
- **Stage 5 re-ran** on the new base: the same 0-of-36 verdicts *at that vintage* (the totals moved later —
  to 15/9/12, then to 14/9/12 with one pass), with the reasons recomputed — the outcome
  blocker is now cleared and the remaining one is the dose axis plus the population denominator. The cards
  carry that, and the one stale sentence they carried ("missing a state-attributed outcome", on the same
  page as 21,238 outcome values) is now derived from the artifacts rather than typed beside them.

**Previous action (2026-10-17, first session): Stage 5 re-run — the dose's checks recomputed on the axis the estimand is
actually written on.**

The registry had drifted from the base and the drift was the kind that flatters: `tests/verify_stage5.py`
compared the recorded Stage 5 artifact against the panel and **failed** — `dose_status_values`
`{'declared_gap': 12358}` in the artifact against `{declared_gap: 8218, observed: 4104, not_covered: 36}`
in the base — because the artifact was computed before the FAAC dose landed. Its Family A cards still read
"dropped — 0 of 12,358 dose values present", which had stopped being true on 2026-10-16.

- **The fix is a re-run, not a re-word.** `analysis/R/02_diagnostics.R` recomputes everything from the
  base and stamps the artifact with the data vintage, so the re-run is what makes the registry honest.
  It now writes `registry/diagnostics/2026-10-16/` (the vintage of the Stage 3 report it reads) and
  rebuilds all 36 cards through `01_build_dags.R`.
- **The dose is measured on the specified axis and on the others, separately.** A new declared field,
  `dose.specified_axis: D1`, decides the family; the nominal FAAC column is a measured axis, not a
  substitute. Result: `D1=absent, D1_nominal=pass, D2=absent, D3=not_built`, and Family A stays
  **dropped** — for `specified_dose_axis_absent:D1 and no_state_attributed_outcome` instead of "no dose
  series". A dose that exists on the wrong axis cannot turn the gate green by proxy, and the card says
  which axis it is waiting on (S5-10).
- **The Family A card text is now derived from the dose block rather than typed next to it.** It had been
  hard-coded as "no dose series has landed" — true when written, false within a day of the parser
  landing, and invisible to every check, because a sentence cannot fail. The same defect class as C-42:
  an assumption about the data's shape that the data eventually violated quietly.
- **A second silent-skip bug was found in the same run and fixed.** Stage 5 picks the Stage 3 report to
  describe by globbing directories that match a **date** (`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`). The report's
  vintage had just become `2026-10-16-correction` (the FAAC raw vintage's correction label), so the glob
  skipped the newest report and Stage 5 described the previous one — silently, and while writing its
  output into that older vintage's directory (C-44). Fixed on both sides: the Stage 3 report's own label
  is a date again (the raw correction label still travels per source in `source_vintages`), and the
  verifier now reads the latest diagnostics vintage instead of a hard-coded one (S4-20).
- **The verdict totals were 15 fail, 7 degraded, 14 not attempted, 0 of 36 passing at this vintage** — the
dose's arrival changed *why* an estimate was not yet possible, not whether one was. Both totals have since
moved: 2026-10-17 gave 15 / 9 / 12, and widening the donor pool on 2026-10-18 gave 14 / 9 / 12 with **one
pass** (`u5mr` under Design C).

Immediately prior (2026-10-17) — **the FAAC dose through Stage 3, and a verifier that had been broken by
the landing without saying so.**

Stage 3 was the last thing standing between the dose and its being usable, and running it found two
things, one of which was a defect of mine:

- **The gate flow and its verifier both died on the FAAC payloads, silently.** Both walked `data/raw` and
  assumed every page file was JSON — true while every source was an API, false the moment 174 PDFs and
  spreadsheets landed. `tests/verify_quality.py` raised `UnicodeDecodeError` on the first byte of a PDF,
  and the gate flow had the same line and would have died identically, leaving the newest source in the
  raw layer with **no gate result at all** while the report on disk still read 88 series. That is the
  exact failure the Stage 3 exit criterion exists to prevent, seen from the other side (C-42).
- **Document sources are now gated from their parsed artifact**, declared in `quality.yml`
  (`document_sources`), because a PDF has no series until the parser reads it — and gating the parsed
  table means the gate and Stage 4 read the *same* series rather than two derivations of it. The
  publisher preference is read from `harmonisation.yml` for the same reason. 37 rows: 36 states plus the
  national aggregate, on the argument that a national series passing while one state's column is broken
  leaves the dose ungated where it is actually used (S4-19).
- **The dose is gated and the gate does not pass it quietly.** All 37 series come back **`flagged`**: the
  distribution moves more than the declared 50 % in a month nine or ten times per state, and most of
  those months fire at **all 36 states at once** (2024-12 at 36 of 37, largest move +606 %; 2021-07 at
  37). A month flagged in every unit is a movement of the distribution, not a per-state extraction
  error — and it is corroborated independently, since every document reconciles against its own
  published Total row. So the flag is carried, not resolved: `state_panel.dose_gated` is `true` with
  `dose_gate_status = 'flagged'`, read from the report, and the spikes are deliberately left
  **unadjudicated** because a verdict without evidence would be worse than the prompt (C-43).
- **The panel can no longer claim a gate it does not carry.** `dose_gated`/`dose_gate_status`/
  `dose_gate_vintage` come from the quality report by join, and a new dbt test fails if they disagree — or
  if the join matches nothing, which is the failure mode that makes every row read "ungated" while staying
  internally consistent. The test was break-tested against a doctored panel (a state that loses its gate
  result, a state claiming a status it lacks, an empty join, the FCT wrongly gated): it catches all four
  and is clean on the real table.
- **A fresh number for the report:** Stage 3 now covers **125 series — ok 60, flagged 65, empty 0** (242
  after the UCDP scopes landed on 2026-10-17),
  up from 88, with `tests/verify_quality.py` recomputing every one of them independently (and checking
  that every one of the 174 landed documents is referenced by the parse).
- **What this does not do.** It does not put FAAC on the metric spine. That needs a declared
  monthly-to-annual aggregation and a national outcome decision — a different question from whether the
  series has been checked, which it now has. S4-17's blocker is narrowed to
  `faac_gated_but_too_short_at_outcome_grain`, and X-09 (the population denominator) is still open.

Immediately prior (2026-10-16) — **the FAAC fiscal dose — acquisition, parser and dose.** Stage 5 named the NBS
FAAC parser as the single action that moves the most, and this is it. The monthly disbursement workbook is
acquired from **both** of its publishers, parsed into per-state items, and carried into the base as the
exposure Family A's estimand is written on:

- **174 documents landed and parsed** — 83 OAGF PDFs (2019-04 → 2026-06) and 91 NBS XLSX reports
  (2016-12 → 2024-07), 114 distinct months. Every document yields all 36 beneficiaries, and **every
  document reconciles against its own published Total row**; the parser refuses a month that does not.
- **The acquisition corrected a Stage 1 finding.** PHASES.md recorded the OAGF portal as unreachable (20s
  timeout) and called for a source substitution. The portal is still unreachable, but the OAGF publishes
  the monthly PDFs from its own site, so **D1's primary source was recovered rather than substituted** —
  and it is the longer of the two series.
- **The dose column is the one every layout agrees on**: `gross_total` (statutory allocation + the 13%
  derivation share). Three other candidates were rejected *against the documents* — the full-share column
  exists only from 2024 and its declared column formula does not survive extraction on every layout, so
  reading it back was wrong by hundreds of millions on several months rather than failing (S4-13).
- **The cross-check did not corroborate the way the design assumed, and that is now recorded rather than
  smoothed.** 2,124 of 2,160 overlapping state-months (98.3%) agree to within a naira and 59 of the 60
  overlapping months agree at every state — but **2023-04 disagrees at every one of the 36 states**
  (~1.83×), while both documents reconcile to their own Total rows. The dose's level is therefore
  publisher-dependent for that month, so the publisher is a column and the choice is a robustness axis
  (C-39).
- **A silent loss was found and closed.** The 2022 OAGF layouts publish a 13% derivation column whose
  header the PDF text layer interleaves (`13% SHAR(EN OEFT D)ERIVATION`), so it never resolved and eleven
  months were missing a component the documents do carry. The dose is unaffected (`gross_total` resolves
  and reconciles everywhere), but header cells that do not resolve are now **collected per document and
  persisted** instead of dropped — 541 of them, enumerated in the parse report (C-40).
- **What this does not fix, stated plainly.** The series begins 2016-12, so at the annual grain the
  outcomes are on it is 10 calendar years against the ~20-observation floor Johansen needs, and it has no
  Stage 3 gate — so it is **not** on the metric spine and the Tier-3 system is still not estimable as
  written. The blocker moved from "FAAC is absent" to "FAAC is ungated and short" (S4-17, C-41) — a
  blocker the next day's Stage 3 gate replaced with a narrower one, and the re-run below recorded that
  (S4-19, S5-10).

Immediately prior (2026-10-11) — **Stage 5, pre-analysis diagnostics and design validation.** Built the
engine that decides what the data can support *before* anything is estimated, and dropped designs on
the record rather than after an estimate looked inconvenient. The stage turned several expectations
over:

- **Nothing clears its gate — as the totals stood then** (0 pass, 15 fail, 7 degraded, 14 not attempted;
  they moved to 15 / 9 / 12 at the 2026-10-17 re-run and to 14 / 9 / 12 with one pass at 2026-10-18). The
  state dose was empty (Family A dropped); the national VECM family ran at **annual** grain without FAAC
  (degraded); and **no convex combination of the 13 donors tracked Nigeria's pre-treatment path**, so the
  synthetic control was reported infeasible rather than shipped weak — a verdict the widened 99-candidate
  pool later lifted to `candidate` on `u5mr` (S5-12).
- **The base-spec Tier-3 design can detect almost nothing.** The mandated `oil × tenure` interactions
  are nearly collinear with the tenure dummies themselves (R² 0.997–0.999), inflating the minimum
  detectable effect from ~2 residual SDs to **35–99**. That is a property of the *design matrix*, not
  the data, and it is written down before any estimate exists (C-35).
- **A real bug, found by an independent implementation.** `urca::ca.jo` returns its statistics ordered
  r = K-1 … 0; the engine had labelled them r = 0 … K-1, inverting every per-row rank label on every
  Design B card (the *rank* itself, a count of exceedances, was right; the label was wrong). Fixed, and
  the verifier now re-derives the rank from the eigenvalue problem. On the one outcome where the two
  implementations still disagree — `mmr`, whose deciding statistic sits only 8.9 % over its critical
  value — the card carries `rank marginal` rather than claiming certainty (C-36).
- **The estimator the design spec names for the synthetic control lost to a single donor.** `Synth`'s
  default V search returned a fit worse than the best single donor on every window; recorded for Stage 6
  rather than trusted (C-37).

Immediately prior (2026-10-11) — **Stage 4, the analytical base.** Built the dbt project
(staging → analytics) that turns the gated raw layer into the single table the models and the app both
read: `fact_metric`, on a local DuckDB file (`data/analytics.duckdb`, gitignored — reproducible from
`data/raw/` plus `analysis/specs/`). Three substantive results:

- **The base is reproduced, not asserted.** `tests/verify_harmonisation.py` recomputes the entire
  spine from the raw payloads and the declared specs — 7,682 rows compared row for row, every
  `observation_type`, every index value, the administration spine against base spec §7, and the four
  tenure strata — while 92 dbt tests hold the same invariants from inside the build. Twenty guards were
  then mutated to confirm they *can* fail (seven dbt tests and thirteen verifier checks), because a
  green test that cannot go red proves nothing.
- **10.1 % of the base was observed at this vintage** (775 of 7,682 rows; 4,389 interpolated, 2,518 empty —
  the same measure reads 16.2 %, 1,349 of 8,350, after the 2026-10-16/17 monthly landings). That ratio is the
  honest cost of a monthly spine over annual sources, and it settles a question §8 had left open:
  **design B on `cpi_yoy` cannot see the 2023-06 → 2023-12 window monthly**, because the landed series
  is annual and that window contains two observations (C-30). `dim_metric.frequency_gap` flags
  `cpi_yoy`, `gdp_growth` and `unemp` for the same reason.
- **The state panel that will carry the FAAC dose was built complete (37 × 334) with its dose columns
  typed, empty and labelled `declared_gap`, rather than absent and ambiguous** (S4-09). It was the right
  call at the time and the dose landed into it without a schema change — `dose_status` was widened from a
  table-level label to a per-row one when the nominal dose arrived (S4-14).

Immediately prior (2026-10-11) — **Stage 3, the quality gates**: Built the five gates PHASES.md calls "the
honesty chokepoint" and ran them over every landed series. Two of the three headline results are
defects the gates found rather than checks they passed:

- **The study-window floor now exists and is quantified.** An unwindowed scan reports **198 pre-1999
  spike flags**; the windowed report contains none. That closes C-06 and C-21, which had been open
  since Stage 1 (decisions C-26).
- **The gate found a gap in its own specification.** It flagged Nigerian inflation at 2024→2025
  (−10.23 points) and the cause was an undeclared definition break — the NBS rebased the CPI in
  January 2025, the first time since 2009 (C-27).
- **A covariate the designs condition on is contaminated.** `donor_oda` rose **+1006% in 2005** because
  Paris Club debt relief is recorded as ODA. `donor` sits in the adjustment set for designs A and B on
  every health and education outcome, so those designs partially condition on a debt restructuring
  (C-28). This is the most consequential thing Stage 3 produced and it is carried into Stage 5.

Immediately prior: the **FRED key** (account registered, Brent landed at 10,275 rows, `oil` flipped to
*acquired*, taking design C to zero unsourced nodes — C-23…C-25).

---

## 1. What this project is

An interactive causal-inference explorer for national outcomes across Nigerian presidential
administrations (1999–present). Visitors ask causal questions of a model **and** inspect the fitted
models behind the answers — coefficient tables, diagnostics, sensitivity bounds.

Presidents are one input among oil cycles, state governments, donor funding and inherited conditions.
The project's job is to show those confounders, not to bury them. Nothing here identifies a causal
effect that the design cannot support.

## 2. Written deliverables

| Document | Purpose | Status |
|---|---|---|
| `#CausalPresidents.txt` | Base spec (README v1.0) — the original dashboard brief | Source, unmodified |
| `nigeria-causal-inference-spec.md` | Design spec — upgrades the dashboard to a causal-inference explorer; records which base-spec `[LOCKED]` items are overridden and why | Complete |
| `PHASES.md` | Phase plan, Stages 0–8 from data collection to analysis, with exit criteria and gotchas per stage | Complete |
| `docs/dags.md` | The causal-graph layer: node vocabulary, the three designs as assumptions, every variable's source, and what is still missing | Complete |
| `docs/decisions.md` | Decision log — 40+ dated decisions: framing, method, data, access findings, coverage findings, infrastructure, RAG | Live, updated as evidence arrives |
| `docs/licences.md` | Licence register — redistribution rights per source, plus 5 open licensing questions | Live |
| `docs/data-dictionary.md` | Every column of the analytical base: grain, meaning, imputation rules, vintage conventions and the declared gaps | Complete |
| `docs/intent.md` | What the chat layer may refuse and on what evidence — the rule set, the held-out measurement, the A16 closure and the declared gaps | Complete |
| `docs/answer.md` | What an answer may contain — the extractive assembly, the R-04 post-check and the measured answer rate | Complete |
| `knowledge.md` | Agent-facing repo context | Live |
| `PROGRESS.md` | This file | Live |

## 3. Code and data artefacts

| Artefact | What it does | Verified |
|---|---|---|
| `ingestion/clients/provenance.py` | Shared provenance: byte-exact payload storage, sha256, POSIX paths, **credential redaction** | Redaction confirmed |
| `ingestion/clients/worldbank.py` | World Bank acquisition; retries, pagination, row-count assertion, detects the 200-with-error envelope | Working |
| `ingestion/clients/fred.py` | Brent crude (`DCOILBRENTEU`) — oil covariate for the VECM/ARDL family | **Working** (key present) |
| `ingestion/clients/ucdp.py` | UCDP GED fatalities — security domain (CC-BY, redistributable) | **Working** — bulk archive, keyless (C-45) |
| `ingestion/flows/pull_worldbank.py` | Lands a vintage: raw pages + `manifest.json` + provisional `coverage.json` | Exit 0, 22/22 |
| `ingestion/flows/probe_candidates.py` | Reconnaissance: which indicators actually reach the APC era | Exit 0 |
| `ingestion/flows/probe_missing_variables.py` | Reconnaissance: what the causal graphs need that nothing sources | Exit 0 |
| `ingestion/flows/pull_worldbank_donors.py` | The Design C donor panel — 13 countries × 5 screening predictors | Exit 0, 5/5 |
| `ingestion/flows/pull_fred.py` | Lands the oil covariate: Brent crude, daily; refuses to overwrite a landed vintage (X-07) | Exit 0, 1/1 |
| `ingestion/flows/pull_faac.py` | Acquires the FAAC monthly disbursement documents from both publishers (174 PDF/XLSX payloads, 2016-12 → 2026-06) | Exit 0, 174/174 |
| `ingestion/parsers/faac_disbursement.py` | Parses the documents into per-state items and persists the parse report (per-document reconciliation + the header cells that did not resolve) | Exit 0, 4,104 state-months |
| `ingestion/flows/pull_ucdp.py` | Lands the UCDP GED bulk archive — keyless, 28 MB, CC-BY — which is the state-attributed security outcome | Exit 0, 1/1 |
| `ingestion/parsers/ucdp_events.py` | Filters to Nigeria, aggregates to scope × month × item, and carries the 47 unattributed events as their own scope rather than dropping them (S6-04) | Exit 0, 37,734 rows |
| `tests/verify_faac.py` | Re-reads the parsed documents and re-derives the dose, the publisher rule and the cross-publisher differences | Exit 0 |
| `analysis/specs/quality.yml` | Stage 3 gate configuration: study window, thresholds, grains, frozen resample rules, definition breaks, spike adjudications, and the `document_sources` block that gates a PDF/XLSX source from its parsed artifact | 672 series configured |
| `ingestion/quality/gates.py` | The five gates (gap · spike · revision · definition-drift · provenance) as pure functions | covered by `verify_quality.py` |
| `ingestion/flows/check_quality.py` | Runs the gates over every landed series; enforces the exit criterion in code (the multi-country count is per retrieval, C-62) | Exit 0, 672/672 |
| `registry/quality/2026-10-18/` | The vintage quality report — `report.json` + a human-readable `report.md` (older vintages are kept) | 672 series: 357 ok, 313 flagged, 2 empty (Eritrea/Somalia CPI; the donors' 495 country-series are gated like any other) |
| `tests/verify_quality.py` | Recomputes the gap and spike results from the raw payloads independently of the gate module | Exit 0 |
| `tests/verify_provenance.py` | Re-derives every sha256, for every source, and detects orphaned files | Exit 0, 5 sources / 203 payloads |
| `data/raw/worldbank/2026-10-11/` | 22 payloads + manifest + coverage report | Gitignored, never committed |
| `data/raw/worldbank_donors/2026-10-18/` | 60 payloads over 40 requests in **5 chunks of 20 candidates** (99 donors), plus the WAF-split requests, + manifest + coverage | Gitignored, never committed |
| `data/raw/fred/2026-10-11/` | 1 payload (Brent, 10,275 rows) + manifest + coverage profile | Gitignored, never committed |
| `analysis/specs/outcomes.yml` | Outcome registry for the DAG layer — 12 catalogue outcomes with Stage-1 coverage status | 12/12 |
| `analysis/specs/dag_designs.yml` | The three identification designs as node/edge templates, with assumption text | 36/36 instantiated |
| `analysis/R/01_build_dags.R` | DAG generator: acyclicity check → dagitty adjustment set → ggdag SVG → in-figure legibility check | Exit 0, 36/36 |
| `registry/dags/` | 36 DAG cards + 36 SVG figures + index — the assumption layer **and the published results**, i.e. everything the app reads | Verified: 2 cards carry a published number, 34 carry a reason |
| `analysis/specs/registry.yml` | Stage 8's contract: the mapping rule, both of its counts, the cardless specification, the closed reason set, the ordering constraint | 36 cards mapped |
| `analysis/R/05_registry.R` | The Stage 8 assembler: copies the published specification onto the cards it is about, lifts the design-level results onto the index, fits nothing | Exit 0, 2 estimated / 34 explained |
| `tests/verify_registry.py` | Re-derives the mapping and checks every card's number against the artifact it names; fails when a card that should carry one does not | Exit 0 |
| `docs/registry.md` | The Stage 8 output: what the app reads, which cards carry a number, and why the rest do not | Complete |
| `tests/verify_dags.py` | Independent verification of every DAG card (schema, acyclicity, backdoor blocking) | Exit 0 |
| `analysis/specs/harmonisation.yml` | Stage 4's declared rules: spine, annual→monthly alignment, interpolation, the index anchor and its recorded fallback, and the declared gaps | 5 gaps declared |
| `dbt/` | The transformation project (D-05: SQL, never Python): staging → analytics, run into a local DuckDB | 25 models, 4 seeds |
| `dbt/seeds/raw_administration.csv` | Administration spine + term count, base spec §7 | 5 rows |
| `dbt/seeds/raw_metric_catalogue.csv` | The metric dimension's source: label, unit, **direction**, domain, catalogue vs landed frequency, coverage status | 25 metrics, 12 outcomes |
| `dbt/seeds/raw_shock_bands.csv` · `raw_state.csv` | Base spec §8 shock bands · the 37 state-level units | 3 · 37 |
| `dbt/models/analytics/fact_metric.sql` | **The analytical base**: 25 metrics × 334 months with the index, the observation type and the tenure strata | Built, 8,350 rows |
| `dbt/models/analytics/metric_anchor.sql` | The index anchor per metric, naming the rule that produced it | 25 rows (18 fixed, 7 fallback) |
| `dbt/models/analytics/int_metric_monthly.sql` | The spine before indexing: observed / interpolated / unobserved, no extrapolation, no interpolation across a gap | 8,350 rows |
| `dbt/models/analytics/dim_administration_term.sql` | Term-level spans carrying the four LOCKED party-by-tenure strata | 7 terms |
| `dbt/models/analytics/dim_metric.sql` | The metric dimension, with the Stage 3 quality status and definition breaks travelling on it | 25 rows |
| `dbt/models/analytics/state_panel.sql` | 37 × 334 panel: the FAAC dose and the UCDP outcome where their sources cover the month, the rest typed and declared | 12,358 rows, 4,104 doses observed |
| `dbt/models/analytics/fact_donor_panel.sql` | Design C's donor pool, kept off the national spine | 27,352 rows, 99 countries |
| `dbt/models/analytics/faac_state_allocation.sql` | The dose itself: one publisher chosen per state-month by the declared rule, the other measured beside it | 4,104 rows |
| `dbt/models/analytics/faac_national_monthly.sql` | The dose summed over the 36 states — the fiscal transfer channel on a national spine | 114 months |
| `dbt/models/analytics/ucdp_state_month.sql` | The security outcome at state-month grain, `observed` / `not_covered` distinguished | 15,244 rows |
| `dbt/models/analytics/ucdp_national_monthly.sql` | The same archive at national grain, summed over 38 scopes so the country is not the sum of its states | 331 rows |
| `dbt/tests/` | 13 singular tests for what generic tests cannot express: no extrapolation, no interpolation across a gap, the frozen Brent rule, vintage isolation, spine completeness, term coverage, declared gaps | 136 data tests total |
| `tests/verify_harmonisation.py` | Recomputes the whole base from `data/raw/` + the specs, independently of dbt and of the gate module | Exit 0 |
| `analysis/specs/diagnostics.yml` | Stage 5's declared parameters: grain, unit-root reconciliation, cointegration rule, dose thresholds, pre-fit gate, DoF/power, collinearity, candidate windows, design gates | 9 thresholds echoed |
| `analysis/R/02_diagnostics.R` | The Stage 5 engine: integration order, Johansen, shock visibility, dose validation, pre-fit QP, DoF/power, collinearity — then attaches a verdict to every card | Exit 0, 36/36 cards |
| `registry/diagnostics/2026-10-18/` | The Stage 5 result, re-run over the widened donor pool — `diagnostics.json` + a human-readable `report.md` | **1 of 36 passes** (`u5mr` under C): 14 fail, 9 degraded, 12 not attempted; **Design C: `u5mr` pass (3/4 windows), `gdp_growth` 1/4, `cpi_yoy` 0/4** |
| `docs/design-memo.md` | The Stage 5 output: per outcome, which family is credible, which is not attempted, and the diagnostic that decides it | Complete |
| `analysis/specs/estimation.yml` | Stage 6's declared parameters: the 12 specifications, horizons, HAC lags, the placebo and null designs, and the rule that decides a design's verdict | 12 specifications |
| `analysis/R/03_estimate.R` | The Stage 6 engine: local projections, PPML count models, the placebo, the time-shift null, the power bound | Exit 0, 12 specifications |
| `registry/estimates/2026-10-18/` | The Stage 6 result — `estimates.json` + a human-readable `report.md`, each estimate carrying the check that decided its verdict | 12 specifications: 3 Design A outcomes, 9 Design B horizons; Design C's reason rewritten from "the pool fails" to "the pool passes on `u5mr`; the estimator and its placebos are next" |
| `docs/estimates.md` | The Stage 6 output: what the data can answer, what it cannot, and the check behind each verdict | Complete |
| `tests/verify_stage6.py` | Recomputes every coefficient, sample size, horizon and verdict from the base to within 1e-12 | Exit 0 |
| `analysis/specs/robustness.yml` | Stage 7's declared multiverse: the 4 live axes per design, the windows, the two Oster analogues, the placebo and leave-one-out rules, the support-count rule, and the 6 axes that are dead or unbuilt with their reasons | 105 specifications declared |
| `analysis/R/04_robustness.R` | The Stage 7 engine: fits the whole grid, computes the sensitivity checks, the support counts and the majority-flip rule, draws the specification curve | Exit 0, 81 A + 24 B |
| `registry/robustness/2026-10-18/` | The Stage 7 result — `robustness.json`, `report.md` and `specification_curve.svg` (two panels, axis strips beneath, pre-registered cell marked) | 105 specifications: A 45 positive / 36 negative, B 24 positive; 6 inside the declared ±0.02 near-zero band |
| `analysis/specs/events.yml` · `analysis/R/06_events.R` · `registry/events/2026-10-18/` | **Stage 8b — the transition event study**: 4 in-window transitions on 312 months of UCDP conflict, 32 specifications, exhaustive placebo inference over 58 eligible months, a pre-trend placebo, a reporting-divergence check and the party split as description | 2 of 8 cells `shift_detected`, 4 `not_interpretable_pre_trend`, 1 event `check_not_available`, 1 `no_shift_detected` |
| `registry/schema/events.schema.json` · `tests/verify_events.py` | The Stage 8b contract and its independent verifier (re-fits all 32 specifications and re-enumerates the placebo distribution; worst HAC SE gap 0.002 % against a stated 5 % allowance) | Exit 0 |
| `registry/schema/robustness.schema.json` | The Stage 7 contract: every row carries its axis levels, its interval and its sign; the preferred cell is flagged; an unbuilt axis is listed rather than omitted | Validated by `validate_artifacts.py` |
| `tests/verify_stage7.py` | Re-fits all 81 PPML specifications (statsmodels, not fixest), all 24 local projections, 36 leave-one-state-out refits and 48 placebo alignments, and recomputes both Oster bounds and every count | Exit 0, worst coefficient gap 6.5e-9 |
| `docs/robustness.md` | The Stage 7 output: what survived, what did not, and the checks behind each | Complete |
| `tests/verify_stage5.py` | Recomputes every Stage 5 headline number from the base in numpy/scipy and re-derives the design verdicts from the card statuses | Exit 0, 1 warning |
| `scripts/validate_artifacts.py` | Contract test on names and shapes: every landed payload readable by the reader its **extension** declares, the newest gate report date-labelled and self-consistent, Stage 5 describing it, every registry JSON schema-valid | Exit 0 (1 check skipped without `data/raw`, which is the CI case) |
| `scripts/verify.sh` | One command that runs the whole chain — compile, artifact contracts, acquisition when nothing is landed, Stage 3, dbt, Stages 6–8c, the Stage 9 intent gate, every verifier — and returns the first failure's status | Exit 0 |
| `.github/workflows/verify.yml` | CI: installs the pinned requirements and runs `scripts/verify.sh` on a clean runner (the R engines are skipped there; every verifier still runs) | Wired, runs on push |
| `requirements.txt` · `requirements-dev.txt` | The pinned Python dependencies (runtime · verification), beside the `ds-general` conda environment rather than replacing it | Pinned |
| `docs/data-dictionary.md` | Every column of the base, documented — Stage 4's exit criterion and the Stage 0 data dictionary that was never written | Complete |
| `analysis/specs/intent_gate.yml` · `app/intent_gate.py` | **Stage 9 — the pre-retrieval intent gate**: nine declared rules, unique priorities, first match decides, default `answerable`, and a refusal only when its route resolves to exactly one chunk | 9 rules, frozen at `3dcb555` |
| `analysis/specs/intent_gate_eval_v3.yml` · `scripts/eval_intent.py` · `registry/rag/2026-10-18/intent_eval.json` | The current held-out set (49 questions written after the v3 rules froze) and the harness that scores both sets and writes one artifact; v1 and v2 are retained with their numbers | 0.980 intent accuracy, 0.947 out-of-scope refusal, 1.000 reason cited, 1.000 answerable kept, 1.000 regression |
| `registry/reference/countries.json` · `registry/donors/2026-10-18/panel.json` · `scripts/build_country_vocabulary.py` | The committed inputs to the country rule: ISO 3166-1 names (Nigeria excluded from refusal) and the 99-country donor pool, both schema-validated | 249 countries, 99 panel members; rear-view reproducible from a fresh clone |
| `registry/schema/intent_eval.schema.json` · `tests/verify_intent.py` | The artifact's contract, and a verifier that re-derives the questions, re-applies the rules with a second implementation and checks the freeze against git | Exit 0; six break-tests caught |
| `docs/intent.md` | The Stage 9 output: what may be refused and why, the measured numbers on both sets, the missed target published, and the four declared gaps | Complete |
| `app/answer_layer.py` · `scripts/eval_answer.py` · `registry/rag/2026-10-18/answer_eval.json` | **Stage 9 — the answer layer**: gate → BM25 retrieval (no model) → extractive assembly → R-04 post-check under a three-shape contract → plain-language reading, measured over the 38 answerable questions | 36 answered, 2 declined, 0 answered around a refusal; every number in its citation |
| `app/streamlit_app.py` (the **Ask** tab) · `docs/app.md` §3 | The app's fourth tab: the gate and the answer layer in the reader's own words, offering the project's own measured questions and rendering the citation, the plain reading and a cited refusal | The tab reproduces the measurement; `tests/verify_app.py` asks it the four published questions and compares the answers with the artifacts |
| `docs/glossary.md` · `registry/schema/answer_eval.schema.json` · `tests/verify_answer.py` | The plain-language definitions the layer quotes, the artifact's contract, and a verifier that re-checks every part, every sentence, every number, every definition and a keyless run | Exit 0; two new break-tests caught |

## 4. Verification evidence

Commands and their observed results — these are measurements, not assertions. Every exit status
below was captured directly, not inferred from filtered output.

**Vintage 2026-10-18 (eleventh session) — the gate at v3, and the plain-language answer:**

```
eval_intent.py             -> exit 0  49 held-out questions from intent_gate_eval_v3.yml; intent accuracy
                                      0.980, out-of-scope refused 0.947, answerable kept 1.000, route
                                      resolved 1.000, reason cited 1.000; regression 23/23; one miss (P03)
verify_intent.py           -> exit 0  49 questions re-derived, 9 rules re-applied by a second implementation
                                      (including the country condition and its possessive variant), the
                                      freeze at 3dcb555 holds against git, every panel member present in
                                      the country vocabulary, every metric and `met` flag recomputed
eval_answer.py             -> exit 0  38 answerable questions: 6 answered (published 3/16 = 0.188,
                                      held-out 3/22 = 0.136), 32 declined by R-04, 0 refused by the
                                      gate; 6 of 6 carry every part and a plain reading; 0 quote a number
                                      absent from their citation, in either rendering
verify_answer.py           -> exit 0  the plain reading's sign, bounds, zero-crossing and sample recompute
                                      from the answer's own text; every definition is a line of
                                      docs/glossary.md; the layer runs and answers in a child process with
                                      every key-shaped variable stripped
validate_artifacts.py      -> exit 0  48 registry documents schema-validated (was 46); countries.json and
                                      panel.json now have schemas of their own
```

**Break-tests — two new failures, each caught, each file restored byte-for-byte:**

```
answer artifact: a plain reading's interval_low -> +99.9   -> exit 1  the reading disagrees with the
                                                                       answer's own numbers
answer artifact: the reading's headline replaced         -> exit 1  the headline is not the reading's sentence
docs/glossary.md: a meaning edited in place               -> exit 1  the definition is not in the page
                                      each case restored -> exit 0  verifier green again
```

**Vintage 2026-10-18 (tenth session) — the intent gate, its v2 freeze and the answer layer:**

```
eval_intent.py             -> exit 0  49 held-out questions rebuilt from the eval spec, the index, the
                                      state and administration seeds and the corpus; intent accuracy
                                      0.959, out-of-scope refused 0.944 (17/18), answerable kept 0.957
                                      (22/23), route resolved 1.000, reason cited 1.000, gold route
                                      0.625; published-22: out-of-scope 1.000, reason cited 1.000,
                                      answerable kept 1.000, answerable recall@5 1.000
verify_intent.py           -> exit 0  49 questions re-derived, 8 rules re-applied by a second
                                      implementation, the freeze at 30afc23 holds against git, every
                                      metric and every `met` flag recomputed from the artifact's own
                                      rows; 2 misses named (A16, P01); docs/intent.md quotes every rate
eval_intent.py (v2)        -> exit 0  49 held-out questions from intent_gate_eval_v2.yml; intent accuracy
                                      0.980, out-of-scope refused 0.947, answerable kept 1.000, route
                                      resolved 1.000, reason cited 1.000; regression 6/6; one miss (P02)
eval_answer.py             -> exit 0  38 answerable questions: 5 answered (published 3/16 = 0.188,
                                      held-out 2/22 = 0.091), 33 declined by R-04, 0 refused by the
                                      gate; 5 of 5 carry every part; 0 quote a number absent from
                                      their citation
verify_answer.py           -> exit 0  every row's intent is the intent artifact's, every refusal cites
                                      the gate's pinned chunk, every quoted sentence appears verbatim
                                      in a cited chunk, every number is in its citation
validate_artifacts.py      -> exit 0  46 registry documents schema-validated (was 44); intent_eval.json
                                      and answer_eval.json describe the corpus sha256 beside them, and
                                      the answer artifact names the intent artifact it was measured on
```

**Break-tests — six mutations of the v2 gate and five of the answer layer, each caught, restored byte-for-byte**
(`.probe/break_answer.py`, gitignored):

```
artifact: intent accuracy 0.980 -> 0.999              -> exit 1  recomputed from the rows
artifact: a held-out question dropped                 -> exit 1  missing held-out question(s)
gate spec: one comment line added                     -> exit 1  not the rule spec at freeze 8b9ba3b
eval spec: an authored question reworded              -> exit 1  the spec moved after the measurement
docs/intent.md: accuracy 0.980 -> 0.981               -> exit 1  the page has drifted
regression: a case's expected intent flipped          -> exit 1  artifact disagrees with the spec
answer: a quoted number changed                       -> exit 1  not in the cited chunk
answer: a part cut out of an answered row             -> exit 1  the answer carries no interval
answer: a declined row relabelled `answered`         -> exit 1  the answer carries no interval
answer: a set count moved                             -> exit 1  recomputed from the rows
answer: a sentence edited out of a citation           -> exit 1  quoted sentence not in any cited chunk
                                      each case restored -> exit 0  both verifiers green again
```

**Break-tests — six mutations, each caught, each file restored byte-for-byte** (`.probe/break_intent.py`,
gitignored; the mutations are described here so the record survives it):

```
artifact: intent_accuracy 0.959184 -> 0.999        -> exit 1  recomputation from the rows gives 0.959184
artifact: missed gate flagged met                  -> exit 1  met=True but 0.956522 against 1.0 gives False
artifact: a held-out question dropped              -> exit 1  missing held-out question(s) ['M1_01']
gate spec: one comment line added                  -> exit 1  the rule spec on disk is not the rule spec
                                                              at the freeze commit 30afc23
eval spec: an authored question reworded           -> exit 1  the spec moved after the measurement
                                                              (sha256 differs from the artifact's)
docs/intent.md: accuracy 0.959 -> 0.960            -> exit 1  the page has drifted from the artifact
                                      each case restored -> exit 0  verifier green again
```

**Vintage 2026-10-17 (superseded for the base, retained for the UCDP landing and Stage 6):**

```
pull_ucdp.py               -> exit 0  1/1 — GED 25.1 bulk archive, 28.0 MB, sha256 e256f1fb20a5,
                                      keyless; 7,418 Nigeria events, 1990-09 -> 2024-12,
                                      38 state labels, 46 events with no state
ucdp_events.py             -> exit 0  37,734 staging rows = 38 scopes x 331 active months x 3 items;
                                      totals 73,822 fatalities, 7,418 incidents, 19,538 civilians;
                                      parse report carries the 81 inactive months and the 47
                                      unattributed events
check_quality.py           -> exit 0  242/242 series gated (60 ok, 182 flagged, 0 empty); the 117
                                      new ones are the UCDP scopes, flagged on monthly volatility
                                      as any count series is; 0 omitted, exit criterion enforced
verify_quality.py          -> exit 0  242 series, exit criterion met, every gap/spike reproduced
                                      independently; the multi-item document source is handled
                                      by the verifier's own reader, not by the gate's
dbt build                  -> exit 0  165 nodes: 4 seeds, 25 models, 136 tests, 0 errors. New:
                                      stg_ucdp_state_month, ucdp_state_month,
                                      ucdp_national_monthly, plus the spine and panel joins
verify_harmonisation.py    -> exit 0  25 metrics, 8,350 spine rows, 1,349 observed (16.2%), and the
                                      count metrics carry **0 interpolated months** (the rule is
                                      keyed on the catalogue's unit = 'count')
verify_stage6.py           -> exit 0  12 specifications reproduced independently: PPML coefficients
                                      agree to 2e-12, cumulative LP coefficients to 1e-12, and the
                                      five verdicts re-derived from the declared rules
03_estimate.R              -> exit 0  12 specifications + 60-offset lead-shift distribution +
                                      499-draw secondary null; design A estimated_not_identified,
                                      design B estimated
verify_stage5.py           -> exit 0  36 cards, diagnostics re-run on the new base; 1 reported
                                      warning (the marginal mmr cointegration rank), 0 failures
verify_dags.py             -> exit 0  36/36 cards acyclic, schema-valid, adjustment sets block
                                      every backdoor path in the assumed graph
```

**Vintage 2026-10-18 (fourth session) — Stage 7, the multiverse:**

```
04_robustness.R            -> exit 0  105 specifications fitted (81 Design A PPML, 24 Design B
                                      local projections at h=2); support A 45 positive /
                                      36 negative, B 24 / 0; 5 axis levels flip by majority;
                                      6 of the 105 inside the declared ±0.02 near-zero
                                      band; the pre-registered cell reproduces Stage 6
                                      to 4.3e-12; spread decomposition 0.4073 across
                                      covariate sets / 0.7548 across shock definitions;
                                      base fingerprint state_panel dd11d300f588,
                                      national 0084ea1d7129, oil 167ff0dce42d;
                                      specification_curve.svg written (94,502 bytes,
                                      505 marks across two panels)
verify_stage7.py           -> exit 0  every specification re-fitted independently: 81 PPML
                                      fits in statsmodels, 24 local projections, 36
                                      leave-one-state-out refits and 48 placebo alignments;
                                      worst coefficient gap 6.5e-9, worst clustered-SE gap
                                      0.85 % against the stated 5 % allowance; both Oster
                                      bounds, the majority-flip rule, the HAC table and
                                      the spread decomposition reproduced — the spread
                                      from the verifier's own re-fitted coefficients,
                                      not from the published rows
validate_artifacts.py      -> exit 0  105 specifications, 81 A / 24 B; the support counts are
                                      recomputed from the artifact's own rows, exactly one
                                      specification per design is flagged pre-registered,
                                      the curve exists and draws at least one mark per
                                      specification; 38 registry documents schema-valid
scripts/verify.sh          -> exit 0  the whole chain in one status — compile, contracts,
                                      Stage 3 gates, dbt build, Stage 6 estimates, Stage 7
                                      grid and all seven verifiers — ending "all checks
                                      passed" with the Stage 7 curve regenerated in the
                                      same run it was verified against
```

**Vintage 2026-10-18 (current, fifth session) — Stage 8, the registry:**

```
05_registry.R             -> exit 0  vintage 2026-10-17 | 36 cards | 2 carry a published number,
                                    34 do not: outcome_series_absent 12,
                                    no_specification_declared 10,
                                    design_result_is_channel_level 9, design_not_run 3;
                                    published without a card: fatalities_civilians;
                                    design results A estimated_not_identified (3 specs),
                                    B estimated (9, channel-level), C not_run
verify_registry.py        -> exit 0  the mapping re-derived from the artifacts: 2 of 36 cards
                                    should carry a number and 2 do; every attached number
                                    equals the estimates artifact's to 1e-9; every
                                    not_estimated card's reason is the recomputed one; the
                                    index's design-level results are the artifacts' numbers;
                                    B is declared channel-level
validate_artifacts.py     -> exit 0  2 of 36 cards carry a published number; the index's counts
                                    recomputed from the cards on disk; 38 registry
                                    documents schema-valid against 0.3.0
```

**Stage 8 break-tests — three guards mutated, the failure observed, then restored.** The driver backed up
all 37 registry documents, kept the digest of the directory, and checked afterwards that it was
byte-identical (`ed6a53a8c7da6630`): a break-test that leaves the artifact changed is worse than none.

```
validate_artifacts  a card's estimate block reset (the   -> exit 1  "registry/dags: the index says 2 card(s)
                   ordering trap)                                    carry a published number and the cards
                                                                     say 1 — the registry is stale against
                                                                     its own cards"
verify_registry    a coefficient moved off the artifact's-> exit 1  "fatalities__A: coefficient is
                   value                                             0.4892847253 on the card and
                                                                     0.4792847253 in registry/estimates/
                                                                     2026-10-17/estimates.json"
verify_registry    a not_estimated card's reason swapped -> exit 1  "mmr__B: reason
                                                                     'no_specification_declared',
                                                                     recomputed
                                                                     'design_result_is_channel_level'"
                                     each case restored  -> exit 0  contracts green again; registry
                                                                    digest unchanged
```

**Stage 7 break-tests — eight guards mutated, the failure observed, then restored.** The first four are
contract tests and run in seconds; the last four re-run the verifier, which re-fits the whole grid (three
minutes each). The driver kept each run's full output and checked afterward that the artifact's sha256 was
byte-identical to the one it started from — a mutation that leaves the artifact changed is the failure
mode a break-test exists to rule out, and a restored-but-different artifact would look green.

```
validate_artifacts  support count 45 -> 46 in the summary     -> exit 1  "design A support n_positive
                                                                          is 46 in the summary and 45
                                                                          in its own rows"
validate_artifacts  a second specification flagged preferred -> exit 1  "design A has 2 specifications
                                                                          flagged preferred; exactly one
                                                                          per design is the pre-registered
                                                                          one"
validate_artifacts  specification_curve.svg moved aside      -> exit 1  "the specification curve is
                                                                          missing or empty — the exit
                                                                          criterion is a rendered curve,
                                                                          not a table"
validate_artifacts  artifact vintage -> 2026-10-16           -> exit 1  "the artifact's own vintage is
                                                                          '2026-10-16', which disagrees
                                                                          with the directory holding it"
verify_stage7       one coefficient moved by 0.01            -> exit 1  "design A / A|fatalities|lag0|
                                                                          state_fe|full: reported
                                                                          -0.062311 vs recomputed
                                                                          -0.052311"
verify_stage7       the `fatalities` flip level removed      -> exit 1  "flip list: published [...] vs
                                                                          recomputed [...]" — the published
                                                                          4 omit 'outcome = fatalities' from
                                                                          the recomputed 5 — and "flip count
                                                                          disagrees with the recomputed
                                                                          majority rule"
verify_stage7       the per-capita axis removed from the
                    unbuilt list                             -> exit 1  "unbuilt axes: population_
                                                                          denominator is neither varied
                                                                          nor declared as unbuilt"
verify_stage7       the spread decomposition moved to 0.9   -> exit 1  "spread / design B /
                                                                          across_shock_definitions:
                                                                          published 0.900000 vs
                                                                          recomputed 0.754829 — the
                                                                          magnitude claim is not the
                                                                          fitted grid's"
                                      each case restored  -> exit 0  contracts and verifier green again;
                                                                     artifact byte-identical to the
                                                                     one the run started from
```

The earlier vintages below are kept as history. Note that the report's own label is a date and the raw
vintages are not (S4-20) — `registry/quality/2026-10-17/` is the current gate report.

**Vintage 2026-10-16-correction (current, 2026-10-17):**

```
check_quality.py           -> exit 0  125/125 series gated (60 ok, 65 flagged, 0 empty);
                                      exit criterion enforced in code, 0 series omitted
                                      (37 of the 125 are the FAAC dose, gated from its
                                      parsed artifact rather than from its PDF payloads)
verify_quality.py          -> exit 0  every series has a gate result; gap and spike results
                                      reproduce from the raw payloads and the parsed
                                      artifact; all 174 landed FAAC documents shown to be
                                      referenced by the parse; 198 pre-1999 spikes
                                      shown to exist in an unwindowed scan and correctly
                                      absent from the report; 7 adjudications live,
                                      0 stale; 437 spikes left unadjudicated and printed
dbt build                  -> exit 0  144 nodes: 4 seeds, 22 models, 118 tests; the new
                                      dose-gate test break-tested against a doctored
                                      panel (4 lies, all caught; 0 false positives)
```

The 2026-10-11 figures for the same commands — 88 series, 60 ok, 28 flagged — are the earlier vintage and
are kept in §5 below as history, not as the current result.

```
probe_missing_variables.py -> exit 0  7 World Bank variables probed: 6 keyless and covering the study
                                      window (mmr, immun_penta3, unemp, fx, donor, oil_rents),
                                      1 flagged SPARSE (skilled_birth, 9 obs / 33y); donor pool
                                      13/13; the oil section now exercises the KEYED client
pull_worldbank.py          -> exit 0  22/22 (was 15/15) — the DAG-required variables added
pull_worldbank_donors.py   -> exit 0  5/5 predictors x 13 donors
pull_fred.py               -> exit 0  1/1 — Brent DCOILBRENTEU, 10,275 rows (9,102 with values),
                                      1987-05-20..2026-10-06, 474/474 months carry an observation,
                                      longest missing run 12 days, sha256 b6807052c734
verify_provenance.py       -> exit 0  28 payloads across 3 sources (22 + 5 + 1), 0 orphaned,
                                      every sha256 reproduced
01_build_dags.R            -> exit 0  36/36 DAGs (12 outcomes x 3 designs), 0 failures;
                                      every label present in the SVG, none overflowing its node
verify_dags.py             -> exit 0  36/36 schema-valid, acyclic, adjustment set blocks
                                      every backdoor path (3-8 per graph); 0 orphaned cards;
                                      variables_still_missing recomputed from the cards: 7
py_compile (8 files)       -> exit 0
ruff check (files edited)  -> the 5 remaining hits are the repo's own pre-existing noqa: E402
                                      convention (pull_worldbank.py carries the identical two)
```

**Stage 4 — the analytical base (built 2026-10-11):**

```
dbt build --project-dir dbt --profiles-dir dbt
                           -> exit 0  115/115 (4 seeds, 19 models, 92 data tests, 7 views)
                                      PASS=115 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0
                                      fact_metric 7,682 rows = 23 metrics x 334 months
                                      (1999-01 .. 2026-10); observed 775 (10.1%),
                                      interpolated 4,389, unobserved 2,518
verify_harmonisation.py    -> exit 0  the whole spine recomputed from data/raw/ + the declared
                                      specs and compared row for row: 0 observation-type
                                      disagreements and 0 value disagreements beyond float
                                      noise (largest relative difference 8.9e-16 = 4 ulps,
                                      against a one-month population step of ~2e7);
                                      23 anchors (16 fixed at 2000-01, 7 on the recorded
                                      fallback); 474 monthly Brent values reproduce the
                                      frozen mean-of-daily rule; administration spine matches
                                      base spec section 7 including the decided Yar'Adua ->
                                      Jonathan boundary (2010-05-05 -> 2010-05-06); four
                                      strata covering 329 months + 5 pre-study; 25 metrics,
                                      12 outcomes, 8 definition breaks; state panel
                                      37 x 334 with 0 doses; donor panel 13 countries,
                                      0 treated-unit rows
py_compile + ruff check    -> exit 0  new verifier clean
verify_quality.py          -> exit 0  unchanged, so Stage 4 introduced no regression in Stage 3
verify_dags.py             -> exit 0  unchanged
verify_provenance.py       -> exit 0  unchanged (28 payloads, 3 sources, 0 orphaned)
```

**Stage 5 — pre-analysis diagnostics (re-run at vintage 2026-10-16, 2026-10-17):**

```
02_diagnostics.R           -> exit 0  vintage 2026-10-16 (taken from the latest Stage 3 report);
                                      dose axes measured separately: D1=absent, D1_nominal=pass,
                                      D2=absent, D3=not_built; the specified axis D1 decides the
                                      family; 36 card pre-checks attached (15 fail, 7 degraded,
                                      14 not attempted, 0 pass)
01_build_dags.R            -> exit 0  36/36 cards rebuilt at vintage 2026-10-16
verify_stage5.py           -> exit 0  every headline diagnostic reproduced from the base; the new
                                      dose-axis claims recomputed (including that a length-one
                                      present_axes is an array, not a string); 1 warning (mmr, as
                                      before), 0 failures
verify_dags.py             -> exit 0  unchanged, so the Stage 5 re-run introduced no regression
                                      in the DAG layer
```

The 2026-10-11 Stage 5 run — the one that produced the first set of verdicts against the pre-FAAC base —
is recorded in §5 as history; its artifact directory was superseded rather than kept, because it described
a base that no longer exists (C-44).

**Stage 5 — first run (built 2026-10-11, superseded):**

```
02_diagnostics.R           -> exit 0  native grain, study floor 1999-01-01; 26 series, 18 classified,
                                      10 inconclusive (carried as I(1), the conservative branch);
                                      Johansen on {Y, log(oil), fx}: 6 outcomes ranked, estimators
                                      assigned by the base-spec rule; 3 shock windows x 23 metrics
                                      counted; dose validation (0 of 12,358); 12 pre-fit QPs;
                                      6 Tier-3 MDEs; VIF per outcome; 36 card pre-checks attached
01_build_dags.R            -> exit 0  36/36 cards rebuilt, each now carrying its `diagnostics` block
verify_dags.py             -> exit 0  unchanged, so Stage 5 introduced no regression in the DAG layer
verify_stage5.py           -> exit 0  spec echo (9 thresholds) · observed-spine fraction (775/7,682
                                      = 10.1%) · 69 shock-window counts and verdicts · dose
                                      validation · Johansen rank (6/6; 5 exact, 1 warned) ·
                                      12 pre-fit QPs re-solved with scipy · 6 Tier-3 MDEs rebuilt ·
                                      card statuses and design verdicts re-derived; 1 warning
                                      (mmr rank marginal), 0 failures
py_compile + ruff check    -> exit 0  new verifier clean
verify_quality.py          -> exit 0  unchanged
verify_harmonisation.py    -> exit 0  unchanged
verify_provenance.py       -> exit 0  unchanged
```

**Stage 5 break-tests.** Ten guards mutated — the failure observed, then restored. Eight on the
verifier (each mutation of `diagnostics.json` below turns `verify_stage5.py` red), two on the engine:

```
verifier: shock 1/oil observed count 31 -> 30    -> exit 1  counts differ from the base
verifier: dose D1 n_non_null 0 -> 5              -> exit 1  disagrees with state_panel
verifier: prefit u5mr/yaradua ratio 0.670 -> 0.5 -> exit 1  differs from the re-solved QP
verifier: gdp_growth Johansen rank 0 -> 1        -> exit 1  recomputed rank 0 != engine rank 1
verifier: card u5mr__A status fail -> pass       -> exit 1  != recomputed fail
verifier: mde u5mr pdp_first halved             -> exit 1  != rebuilt design matrix
verifier: design B status degraded -> candidate  -> exit 1  != recomputed from the cards
verifier: u5mr trace rows reordered              -> exit 1  rows are not labelled r = 0 .. K-1
engine:   A card status fail -> pass             -> exit 1  "a declared_gap outcome cannot pass"
engine:   drop a non-pass card's blocker         -> exit 1  "status 'fail' with no blocker recorded"
                                      each case restored -> exit 0  base green again
```

**Break-tests — every new guard mutated, the failure observed, then restored.** Twenty of them: seven
dbt tests and thirteen verifier checks. A green guard that cannot go red proves nothing.

```
fact_metric index /100 -> /101                  -> exit 1  anchor months are not indexed at 100
interpolation bound 12 months -> 400            -> exit 1  4,389 rows carry the wrong
                                                          observation_type (the 108-month hole)
stg_fred_monthly avg -> max                     -> exit 1  monthly Brent disagrees with the
                                                          frozen rule
fact_metric term join widened by one month      -> exit 1  duplicate (metric, month) rows
seed: fatalities coverage_status cleared        -> exit 1  unlanded outcome with no declared gap
int_metric_monthly: unobserved filled with 0.0  -> exit 1  values outside the observed span
stg_raw_manifest: vintage filter removed        -> exit 1  a superseded vintage reached fact_metric
verifier: spec anchor moved to 2001-01          -> exit 1  metric_anchor disagrees with the spec
verifier: spec spine floor moved to 2000-01     -> exit 1  grid differs: 5 extra months
verifier: spec interpolation span -> 1 month    -> exit 1  4,389 observation-type disagreements
quality.yml: frozen resample rule renamed       -> exit 1  "verifier does not implement the
                                                          declared resample rule"
verifier: one base value +1                     -> exit 1  301 rows differ, e.g. u5mr/1999-07
verifier: one index value x1.01                 -> exit 1  1 row is not value/anchor*100
verifier: one spine month deleted               -> exit 1  grid: 1 missing (2023-06)
verifier: a tenure stratum relabelled           -> exit 1  dim_administration_term 21 differs
verifier: a definition break deleted            -> exit 1  the fx breaks are missing
verifier: a state-panel dose column populated   -> exit 1  dose populated with no source landed
verifier: an outcome's declared gap cleared     -> exit 1  coverage_status vs outcomes.yml
verifier: quality status desynced from report   -> exit 1  u5mr 'flagged' vs the report's 'ok'
verifier: a frequency gap erased                -> exit 1  cpi_yoy catalogue_frequency
                                      each case restored -> exit 0  base green again
```

**Break-tests — the artifact contracts (2026-10-17).** The three checks in `scripts/validate_artifacts.py`
exist because C-42 and C-44 were both a *name or a shape that stayed in the code after it stopped being
true*. Each was mutated and the failure observed, on the real raw layer, then restored:

```
validate_artifacts  PDF_SUFFIXES = {} (drop the reader)      -> exit 1  data/raw/faac/2026-10-16-correction/
                                                                       oagf-2019-04/page-0001.pdf: unregistered
                                                                       payload extension '.pdf'
validate_artifacts  report label must be '...-correction'    -> exit 1  registry/quality/2026-10-17: the report's
                                                                       own label is not a date, so every consumer
                                                                       that selects the newest report by date
                                                                       will skip it
validate_artifacts  Stage 5 must describe 2026-10-11 instead -> exit 1  registry/diagnostics/2026-10-17
                                                                       describes a superseded gate report
                                         each case restored  -> exit 0  contracts green again
```

```bash
# Stage 4 — build the analytical base, run its tests, then verify it independently
# (dbt is not on PATH: it lives in the ds-general env, so it needs the same conda run wrapper)
conda run -p C:/Users/TOSHIBA/ds-general dbt build --project-dir dbt --profiles-dir dbt
$PY tests/verify_harmonisation.py
```

**Vintage 2026-10-10 (first, superseded but retained for revision detection):**

```
pull_worldbank.py     -> exit 0   succeeded: 15/15   failures: 0
verify_provenance.py  -> exit 0   page files on disk: 15, referenced: 15, orphaned: 0
probe_candidates.py   -> exit 0   covers 2015+: 10 of 15
fred (no key)         -> MissingCredential raised (actionable message)
ucdp (no key)         -> MissingCredential raised (actionable message)
```

**Break-tests — checks that were made to fail on purpose.** A green test that cannot go red proves
nothing, so each guard was mutated and the failure observed, then restored:

```
verify_dags.py  drop 'oil' from an adjustment set   -> exit 1  fails to block backdoor path
verify_dags.py  add a back edge Y -> oil            -> exit 1  graph is cyclic
verify_dags.py  blank a node's source               -> exit 1  CHECK FAILED
verify_dags.py  drop a gap from the index           -> exit 1  index disagrees with the cards (6 vs 7)
verify_dags.py  adjustment_set as a string          -> exit 1  schema violation
verify_dags.py  delete a rendered SVG               -> exit 1  svg missing or empty
pull_fred.py    no key in .env (moved aside)         -> exit 1  REFUSED "FRED_API_KEY is not set";
                                                               no vintage directory created
pull_fred.py    key present but unregistered         -> exit 1  REFUSED "FRED rejected the API key";
                                                               partial vintage deleted, none left
pull_fred.py    same-day re-run (vintage exists)     -> exit 1  REFUSED "vintage '2026-10-11' already
                                                               exists ... raw layer is immutable"
pull_fred.py    --vintage <new label>               -> exit 0  identical sha256 (reproducible fetch)
verify_prov.    flip one byte of the Brent payload   -> exit 1  sha256 mismatch (b6807052 vs 154ffdc3)
verify_quality  inflate a reported spike count       -> exit 1  "n_spikes 2 vs reported 99"
verify_quality  drop a series row from the report    -> exit 1  "exit criterion: worldbank/u5mr/NGA is
                                                               in the manifest but has no gate result"
verify_quality  add an adjudication that matches
                nothing to the spec                  -> exit 1  "stale adjudication: population/2011
                                                               matched no flagged event"
verify_quality  disable the study-window floor
                (start 1900) and regenerate          -> exit 1  198 problems, "the report flags a
                                                               pre-1999 spike (1990-08)"; flagged
                                                               series rise 28 -> 45
check_quality   125 series, one flag flipped to pass -> n/a    status is derived, not asserted;
                                                               empty/gap/spike alone decide it
dbt build       doctor the state panel: a state
                loses its gate result, then claims
                one it lacks, then the join is
                emptied, then the FCT is gated  -> exit 1  "dose_gate_status_agrees_with_dose_gated"
                                                               returns 1, 2, 12,024 and 334 rows
                                                               respectively; 0 on the real table
each case, restored                                 -> exit 0
```

Reproduce with:

```bash
PY="conda run -p C:/Users/TOSHIBA/ds-general python"

# what the graphs need that nothing sources
$PY ingestion/flows/probe_missing_variables.py

# land the national series, the donor panel and the oil covariate, then prove all three
$PY ingestion/flows/pull_worldbank.py
$PY ingestion/flows/pull_worldbank_donors.py
$PY ingestion/flows/pull_fred.py        # needs FRED_API_KEY; in .env or exported
$PY tests/verify_provenance.py          # every source under data/raw

# Stage 3 — gate every landed series, then verify the report independently
$PY ingestion/flows/check_quality.py
$PY tests/verify_quality.py

# DAG layer (R 4.5.2 + ggdag/dagitty)
Rscript analysis/R/01_build_dags.R
$PY tests/verify_dags.py
```

Note: `conda run -n ds-general` does **not** work — `ds-general` is a prefix environment at
`~/ds-general`, not a named one under `miniconda3/envs` (decisions.md I-01).

## 5. Findings so far

**Design C's donor pool, widened (2026-10-18).** Full write-up: `docs/design-memo.md` §4;
artifact `registry/diagnostics/2026-10-18/`.

- **The `infeasible` verdict was about the pool, and the pool was fixable.** Against 13 countries chosen on
  GDP comparability no window could track Nigeria (ratios 0.58–1.55 against a 0.10 threshold). Against **99
  candidates** screened on oil dependence, region/income band and coverage: `u5mr` **passes 3 of its 4
  runnable windows** (ratios 0.0014–0.0042; ratio-on-differences 0.013–0.064), `gdp_growth` passes 1 of 4,
  `cpi_yoy` none (C-59).
- **A pass the design cannot celebrate yet.** A 99-donor simplex can fit almost any pre-period — the
  `gdp_growth`/yaradua window reaches a ratio of 1.7e-06, which is interpolation rather than validation — so
  the pre-fit gate is **weaker evidence than it was with 13 donors**, `Synth` still loses to the best single
  donor, and Design C remains **not estimated**: the estimator and the placebos Stage 5 deferred to Stage 6
  are the next build.
- **The rollup rule was undeclared, and the widened pool is what made that matter.** With 13 donors nothing
  passed, so the engine's "any window passes" rule never showed; with 99 it would have reported
  `gdp_growth: pass` on one window of four. It is now declared as a strict majority of the runnable windows,
  implemented by the engine and the Stage 5 verifier, and break-tested (S5-12).
- **Two acquisition defects were found by the chain, not by review.** The World Bank WAF rejects some country
  *combinations* deterministically (`LK;LR` 200, `LK;LR;LS` 403), so the flow splits and retries and records
  the split depth (C-60); and the chunked landing silently broke the `dataset_id` join, emptying the donor
  panel under a green `dbt build` with every Stage 5 outcome reported `not_attempted` rather than failing
  (C-61). The second was found by reading a reason string, and the flow now checks its own landing contract.

**Stage 8b — comparing tenures on the one monthly outcome (2026-10-18).** Full write-up: `docs/events.md`;
artifact `registry/events/2026-10-18/`.

- **Two of eight event-outcome cells survive both checks.** Reported incidents rose **+391 %** in the 12
  months after the 2010 transition and fatalities **+77 %** after the 2023 one, each at p = 0.017 — the
  floor of what 58 placebo months can resolve — with the pre-trend placebo smaller than the post-window
  shift (C-56).
- **Four cells fail the pre-trend placebo**, including the largest shift in the series: the 2015 fall in
  fatalities (−67 %, family-wise p = 0.017) was already under way 24 months before the transition. Buhari
  2015 on incidents and Tinubu 2023 on incidents fail for the same reason, in the other direction (C-56).
- **One transition cannot be checked at all.** Yar'Adua 2007 has 100 months of history and the pre-trend
  placebo needs 120; the artifact reports `check_not_available` rather than scoring the missing check as a
  null (S8b-05).
- **The placebo null drifts down by 32 %**, so the first inference rule written for this stage — two-sided
  in magnitude — was discarded before publication: it scored the largest fall in the series as unremarkable
  while its own left tail said the opposite (C-57). The published rule is the same-side signed tail in the
  add-one form, and the reason is on the artifact.
- **No party comparison is published.** Two events against two events has no sampling distribution; the
  PDP/APC medians (+55.3 % / +4.6 %) are published as description with `no_test_computed: true`, and the
  verifier fails if a test statistic appears in that block (S8b-06).

**Stage 7 — what survives the choices (2026-10-18).** Full write-up: `docs/robustness.md`.

- **Design B's sign is invariant; its timing is not.** 24 of 24 specifications positive, all 24 intervals
  excluding zero, the pre-registered cell reproducing Stage 6 to 4.3e-12 — against an in-time placebo of
  **p = 0.0625** (3 of 48 shifted alignments as large as the estimate) and a coefficient that spans 0.3968
  to 2.3976 across the grid, mostly because the three-month shock is a smoother regressor. The honest
  reading: the channel and its sign are the result; "two to three months" is a weaker claim that now
  carries its placebo (C-51).
- **Design A is not robust, and the axis that moves it is the dose lag.** 45 of 81 positive against 36
  negative; the lag-1 specification is negative in all three windows while the pre-registered same-month
  one is positive; `state_fe` and `state_month_fe_state_trend` also flip by majority. Leave-one-state-out
  does not flip it (0 of 36), so the instability is not one unit — and dropping the three oil-producing
  states moves the estimate from +0.479 to +0.666, the same oil-price concentration C-47 measured (C-50).
- **The per-capita dose is still missing and the curve says so.** Every cell is the nominal dose, because
  `d1_faac_per_capita` is 0 of 12,358 rows (X-09). S6-06's invariance argument is an argument, not a fitted
  specification, and the artifact lists the axis as unbuilt rather than quietly omitting it.
- **Oster's delta does not certify anything here, and the artifact says which case it is in.** Negative for
  both designs — the controls move Design B away from zero (−44.04) and flip the sign of Design A's linear
  analogue (−0.1023 → +0.0882) — so the δ ≥ 1 cutoff has no reading. Rosenbaum bounds are recorded as not
  applicable rather than omitted (S7-05).

**Stage 6 — what could actually be answered (2026-10-17).** Full write-up: `docs/estimates.md`.

- **The presidential-tenure question is not answerable**, and the reason is arithmetic: four to five
  administrations against 27 annual observations put the minimum detectable effect at 35–80 residual
  standard deviations (Stage 5's rebuilt design matrices). It is not "no evidence yet"; it is a question
  this data cannot carry. Any tenure number would be a restatement of its own assumptions.
- **The fiscal channel is answerable, and now estimated.** A 10 % Brent rise reaches state allocations as
  **~5 % more money, two to three months later** (cumulative elasticity +0.518 at h=2, HAC SE 0.166;
  −0.160 at h=0; 6-month lead placebo +0.095). The lag matches the disbursement calendar rather than
  contradicting it, and the zero at h=0 is part of the finding (C-48).
- **The dose-response question is estimable and not identified.** Higher allocations do not visibly buy
  less violence, and the design cannot distinguish that from any other timing: 8 of 60 mis-timed doses
  return an estimate at least as large as the estimate itself, and the 24-month placebo (+0.302) is nearly
  the estimate (+0.479). The cause is measurable, not rhetorical — after state and month effects the
  dose's variation is the 13 % derivation share moving with the oil price (residual sd 0.50 in Delta,
  Bayelsa, Rivers; 0.11 elsewhere) — a national shock interacted with a fixed state characteristic (C-47).
- **A monthly NGN/USD series does not exist on any keyless source** (C-46), so the price and exchange-rate
  channels cannot be separated inside Design B. It is a stated limitation on the estimate, not a silent one.

**Access (probed 2026-10-10; "unreachable" = failed via two independent network paths):**

| Source | Result |
|---|---|
| World Bank API | ✅ keyless, working — the backbone |
| NBS, CBN | ✅ reachable (HTML/PDF, no API) |
| IMF DataMapper | ⚠️ 403 to scripted clients, 200 via relay |
| FRED | ✅ **resolved 2026-10-11** — key registered, HTTP 200, Brent landed |
| UCDP | ✅ **keyless via the bulk archive (2026-10-17)** — the *API* still returns 401 without a token, but `ged251-csv.zip` is a plain 200 (29,307,888 bytes) and CC-BY. Landed as the security outcome (C-45) |
| ACLED | ❌ documented endpoint dead; now **OAuth** |
| OAGF (`oagf.gov.ng`), Open Treasury, NEMIS | **OAGF 🟡 corrected 2026-10-16** — the Open Treasury portal is still unreachable, but the OAGF's own site publishes the monthly disbursement PDFs and was crawled successfully (83 documents). Open Treasury and NEMIS remain ❌ — two Nigerian gov hosts of the three |
| UNESCO UIS | ❌ every path 404, including root |

**Variable gaps (probed 2026-10-11).** The causal-graph layer named variables that nothing was
sourcing, so the difference was probed rather than assumed. Seven were keyless and reach 1999+ 2015+,
and are now landed (`donor` had no source at all before this). **The oil gap closed on 2026-10-11**
(C-23/C-24): Brent crude is landed and the `oil` nodes are `acquired`. `index.json` carries the residue
as `variables_still_missing` — **7 variables, 3 root causes**:

| Root cause | Variables | Needs |
|---|---|---|
| Fiscal dose | `dose` (D1), `faac` | ✅ **The acquisition is done (2026-10-16)** — 174 documents, 114 months × 36 states, `state_panel.faac_gross_total_naira` — **and the Stage 3 gate is done (2026-10-17)**: 37 series gated, all `flagged` on distribution-cycle spikes, with `dose_gate_status` on the panel. What remains is a **decision** (the state population denominator, X-09), a **catalogue entry** for a panel with no declared national aggregation, and a decision about the annual-grain length |
| Education outcomes | primary completion, net enrolment, youth literacy | No open source reaches 2015+ |
| Security outcomes | fatalities, incidents | ✅ **Closed 2026-10-17** — UCDP GED bulk archive, keyless, state-attributed, on the panel and on the spine (C-45). ACLED would still be a second, richer source, and its terms stay unresolved without leaving a hole |

**Oil price — closed.** Brent crude is landed as a daily series: 10,275 rows, 9,102 with values,
1987-05-20 → 2026-10-06, sha256 `b6807052c734`. All **474 months** in the span carry at least one
observation (min 4, max 23) and the longest gap is 12 days, so a monthly oil series is constructible
across the whole study window including the 2023 subsidy window. Spot-checked against the real Brent
history: 2008-07-03 = $143.95, 2020-04-21 = $9.12, and the 2008-07-04 US holiday is correctly marked.
**Caveat:** the series is *daily*, and Stage 4 must freeze the daily→monthly rule before any
oil-adjusted estimate is computed — changing it later changes every adjusted result (C-23).

Design C's donor pool is **not** blocked: all 13 candidates carry all 5 screening predictors to 2015
(only Venezuela's oil-rents series stops early). With `common` now `derived`, **design C has zero
unsourced nodes**; designs A and B are each down to one, the FAAC fiscal dose.

**Coverage (22 indicators as of 2026-10-11; the 15-indicator first vintage reads the same):**

- **Health is strong** — `u5mr` 61 obs no gaps, `life_expectancy` 65, `measles_imm` 41, `health_spend_gdp` 24
- **Health gained three series** — `mmr` 39 obs to 2023 (now `ok`), `immun_penta3` 41 obs to 2024
  (`partial`: an annual DPT3 stand-in, since DHIS2 is credential-blocked), `skilled_birth` 9 obs in 33
  years (`partial`: a survey series, not an annual one — it must render as flagged points)
- **Economy is strong** — `gdp_per_capita`, `population`, `cpi_yoy` all 66 obs no gaps
- **Security has no usable World Bank series** (`homicides`: 3 obs) — depends entirely on UCDP/ACLED
- **Education is unusable after 2010** — every outcome series stops in 2010–2011. Primary completion,
  lower-secondary completion, pupil-teacher ratio and tertiary enrolment all end mid-Jonathan, so they
  cannot see the APC tenures at all. Only `educ_spend_gdp` (a policy input, not an outcome) and
  `adult_literacy` (6 points) reach the present.

  **Consequence:** of the four registry domains, education should be recorded as a **declared gap**.
  "We found no education effect" and "we had no education outcome data after 2010" are different
  statements, and only the second is true.

**Stage 3 gate results (2026-10-11) — 88 series, 60 `ok`, 28 `flagged`.** The full report is
`registry/quality/2026-10-11/report.md`. What the gates found, rather than what they waved through:

- **The study-window floor works, and the size is now measured.** An unwindowed scan reports **198
  pre-1999 spike flags** across the landed series; the windowed report contains none. C-06 and C-21
  are closed, and `verify_quality.py` fails if the floor ever becomes inert.
- **An undeclared definition break, found by the gate.** `cpi_yoy` 2024→2025 falls 10.23 points, and
  the cause is the **NBS rebasing the CPI in January 2025** on a new 2024 base year — the first
  rebasing since 2009 (Reuters, NBS). Headline inflation fell 34.80% → 24.48% at the rebasing. Not a
  data error, and not detectable from the numbers alone.
- **`donor_oda` is contaminated, and that touches the adjustment set.** Net ODA rose **+1006% in 2005**
  ($0.58bn → $6.4bn) and reversed −82.9% by 2007, because **Paris Club debt relief is recorded as
  ODA** (OECD, UNCTAD; Nigeria's US$18bn deal was announced October 2005, completed April 2006).
  `donor` is in the adjustment set for designs A and B on every health and education outcome, so a
  design conditioning on it partially conditions on a debt restructuring. **This is the most
  consequential output of Stage 3 and it goes to Stage 5.**
- **The gaps are real and now quantified:** `adult_literacy` has a **108-month** hole (2006→2016),
  `literacy_youth` and `skilled_birth` 48-month holes, `primary_completion` and `ner_primary`
  36-month holes. These are the C-03/C-04/C-07 findings restated as gate results.
- **One gate had to be rebuilt after running it.** A single 50%-relative spike rule flagged **52 of 88**
  series — Ecuador's growth rate 18 times in 27 years — because a rate moving 0.5%→3.0% is a 500%
  relative change and a 2.5-point move. Splitting the measure by series type (relative for levels,
  percentage points for series already in percent) brought it to 28 and let the real signals through.
- **60 of 67 spikes are deliberately left unadjudicated.** The immunisation and primary-completion
  swings have no documented cause, so the report says `UNADJUDICATED` rather than inventing one.

**Donor pool and re-vintage verification (2026-10-18, sixth session) — transcript.**

```
$ python ingestion/flows/pull_worldbank_donors.py
vintage: 2026-10-18   donors: 99   predictors: 5   chunk size: 20
  group neighbour_west_africa       13 candidate(s)
  group oil_exporter                29 candidate(s)
  group africa_comparator           28 candidate(s)
  group lower_middle_income_large   35 candidate(s)
  treated unit NG excluded from the pool
  note gdp_growth  NY.GDP.MKTP.KD.ZG-p03s01  5 country(ies) landed after 2 WAF split(s)
  ok   u5mr        SH.DYN.MORT        chunks=5 rows=6534 donors=99/99 reaching_2015=99/99
succeeded: 5/5 predictor(s) in 40 request(s)   failures: 0

$ dbt build                -> 165 PASS, 0 ERROR   (donor panel 27,352 rows / 99 countries)
$ ingestion/flows/check_quality.py   -> 672 series gated: 357 ok, 313 flagged, 2 empty
$ Rscript analysis/R/02_diagnostics.R
5. pre-treatment fit — 3 outcomes attempted, 1 pass, 2 infeasible on pre-fit
     u5mr               pass                       3 of 4 runnable window(s) pass
     gdp_growth         infeasible_weak_pre_fit    1 of 4 runnable window(s) pass
     cpi_yoy            infeasible_weak_pre_fit    0 of 4 runnable window(s) pass

$ all verifiers (vintage 2026-10-18)
validate_artifacts -> 0   quality -> 0   stage6 -> 0   stage7 -> 0   registry -> 0
harmonisation -> 0        faac -> 0      dags -> 0     stage5 -> 0    events -> 0   provenance -> 0
registry schemas : 41 document(s) validated

$ python .probe/break_events.py     -> all 5 mutations caught, restored byte-for-byte
$ python .probe/break_stage5_c.py   -> caught: status -> pass while 0 of 4 runnable window(s) pass
```

**Stage 8b verification (2026-10-18) — transcript.**

```
$ Rscript analysis/R/06_events.R
series: 312 months 1999-01 -> 2024-12, 25 blank month(s) filled with zero
events: 4 | specifications fitted: 32 (h=12: 16, h=24: 16) | declared skips: 0
placebo: 58 eligible month(s) per outcome/horizon, enumerated (no RNG)
figure: event_study.svg (196379 bytes)

verdicts (h=12, baseline):
  yaradua_2007   fatalities   check_not_available          post=-0.1712 pre=—      p=0.610
  yaradua_2007   incidents    check_not_available          post=-0.3434 pre=—      p=0.186
  jonathan_2010  fatalities   not_interpretable_pre_trend  post=1.2770  pre=1.9558 p=0.017
  jonathan_2010  incidents    shift_detected               post=3.9125  pre=0.8758 p=0.017
  buhari_2015    fatalities   not_interpretable_pre_trend  post=-0.6747 pre=0.8381 p=0.017
  buhari_2015    incidents    no_shift_detected            post=-0.4795 pre=0.4041 p=0.085
  tinubu_2023    fatalities   shift_detected               post=0.7664  pre=0.5275 p=0.017
  tinubu_2023    incidents    not_interpretable_pre_trend  post=0.0671  pre=0.2547 p=0.169

$ python tests/verify_events.py                              -> exit 0
artifact         : registry/events/2026-10-18/events.json (32 specifications)
series           : 312 months 1999-01 -> 2024-12, 25 blank month(s) filled, 10 year(s) affected
transitions      : 4 of 4 bound to dim_administration_term at the declared dates and strata
specifications   : 32 rows re-fitted from the base; worst SE gap 0.002%, allowance 5%
placebo          : 58 month(s) re-enumerated per outcome/horizon, distributions and quantiles reproduced
inference        : 8 verdict(s) re-derived; 6 pre-trend placebo(row)s reproduced, 1 event declared uncheckable
party split      : 4 event(s) grouped into 2 group(s), medians and shifts reproduced, no test field present
PASS

$ python scripts/validate_artifacts.py                       -> exit 0
stage 8b artifact: 2026-10-17 (32 specifications over 4 transitions, 1 declared uncheckable pre-trend,
                   cells accounted for)
registry schemas : 39 document(s) validated
PASS

$ python .probe/break_events.py                              -> exit 0
1. coefficient moved 2 %                         verifier=1 contract=1  caught
2. one row deleted (silent omission)             verifier=1 contract=1  caught
3. uncheckable pre-trend scored as a pass        verifier=1 contract=1  caught
4. test statistic added to the party description verifier=1 contract=1  caught
5. figure deleted                                verifier=1 contract=1  caught
restored byte-for-byte: True True
PASS — all 5 mutations caught by at least one guard
```

**Stage 4 harmonisation (2026-10-11) — what building the base measured.** The stage's job was to build
a table; what it produced that matters is one constraint and two confirmations.

- **The monthly spine is 16.2 % observed (C-30)** — 1,349 of 8,350 rows — and was **10.1 %** (775 of
  7,682) when the finding was first recorded, before the monthly Brent, FAAC and UCDP landings. 4,389 rows
  are linear interpolations between annual points and 2,612 are empty months within the spine's span. That
  is not a defect — it is what a monthly spine over annual sources *is* — but it has a consequence that
  changes the plan: **the landed `cpi_yoy` is annual, so a monthly design-B estimate cannot see the
  2023-06 → 2023-12 window**, which contains two observations. `dim_metric.frequency_gap` flags
  `cpi_yoy`, `gdp_growth` and `unemp`. The three ways forward are in §8.
- **Brent at every administration's start reproduces the real oil history (C-31).** 1999-05-29 carries
  no quote (a Saturday) with a May-1999 month mean of **$15.44**; 2007-05-29 **$69.31**; 2010-05-06
  **$80.21**; 2015-05-29 **$63.16**; 2023-05-29 no quote, month mean **$75.47**. Obasanjo's *second*
  term starts at **$26.05**, not his first term's $15.44 — the number a reader would sanity-check an
  oil-adjusted estimate against, and the reason the price is computed per term.
- **A level shift is now annotatable rather than a finding (C-32).** 8 definition breaks reach the base
  as a dimension: the 2014 GDP rebasing (×2), the 2016 float, the 2023 unification, the 2014 and 2023
  unemployment methodology changes, the 2020 WTI episode carried on Brent, and the January-2025 CPI
  rebasing. A verifier check fails if the Stage 3 report's breaks do not all arrive.

## 6. Corrections made (kept visible rather than quietly fixed)

1. **My first endpoint probe was buggy** — it reused a temp file, so failed requests printed the
   previous request's body. Caught and re-run clean; all recorded findings come from the corrected run.
2. **A false-gap hazard in the client.** An invalid World Bank indicator returns **HTTP 200 with an
   error envelope**, not a 4xx. Left unchecked it registers as "no data" and manufactures a fake
   coverage gap. The client now detects the envelope; a negative test confirms `SH.DYN.NMR` raises.
   (The correct neonatal code is `SH.DYN.NMRT`.)
3. **Windows backslash paths in the manifest**, exposed by the orphan check reporting 15/15 files
   orphaned. This would have broken the Linux CI runners the plan schedules against. Fixed with
   `as_posix()`; orphans now 0.
4. **A secret-leak risk removed before it existed.** The FRED key travels in the query string, so an
   un-redacted manifest would have written it into git. Credentials are now masked in both the
   parameter map and the URL.
5. **A YAML 1.1 trap in the DAG specs.** An unquoted `Y` parses as boolean `TRUE` — YAML 1.1 treats
   `y`/`Y` as true — so the outcome node's id silently became a logical and the first generator run
   died on `vapply`. Node ids are now quoted. Instructive because it failed *loudly*; the dangerous
   version of the same bug is a node that quietly never appears.
6. **`ggdag`'s tidy layout emits one row per edge, not one per node.** Nodes with no outgoing edge
   (the terminal outcome) get a standalone row; every other node appears only as an edge source.
   Labelling "rows where `to` is NA" therefore labelled exactly one node and dropped the rest — and
   the figures still rendered, so nothing failed. Caught only by reading the SVG back and asserting
   every node label is present. That assertion is now a build-time gate.
7. **`jsonlite`'s `auto_unbox` collapsed single-element arrays.** `adjustment_set: ["oil"]`
   serialised as the string `"oil"`, violating the card schema. Fixed with `I()` on the array
   fields, and the verifier now validates against the JSON Schema so this class of error cannot
   return silently.
8. **`ggdag` does not render latent nodes dashed** in this version, so the identifying assumption
   would have been invisible on the figure. It is now stated inside the node itself
   (`(assumed absent)`) and in the caption, and the generator asserts the marker reaches the SVG.
9. **The browser-automation session captured the API key in a page snapshot.** Registering the FRED
   key required driving a real browser, and `playwright-cli` writes a YAML snapshot of every page it
   visits into `.playwright-cli/`. One of those pages *displays the freshly issued key*, so
   `.playwright-cli/page-2026-10-11T07-06-49-517Z.yml` contained the credential in clear — a
   directory that was sitting untracked inside the repo. Caught by grepping the working tree for the
   key after the fact, not by any existing check. Directory deleted and `.playwright-cli/` added to
   `.gitignore`; the key now exists only in the gitignored `.env`. Same class of risk as D-01c
   (TOOLING.md) and the reason I-07 redacts manifests — this time in a tool the project does not own.

10. **`dim_definition_break` produced 34 rows for 8 breaks.** The donor panel reports the same
    definition breaks for the same indicator ids once per country, so all 13 `u5mr` rows were identical
    duplicates. A break is a property of the indicator's definition, not of the country reading it, and
    the dimension is keyed by `metric_id`. Found by reading the built table rather than by any test —
    the count looked plausible until it was compared with the report's distinct breaks. Now national
    series only (8 rows, decision S4-11).
11. **`oil_price_at_start` was attached to both terms of a two-term administration.**
    `dim_administration_term` joined the *administration's* start price, so Obasanjo's second term
    reported May-1999 rather than May-2003. Same class of error as an off-by-one date: it looks like a
    number and it is wrong. Caught by reading the built table — `$15.44` beside a 2003 term start was
    the tell. The term model now joins the price at its own start month (**$26.05**).
12. **A seed CSV field with an internal comma** ("Two terms — one spine row, two terms") parsed as an
    eighth column and failed the seed load. Quoted. Worth recording because the same class of error is
    invisible in a diff and a comma inside a free-text field is exactly what a `notes` column attracts.
13. **The verifier's value comparison was absolute and is now relative.** Ten of 7,682 rows first
    "failed" at a 1e-9 *absolute* tolerance on float round-tripping. Measured before loosening
    anything: the largest relative difference is **8.9e-16** (four ulps), against a one-month
    interpolation step of ~2e7 on the population series — so the tolerance remains ~14 orders of
    magnitude tighter than the smallest real defect it has to catch. A bounded, justified loosening,
    not a silenced assertion; the measurement is in §4.
14. **The dbt `profiles.yml` path is relative to the invocation directory, not the project directory.**
    `../data/analytics.duckdb` resolved to `D:\data\analytics.duckdb` and failed. Now written relative
    to the repository root, matching the `raw_root` var, with every documented command run from there.
15. **`read_json_auto(filename = true)` returns Windows backslash paths** while the manifests store
    POSIX paths — the same Windows/Linux break the Stage 2 manifest fix addressed (correction 3), one
    layer down, and the same one that would break the Linux CI runner the plan schedules against.
    Normalised in one place with `chr(92)`, not a backslash literal: a bare `'\'` inside a DuckDB
    string literal is an escape character, not a path separator.
16. **The Stage 5 card totals were stale in six published places, and the artifact said so.** Both later
    re-runs moved the totals (`15/7/14` at 2026-10-16 → `15/9/12` at 2026-10-17 → `14/9/12` **with one
    pass** at 2026-10-18), but `README.md`, `knowledge.md`, `PHASES.md`, `docs/dags.md`,
    `docs/design-memo.md` and `docs/registry.md` still carried the first set — the README said "0 of 36
    pass" in the same sentence that announced Design C had moved to `pass` on `u5mr`. Found by reading the
    artifact next to the prose while answering a coverage question, not by a test. Corrected in all six, and
    the    per-vintage totals are now written where the re-runs are narrated, so the next movement reads as a
    change rather than as a contradiction.
17. **A "needs a separate acquisition" claim that the raw layer already paid for.** `docs/design-memo.md`
    said a Design C for the conflict outcomes needs a donor conflict path, "a separate acquisition this
    re-run did not make". The landed UCDP payload is the **global** GED 25.1 archive — 385,918 events over
    124 countries, 1989–2024 — and only the parse step filters to Nigeria, so the missing piece is a
    parser extension and a name/ID crosswalk, not a download. Found by opening the landed zip instead of
    trusting the prose; the same sentence now carries the two facts a build needs (Gleditsch–Ward
    `country_id`, and that a name-only join reaches 70 of the 99 donors).


## 7. Blocked

| Blocker | Needs |
|---|---|
| ~~FRED key~~ | ✅ **Unblocked 2026-10-11** — registered, key in `.env`, Brent landed, `oil` acquired (C-23) |
| ~~UCDP token~~ | ✅ **Not needed 2026-10-17** — the bulk archive is keyless and the security outcome is landed (C-45). ACLED stays unwired by choice: UCDP is CC-BY and already answers the domain |
| ~~FAAC parser (D1)~~ | ✅ **Unblocked 2026-10-16** — both publishers crawled, 174 documents parsed, every one reconciled to its own Total row (C-39/C-41) |
| State IGR parser (D2) | NBS publishes PDFs and HTML, no API. D2 is FAAC ÷ (FAAC + IGR), so the IGR half is now the only missing input |
| ~~A Stage 3 gate on the FAAC series (S4-17)~~ | ✅ **Done 2026-10-17** — 37 series (36 states + the national aggregate) gated from the parsed artifact and the result read onto the panel (S4-19). What the national series still lacks is a **catalogue entry**, which needs a declared monthly-to-annual aggregation, not a gate |
| UNESCO UIS current API path | Its docs (web search unavailable in this environment) |
| NEMIS reachability | A check from a network other than this one |
| DHIS2 tenant access | Institutional credentials; do not design a model on it until confirmed |
| Monthly NBS CPI — the grain the app's chart spec states | The manual-download parser. The landed CPI is annual, so design B cannot see the 2023 window monthly on it (C-30) even though the spine is now 16.2 % observed. Either parse the monthly series, or run design B at its annual cross-check |
| **`oagf.gov.ng` TLS certificate — expired 2026-10-17** | The publisher to renew it. The leaf expired `2026-10-17 08:45:30 UTC` (issuer `Certum OV TLS G2 R39 CA`), so `curl` returns `SEC_E_CERT_EXPIRED` and `pull_faac.py` refuses. Plain HTTP 301-redirects to HTTPS, `www.` has the same expired leaf and NBS does not resolve from here — so the FAAC vintage cannot be re-landed anywhere, local or CI, until renewal. Nothing is worked around: disabling verification would make a dead source look green |

**CI's `data` job ran for the first time on 2026-10-18** (run `39124538665`, `workflow_dispatch` on
`5a48f55`, after `FRED_API_KEY` was set as a repo secret). It acquired World Bank national **22/22**, the
donor pool **5/5 in 40 requests** and Brent **1/1** (`DCOILBRENTEU`, 9,108 obs, `1987-05-20..2026-10-14`
— the secret works in CI), then stopped at `oagf.gov.ng` on the certificate above. `static contracts`
passed. The job stays red until the publisher renews; the weekly cron retries it.

## 8. Next steps, in order

**Stages 0–6 are done. No credential gates anything on the critical path, and the first estimates exist.**
What is left is not acquisition: it is the two *decisions* that would let the unidentified design become
identified (X-09 and a non-oil fiscal instrument), the designs that were never runnable, and the stages
that turn estimates into a product.

**A. Credentials: none outstanding.**

1. ~~**UCDP token**~~ **Not needed — 2026-10-17.** The API wants a token (401 on three versions) but the
   bulk archive does not, and it is CC-BY, so the security outcome landed keyless (C-45). ACLED stays the
   richer alternative and stays unwired: it needs OAuth and forbids redistribution, and the domain is
   answered. FRED needed no further action either (key in `.env`, Brent landed) — so the covariate gap
   that appeared against designs A, B and C is closed for three of those nodes at once.

**B. Unblocked now, no credentials needed.**

2. ~~**Stage 3 — quality gates.**~~ **Done 2026-10-11.** The study-window floor is in and quantified
   (198 pre-1999 spikes suppressed); the Brent daily→monthly rule is **frozen as a declared input**
   (`mean_of_daily_observations`) and applied by the gates, so Stage 4 must reuse it rather than
   re-choose it. Carried forward: **60 unadjudicated spikes**, and the `donor_oda` contamination that
   must reach every health and education card (C-28).
3. ~~**Stage 4 — harmonisation** (dbt).~~ **Done 2026-10-11.** The analytical base exists: 7,682 rows
   (23 metrics × 334 months, 1999-01 → 2026-10; 25 metrics after the FAAC and UCDP landings) on a local
   DuckDB, with the January-2000 index anchor
   and its recorded fallback, direction labels as a dimension, the base-spec §7 administration spine
   plus term-level party-by-tenure strata, the 37 × 334 state panel with declared-empty dose columns,
   the shock bands, and the Stage 3 quality status and 8 definition breaks travelling on it. 92 dbt
   tests and 20 break-tests; `tests/verify_harmonisation.py` recomputes the whole base independently.
4. ~~**Stage 5 — the design memo.**~~ **Done 2026-10-11, re-run 2026-10-16 and 2026-10-17** — it took
   C-30 (the 2023 window is not monthly-visible on the landed annual CPI), C-28 (the `donor_oda`
   contamination), C-27 (the 2025 CPI rebasing), the unadjudicated spikes and the 3 frequency gaps, and
   dropped failing designs *on the record*: 0 of 36 cards passed at that vintage (the 2026-10-18 re-run
   over the widened donor pool leaves 1 passing, `u5mr` under Design C). Diagnostics are attached to every
   card; the current artifact is `registry/diagnostics/2026-10-18/` and the narrative is
   `docs/design-memo.md` at the vintage it was written against.
5. ~~**The FAAC parser (D1)**~~ **Done 2026-10-16.** All four publishers' paths are now acquired and the
   dose is in the base. ~~**Stage 3 gate on the FAAC series**~~ **Done 2026-10-17** — 37 series (36 states
   + national) gated from the parsed artifact, all `flagged` on spikes that fire at every state at once,
   with the result read into `state_panel.dose_gated`/`dose_gate_status` and a break-tested dbt test
   holding it honest (S4-19, C-42, C-43). What is left from this item is not acquisition: **D2** (the NBS
   state IGR half of the share) and the **population denominator decision** (X-09).
   Note the constraint the landing measured rather than assumed: the dose begins 2016-12, so it is an
   APC-era exposure and 10 years long at the annual grain — the dose now exists, but a *monthly*
   dose-response estimate is not what this makes possible (C-41).

**C. Then, in plan order.**

6. ~~**Stage 5 re-run — the design memo.**~~ **Done 2026-10-17, twice: at vintage 2026-10-16 over the FAAC dose and at vintage 2026-10-17 over the security outcome** (artifact: `registry/diagnostics/2026-10-17/`; the second re-run also replaced the two hand-typed numbers in the report with computed ones, C-49). The dose and
   Tier-3 checks were re-run against the post-FAAC base: the nominal column is now a measured dose axis,
   the specified axis `D1` (per capita) still decides the family, the Family A card text is derived
   rather than typed, all 36 cards were re-emitted, and `tests/verify_stage5.py` passes again (S5-10,
   S4-20, C-44). What the re-run **did not** do, and what now heads this list:
   - **X-09 — the state population denominator.** It is the only thing standing between the landed
     nominal dose and the per-capita axis Family A's estimand is written on, and it is a decision.
   - ~~**A state-attributed outcome.**~~ **Done 2026-10-17** — UCDP GED landed keyless, state-attributed,
     on the panel and the spine (C-45). Family A's other blocker is cleared; what remains on it is the
     dose axis and the identification below.
   - **A metric-catalogue entry for the FAAC panel** with a declared monthly-to-annual aggregation, which
     is what Family B's Tier-3 system is missing now that the series exists and is gated.
   - **`dag_designs.yml`'s `dose`/`faac` nodes still read `source_status: gap`,** deliberately — the node
     is specified as *per capita*, and the per-capita axis is absent. Noted in `docs/dags.md` rather than
     flipped, because `gap` is under-specified here, not wrong.
7. ~~**Stage 6 — estimation (R).**~~ **Built 2026-10-17, partially.** Twelve specifications across two designs
   (`registry/estimates/2026-10-17/`, verifier `tests/verify_stage6.py`, output `docs/estimates.md`).
   Design B — the fiscal transmission channel — is **estimated**; Design A is **estimated, not
   identified**, and says so with the check that decided it. The plan's `did` estimator was not used and
   the deviation is recorded (the dose has no staggered adoption; it is a magnitude, not a switch).
   **Still open, and this is what heads the list now that the estimates exist:**
   - **Identification for Design A.** C-47 measured the problem: the post-fixed-effect dose variation is
     the 13 % derivation share moving with the oil price. A fiscal instrument that varies within state
     for reasons unrelated to oil (state IGR, the VAT distribution) is a different acquisition, not a
     different estimator.
   - **The estimate block on the card schema** — Stage 8 work, not claimed by Stage 6. A card without an
     interval still does not ship, and no card currently carries an estimate.
   - **The FX channel** inside Design B (C-46): a monthly NGN/USD series would separate the price and
     exchange-rate channels and has no keyless source, so it would have to be assembled from CBN.
8. ~~**Stage 7 — robustness and the multiverse.**~~ **Built 2026-10-18** (`registry/robustness/2026-10-17/`,
   verifier `tests/verify_stage7.py`, output `docs/robustness.md`). 105 specifications declared before
   fitting and all published; the exit criteria are met by construction rather than by assertion — support
   counts per sign computed from the fitted rows, the pre-registered specification marked on the curve,
   and the five majority sign-flip levels named in the artifact, the figure and the narrative. What it
   changed: Design B's verdict now carries a timing bound (placebo p = 0.0625) and Design A's verdict is
   sharper than `estimated_not_identified` — its **sign** does not survive the grid. **What is still open
   from this stage:** the per-capita dose axis (X-09), the IGR instrument (D2), and a donor pool that would
   let Design C run at all.
9. ~~**Stage 8 — the registry, narrative and RAG corpus.**~~ **Built.** The registry and all three
   figures (2026-10-20), `docs/limitations.md` (2026-10-20), and the retrieval corpus — **482 chunks from
   53 attributed sources** at the registry's vintage (`registry/rag/2026-10-18/`, `docs/rag.md`), extended
   2026-10-23 with the glossary and the licence register after measuring that they cost no retrieval
   metric. **What is still open from it:** the generation half of the RAG evaluation (RAGAS is `not_run` —
   it needs an LLM key and a judge model); chunks for the families the corpus currently summarises (the
   donor panel, the robustness grid); and the decision log, which is **not** in the corpus because adding
   it measurably sank MRR and gold coverage (measured 2026-10-23, recorded in `analysis/specs/rag.yml`).
10. ~~**Stage 9 — the read-only app and the chat layer.**~~ **Built 2026-10-22.** The app
   (`app/streamlit_app.py`, `docs/app.md`), the **pre-retrieval intent gate** (`analysis/specs/intent_gate.yml`,
   v3 frozen at `3dcb555`, `docs/intent.md`) and the **answer layer** (`app/answer_layer.py`,
   `docs/answer.md`) are measured end to end, and the **chat tab** — the app's fourth tab — is built on
   them. **36 of 38 answerable questions answered (0.947)** under the three-shape contract, every quoted
   sentence and number attributable to its citation, every answer carrying a plain-language reading
   defined from `docs/glossary.md`, and no model or key anywhere in the answering path. The verifier asks
   the tab the four published example questions and compares the answers with the artifacts.
   **What remains in this stage:** RAGAS's generation half (a key and a judge model, `not_run`); the
   corpus families the corpus summarises rather than chunks (the donor panel, the robustness grid); the
   items `docs/app.md` declares unbuilt — per-card URLs, node-level graph interaction, deployment; and the
   two lexical declines the layer publishes rather than smooths (L02: a 2016 inflation value and a
   "fatal crashes" outcome that is not in the catalogue).

### The smallest credible end-to-end slice — revisited by Stage 4

`nigeria-causal-inference-spec.md` §16 Step 1 calls for one defensible model, end to end, as the
checkpoint. Stage 3 named design B on `cpi_yoy` (the 2023 subsidy window) as the fastest unblocked route,
on the grounds that `cpi_yoy` is `ok` (66 observations, no gaps) and its only non-outcome covariate — the
oil price — was landed and gated. **Building the base measured something that argument missed: those 66
observations are annual** (C-30). On a monthly spine, the 2023-06 → 2023-12 window contains two of them,
and the other ten months are interpolated. A monthly VECM on interpolated annual data estimates
something about the interpolation rule, not about the subsidy removal.

Three routes, in the order Stage 5 should weigh them:

1. **Run design B on `cpi_yoy` at its annual cross-check** (~26 observations, which base spec §9 already
   assumes and its sample-size constraint already discloses). Cheapest, fully unblocked, and honest —
   the interval will be wide and the card says why. It just cannot answer a *monthly* question.
2. **Parse the monthly NBS CPI.** The app's chart spec states a monthly CPI, so this is the acquisition
   that closes the gap rather than working around it. It is the same parser family as the FAAC work
   (NBS PDF/HTML), so doing both together is cheaper than either alone.
3. **Pick a genuinely monthly outcome instead.** `oil` is monthly and complete (334/334 observed), but it
   is a covariate, not an outcome.

What is already true either way: the study-window floor exists, the daily→monthly Brent rule is frozen
and verified, the base is built and independently reproduced, and **nothing on the estimation path is
credential-blocked**. The remaining caveats are annotatable rather than blocking — `cpi_yoy` carries the
January-2025 CPI rebasing inside the study window (C-27), so any estimate spanning it mixes a real
inflation path with a measurement change; that is an exclusion axis and a card annotation.

### Resolved by Stage 5 — the slice is the *boundary*, not a headline

Stage 5 weighed the three routes and found that **none of the 36 (outcome × design) cards passes its
pre-check**, so there is no headline estimate to build the end-to-end slice on. What Stage 5 hands to
Stage 6 instead is the boundary: the *annual* Design B VECM/ARDL and the *differenced* synthetic control
are the only estimators with a testable question, and each carries its own disclaimer (a 38–99 SD
detectable effect on the Tier-3 design; a donor pool that tracks changes but not levels). The one
action that moves the most is the **NBS FAAC parser** — it revives Family A outright and restores the
base-spec Tier-3 system for Family B — and it is the same parser family as the monthly NBS CPI, so
doing both together is cheaper than either alone. The full reasoning is `docs/design-memo.md`.

## 9. Standing constraints

- **Free tier only.** No paid service at any layer.
- **Publish code and derived aggregates; never restricted raw data.** ACLED and DHS/NDHS may not be
  redistributed, which is why this repo's `.gitignore` excludes `data/raw/`.
- **Never a point estimate without its interval.** Six-item rigor floor acts as a shipping gate.
- **The app never fits a model at render time.**

## 2026-10-25 — the guided flow, built and measured

The static site now has all seven screens (`/`, `/study/`, `/compare/`, `/graph/`, `/estimates/`,
`/chart/`, `/ask/`) and two new descriptive artifact families behind them. What was added, and what
each one is checked by:

- **`registry/comparisons/`** — 12 outcome panels, 56 groups, group means only. `tests/verify_comparisons.py`
  recomputes every mean, both means, unit and month counts and byte counts from DuckDB and refuses any
  inferential field.
- **`registry/changepoints/`** — 8 searched series, 10 estimated breaks, 4 definition breaks marked,
  4 refusals with the count that caused them. Fitted on native observations only; a break on the
  interpolated spine fails `tests/verify_changepoints.py`, which also refits every searched series in a
  separate R script.
- **`site/assets/answer.mjs`** — the gate, BM25, the three-shape contract and the plain reading, ported to
  JavaScript over JSON the build emits from `intent_gate.yml` and `rag.yml`. `tests/verify_answer_js.py`
  runs it over the artifact's 38 questions and compares status, shape, rule, citation, passages, text and
  plain reading field for field: 38 of 38 reproduce, 36 answered in the artifact's own 8/14/14 shape split.
- **`tests/verify_site.py`** — builds the site and compares every page with the registry: the ratio, the
  chosen design per outcome, each published coefficient on its own block, every group and break caption,
  every stamp, and no external reference.
- **`.github/workflows/verify.yml`** — `site pages` and `answer layer (JavaScript)` join the static job, and a
  `pages` job deploys `site/dist/` only after `static` passes.

**Correction to an earlier entry.** The 2026-10-24 header said the twelve panels cover 3,008 outcome-months.
They cover 4,008: the artifact's own `spine_rows` sum to 764 + 1,826 + 1,418. `docs/app.md` was corrected and
`tests/verify_app.py` now derives the total from those three counts instead of trusting prose.

## 2026-10-27 — the guided flow's verifiers, broken on purpose

The 2026-10-25 session shipped three verifiers — `verify_site.py`, `verify_changepoints.py`,
`verify_answer_js.py` — and no attempt to make any of them fail. A verifier that has never been red is a
claim, not a check, and this repository has had the other kind before: a check that reported its own declared
budget as a violation, and a prose total that every verifier passed. So this session did the missing half.

**`.probe/break_guided_flow.py` applies thirteen cases, one at a time, to the real files.** Each case names
the verifier that owns the claim and **the sentence the red run must contain**, so a mutation caught by a
crash, or by some unrelated check, is reported as a failure of the probe rather than counted as a catch.
Every file is restored from the bytes read before the mutation and its sha256 compared afterwards, and the
three verifiers are re-run on the restored tree at the end.

**What was broken, and what caught it:**

- **The renderer (5).** A published coefficient rounded to two places (its own block; `+0.4793` is not
  `+0.48`); an undeclared pill word (`proven`); the changepoint caption dropped from the chart screen; a
  president named beside an outcome (`Buhari`, which is the claim the build refuses to make anywhere); and an
  external stylesheet, which the no-network check reads as a reach for the network.
- **The changepoint artifact (4).** An estimated break moved one month off the refit (the separate R script
  found `2013-03`, the artifact declared `2013-04`); a break statement carrying `because of the
  administration`; a native count the base does not have; and a `counts` block moved by one.
- **The browser answer layer (4).** The ranking direction inverted, and IDF flattened to a constant — both
  break the parity with `answer_eval.json`; a `fetch(` smuggled into the module, which the "no second copy"
  scan reads as a network call.

**Twelve of thirteen were caught. The thirteenth is a measurement, and it is the interesting one.** Retuning
BM25 — `k1` from 1.5 to 0.5, or `b` from 0.75 to 0, or both — changes **no published answer**: all 38 stay
identical, so the parity check stays green. The 38 questions are decided by *which* chunks carry their terms
(IDF and the ranking order are live: flattening IDF fails on `q12_interpolation_visible`, inverting the order
fails on `q04_oil_to_states`), not by how the score trades term frequency against document length. That is
now a published statement about the check's power rather than an assumption about it, and the case stays in
the probe with no expected failure attached, so the next session re-measures it instead of rediscovering it.

**Writing the suite found a real gap, which is the reason to write it.** `verify_changepoints.py` printed the
artifact's `counts` block — `outcomes_searched`, `breaks_estimated`, `known_breaks_passed` — without
recomputing any of it, so the stale-count mutation passed. The counts are now derived from the outcomes array
(five tallies, `outcomes_considered` included), and the mutation fails on `counts.breaks_estimated is 11, the
outcomes array gives 10`. `verify_comparisons.py` had recomputed its own counts since it was written; the
newer verifier had not.

**The chain ran green in one unbroken run, which it had not done since 2026-10-24.** `scripts/verify.sh`
returned `all checks passed`: stages 0–8f, the corpus rebuild with its vectors, both answer evaluations, and
**all twenty verifiers** — **0 failures, 50 registry documents schema-validated**. It had been green in two
pieces because the embedding step's model lookup fails online on this machine although the snapshot is cached;
with `HF_HUB_OFFLINE=1` the whole chain completes, and the flag is recorded here rather than assumed. Stage 8f
and `verify_changepoints.py` were inside that same run, so the newest stage is not being signed off by a chain
that predates it.

**The clone check found one more defect, in the stage this session was committing.** The three stages added
since the forest plot recorded a raw `file.size()` as each figure's byte count, and their verifiers compared it
to a raw `st_size` — a pair that is true only on the Windows checkout that wrote the files, because
`.gitattributes` stores this repository's text with `eol=lf`. Checked on a clone of the commit that added
stage 8f: **32 of 32 figures mismatch**, each recorded number 90–900 bytes larger than the file the clone
holds. Stage 6 had solved it already (`canonical_bytes()` in `03_estimate.R`, canonical comparison in
`verify_stage6.py` and `validate_artifacts.py`), so the three later stages were the exception rather than the
rule — and the chain could not see it, because the chain only ever ran on the machine that wrote the files.
The three R stages and their three verifiers now share Stage 6's rule, the artifacts were regenerated rather
than re-worded, and the same clone check on the fix reads **0 of 32**.

**What this does not cover.** The suite mutates the *artifacts and the renderer*, not the browser: no
click-through, no keyboard path, no DOM state after the script runs. Those are declared limits in
`presidents-guided-flow-spec.md`, and `verify_answer_js.py` runs the layer under node, where its answers can be
compared with the artifact — nothing here proves the page paints them. The Streamlit app's own verifier
(`verify_app.py`) is untouched: its 2026-10-21 break-tests still stand and still cover the card side. And the
site's coefficient check has only two rows to look at, because no card carries a Design B number — that absence
is the card rule's doing (`design_result_is_channel_level`), not this verifier's, and `verify_site.py` says so
in the count it prints rather than in a promise it cannot keep.

