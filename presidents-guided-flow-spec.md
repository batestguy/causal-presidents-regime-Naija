# Presidents guided flow — specification

**Short name:** `presidents-guided-flow` · **Status:** built — seven screens, two descriptive artifacts, both
verifiers, and the Pages deploy. Portraits remain empty frames (§7.1).
**Written:** 2026-10-25 · **Revised:** 2026-10-25 (framework → static site; changepoint family added)

Adds a guided front end over the published registry. The registry contract, the 36-card rule and the
answer layer's measurements all stay as they are — the flow renders them, it does not re-decide anything.

Companions: `docs/app.md` (today's app), `docs/limitations.md` (why tenure comparison is refused),
`docs/rag.md` + `docs/answer.md` (the chat layer and its numbers), `docs/intent.md` (the gate),
`PHASES.md` Stage 9.

---

## 1. The request, and what it became

> An intro page with all Nigerian political presidents in vertical tabs, and a Begin button. Begin asks what
> variables you wish to study; the next page tells you the identifiable comparisons; you select the DAG +
> diagram; then you see the estimates in simple words, plus a graph of the comparisons by identifiable
> treatment groups, with trend lines and explanations in simple words — and a technical bonus.

Refined in interview into **six screens** (§4), served as a **static site on GitHub Pages** (§3, D-19).

**What the requester actually wants:** not a per-tenure scorecard. The presidents are a **cover** — the faces
of the study window — not a comparison. The readable output is: pick an outcome, be told what this data can
and cannot say about it, see the number or the reason, and see it drawn.

---

## 2. What the flow may read

Every visible number, date, count, status word and reason must be a field of a published registry artifact,
or a constant declared in an `analysis/specs/` file. The page computes nothing.

| Artifact | Vintage | Holds | Step |
|---|---|---|---|
| `registry/dags/index.json` + 36 cards | 2026-10-18 | 12 outcomes, 3 designs, per-card status/blocker, adjustment sets, published results A/B, counts 2/34 | 2, 3, 4 |
| `registry/dags/*.svg` | 2026-10-18 | one causal graph per (outcome × design) = 36 | 3 |
| `registry/series/2026-10-18/` | 2026-10-18 | 12 outcome panels + captions, observed/interpolated/unobserved counts, Stage 3 status, definition breaks | 1, 4, 5 |
| `registry/events/2026-10-18/` | 2026-10-18 | 4 transitions × 2 outcomes, placebo p, pre-trend verdicts, party split as description, `not_claimed` | 6b |
| `registry/estimates/2026-10-18/` + forest plot | 2026-10-18 | 12 specifications, verdicts with failed checks | 4, 6b |
| `registry/robustness/2026-10-18/` + curve | 2026-10-18 | 105 specifications, support counts, sign-flip levels | 6b |
| `registry/diagnostics/2026-10-18/` | 2026-10-18 | per-design gates, blockers, next steps, card status counts | 2, 3 |
| `registry/rag/2026-10-18/` + gate/contract specs + glossary | 2026-10-18 | corpus, eval set, eight gate rules, three answer shapes | 6 |
| **`registry/reference/administrations.json`** (new) | as index | five administrations, portrait paths and status | 0 |
| **`registry/comparisons/<vintage>/`** (new) | as index | descriptive group means and per-group series | 5 |
| **`registry/changepoints/<vintage>/`** (new) | as index | declared breaks per outcome, with native counts | 5 |

**Not readable by the site:** `data/analytics.duckdb`, `dbt/seeds/*`, the network, and any model.

---

## 3. Decisions taken in interview

| # | Question | Decision |
|---|---|---|
| D-01 | Wizard vs the four tabs | **Wizard in front, cards kept behind it.** Today's tabs remain reachable at the end as "go deeper". |
| D-02 | President tabs | **A pure cover.** Name, party, dates, terms, one line on how the tenure ended. No number attributed to a president. |
| D-03 | Portraits | **Frames now, images later.** A named asset path per president, a visible "image not yet supplied" frame, and a `docs/licences.md` row required before any real file is committed. Read from disk, never the network. |
| D-04 | Clicking a president | Nothing is scoped by president; **Begin starts the flow for the whole 1999–2026 window.** |
| D-05 | What the reader studies | **The 12 catalogue outcomes only**, grouped by domain. No covariates, no free text. |
| D-06 | Who picks the treatment | **The app decides**, from the artifacts. |
| D-07 | The tenure-comparison want | Refused once, in plain words, on step 2, with the arithmetic; then routed to the comparisons that exist. Never a per-president verdict. |
| D-08 | Chart grouping | **The reader picks**, in plain words, from the groupings the project can defend (party/tenure; state money-groups). |
| D-09 | Outcome with no usable design | **The reader chooses on the page**: "show me why not" or "show me the closest thing we have". |
| D-10 | Numbers behind the chart | **A new calculation stage is approved** — spec first, run by R, published under `registry/`, verified, in `verify.sh`. |
| D-11 | DAG step | The chosen design's graph is the main exhibit; the other graphs for that outcome are browsable under an amber "failed its check" label; browsing does not change the estimate page. |
| D-12 | Which graphs exist to browse | **Best available only** — the usable design where one exists, the least-bad tested design with a warning where none does. No blank screens. |
| D-13 | Reading level | **Plain words first, term in brackets** — "children dying before five (under-5 mortality, U5MR)". |
| D-14 | Technical bonus | **One collapsed expander per result block.** |
| D-15 | Chart scope | **All 12 outcomes get a grouped chart, stamped "description, not a causal comparison".** |
| D-16 | Navigation | **A real URL per step** — `/compare/?outcomes=<ids>`, `/graph/?outcomes=<ids>`, `/estimates/?outcomes=<ids>`, `/chart/?outcomes=<ids>`. Back/Next are links that carry the selection. *(Supersedes the earlier session-state decision, which existed only because Streamlit has no routing.)* |
| D-17 | The chat | **Kept as the last step and ported to JavaScript** over the published corpus, so the static site still answers. This is a second implementation of the answer layer and is measured as one (D-21). |
| D-18 | Hosting | **GitHub Pages, deployed from CI only when `verify.sh` is green.** The Streamlit app stays in the repo as the local working tool. |
| D-19 | Framework | **Static site generated from the registry** (HTML/CSS/SVG, no framework, no npm dependency), because the content is already static and the flow needs real layout and real URLs. |
| D-20 | Changepoints | **In scope for this build**: a third descriptive family describing when each outcome series changes, held to the rules in §6.3. |
| D-22 | Design-level figures | **One page, `/designs/`, outside the flow.** The forest plot, the specification curve and the event study already exist as artifact-backed figures with recorded byte counts; they were reachable from nowhere. The page reads them and the fields that decided each verdict, shows transitions by month rather than by president, and is linked from the estimate screen and the Ask footer. |

### Assumptions where the interview left a gap

- **A-01** "Best available" is ordered in two steps: **a design that published a number for this outcome comes
  first** — with its `estimated_not_identified` verdict and the check that decided it — and only then by Stage 5
  status `pass` > `degraded` > `fail` > `not_attempted`. Status alone would have ranked a `degraded` Design B
  above the published Design A number, and Design B's result is about the national money channel, not about the
  outcome on the card. The order is a declared field in the built data, not a judgement in code.
- **A-02** The two groupings are (a) **party/tenure** — PDP first, PDP second, APC first, APC second — and
  (b) **state money-groups** — 36 states in four groups by FAAC allocation. Each chart states its grain.
- **A-03** The "closest thing we have" is mapped per outcome in the comparison artifact: the national FAAC channel
  for economy outcomes, the event study for security outcomes, the series panel otherwise.
- **A-04** The site is generated by **one Python build script** (`site/build.py`) that reads the registry and writes
  `site/dist/`; the route table is data, so a new step is a line, not a code path.
- **A-05** The covered language is English only.
- **A-06** JavaScript is written as plain ES modules with **no npm dependencies** and tested with Node's own runner
  (`node --test`, node v24 is installed). Nothing in the chain gains a package manager.

---

## 4. The flow, screen by screen

Six screens. Every sentence that is not chrome comes from an artifact or a spec (§5).

### Screen 0 — Cover · `/`

- Left rail: **five vertical cards**, date order, one per administration —

  | Slug | President | Party | Dates | One line |
  |---|---|---|---|---|
  | `obasanjo` | Olusegun Obasanjo | PDP | 1999-05-29 → 2007-05-29 | two terms, handed over after two |
  | `yaradua` | Umaru Musa Yar'Adua | PDP | 2007-05-29 → 2010-05-05 | died in office |
  | `jonathan` | Goodluck Jonathan | PDP | 2010-05-06 → 2015-05-29 | acting from 2010-02-09; sworn in 2010-05-06 |
  | `buhari` | Muhammadu Buhari | APC | 2015-05-29 → 2023-05-29 | two terms, handed over after two |
  | `tinubu` | Bola Ahmed Tinubu | APC | 2023-05-29 → present | incumbent; end date deliberately open |

  Each card: portrait frame (`site/assets/presidents/<slug>.png`, or the "not supplied" frame), name, party,
  dates, terms, the one line. No number, no verdict, no series. Clicking selects; it filters nothing.
- Right: title, the existing caption *"Presidential transitions and national outcomes in Nigeria, 1999–present"*
  and *"Read the assumption before the number"*, three derived paragraphs, and the ratio — **2 of 36 model cards
  carry a published number; the rest say why not.** One button: **Begin**.

### Screen 1 — What do you want to study? · `/study/`

Multi-select of the 12 outcomes grouped Health / Education / Security / Economy, each row with plain name, unit,
direction and coverage word. One caption under the list: 4,008 outcome-months, 764 observed, 1,826 filled in
between, 1,418 with nothing. Next is disabled until something is chosen, and says why.

### Screen 2 — What this data can tell you · `/compare/?outcomes=<ids>`

One row per chosen outcome, left to right: plain label (term in brackets) → **the comparison the app chose**, in
plain words, with design id → status word (*usable* / *usable with a warning* / *the check it needed failed* /
*not attempted*) → one sentence on what that comparison assumes → the reason and next step where there is no
usable design, with the two reader choices from D-09.

**The tenure paragraph appears once, at the top of this screen**, not per row.

### Screen 3 — The assumption and the graph · `/graph/?outcomes=<ids>`

The chosen design's SVG as the main exhibit, with the assumption in a sentence, the adjustment set resolved to
`label (node_id)`, the node assumed absent, and the cannot-rule-out list. Beneath: a collapsed "other graphs for
this outcome", each with its assumption and an amber label naming the check it failed. Browsing is read-only.

### Screen 4 — The estimate in plain words · `/estimates/?outcomes=<ids>`

One block per outcome, in the order chosen:

1. **Plain reading** — direction, whether the range includes zero, the sample, the assumption in one sentence,
   caveats, and the technical words the answer uses defined from the glossary.
2. **The number**, when published — coefficient, 95 % interval, p, observations, units, months, verdict and the
   check that decided it.
3. **Or the reason** — code in plain words, detail sentence, pointer to the design-level result.
4. **Technical expander** (D-14) — every field of the specification, the adjustment set, the Stage 5 pre-check,
   one Stage 7 grid line, the artifact path.

A Design B number says in those words that it is about the **national FAAC channel**, not the card's outcome.

### Screen 5 — The comparison chart · `/chart/?outcomes=<ids>`

- A two-option control in plain words: *by who was in power* / *by how much money a state received*.
- One chart per outcome, from the comparison family, with the grouping named plainly and technically, **trend
  lines with observed points solid and interpolated months dotted** (the panels' grammar, learned once), declaration
  breaks marked where they fall, a plain caption per group, and the stamp **"description, not a causal comparison"**.
- **Break markers** from the changepoint family where the declared rule found one, labelled "the series changes
  here", never as an event of a presidency.
- Where an outcome has no monthly life (education stops in 2010), the chart says so instead of drawing a line.

### Screen 6 — Ask, and go deeper · `/ask/`

- The **Ask** box, now JavaScript: the eight gate rules, BM25 over the published corpus, the three-shape contract
  and its post-check, the glossary readings — all read from JSON the build emits from the same specs the Python
  layer reads (§6.4). It states its measured limit (36 of 38 answered) in one line and refuses with rule, meaning,
  passage and citation.
- **Go deeper:** the card-level screens (Model card, Design-level results, What this reads) generated into the
  same site, so the contract of `docs/app.md` §4 still holds on the published page. The **Design-level results**
  half is built as Screen 6b; the Model card and What-this-reads halves are not.

### Screen 6b — The design-level results → `/designs/`

The three figures Stage 8 published — the forest plot, the specification curve and the event study — each exist
as an artifact with a recorded byte count, and each is reachable from exactly one page. This is that page. It is
**not a step in the flow**: it is not per-outcome, so putting it between two outcome screens would either break
the selection carried in the URL or imply that the reader's outcomes change what it shows.

- **One section per artifact family:** what was published (the forest plot, which carries a panel per design),
  the grid that qualifies it (the specification curve), Design C's non-run, and the transition study. Each
  section carries the figure, the artifact's own `layout` sentence describing what it draws, and the fields that
  decided the verdict.
- **The number is never alone.** Design A's section shows its verdict (`estimated_not_identified`), the failed
  check in the artifact's words, the 24-month placebo estimate and the lead-shift p with its draw count. Design B's
  shows its support counts, the coefficient range across the grid and the in-time placebo p. Design C's shows why
  it was not run and its declared next step — the absence is an argument, not a blank.
- **The transitions are shown by month, never by name.** The event study is a timing comparison; the artifacts
  carry surnames in their `label` fields, and this page prints none of them. That is the "no per-president
  verdict" rule (§5.5) applied to the one screen where breaking it would be easy.
- **What it reads:** `registry/estimates/<vintage>/` (specifications, verdicts, checks, the forest figure),
  `registry/robustness/<vintage>/` (support, spread, the in-time placebo, the curve) and
  `registry/events/<vintage>/` (verdicts, the declared rule, `not_claimed`, the event figure). No new stage and
  no new number: this screen is a reader for artifacts that already exist.
- **Reached from:** the estimate screen, where a card with no number already names the design's result instead of
  showing one, and the Ask screen's footer.

---

## 5. What the built site must never do

1. **No number typed into a template, script or stylesheet.** Every value comes from the registry or a spec.
2. **No runtime fetch, no model, no database.** The site is files; JavaScript reads only same-origin JSON emitted
   by the build.
3. **The card wins.** Page and card disagree → the card is right and the page is a defect.
4. **A reason is never silent.** Every outcome without a usable comparison names a code, a detail and a next step.
5. **No per-president verdict** — not in a tab, a chart label, a caption, an alt-text or a tooltip.
6. **A descriptive chart is never labelled causal**; a causal number is never shown without its verdict and the
   check that decided it.
7. **Vintage discipline.** Every page carries the registry vintage it was built from; the build refuses a mixed
   vintage; CI redeploys only from a green chain, so a stale vintage is never silently served (UI-08).
8. **Attribution travels.** Every page footer carries the licence rows for the sources the page's numbers came from
   (UCDP CC-BY, World Bank terms, NBS/OAGF), read from the licence register rather than typed.

---

## 6. What has to be built

### 6.1 `registry/reference/administrations.json`

Five administrations — `admin_id`, `slug`, `president`, `party`, `start_date`, `end_date` (null for the incumbent),
`n_terms`, `note`, `portrait_path`, `portrait_status` — generated from `dbt/seeds/raw_administration.csv` so the
site's copy cannot drift from the base's spine. Verified in the site verifier (five rows, dates equal to the seed,
exactly one open-ended).

### 6.2 `registry/comparisons/<vintage>/` — descriptive group means (new R stage)

- **Spec first:** `analysis/specs/comparisons.yml` declares the groups, the group-mean rule, the grain, the windows
  and the caption templates, before any number is computed.
- **Engine:** `analysis/R/08_comparisons.R` reads the base and writes `comparisons.json` plus one SVG per
  (outcome × grouping), recording each figure's byte count — the contract the forest plot and series panels carry.
- **Content:** group label (plain + technical), units, months, the group series (observed points, interpolated
  months flagged), the mean over the declared window, observed share, definition breaks inside the window, a plain
  caption, and the closest-evidence mapping (A-03).
- **Forbidden:** any test statistic, p-value, standard error or interval. A contrast is an estimate; estimates
  belong to Stage 6.
- **Groups:** the four published tenure strata; four state groups by nominal FAAC dose (2016-12 → 2026-06, with the
  pre-2016 months a declared gap, not a zero).

### 6.3 `registry/changepoints/<vintage>/` — when each series changes (new R stage, D-20)

- **Spec first:** `analysis/specs/changepoints.yml` declares method, cut-offs and handling rules before fitting:

  | Rule | Value |
  |---|---|
  | Method | `strucchange::breakpoints` (Bai–Perron) on the native observations; `segmented` only for a fixed-date fit |
  | Input | **native observations only** (`fact_observation_native`) — never the interpolated spine, whose 1,826 filled months would be detected as breaks (the C-30 trap) |
  | Minimum | ≥ 20 native observations for a search; 7–19 may receive a **fixed-date** segmented fit at inaugurations only; < 7 gets no fit and says so |
  | Max breaks | declared per regime (1 for 20–40 observations, 2 above), selected by BIC |
  | Definition breaks | passed in as **known** breaks or labelled as measurement, never reported as era changes |
  | Inference | **no p-values, no intervals, no test statistics.** This is description; timing inference belongs to the events stage's enumerated placebo |
  | Attribution | a break is never described as a president's effect |
- **Engine:** `analysis/R/09_changepoints.R` → `changepoints.json` (per outcome: native count, declared method,
  selected breaks with a plain sentence, refused outcomes with the reason) + per-outcome SVG with break markers,
  byte counts recorded.
- **Coverage as built:** fatalities and incidents (287 native months) get a real search; the 25–27-observation
  annual outcomes get 1 break; skilled_birth 8, literacy_youth 7, primary_completion 8, ner_primary 9 get either a
  fixed-date fit or an explicit refusal — the artifact says which, per outcome, rather than dropping them silently.
- **R dependencies:** `strucchange` and `segmented` are installed on this machine; `changepoint` and CausalImpact
  are not, and are **not** added.
- **Explicitly out of scope:** Granger causality, VAR, any lead–lag test — 27 annual points, a 16.2 % observed
  spine, and Design B's local projection already carries the one transmission question the data supports.

### 6.4 The site

- **`site/build.py`** — one Python build script, no new dependency. Reads the registry, `analysis/specs/*.yml`,
  `docs/glossary.md` and the licence register; writes `site/dist/`:
  - `index.html` (cover), `study/index.html`, and per outcome-set routes for screens 2–5;
  - `cards/<outcome>__<design>.html` and the design-results pages (the "go deeper" half of D-01);
  - one static copy of each SVG, referenced by relative path;
  - `data/*.json` — the normalised `gate.json`, `contract.json`, `glossary.json`, the corpus and the eval answers;
  - `assets/` — CSS and the ES modules; `assets/presidents/` for portraits.
- **Route table as data:** the six-step order, the disabled-reason strings and the back/next labels live in
  `analysis/specs/guide.yml`, so a step is a spec line rather than a template.
- **Plain-words dictionary:** `analysis/specs/guide.yml` maps design id → comparison phrase, `diagnostics_status` →
  status word, reason code → sentence, grouping id → grouping name. The site's wording lives in a reviewable
  document, not in Python or JavaScript.
- **JavaScript:** plain ES modules, no npm, no framework. `answer.js` implements the gate, BM25, the three-shape
  contract, the post-check and the glossary reading **from the JSON the build emits from the same YAML specs the
  Python layer uses** — so the rules exist once, in `analysis/specs/`, and the JS carries no second copy.
- **Streamlit stays.** `app/streamlit_app.py` and `app/registry_data.py` remain the local working tool; nothing is
  deleted. The site is a second renderer over the same artifacts, not a replacement of the registry contract.

### 6.5 Verification

- **`tests/verify_site.py` (new)** — runs `site/build.py` into a temp directory and parses the emitted HTML with
  stdlib `html.parser`, then asserts against the artifacts: all 12 outcomes reachable; every rendered sentence,
  status word, reason and grouping present in `guide.yml`; administration dates equal to the seed's; the ratio
  equals the index's counts; every published coefficient appears with its verdict and failed check; a Design B
  number never appears on an outcome page; no per-president verdict anywhere; the vintage stamp and the licence
  rows present; the changepoint and comparison captions equal their artifacts.
- **`tests/verify_answer_js.py` (new)** — runs the JS answer layer under `node --test` against the published
  `answer_eval.json`: the same questions, the same citations, the same needles, the same plain reading. **The JS is
  accepted only if it reproduces the artifact's measured answers**, not if it merely answers.
- **`tests/verify_comparisons.py`, `tests/verify_changepoints.py` (new)** — re-derive group means, native counts,
  selected breaks and byte counts from DuckDB; fail on any statistical field in the descriptive artifacts; fail on
  a break that coincides with a definition break without being labelled as measurement.
- **`tests/verify_guide.py` (new)** — coverage both ways: every design, status, reason code and grouping the
  renderer can show has an entry, and every entry is used.
- **`scripts/verify.sh`** gains the two R stages, the site build, and the new verifiers; `.github/workflows/verify.yml`
  gains a `pages` job that deploys `site/dist/` **only when the chain passes**, stamping the vintage.
- **Break-tests before publishing**, as with every earlier stage: a typed count, a switched status word, a dropped
  reason, a caption moved by one, a group mean moved, a fabricated portrait, a per-president verdict, a break
  reported on an interpolated month, and a JS answer that drifts from the artifact. Each must fail a verifier;
  each restored byte-for-byte.

---

## 7. Open questions for the requester (do not block the build)

1. **Portraits.** Which images, from where, under what licence? Until answered the frames stay empty and
   `docs/licences.md` gains no row.
2. **`literacy_youth`** still says `declared_gap` while the base carries 7 observations to 2024. Changing it
   regenerates all 36 cards — the requester's call, not this build's.
3. **A third grouping** (geopolitical zone, say) is a line in `comparisons.yml` and a new spec round; the artifact
   schema is group-agnostic, the spec is not.
4. **Whether the public site shows the chat at all**, now that it is a second implementation with a second
   measurement. It is in scope (D-17); it can also be shipped behind a "not yet measured" note if the requester
   prefers to publish the flow first.

---

## 8. Out of scope

- Any per-tenure or per-president estimate, ranking or scorecard.
- Granger causality, VAR, lead–lag tests, or any new inference from the annual series.
- Interactive node-level graph clicking; a monthly series for an outcome that has none.
- Changing any published number: this build adds description, routing and a renderer; it re-fits nothing.
- Hosting anything with a runtime. Pages serves files; the chat's Python original stays local.

---

## 9. Acceptance criteria

1. A reader reaches a plain-words estimate — or a plain-words reason — in **six screens**, on a phone, with no
   document, and can share the address of any screen.
2. Every one of the 12 outcomes answers something: a comparison, a warning, a break description, or a stated reason
   with a next step.
3. Every number, date, count, status word and reason on screen is traceable to an artifact, and `tests/verify_site.py`
   proves it by parsing the built HTML.
4. The JS answer layer reproduces `answer_eval.json` — same citations, needles and readings — or it is not shipped.
5. `scripts/verify.sh` is green with the two new R stages and four new verifiers, and every existing verifier still
   passes unchanged, including the 36-card contract and the Ask tab's measured answers.
6. The deployed site stamps its vintage, carries its attribution rows, and is rebuilt only from a green chain.
7. The break-tests in §6.5 all fail their verifiers and are restored byte-for-byte.
8. `docs/app.md` describes the flow and the static build as built, with its counts and ratio derived from the
   artifacts.
