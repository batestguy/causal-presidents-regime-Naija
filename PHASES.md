# causal-presidents — Phase Plan: Data Collection → Analysis

**Scope of this document.** Stages 0–9: from an empty repo to a defensible set of analysis products, and the
app that renders them. The interactive app is Stage 9, downstream, and **consumes Stage 8 output only** — it
never touches R, a database or a model.
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
| 9 | The read-only app | the chat layer | Every card reachable, every number traceable to a card field |

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

**STATUS: BUILT 2026-10-11 · RE-RUN 2026-10-16 over the FAAC document source and again 2026-10-17 over UCDP.**
**242 series** gated (60 ok, 182 flagged, 0 empty) → `registry/quality/<vintage>/`. Config in
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
and gated from their **parsed** artifact, so the gate reads the same series Stage 4 reads. With FAAC and the UCDP scopes in, the
report is **242 series — ok 60, flagged 182, empty 0**, and the dose, its gate status and the security
counts are on the panel. See S4-19, C-42, C-43.

**Exit criteria.** No series reaches Stage 4 without a gate result; the quality report is published with
the vintage timestamp.

---

## Stage 4 — Harmonisation: the analytical base

**STATUS: BUILT 2026-10-11, extended 2026-10-16 (the FAAC dose) and 2026-10-17 (the security outcome).**
`fact_metric` holds **8,350 rows = 25 metrics × 334 months
(1999-01 → 2026-10)**, built by dbt into a local DuckDB (`data/analytics.duckdb`, gitignored and
reproducible). Rules declared in `analysis/specs/harmonisation.yml`, models under `dbt/models/`, seeds
under `dbt/seeds/` (administration spine, metric catalogue, shock bands, the 37 state units), and a build
of 165 nodes — 4 seeds, 25 models and 136 tests, 19 of them singular — independent verifier
`tests/verify_harmonisation.py`, and every column documented in `docs/data-dictionary.md`. Exit criteria met: one analytical base table, every column
documented, reproducible from the vintage plus the anchor config — with **20 break-tests** showing each
new guard can fail, **plus three more added 2026-10-17 for the artifact contracts**
(`scripts/validate_artifacts.py`, `PROGRESS.md` §4). What the stage *measured* is the important part: **10.1 % of the base was observed** when it was built
(775 of 7,682 rows) and **16.2 %** is observed now (1,349 of 8,350) — the monthly landings moved it — while
the *CPI* series is still annual, so the 2023 subsidy window is not monthly-visible on it (C-30). See decisions S4-01…S4-12, M-11, C-30…C-32.

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

**STATUS: BUILT 2026-10-11 · RE-RUN at vintage 2026-10-16 (2026-10-17) · RE-RUN at vintage 2026-10-18** over
a widened Design C donor pool. The memo is
`docs/design-memo.md`; the machine-readable result is
`registry/diagnostics/<vintage>/diagnostics.json` + `report.md`, attached to all 36 cards. Config in
`analysis/specs/diagnostics.yml`, engine in `analysis/R/02_diagnostics.R`, independent verifier
`tests/verify_stage5.py`. Exit criteria met: **every one of the 36 (outcome × design) cards carries a
pre-check verdict, and exactly one passes** — 14 fail, 9 degraded, 12 not attempted, 1 pass
(`u5mr` under Design C, since the 2026-10-18 re-run). The earlier re-runs' totals are kept because they
moved: 2026-10-16 was 15 / 7 / 14 with 0 pass, and 2026-10-17 was 15 / 9 / 12 with 0 pass.

