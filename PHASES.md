# causal-presidents — Phase Plan: Data Collection → Analysis

**Scope of this document.** Stages 0–8: from an empty repo to a defensible set of analysis products.
The interactive app is Stage 9, downstream, and **consumes Stage 8 output only** — it never touches R.
Companions: `nigeria-causal-inference-spec.md` (design decisions), `#CausalPresidents.txt` (base spec),
`knowledge.md` (environment).

**Repo title (decided 2026-10-10).** Slug `causal-presidents`. Display title **"Causal Presidents"**.
README H1: *Causal Presidents — Presidential Transitions and National Outcomes in Nigeria, 1999–present*.
Deliberately excluded from any title or subtitle: *performance*, *scorecard*, *accountability*,
*ranking*. Those words presuppose a verdict the analysis cannot deliver, and the title is part of the
honesty layer.

**Governing principle.** The data is tiny. National monthly series are ~320 rows; the full state panel is
~12,000. Nothing here is a compute problem. Every hour in this plan is spent on **validity**, which is why
Stages 3 and 5 exist at all.

---

## Stage overview

| Stage | Delivers | Blocks | Exit gate |
|---|---|---|---|
| 0 | Governance, licences, decisions, env pins | everything | A stranger can read the decision and licence logs |
| 1 | Source register | ingestion | Every metric maps to a source, or is a declared gap |
| 2 | Immutable raw layer | validation | Every row traces to a retrieval event |
| 3 | Quality gates + vintage report | harmonisation | No series advances without a machine-readable quality status |
| 4 | Analytical base (dbt) | diagnostics | One table read by both models and app |
| 5 | Design memo | estimation | Each model has a stated assumption and a passing pre-check |
| 6 | Model registry (R) | robustness | Every card satisfies the six-item rigor floor |
| 7 | Spec curve + sensitivity | products | Preferred spec marked, support count computed |
| 8 | Registry, narrative, RAG corpus | the app | App buildable without touching R again |

**Critical path:** 0 → 1 → 2 → 3 → 4 → 5 → 6. Stage 5 is where models die cheaply. Skipping it is the
single most likely way this project becomes indefensible.

---

## Stage 0 — Scaffolding, governance, decision locks

**Purpose.** Freeze decisions now that would otherwise be made silently, mid-analysis, in whichever
direction produced a nicer number.

**Work**

- Directory skeleton (below), `.gitignore` with `data/raw/**` and any credentialed extract excluded,
  `.gitattributes` normalising line endings (Windows host, cross-platform R/Python).
- `docs/licences.md` — one row per source: access path, licence/terms, **redistribution permitted y/n**,
  substitute if n, attribution text.
- `docs/decisions.md` — every `[LOCKED]` item from the base spec, plus the interview overrides, each with
  a date and a one-line reason. Minimum entries: R-for-everything; monthly panel with quarterly
  robustness; exposure metric D1 primary (below); mixed pre-fit donor pool; public ungated access;
  Tier 4/5 promoted into v1; assumption-first answer shape.
- `docs/data-dictionary.md` — skeleton with one row per variable: name, unit, direction (↑/↓ better),
  source, retrieval method, imputation rule, vintage rule.
- Environment pins: `renv.lock` initialised **project-local**, Python pinned from the `ds-general` env.
- Vintage convention: `vintage_date` = ingest date, carried on every table; `metric_anchor` logs anchor
  revisions as new vintages rather than edits.

**Exit criteria.** Decision log and licence register are complete enough that an outsider could tell what
is collected, what may legally be published, and why each methodological choice was made.

**Gotcha that will bite.** Initialising `renv` while the system library is on `.libPaths()` snapshots all
~1,075 installed packages. Use a project library, and confirm `renv::status()` is clean afterwards.

---

## Stage 1 — Source register and access verification

**Purpose.** Turn base spec §5 from a wish list into an access map **before** writing a single client.
This stage frequently kills or reshapes a planned model, which is exactly why it runs first.