**What the 2026-10-18 re-run changed (the donor pool).** Design C's `infeasible` verdict was always a
statement about the *pool*: with 13 countries chosen on GDP comparability, no convex combination could track
Nigeria's pre-treatment path. The candidate set is now **99 countries** in four declared groups (West
African neighbours, oil exporters, African comparators, large lower-middle-income countries) screened on oil
dependence, region/income band and coverage, and the gate answers differently: **`u5mr` passes 3 of its 4
runnable windows, `gdp_growth` 1 of 4, `cpi_yoy` 0 of 4** — under a rollup rule (`outcome_rollup`) that is
now **declared** as a strict majority of the runnable windows, where the previous rule ("any window
passes") was undeclared and would have credited `gdp_growth` on one window of four (S5-12). Design C is
still not estimated: the estimator and the placebos Stage 5 deferred to Stage 6 are the next build, and the
pass carries the warning that a 99-donor simplex can fit almost any pre-period, so the gate is now weaker
evidence than it was at 13 donors (C-59).

**What the 2026-10-17 re-run changed, and why it was not optional.** The 2026-10-11 verdicts were computed against a
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
> real monthly fiscal series. The verdicts above are the current ones — 1 of 36 passes (`u5mr`, Design C),
> with the reasons
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

**STATUS: BUILT 2026-10-17.** Spec in `analysis/specs/estimation.yml`, engine in
`analysis/R/03_estimate.R`, artifacts in `registry/estimates/2026-10-17/` (`estimates.json` +
`report.md`), independent verifier `tests/verify_stage6.py`, output document `docs/estimates.md`.
**Twelve specifications published across two designs — three Design A outcomes and nine Design B horizons — and one of the two designs is reported as not identified.**

**What was estimated, and what the plan expected.** Stage 5 left 0 of 36 cards passing (at the vintage
Stage 6 was fitted against), so Stage 6 could not run the plan's three families as written. What it ran instead is the subset the landed data can
carry, declared before the numbers were read:

- **Design A — state dose-response** (the Family A estimand, on 3,456 state-months from 2016-12 to
  2024-12): PPML with state and month effects, clustered by state, for fatalities, incidents and civilian
  fatalities. **`estimated_not_identified`**: a mis-timed dose (each state's own series shifted by any
  non-zero offset in ±30 months) returns an estimate at least as large for 8 of 60 offsets, p = 0.133,
  and the deterministic 24-month placebo (+0.302) is nearly as large as the estimate (+0.479). The reason
  is measured rather than asserted: after state and month effects the dose's residual variation is 0.50 in
  Delta/Bayelsa/Rivers against 0.11 elsewhere, i.e. it is the 13 % derivation share moving with the oil
  price (C-47).
- **Design B — national fiscal transmission** (114 months): local projection of the cumulative log change
  in state FAAC on the Brent shock, Newey-West at 12 lags. **`estimated`**: −0.160 at h=0, **+0.518 at
  h=2** (SE 0.166), **+0.470 at h=3** (0.158), tapering to +0.325 at h=12; the 6-month lead placebo is
  +0.095 (C-48). A 10 % Brent move reaches the states as ~5 % more money two to three months later.
- **Design C — synthetic control**: **not run**, and Stage 5's reason is carried onto the artifact
  rather than dropped. The next step is the donor pool, not the estimator.

**The deviation from the plan, on the record.** The plan specified Callaway & Sant'Anna group-time ATTs
with `did`. That estimand needs a treatment date per unit, and this dose has no staggered adoption — every
state receives an allocation every month, and the variation is a magnitude, not a switch. The
identification the family actually proposes is exposure intensity, so the estimator is a dose-response
count model. `did` remains correct for a future design with a real adoption date (a state-level policy
with different start months); it is not a substitute for one.

**Exit criteria — partially met, and the gap is named.** "Every card satisfies all six rigor-floor
items" cannot be met while no card *passes* its pre-check: Stage 5's verdicts stand, and Stage 6 attached
estimates to the one family that became estimable, on the nominal dose axis rather than the specified one
(S6-06). What the shipped estimates do carry is intervals, a placebo, a randomisation check, a dominant
residual-variation measurement, an explicit DoF/cluster caveat and named assumptions — five of the six
items, with "confounding sensitivity" replaced by the harder statement that the design is not identified.
The card schema for estimates is Stage 8 work and is *not* claimed here.

**Gotchas, from this run.** A permutation null is not automatically a valid null: shuffling the dose
across states within a month destroys the cross-state mean that the state fixed effects already absorb,
so it compares against a null with far less structure than the design uses — it returned p = 0.000 on a
design whose own placebo was nearly as large as its estimate (S6-07). The check that decides a timing
claim has to be a *timing* null. And a count series must never be interpolated: the monthly spine would
otherwise have carried 25 fabricated fatality-months between 1999 and 2009 (S6-05).

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

**STATUS: BUILT 2026-10-18.** Spec in `analysis/specs/robustness.yml`, engine in
`analysis/R/04_robustness.R`, artifacts in `registry/robustness/2026-10-17/` (`robustness.json` +
`report.md` + `specification_curve.svg`), independent verifier `tests/verify_stage7.py`, output document
`docs/robustness.md`.
**105 specifications declared before any was fitted and all published; the curve is drawn, the support
counts are computed from the fitted rows, and the two designs get opposite answers.**

**What the plan asked for, and what was fitted.** The plan names eight axes; four are live here
(outcome, dose lag, adjustment set, sample window for Design A; shock definition, covariate set, window
for Design B), and **four are declared dead with their reasons rather than dropped** (imputation
handling, index anchor, donor pool, event window). One axis is live in principle and unbuilt in fact —
the per-capita dose, because `d1_faac_per_capita` is 0 of 12,358 rows (X-09) — so the artifact lists it as
unbuilt and every cell of the curve is the nominal dose.

**What the grid decided.** Design B holds its sign in **24 of 24** specifications (all 24 intervals
exclude zero, the pre-registered cell reproducing Stage 6 to 4.3e-12) but not its timing: the in-time
placebo over 48 shifted alignments returns **p = 0.0625**, published as a bound rather than widened until
it passed (S7-04). Design A does not survive: **45 of 81 specifications positive against 36 negative**,
**five** axis levels flip by majority (including the preferred `outcome = fatalities` level, 14 of 27),
and the sharpest is the dose lag — lagged one month, the estimate is negative in all three windows. The
36 leave-one-state-out refits do not flip the sign ([0.1234, 0.6254], 0 flips), so the fragility is the
identification and the timing rather than one unit. Oster's δ is negative for both designs and is
reported with the case it is in; **Rosenbaum bounds are recorded as not applicable** (continuous
treatment, no matching) with the reason (S7-05).

**Exit criteria.** Support count per sign computed from the fitted rows; the pre-registered specification
marked on the curve and flagged in the artifact (the contract test fails if two are flagged or none); the
sign-flip regions drawn as an axis strip beneath each panel rather than buried in a table. All three hold
in `verify.sh`, and each is break-tested — the observed failures are recorded in `PROGRESS.md`.

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

**STATUS: BUILT (2026-10-21) — the registry, the three figures, the limitations narrative, the transition
event study and the retrieval corpus.** Stage 9 can be built without R. The registry half is built: spec `analysis/specs/registry.yml`,
engine `analysis/R/05_registry.R`, verifier `tests/verify_registry.py`, output `docs/registry.md`, cards and
index at schema 0.3.0. **Two of 36 cards carry a published number; 34 carry a reason**, and the two
design-level results (Design B's channel, Design C's non-run) sit on the index where they cannot be mistaken
for an estimate about a card's outcome.

**What the registry half decided.** Stage 6's twelve specifications do not line up with 36 cards: three
Design A specifications are about catalogue outcomes (two of which have cards), nine Design B specifications
are about the **national FAAC channel** — a *mediator* node on every B card — and Design C was not run. The
mapping is declared with both of its counts and checked in the engine and the verifier, so the count that
matters (cards carrying a number) cannot change unnoticed (S8-02, C-55). An `estimated` card carries its
interval, its Stage 6 verdict with the check that decided it, and the Stage 7 summary for its own axis level;
sensitivity computed on the preferred specification stays design-level (S8-03). The ordering constraint —
`01_build_dags.R` resets the estimate block, so the assembler runs after it — is checked by
`validate_artifacts.py` and `verify_registry.py` rather than documented and hoped for (S8-01).

**The tenure-comparison half is now built (Stage 8b, 2026-10-18).** `analysis/specs/events.yml`,
`analysis/R/06_events.R`, `tests/verify_events.py`, `registry/events/2026-10-17/`, `docs/events.md`. It
answers the one tenure-shaped question the monthly data can carry — did conflict move after each transition
relative to its own path just before it — over the four in-window transitions, with exhaustive placebo
inference over 58 eligible months, a pre-trend placebo per event, a reporting-divergence check and the
party split published as description with no test. **2 of 8 event-outcome cells pass both checks, 4 fail the
pre-trend, 1 cannot be checked at all.** The level question ("which tenure was better?") is still refused,
because it needs the counterfactual Design C cannot supply (S8b-01).

**The forest plot is now built (2026-10-18), and it is the last figure this stage asked for.**
`registry/estimates/2026-10-18/forest_plot.svg`, declared in `analysis/specs/estimation.yml` and rendered by
`analysis/R/03_estimate.R` from the artifact's own rows. Two panels rather than one axis, because Design
A's coefficient is a state-month elasticity and Design B's is a national cumulative response — both
log-points, but a shared axis would invite a comparison the artifact never makes. Each design's decisive
check is drawn **hollow** beside its estimate (A: the 24-month mis-timed dose that returns an estimate as
large as the published one; B: the 6-month lead placebo), because a forest plot of estimates alone would
show a number its own artifact says is not identified without showing why. Labels are text, not glyph
outlines — the verifier asserts every published specification appears in the file, so a render loop that
stopped early fails rather than shipping a picture that looks complete.

**The limitations narrative is built (2026-10-20), before the RAG corpus that has to embed it.**
`docs/limitations.md` is the boundary the findings sit inside: the arithmetic that makes the tenure
question unanswerable, the 16.2 %-observed spine, the coverage table node by node, Design A's failed
timing check and its interval that crosses zero, Design B's 0.0625 timing bound, Design C's
permission-not-result, the inference floors (36 clusters, Oster δ negative, Rosenbaum not applicable,
four events with a 1/59 p-floor), the 45/36 sign split, and what reproduction still cannot do. It is
longer than the findings page on purpose (base spec §19). **Its numbers are checked as claims**: the
needles are derived from the artifacts in `tests/verify_registry.py`, `tests/verify_events.py` and
`tests/verify_stage5.py`, so prose cannot stay still while an artifact moves. Writing it found two such
drifts already — `docs/events.md` claimed four pre-trend failures where the artifact has three (plus two
uncheckable), and `docs/design-memo.md` still described the pre-FAAC base's 10.1 % observed share.

**The retrieval layer is now built (Stage 8c, 2026-10-21).** `analysis/specs/rag.yml`,
`analysis/specs/rag_eval.yml`, `scripts/build_rag_corpus.py`, `scripts/eval_rag.py`,
`tests/verify_rag.py`, `registry/rag/2026-10-18/`, `docs/rag.md`. **482 chunks from 53 attributed sources** at
the registry's vintage — one document per model card (179 parts) plus the card in one piece (36), the three
design results (12), the narrative (183), the data dictionary (47), the transition events (13), the
administration and shock tables (8), the two coverage counts and the scope paragraph (4). No chunk is authored by hand: every one is a serialisation of an
artifact whose sha256 is recorded, and a source edited without a rebuild fails the verifier. Two numbers
changed the design before anything shipped: the base spec's `all-MiniLM-L6-v2` caps at **256 tokens**, which
would have truncated every chunk past ~1,000 characters, so the corpus uses `multi-qa-MiniLM-L6-cos-v1`
(512 tokens, same 384 dims), and `--embed` counts the model's own tokens and fails the build rather than
truncating — which it did once, at a 935-token table chunk.

**The measured answer is mixed, and published as such.** Embedding retrieval recall@5 is **0.944** against a
BM25 baseline's 0.833 (MRR 0.724 / 0.676), so the model earns its place. The two refusal gates **fail**: the
refusal-with-reason recall is **0.5** (one compound question retrieves the tenure-limitations passage instead
of the Design C one) and out-of-scope refusal is **0.25**, because a forecast or a recommendation about a
covered outcome embeds closer to the corpus than some genuine questions do — similarity alone cannot refuse
an on-topic out-of-scope question, and the app will need an intent gate. **Answer quality is measured
(2026-10-23)** on the four RAGAS metric definitions — faithfulness **1.000**, answer relevancy **0.800**,
context precision **0.990**, context recall **0.863** over the 16 answered questions — implemented locally in
`scripts/eval_answer_quality.py` rather than by the `ragas` package, which is not installed; the artifact
records `library: false` and says its scores are not comparable to a library run.

**Still to do in this stage:** nothing blocking Stage 9. The remaining items are chunks for the families the
corpus currently summarises rather than chunks (the donor panel, the robustness grid).

**Work**

- **Model registry assembly** — the app's complete data contract.
- Figures: ✅ forest plot with intervals (Stage 8), ✅ event-study panels (Stage 8b), ✅ specification curve (Stage 7).
- ✅ **Limitations drafted before findings** (`docs/limitations.md`, 2026-10-20; base spec §19 ordering
  discipline: limitations longer than findings).
- ✅ **RAG corpus** — `registry/rag/2026-10-18/`: one document per model card (split into parts at the
  embedding budget), plus the design results, methodology, data dictionary, shock annotations, administration
  table and the limitations page, all sharing the registry's `vintage_date` so a stale answer cannot outlive
  the model it quotes. See `docs/rag.md`.
- **RAGAS evaluation set** — ✅ authored and wired (22 questions: 16 answerable, 2 refusals with a cited
  reason, 4 out of scope), ✅ measured on the retrieval half in CI, and ✅ measured on the generation half on
  2026-10-23 as `registry/rag/2026-10-18/answer_quality_eval.json` (verifier
  `tests/verify_answer_quality.py`). The four definitions are implemented locally; the `ragas` library is
  still not installed and the artifact says so.

**Exit criteria.** Stage 9 can be built without opening R. If a card and the narrative disagree, the
**card wins** and the narrative is regenerated.

---

## Stage 9 — The read-only app

**STATUS: READ-ONLY APP BUILT (2026-10-21), REFUSAL GATE BUILT AND MEASURED (2026-10-22), GATE AT v3
AND ANSWER LAYER BUILT (2026-10-22), CHAT TAB BUILT (2026-10-22), OUTCOME PANELS BUILT (2026-10-24),
STATIC GUIDED FLOW BUILT (2026-10-25), ITS VERIFIERS BROKEN ON PURPOSE (2026-10-27), DESIGN-LEVEL RESULTS
SCREEN BUILT AND THE FIGURE PATHS FIXED (2026-10-27), DESIGN C FITTED AND THE GATE RE-FROZEN AT v4
(2026-10-28).**
`app/streamlit_app.py` + `app/registry_data.py`,
`tests/verify_app.py`, `docs/app.md`. Outcome → design → assumption → adjustment set → cannot-rule-out →
the published number or the reason there is none, plus one tab for the two design-level results and one for
asking the registry a question. It reads `registry/dags/`, and for the chat tab `registry/rag/<vintage>/`,
`analysis/specs/` and `docs/glossary.md`: no database, no network, no model, and no coefficient typed into
the UI.

**Stage 8h — Design C (2026-10-28).** The last declared design with no estimate now has one, in its own
artifact family: `analysis/specs/design_c.yml` (declared before a weight was fitted),
`analysis/R/11_design_c.R`, `registry/design_c/2026-10-18/`, `tests/verify_design_c.py` (refits with an
independent solver), wired into the chain before Stage 6 so `estimates.json` carries the design's status rather
than a stale `not_run`. **Four windows estimated, one refused, none identified**; the pre-fit gate passes 304
of the 396 placebo fits too, so the artifact's verdict is that the gate does not discriminate on a 99-donor
pool. Because a synthetic control has no sampling distribution, no gap reaches a card: `u5mr × C` carries the
new reason `design_estimated_not_identified` and points at the artifact. The intent gate was re-frozen at v4
(`613ccf5`) with a new held-out set, because G07's reason sentence had become false.

**Screen 6b, the design-level results (2026-10-27).** The three figures Stage 8 published — the forest plot, the
specification curve and the event study — existed as artifact-backed SVG files with recorded byte counts and were
reachable from **no page at all**. `site/build.py` now renders `/designs/`: the figure, the artifact's own
`layout` sentence, the verdict and the check that decided it, the grid's support counts and sign-flip levels,
Design C's reason and next step, and the transition verdicts **by month, never by president** (the screen where
the no-attribution rule is easiest to break). It is not a flow step — it is not per-outcome, so it sits outside
the selection the URL carries — and it is linked from the estimate screen and the Ask footer. The same session
found a site-wide defect the verifier could not see: every figure on `/chart/` and `/graph/` was written
`src="assets/…"` on a page served from `/chart/` or `/graph/`, so the deployed site requested
`/chart/assets/…` and **404ed while every check stayed green**. The verifier proved a file existed in `dist/`;
it never resolved the markup. It now does, for every `src` and `href` on every page.

**Why read-only first.** The page a reader can use today is the one Stage 8 was built to make possible, and
it has no failing gate in front of it. The chat tab does: out-of-scope refusal measures **0.25**, so a
question like "what will inflation be in 2030?" is not refused by similarity alone. Building the chat first
would ship the exact failure the corpus exists to prevent, so the tab waited for an intent gate, a
re-measurement against the declared eval set, and an answer contract that could carry what the corpus
actually holds — all three now exist (below), and the tab is built on them.

**The refusal decision is a policy now (2026-10-22).** `analysis/specs/intent_gate.yml` declares eight rules
with unique priorities; `app/intent_gate.py` applies them to the question before retrieval; a rule decides an
intent (`answerable`, `out_of_scope`, `refusal_with_reason`) and, for a refusal, pins the chunk the refusal
must quote. No rule matched means `answerable` — the gate may add a refusal, never remove one — and a refusal
whose route does not resolve to exactly one existing chunk falls back to `answerable`, so the gate cannot
refuse without a citation. The study window and the vintage are read from the artifacts; no number is typed.
The rules were **frozen before the held-out questions existed** and `tests/verify_intent.py` reads the rule
spec at that commit and fails if the file moved, so the measurement cannot be re-tuned after the fact. v1
missed one target — `answerable kept` 0.957, because G03 refused a question about the population denominator
— and the miss was published rather than tuned (S9-05). **v2 is the change made the right way round**: G03
excludes the denominator frame and was frozen at `8b9ba3b` **before** a new held-out set existed
(`intent_gate_eval_v2.yml`), with the seen questions moved to a declared regression block. Measured on the
**49 v2 held-out questions**: intent accuracy **0.980**, out-of-scope refusal **0.947**, answerable kept
**1.000**, refusal route resolved **1.000**, reason cited **1.000**, regression accuracy **1.000**; the one
miss is the probe KG01 measures. On the 22 published questions the failed gates move 0.25 → **1.000** and
0.5 → **1.000** with answerable recall unchanged at 1.000. Four gaps are declared rather than hidden
(KG01–KG04). Narrative: `docs/intent.md`; artifact: `registry/rag/2026-10-18/intent_eval.json`.