**Per-source record:** dataset · granularity · coverage years · update cadence · access path (keyless
API / free key / manual download) · credentials needed · licence · metrics it feeds · known failure mode.

| Source | Access | Feeds | Verified 2026-10-10 | Constraint |
|---|---|---|---|---|
| World Bank Indicators | keyless API | GDP, inflation, population, health, education | ✅ **works keyless** — real paginated JSON (66 NG u5mr records, 29,544 indicators) | Revision cycles; rebasing breaks |
| IMF DataMapper | keyless API | macro cross-checks | ⚠️ **403 to scripted clients, 200 via `read_url`** | Blocks non-browser UA; needs browser-like headers or the relay |
| FRED `DCOILBRENTEU` | free key | Brent crude | ✅ **landed 2026-10-11** — key registered, HTTP 200, 10,275 daily obs 1987→2026, provenance verified (C-23) | **Daily** → freeze the daily→monthly resample rule here before any oil-adjusted estimate |
| NBS | manual download | GDP, CPI, unemployment, **state IGR (quarterly)**, **FAAC disbursement reports** | ✅ reachable (HTML, 200) | No API — PDF/HTML parsing; definitional changes |
| CBN | manual download | FX, external reserves | ✅ reachable (HTML, 200) | No API; broken series across FX regimes |
| OAGF (`oagf.gov.ng`) | free, no key | state FAAC allocation (monthly) | ✅ **corrected 2026-10-16: reachable** — 83 monthly PDFs crawled (2019-04 → 2026-06), provenance verified | The *Open Treasury portal* is still unreachable (20s timeout); the OAGF's own site publishes the monthly workbooks from `/wp-content/uploads/`. **D1's primary source was recovered, not substituted** (C-39/C-41) |
| ~~Open Treasury~~ | ~~open portal~~ | ~~state FAAC allocation~~ | ❌ **unreachable — 20s timeout on both curl and the read_url service** | Its OAGF function is covered by the row above; nothing else here was needed |
| DHIS2 (Nigeria HMIS) | verify credentials | immunisation (penta3) | ⚠️ host reachable (302→login); **Nigeria tenant access unverified** | Institutional credentials; not guaranteed |
| DHS / NDHS | registration | u5mr, MMR, skilled birth | — not probed (needs account) | 5-yearly cycles (2003/2008/2013/2018/2023-24); **no redistribution** |
| MICS, UN IGME | free | complementary / modelled child mortality | — not probed | Modelled series ≠ observed |
| UNESCO UIS | free API | literacy, completion | ❌ **every path 404, including the API root** | Endpoint structure changed entirely. **Education fallback 1 blocked (C-11)** |
| NEMIS / NEDI | manual portal | enrolment | ❌ **20s timeout — unreachable** | **Education fallback 2 blocked (C-12)**. Third unreachable Nigerian gov host, with OAGF and Open Treasury |
| ACLED | registration | fatalities, incidents | ❌ old host dead; ✅ **site reachable, docs confirm OAuth** | **Not a key — an OAuth app registration (C-13)**. 12-month embargo; no redistribution |
| UCDP GED | free token | battle deaths | 🔑 **401 — `x-ucdp-access-token` required**; ✅ Swagger UI live; ✅ `ucdp.uu.se` reachable | Free token registration; endpoint and header confirmed (C-14) |

**Exposure metric decision (delegated, resolved here).** The "open and free sources" constraint selects it:

- **D1 (primary) — FAAC allocation per capita.** Monthly, state-level. **Landed 2026-10-16** — both
  publications of the monthly workbook are acquired: the OAGF's own PDFs (the primary, 2019-04 → 2026-06)
  and the NBS republication (2016-12 → 2024-07), 174 documents in total, 114 months × 36 states, every
  document reconciled to its own published Total row. The Open Treasury portal is still unreachable and no
  longer matters: the OAGF publishes the workbooks itself. As predicted here, the series does not reach
  1999, so **  the panel starts when the series does and the earlier years are a declared gap, not
  back-filled** — `state_panel.dose_status` says `declared_gap` for every month before 2016-12. The
  nominal dose is **Stage 3 gated** (2026-10-17: 37 series, all `flagged` on distribution-cycle spikes —
  C-43) and the panel carries that result per row; the per-capita form still needs the population
  denominator decision (X-09).