**v3 closes KG01, and the answer layer reads in plain language (2026-10-22).** The donor panel's 99 member
countries and the ISO 3166-1 names are committed registry artifacts (`registry/donors/2026-10-18/panel.json`,
`registry/reference/countries.json`, both schema-validated), so the country rule is reproducible on a fresh
clone. G09 refuses a question naming any country other than Nigeria, frozen at `3dcb555` **before**
`intent_gate_eval_v3.yml` existed: intent accuracy **0.980**, out-of-scope refusal **0.947**, answerable kept
1.000, route resolved 1.000, reason cited 1.000, and the 23 seen cases at 1.000 — the one held-out miss is
P03, a country reached only through its capital city, which is the lexical remainder the gate declares
(KG03).

`app/answer_layer.py` now returns a `plain` reading beside the contract answer: the sign of the coefficient,
whether the interval includes zero, the sample, the assumption in one sentence, the caveats as bullets, and
the meanings of the technical words actually used — every definition quoted from `docs/glossary.md`, every
figure copied out of the estimate it cites. Nothing is generated, so the path needs **no LLM key**, which
`tests/verify_answer.py` proves by running the layer with every key-shaped environment variable removed.
Measured: **36 of 38** answerable questions answered (0.947) under the three-shape contract, every one with a
plain reading and none quoting a number its citation lacks.