- **D2 (secondary) — FAAC share of state total revenue** = FAAC ÷ (FAAC + NBS state IGR). Measures
  *exposure* (dependence on federal transfers), computable from two open sources.
- **D3 (optional, flagged constructed) — FX/import intensity of the state consumption basket.** Needed for
  the 2023 naira-float window. No ready series exists; if built, it ships with its construction
  assumptions on the model card and is a robustness axis, never the headline dose.

Rejected on availability: oil-derivative revenue share (only patchy state audited accounts) and
net-FAAC-after-deductions (not reconstructable consistently back to 1999).

**Exit criteria.** Every base-spec §6 metric and every variable required by design families A, B and C
maps to a named source, **or is recorded as a declared gap.** Declared gaps are legitimate; silent holes
are not.

**Gotchas.** ACLED's 12-month embargo structurally removes the most recent year — the 2023 subsidy window
analysis cannot use ACLED for its most recent leg without saying so. NDHS's five-year cycle means annual
u5mr is mostly interpolation, so it must render as flagged segments, never smooth annual fact.

---

## Stage 2 — Ingestion: the immutable raw layer

**Purpose.** Land exactly what the source returned, with proof of when and what.

**Work**

- One Prefect flow per source. **No transformation in this layer** — type coercion included.
- Landing contract per retrieval: payload + `source, url, params, retrieved_at, http_status, sha256,
  row_count`. A vintage is the set of retrieval events stamped with one date.
- Manual sources: `ingestion/manual/inbox/` drop zone + one parser per file format, recording the file
  hash so a re-download is detectable and re-parsing never requires re-OCRing.
- Idempotency: natural keys per source; re-running a vintage must not duplicate rows.
- Overwrite is forbidden. A correction creates a **new vintage**; the old one stays for revision
  detection in Stage 3.

**Exit criteria.** `raw` schema populated for one complete vintage; any single value can be traced back to
the retrieval event that produced it.

**Gotchas.** NBS/CBN PDFs need OCR (tesseract 5.4 is installed) — cache the extracted text, do not re-OCR
on every run. World Bank API pagination and silent restatements need an explicit per-page loop and a
row-count assertion. Freeze the Brent daily→monthly aggregation rule here, because changing it later
changes every adjusted estimate.

---

## Stage 3 — Validation and quality gates (the honesty chokepoint)

**STATUS: BUILT 2026-10-11 · RE-RUN 2026-10-17 over the FAAC document source.** 125 series gated
(60 ok, 65 flagged, 0 empty) → `registry/quality/<vintage>/`. Config in
`analysis/specs/quality.yml`, gates in `ingestion/quality/gates.py`, runner
`ingestion/flows/check_quality.py`, independent verifier `tests/verify_quality.py`. Exit criteria met:
every series has a gate result, enforced in code — including the 37 that only exist after a parser reads
a document, which is what the 2026-10-17 re-run had to add (C-42). See decisions Q-01…Q-08, S4-19,
C-26…C-29, C-42, C-43.

**Purpose.** This is where "rigorous enough" is actually earned. Stage 8's limitations section is mostly
written from this stage's output.

**Gates** (base spec §13 supplies the first two; the rest are the upgrade):

1. **Gap gate** — any metric with a >3-month gap is flagged.
2. **Spike gate** — any >50% month-over-month move is flagged as a probable data error, not analysed as a finding.
3. **Revision gate** — new vintage vs previous for the same period beyond tolerance → logged as a
   revision event, never a silent overwrite.
4. **Definition-drift gate** — series whose definition changed (unemployment methodology, GDP rebasing
   in 2014, FX regime breaks) carry an explicit break annotation.
5. **Provenance gate** — every interpolated or extrapolated value carries its method, so imputation can be
   rendered as dashed and excluded in robustness.