**What the verifier establishes.** It renders all 36 cards through Streamlit's own test harness and compares
the output with the card JSON, formatting the card's values itself rather than importing the app's formatter:
every coefficient, interval, p-value, verdict *and the failed check behind it*, every reason code *and its
detail sentence*, every adjustment node resolved to `label (node_id)`, and every caveat. Two negative
checks matter as much: the published coefficients are searched for as literals in the app's source (the card
wins), and the source is scanned for database, network and fitting imports (base spec §18). A design-level
result is also checked never to appear on a card: pointing the results tab at another design while each B
card renders is what makes that check real rather than vacuous. The chat tab is checked the same way — the
verifier asks it the questions it offers and compares the answers with the published artifacts, so the tab
reproduces the measurement rather than re-deciding it.

**Framework decided on the record (2026-10-21, `docs/decisions.md` UI-01…UI-06).** Streamlit, because
`AppTest` renders the real app without a browser — which is why the 36-card contract check runs in
`verify.sh` and CI instead of by hand — and because a page that is a pure function of the registry has no
state for the rerun model to desynchronise. Its costs are written down rather than glossed: no per-card URL
(`st.query_params` is the fix, not done), coarse layout, a static SVG graph. The trigger to leave the
framework is the interactive graph becoming the product, not styling; Dash is the smallest honest jump from
there, and `app/registry_data.py` is framework-free so it would survive the move.