**Output.** A machine-readable vintage quality report plus a human-readable page. Every published series
carries a quality status field that travels with it into the app.

**Two implementations notes, learned by running it.** (a) A single 50%-relative spike rule flagged 52 of
88 series, because a *growth rate* moving 0.5%→3.0% is a 500% relative change and a 2.5-point move; the
measure is now declared per series type (relative for levels, percentage points for series already in
percent). (b) Only adjacent periods are compared — the earlier zip over consecutive *observed* periods
reported a multi-year level change across a hole as a one-year "spike".

**Third implementation note — the one that cost a re-run (2026-10-17).** The flow and its verifier both
walked `data/raw` and assumed every page file was JSON, which held while every source was an API. The
FAAC landing put 174 PDFs and spreadsheets in that directory, and `tests/verify_quality.py` then died on
the first byte of a PDF while the report on disk still read 88 series — the gate had no result for the
raw layer's newest source and nothing said so (C-42). Document sources are now declared in `quality.yml`
and gated from their **parsed** artifact, so the gate reads the same series Stage 4 reads. With FAAC in,
the report is **125 series — ok 60, flagged 65, empty 0**, and the dose plus its gate status is on the
panel. See S4-19, C-42, C-43.

**Exit criteria.** No series reaches Stage 4 without a gate result; the quality report is published with
the vintage timestamp.

---

## Stage 4 — Harmonisation: the analytical base

**STATUS: BUILT 2026-10-11.** `fact_metric` holds **7,682 rows = 23 metrics × 334 months
(1999-01 → 2026-10)**, built by dbt into a local DuckDB (`data/analytics.duckdb`, gitignored and
reproducible). Rules declared in `analysis/specs/harmonisation.yml`, models under `dbt/models/`, seeds
under `dbt/seeds/` (administration spine, metric catalogue, shock bands, the 37 state units), and a build
of 144 nodes — 4 seeds, 22 models and 118 tests, 19 of them singular — independent verifier
`tests/verify_harmonisation.py`, and every column documented in `docs/data-dictionary.md`. Exit criteria met: one analytical base table, every column
documented, reproducible from the vintage plus the anchor config — with **20 break-tests** showing each
new guard can fail. What the stage *measured* is the important part: **10.1 % of the base is observed**
(775 of 7,682 rows), because every open source here is annual, so the 2023 subsidy window is not
monthly-visible on the landed CPI (C-30). See decisions S4-01…S4-12, M-11, C-30…C-32.

**Purpose.** One table that the models and the app both read, with nothing computed at render time.

**Work (dbt: staging → analytics)**

- Staging: one model per source — typed, renamed, deduplicated, no business logic.
- Analytics: `fact_metric`, `dim_metric` (label, unit, **direction**), `dim_administration`,
  `metric_anchor`, and the state panel.
- **Indexing:** store `value` and `value_indexed` (index to 100 at January 2000, fixed anchor) plus the
  anchor row. Base spec §8 requires the subtitle to state the anchor and tooltips to show raw values.
- **Direction labels** are a dimension column, never inferred at render time.
- **Frequency alignment:** monthly spine. Annual series interpolated with the method recorded; quarterly
  state IGR apportioned to months by a documented rule; quarterly NBS series labelled as such rather than
  smoothed into monthly pretence.
- **Administration spine:** 5 rows, party, start, end, `oil_price_at_start`. The Yar'Adua → Jonathan
  boundary must be a single decided date, logged: acting from 2010-02-09, sworn in 2010-05-06.
- **Tenure stratification columns:** `PDP_first`, `PDP_second`, `APC_first`, `APC_second` — base spec §9
  requires party effects stratified by term, not aggregated.
- **State panel:** 37 units × month; joins FAAC (D1 — **landed 2026-10-16 as the nominal dose** and
  **gated 2026-10-17**, so `dose_gated`/`dose_gate_status` are read from the Stage 3 report rather than
  set by hand; the per-capita form waits on X-09), state IGR (D2), ACLED/UCDP state attribution, and
  whichever health/education series survive Stage 1. Built 2026-10-11 and populated without a schema
  change.

**Exit criteria.** A single analytical base table, every column documented, reproducible from
`vintage_date` + anchor config alone (base spec §18).

**Gotchas.** GDP rebasing (2014) means pre-2014 and post-2014 levels are not the same series — decide and
document whether the index anchor is pre- or post-rebase, and annotate the break. Per-capita doses need
one consistent population denominator; World Bank and NBS projections diverge, so pick one and say why.
ACLED geocoding quality determines how many events can be attributed to a state.

---

## Stage 5 — Pre-analysis diagnostics and design validation

**STATUS: BUILT 2026-10-11 · RE-RUN at vintage 2026-10-16 (2026-10-17).** The memo is
`docs/design-memo.md`; the machine-readable result is
`registry/diagnostics/<vintage>/diagnostics.json` + `report.md`, attached to all 36 cards. Config in
`analysis/specs/diagnostics.yml`, engine in `analysis/R/02_diagnostics.R`, independent verifier
`tests/verify_stage5.py`. Exit criteria met: **every one of the 36 (outcome × design) cards carries a
pre-check verdict, and none passes** — 15 fail, 7 degraded, 14 not attempted, 0 pass.

**What the re-run changed, and why it was not optional.** The 2026-10-11 verdicts were computed against a
base that no longer exists: Family A read "dropped — 0 of 12,358 dose values present" and Family B read
"FAAC is absent". The dose has since landed and been Stage 3 gated, so the *reasons* were wrong even where
the verdicts were not, and `tests/verify_stage5.py` was failing rather than tolerating the drift. Two
substantive changes came out of it:

- **The dose is now measured on the axis the estimand is written on, separately from the other axes**
  (`dose.specified_axis: D1`). The nominal FAAC column landed and passes its variance checks; D1 is per
  capita and still waits on the population denominator (X-09). Family A therefore stays **dropped, for a
  different and stated reason** — `specified_dose_axis_absent:D1 and no_state_attributed_outcome` — and a
  present-but-unspecified axis can no longer turn the gate green by proxy (S5-10).
- **The Family A card text is derived from the dose block, not written as prose next to it.** The earlier
  version hard-coded "no dose series has landed", which was true when written and false by the time it
  mattered; the card could not notice its own premise changing (C-44).

See decisions S5-01…S5-10 and C-44.

> **Two of those three reasons expired between 2026-10-16 and 2026-10-17, and the re-run above is what
> recorded it.** The FAAC dose is landed and gated, so "0 of 12,358 dose values" and "FAAC absent" no
> longer describe the base: `state_panel` now carries 4,104 dose values and `faac_national_monthly` is a
> real monthly fiscal series. The verdicts above are the current ones — 0 of 36 pass, with the reasons
> recomputed. What has *not* changed is the grain: the dose begins 2016-12, so the Tier-3 system is 10
> years long at the annual grain the outcomes are on, against the ~20-observation floor Johansen needs
> (C-41). And what the re-run refused to do is quietly convert a nominal dose into the per-capita one the
> estimand needs: that is X-09, a decision.

**Purpose.** Establish what the data can support **before** estimating anything. This stage is why the
project is defensible, and it is the one most likely to be skipped under enthusiasm.

**Work**

- **Integration order:** ADF, KPSS, PP on every series (`urca`).
- **Cointegration:** Johansen on the Tier-3 system. The VECM-vs-ARDL choice follows the test result, not
  preference — base spec §9 specifies the fallback rule.
- **Structural breaks:** identify the shock windows in the national series; confirm the 2016, 2020 and
  2023 windows are visible in the data rather than assumed.
- **Dose validation (Family A):** does D1 actually vary enough across states and time to identify
  anything? A dose with near-zero cross-state variance cannot support a dose-response design, and no
  estimator fixes that.
- **Parallel-trends pre-check** on the pre-period for every candidate window.
- **DoF and power reckoning:** compute the detectable effect size given N and residual variance, for the
  national VECM especially, and write it down before seeing any estimate.