**Not built, and declared as such in `docs/app.md`:** node-level graph interaction, links from the card to
the narrative that explains each design, and per-card URLs. **The deployment question is now answered for the
static guided flow** — GitHub Pages, rebuilt from the same commit only after the static job passes, with the
registry vintage stamped on every page — and remains open for the Streamlit app, which is still a local tool.

**Queued for the next static pass (2026-10-28, not built):**

1. ✅ **Ask in the primary navigation — built 2026-10-29.** `/ask/` was the flow's sixth step and reachable only
   by walking the flow or from the Ask footer; it is now one click from every page, so a reader who arrives on a
   bookmarked page can search the registry from there. The change was `guide.yml → nav.ask`, one entry in the loop
   in `site/build.py::page()`, `aria-current` on `/ask/`, and the link added to the per-page nav check in
   `tests/verify_site.py`. **The predicted wrap rule turned out to be unnecessary:** measured in a browser at 320,
   375 and 420 px, the existing `@media (max-width: 719px) .topnav { flex-wrap: wrap }` already puts the five links
   on their own line under the wordmark, with no horizontal overflow on any of the 11 pages — so the wordmark was
   not shrunk, as the handoff required, and no CSS changed.
2. **Bigger charts, with the presidents over them.** The chart screen's comparison and changepoint panels are
   drawn at the 960 px measure while `/designs/` and `/technical/` use 1240; the chart should take the wide
   measure and a taller cap. The portraits (`site/assets/presidents/<slug>.jpg`, already licensed and in the
   manifest) should appear **over each graph as period markers aligned to the tenure bands** — the bands are
   already drawn in R from the administration spans, so the portraits label the axis, not the series. The
   guardrail that makes this safe: a portrait is `aria-hidden` with empty `alt`, carries no name and no verdict
   word, and the surname scan in `tests/verify_site.py` must be told about the block explicitly rather than
   loosened. If the portraits carry attribution text on `/chart/`, the credit list is repeated there or linked
   to the cover's. The first decision to take is the composition: one row of five above the panel (recommended,
   because it reads as a time axis) or one portrait per band as a faint watermark.