- **Collinearity check across D1/D2/D3** — do not proceed with a dose that is mechanically collinear with
  the outcome's pre-trend.

**Output.** `docs/design-memo.md`: for each outcome, which family is credible, which is not attempted, and
the diagnostic that justifies the call.

**Exit criteria.** Every planned model has a stated identifying assumption and the specific diagnostic that
supports it. Models failing their pre-check are dropped **here, on the record** — which is far cheaper than
dropping them after their estimate looks inconvenient.

---

## Stage 6 — Estimation (R)

**Work**

- **Family A — state dose-response DiD.** Callaway & Sant'Anna group-time ATT (`did`), with `fixest`
  two-way FE as a cross-check and event-study plots. Inference by permutation over treatment dates plus
  state-clustered wild bootstrap.
- **Family B — VECM / ARDL.** Oil × administration interaction retained (base spec §9: oil is not
  partialled out as a nuisance; differential response to the same shock is the estimand). Long-run
  multipliers with bootstrap and delta-method intervals reported together.
- **Family C — synthetic control.** Donor pool screened by pre-treatment fit; in-space placebo across
  every donor; in-time placebo; leave-one-donor-out; pool composition as a robustness axis.
- Every model emits a **model card** (schema per the design spec §6) + tidy result tables (Parquet/CSV) +
  a diagnostics bundle. Nothing is typed by hand; estimates flow R → artifacts → app.

**Exit criteria.** Every card satisfies all six rigor-floor items (intervals; placebo/pre-trend/permutation;
confounding sensitivity; DoF disclosure; randomization inference; named assumptions). A card missing one is
fixed or dropped — never rendered with a gap.

**Gotchas.** Bootstrap intervals on a VECM estimated from ~26 annual observations are wide and unstable;
the interval method belongs on the card. **A multiplier whose interval spans both signs is not a finding**
and must not be written up as one, however good the point estimate looks.

---

## Stage 7 — Robustness and the multiverse

**Work**

- Build the specification grid: family × adjustment tier × covariate set × lag order × event window ×
  imputation handling × index anchor × donor pool.
- Fit the full grid and store every result — including the ones that disagree.
- Sensitivity: Oster delta for unobserved confounding; Rosenbaum gamma where applicable.
- Inference robustness: permutation/randomization inference; in-time placebo.
- Render the specification curve with the preferred specification marked.

**Exit criteria.** Support count computed per sign, preferred spec marked, and regions where the sign
flips visible in the figure rather than buried in a table.

---

## Stage 8 — Analysis products and interpretation

**Work**

- **Model registry assembly** — the app's complete data contract.
- Figures: forest plot with intervals, event-study panels, specification curve.
- **Limitations drafted before findings** (base spec §19 ordering discipline: limitations longer than
  findings). Write what cannot be identified first; then what holds.
- **RAG corpus** — one chunk per model card, plus methodology, data dictionary, shock annotations,
  administration table, limitations. Share the registry's `vintage_date` stamp so a stale answer cannot
  outlive the model it quotes.
- **RAGAS evaluation set** — question/answer pairs authored against the finished registry, wired into CI.

**Exit criteria.** Stage 9 can be built without opening R. If a card and the narrative disagree, the
**card wins** and the narrative is regenerated.

---

## Cross-cutting conventions

- **Vintage discipline.** Every table carries `vintage_date`; corrections create vintages, never edits.
- **Single source of truth.** Chart, model card and chat answer all read the same exported artifacts.
- **Licence rule.** Derived aggregates and code publish; raw ACLED and DHS/NDHS never do. A stranger with
  their own credentials must be able to reproduce the aggregates.
- **Imputation is always visible.** Dashed segments on charts, a flag on the card, an exclusion axis in
  the curve.
- **No model at render time.** Base spec §18, retained without exception.

---

## Directory skeleton