**Work**

- ✅ App skeleton reading the index and cards, with the vintage cross-check in the loader.
- ✅ Model-card tab: assumption, computed adjustment set, assumed-absent node, caveats, Stage 5 pre-check,
  the number with its verdict, the whole specification in an expander, the Stage 7 grid line, the SVG graph.
- ✅ Design-level results tab: A's failed timing check, B's channel-level specifications and support count,
  C's reason and next step.
- ✅ `docs/app.md` — the ratio, the rules, and the limits the page does not fix.
- ✅ **The pre-retrieval intent gate** — `analysis/specs/intent_gate.yml`, `app/intent_gate.py`,
  `analysis/specs/intent_gate_eval_v2.yml` (49 held-out questions after the A16 closure),
  `scripts/eval_intent.py`, `tests/verify_intent.py`, `docs/intent.md`. On the v2 held-out set: intent
  accuracy 0.980, out-of-scope refusal 0.947, answerable kept 1.000, reason cited 1.000; the one miss is the
  declared KG01 probe.
- ✅ **The answer layer** — `app/answer_layer.py`, `scripts/eval_answer.py`,
  `registry/rag/2026-10-18/answer_eval.json`, `tests/verify_answer.py`, `docs/answer.md`. It enforces R-04 on
  its own output, under a contract with three shapes: **36 of 38 answerable questions answered (0.947)**, 2
  declined by the contract, 0 answered around a refusal. Every quoted sentence and number is in its citation.