```
causal-presidents/
├── README.md                 # pitch, screenshot, how to run, link to methodology
├── knowledge.md  AGENTS.md
├── docs/                     # decisions.md · licences.md · data-dictionary.md
│   ├── design-memo.md        # Stage 5 output — the defence of the design
│   ├── methodology.md        # public page content
│   └── spec/                 # base spec + design spec
├── ingestion/                # Python · Prefect flows · clients/
│   └── manual/inbox/         # NBS/CBN/FAAC drop zone + parsers
├── dbt/                      # models/staging · models/analytics · tests
├── analysis/                 # R · renv.lock · R/00_prep.R … · specs/  (grid definitions)
├── registry/                 # model cards (JSON) + result tables — the published artifacts
├── app/                      # Streamlit · consumes registry/ + analytics only
├── tests/                    # dbt tests · R unit tests · RAGAS suites
└── .github/workflows/
```

---

## Risks with recommended handling

| Risk | Why it matters | Handling |
|---|---|---|
| Local Prefect agent can't guarantee monthly uptime | Base spec §13 schedules flows on the 1st; a laptop is not a scheduler, and a stale vintage silently undermines every claim | Run the schedule via GitHub Actions cron on the public repo; keep Prefect for dev-time orchestration semantics |
| DHIS2 access never materialises | Family A loses its best monthly health outcome | Confirm in Stage 1; if refused, fall back to ACLED/UCDP and FAAC outcomes, and record the gap |
| ACLED embargo + licence | Removes the most recent year and forbids republication | Document; substitute UCDP for open redistribution; state the embargo in the limitations |
| Donor pool yields no credible counterfactual | Synthetic control becomes a rhetorical ornament | Stage 5 gate: report infeasibility rather than shipping a weak fit |
| Dose D1 fails the variation check | The whole Family A collapses to a level comparison | Stage 5 dose validation, before any estimate |
| Estimates drift from the narrative | The fastest way to lose a reader's trust | Single source of truth; card wins over prose |

---

## Stage → spec mapping

| This plan | Base spec `#CausalPresidents.txt` | Design spec `nigeria-causal-inference-spec.md` |
|---|---|---|
| 0–1 | §5 sources, §18 reproducibility | §10, §13 |
| 2–3 | §13 flows + quality gates | §16 step 0 |
| 4 | §6 catalog, §7 administration, §8 index | §11 data layer |
| 5 | §9 cointegration-first rule | §5.1 dose validation, §15 open decisions |
| 6 | §9 tiers, §10 R packages | §5 families A–C, §6 cards, §7 floor |
| 7 | — (new) | §5.4 specification curve |
| 8 | §15 methodology, §16 honesty, §19 positioning | §9 Q&A layer |
| 9 (out of scope here) | §14 layout | §3 artifact, §12 hosting |
| *(ongoing)* | §13 monthly refresh schedule | §13 reproducibility |

### Base-spec §17 build order → this plan

The base spec's Phase 1–6 sequence is **superseded**, because the "analysis layer first, UI later"
choice reorders it: the base spec builds a chart before it has defensible estimates. Mapping:

| Base spec §17 | Where it lives now |
|---|---|
| Phase 1 — Foundation (admin table, dims, facts, two smoke metrics) | Stage 4 (admin spine, `dim_metric`, `fact_metric`, anchors) |
| Phase 2 — Chart (Yar'Adua→Jonathan boundary, portraits, shock bands) | **Stage 9** — deferred until Stage 8 exists |
| Phase 3 — Pipeline (Prefect schedule, quality gates, CI + dbt tests) | Stages 2–3, scheduled per the risk table (GitHub Actions cron, not a laptop) |
| Phase 4 — Adjustment (Tier 3 R scripts, CI forest plot) | Stages 5–7 (Tier 3 is now one family among four) |
| Phase 5 — RAG (pgvector, LlamaIndex + Groq, RAGAS, chat UI) | Stage 8 (corpus + eval set); the UI is Stage 9 |
| Phase 6 — Documentation and polish (methodology, data dictionary, blog, video, README) | Stage 8 for methodology/data-dictionary; blog/video/README remain **undocumented** |