- ✅ **Chat tab** — the app's fourth tab, on the gate and the answer layer: a cited answer or a cited
  refusal, the plain reading first, no model and no key. The verifier asks it the four published questions
  and compares the answers with the artifacts; a held-out question on the page fails the build.
- ✅ **Outcome panels** — `analysis/specs/series_figures.yml`, `analysis/R/07_series_figures.R`,
  `registry/series/<vintage>/` (12 SVGs + `index.json`), `tests/verify_series_figures.py`. One panel per
  outcome card, drawn from the base at build time: observed months as dots, interpolated months dotted, runs
  with no observation shaded and labelled. The card shows the panel and its caption, and the caption's
  numbers are the artifact's.
- ✅ **The static guided flow** — `site/build.py` over `analysis/specs/guide.yml` and the registry: **seven
  screens** (`/`, `/study/`, `/compare/`, `/graph/`, `/estimates/`, `/chart/`, `/ask/`), a second renderer
  over the same cards, `tests/verify_site.py` in the chain, and a Pages deploy gated on the static job.
- ✅ **Two descriptive artifact families behind it** — `registry/comparisons/<vintage>/` (12 outcome panels,
  56 groups, group means only) and `registry/changepoints/<vintage>/` (8 searched series, 10 estimated
  breaks, 4 definition breaks marked, 4 refusals with the count that caused them), each with its spec
  written before any number was fitted, its schema, its verifier, and its own stage in `verify.sh`.
- ✅ **The answer layer in the browser** — `site/assets/answer.mjs` runs the gate, BM25, the three-shape
  contract and the plain reading over JSON the build emits from `intent_gate.yml`, `rag.yml` and the corpus;
  `tests/verify_answer_js.py` accepts it only if it reproduces the published answers **38 of 38**, field for
  field. The JS carries no rule and no answer text of its own, so there is no second copy to drift.
- ✅ **The guided flow's verifiers are break-tested** — `.probe/break_guided_flow.py` applies **13** cases
  (5 site, 4 changepoints, 4 JS), requires the named defect in each red run, and restores every file
  byte-for-byte; **12 are caught** and the thirteenth is kept as a measurement: retuning BM25's `k1` and `b`
  changes no published answer, so the parity check is a check on decisions, not on weights. Writing it also
  closed a real gap — `tests/verify_changepoints.py` printed the artifact's `counts` block without
  recomputing it, which the stale-count mutation proved, so counts are now derived from the outcomes array.

**Exit criteria.** A reader can reach any card, and no number appears anywhere that is not a field of that
card. A reader can ask the registry a question and get an answer that cites the card it came from, or a
refusal that cites the passage it refuses for. Nothing is fitted at render time.

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
