# Progress log — causal-presidents-regime-Naija

**Last updated:** 2026-10-17 · **Stage:** 5 of 8 complete (designs validated) — no estimates yet
**One-line status:** specification complete; ingestion working and provenance-verified on **four**
sources, including the FAAC monthly disbursement workbook — **the fiscal dose is landed and gated**
(174 documents, 114 months × 36 states, 2016-12 → 2026-06; 37 series through the Stage 3 gates with the
result travelling on the panel); the causal-graph (DAG) assumption layer is built — 36 graphs (12 outcomes × 3 identification
designs); Stage 3's five quality gates run over all 125 landed series (60 `ok`, 65 `flagged`, 0 `empty`
— 37 of those are the FAAC dose, flagged on spikes the whole panel shares);
Stage 4's analytical base exists — one monthly table, **7,682 rows (23 metrics × 334 months,
1999-01 → 2026-10)**; and **Stage 5 has decided what the data can support before anything is estimated**.
Every one of the **36 (outcome × design) cards carries a pre-check verdict and none passes** — 15 fail,
7 degraded, 14 not attempted, and the verdicts have been **re-run at vintage 2026-10-16** because the
first set described a base that no longer exists. The totals are unchanged and the reasons are not:
Family A is still dropped, now because its dose is absent **on the per-capita axis the estimand is
written on** (the nominal dose is landed and gated) and because no outcome is state-attributed; Family B
is degraded (annual grain, FAAC present as data but absent from the catalogue, a 38–99 SD detectable
effect); Family C is infeasible (no convex combination of the 13 donors tracks Nigeria). No estimate is attached to any model yet. The recurring constraint is
the same one Stage 4 measured: **the monthly spine is only 10.1 % observed**, and on the native grain the
study is ~26 annual observations. One credential (UCDP) still gates the security domain.

**Last action (2026-10-17): Stage 5 re-run — the dose's checks recomputed on the axis the estimand is
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
- **The verdict totals are unchanged** — 15 fail, 7 degraded, 14 not attempted, 0 of 36 pass — and that is
the result: the dose's arrival changed *why* an estimate is not yet possible, not whether one is.

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
- **A fresh number for the report:** Stage 3 now covers **125 series — ok 60, flagged 65, empty 0**,
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

- **Nothing clears its gate.** Of 36 (outcome × design) cards, **0 pass** — 15 fail, 7 degraded, 14 not
  attempted. The state dose is empty (Family A dropped); the national VECM family runs at **annual**
  grain without FAAC (degraded); and **no convex combination of the 13 donors tracks Nigeria's
  pre-treatment path**, so the synthetic control is reported infeasible rather than shipped weak.
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
- **10.1 % of the base is observed** (775 rows; 4,389 interpolated, 2,518 empty). That ratio is the
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
| `knowledge.md` | Agent-facing repo context | Live |
| `PROGRESS.md` | This file | Live |

## 3. Code and data artefacts

| Artefact | What it does | Verified |
|---|---|---|
| `ingestion/clients/provenance.py` | Shared provenance: byte-exact payload storage, sha256, POSIX paths, **credential redaction** | Redaction confirmed |
| `ingestion/clients/worldbank.py` | World Bank acquisition; retries, pagination, row-count assertion, detects the 200-with-error envelope | Working |
| `ingestion/clients/fred.py` | Brent crude (`DCOILBRENTEU`) — oil covariate for the VECM/ARDL family | **Working** (key present) |
| `ingestion/clients/ucdp.py` | UCDP GED fatalities — security domain (CC-BY, redistributable) | Failure path only |
| `ingestion/flows/pull_worldbank.py` | Lands a vintage: raw pages + `manifest.json` + provisional `coverage.json` | Exit 0, 22/22 |
| `ingestion/flows/probe_candidates.py` | Reconnaissance: which indicators actually reach the APC era | Exit 0 |
| `ingestion/flows/probe_missing_variables.py` | Reconnaissance: what the causal graphs need that nothing sources | Exit 0 |
| `ingestion/flows/pull_worldbank_donors.py` | The Design C donor panel — 13 countries × 5 screening predictors | Exit 0, 5/5 |
| `ingestion/flows/pull_fred.py` | Lands the oil covariate: Brent crude, daily; refuses to overwrite a landed vintage (X-07) | Exit 0, 1/1 |
| `analysis/specs/quality.yml` | Stage 3 gate configuration: study window, thresholds, grains, frozen resample rules, definition breaks, spike adjudications, and the `document_sources` block that gates a PDF/XLSX source from its parsed artifact | 125 series configured |
| `ingestion/quality/gates.py` | The five gates (gap · spike · revision · definition-drift · provenance) as pure functions | covered by `verify_quality.py` |
| `ingestion/flows/check_quality.py` | Runs the gates over every landed series; enforces the exit criterion in code | Exit 0, 88/88 |
| `registry/quality/2026-10-16/` | The vintage quality report — `report.json` + a human-readable `report.md` (`2026-10-11/` is kept as the previous vintage) | 125 series: 60 ok, 65 flagged, 0 empty |
| `tests/verify_quality.py` | Recomputes the gap and spike results from the raw payloads independently of the gate module | Exit 0 |
| `tests/verify_provenance.py` | Re-derives every sha256, for every source, and detects orphaned files | Exit 0, 3 sources |
| `data/raw/worldbank/2026-10-11/` | 22 payloads + manifest + coverage report | Gitignored, never committed |
| `data/raw/worldbank_donors/2026-10-11/` | 5 payloads (13 donors each) + manifest + coverage | Gitignored, never committed |
| `data/raw/fred/2026-10-11/` | 1 payload (Brent, 10,275 rows) + manifest + coverage profile | Gitignored, never committed |
| `analysis/specs/outcomes.yml` | Outcome registry for the DAG layer — 12 catalogue outcomes with Stage-1 coverage status | 12/12 |
| `analysis/specs/dag_designs.yml` | The three identification designs as node/edge templates, with assumption text | 36/36 instantiated |
| `analysis/R/01_build_dags.R` | DAG generator: acyclicity check → dagitty adjustment set → ggdag SVG → in-figure legibility check | Exit 0, 36/36 |
| `registry/dags/` | 36 DAG cards + 36 SVG figures + index — the assumption layer the app reads | Verified |
| `tests/verify_dags.py` | Independent verification of every DAG card (schema, acyclicity, backdoor blocking) | Exit 0 |
| `analysis/specs/harmonisation.yml` | Stage 4's declared rules: spine, annual→monthly alignment, interpolation, the index anchor and its recorded fallback, and the declared gaps | 5 gaps declared |
| `dbt/` | The transformation project (D-05: SQL, never Python): staging → analytics, run into a local DuckDB | 19 models, 4 seeds |
| `dbt/seeds/raw_administration.csv` | Administration spine + term count, base spec §7 | 5 rows |
| `dbt/seeds/raw_metric_catalogue.csv` | The metric dimension's source: label, unit, **direction**, domain, catalogue vs landed frequency, coverage status | 25 metrics, 12 outcomes |
| `dbt/seeds/raw_shock_bands.csv` · `raw_state.csv` | Base spec §8 shock bands · the 37 state-level units | 3 · 37 |
| `dbt/models/analytics/fact_metric.sql` | **The analytical base**: 23 metrics × 334 months with the index, the observation type and the tenure strata | Built, 7,682 rows |
| `dbt/models/analytics/metric_anchor.sql` | The index anchor per metric, naming the rule that produced it | 23 rows (16 fixed, 7 fallback) |
| `dbt/models/analytics/int_metric_monthly.sql` | The spine before indexing: observed / interpolated / unobserved, no extrapolation, no interpolation across a gap | 7,682 rows |
| `dbt/models/analytics/dim_administration_term.sql` | Term-level spans carrying the four LOCKED party-by-tenure strata | 7 terms |
| `dbt/models/analytics/dim_metric.sql` | The metric dimension, with the Stage 3 quality status and definition breaks travelling on it | 25 rows |
| `dbt/models/analytics/state_panel.sql` | 37 × 334 panel, dose columns typed, empty and declared | 12,358 rows, 0 doses |
| `dbt/models/analytics/fact_donor_panel.sql` | Design C's donor pool, kept off the national spine | 3,866 rows, 13 countries |
| `dbt/tests/` | 13 singular tests for what generic tests cannot express: no extrapolation, no interpolation across a gap, the frozen Brent rule, vintage isolation, spine completeness, term coverage, declared gaps | 92 data tests total |
| `tests/verify_harmonisation.py` | Recomputes the whole base from `data/raw/` + the specs, independently of dbt and of the gate module | Exit 0 |
| `analysis/specs/diagnostics.yml` | Stage 5's declared parameters: grain, unit-root reconciliation, cointegration rule, dose thresholds, pre-fit gate, DoF/power, collinearity, candidate windows, design gates | 9 thresholds echoed |
| `analysis/R/02_diagnostics.R` | The Stage 5 engine: integration order, Johansen, shock visibility, dose validation, pre-fit QP, DoF/power, collinearity — then attaches a verdict to every card | Exit 0, 36/36 cards |
| `registry/diagnostics/2026-10-16/` | The Stage 5 result, re-run after the dose landed — `diagnostics.json` + a human-readable `report.md` | 0 of 36 pass (15 fail, 7 degraded, 14 not attempted) |
| `docs/design-memo.md` | The Stage 5 output: per outcome, which family is credible, which is not attempted, and the diagnostic that decides it | Complete |
| `tests/verify_stage5.py` | Recomputes every Stage 5 headline number from the base in numpy/scipy and re-derives the design verdicts from the card statuses | Exit 0, 1 warning |
| `docs/data-dictionary.md` | Every column of the base, documented — Stage 4's exit criterion and the Stage 0 data dictionary that was never written | Complete |

## 4. Verification evidence

Commands and their observed results — these are measurements, not assertions. Every exit status
below was captured directly, not inferred from filtered output.

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

**Access (probed 2026-10-10; "unreachable" = failed via two independent network paths):**

| Source | Result |
|---|---|
| World Bank API | ✅ keyless, working — the backbone |
| NBS, CBN | ✅ reachable (HTML/PDF, no API) |
| IMF DataMapper | ⚠️ 403 to scripted clients, 200 via relay |
| FRED | ✅ **resolved 2026-10-11** — key registered, HTTP 200, Brent landed |
| UCDP | 🔑 free token still required |
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
| Security outcomes | fatalities, incidents | A free UCDP token (reachable) or ACLED OAuth |

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

**Stage 4 harmonisation (2026-10-11) — what building the base measured.** The stage's job was to build
a table; what it produced that matters is one constraint and two confirmations.

- **The monthly spine is 10.1 % observed (C-30).** 775 of 7,682 rows are direct observations; 4,389 are
  linear interpolations between annual points and 2,518 are empty months within the spine's span. That
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

## 7. Blocked

| Blocker | Needs |
|---|---|
| ~~FRED key~~ | ✅ **Unblocked 2026-10-11** — registered, key in `.env`, Brent landed, `oil` acquired (C-23) |
| UCDP token, ACLED OAuth app | **You** — two free registrations. These are the only route to the security outcomes |
| ~~FAAC parser (D1)~~ | ✅ **Unblocked 2026-10-16** — both publishers crawled, 174 documents parsed, every one reconciled to its own Total row (C-39/C-41) |
| State IGR parser (D2) | NBS publishes PDFs and HTML, no API. D2 is FAAC ÷ (FAAC + IGR), so the IGR half is now the only missing input |
| A Stage 3 gate on the FAAC series (S4-17) | The Stage 3 gates over the new monthly national series, before it can enter `dim_metric` and the Tier-3 system |
| UNESCO UIS current API path | Its docs (web search unavailable in this environment) |
| NEMIS reachability | A check from a network other than this one |
| DHIS2 tenant access | Institutional credentials; do not design a model on it until confirmed |
| Monthly NBS CPI — the grain the app's chart spec states | The manual-download parser. The landed CPI is annual, so the spine is 10.1 % observed and design B cannot see the 2023 window monthly (C-30). Either parse the monthly series, or run design B at its annual cross-check |

## 8. Next steps, in order

Stages 0–4 are done. One registration still gates the security domain, and the critical path to a
fitted model contains no acquisition step at all — but it does contain a **grain problem** that Stage 4
measured rather than inherited (C-30), and that choice belongs to Stage 5.

**A. One free registration left.**

1. **UCDP token** → the only route to the security outcomes (`fatalities`, `incidents`). The endpoint
   and header are already confirmed (C-14) and the client is written and tested on its failure path.
   ACLED remains the richer alternative but needs OAuth and forbids redistribution.

   FRED needed no code and no further action: the account is registered, the key is in `.env`,
   `pull_fred.py` runs keyed, and the `oil` node is acquired — so the covariate gap that appeared
   against designs A, B and C is closed for three of those nodes at once.

**B. Unblocked now, no credentials needed.**

2. ~~**Stage 3 — quality gates.**~~ **Done 2026-10-11.** The study-window floor is in and quantified
   (198 pre-1999 spikes suppressed); the Brent daily→monthly rule is **frozen as a declared input**
   (`mean_of_daily_observations`) and applied by the gates, so Stage 4 must reuse it rather than
   re-choose it. Carried forward: **60 unadjudicated spikes**, and the `donor_oda` contamination that
   must reach every health and education card (C-28).
3. ~~**Stage 4 — harmonisation** (dbt).~~ **Done 2026-10-11.** The analytical base exists: 7,682 rows
   (23 metrics × 334 months, 1999-01 → 2026-10) on a local DuckDB, with the January-2000 index anchor
   and its recorded fallback, direction labels as a dimension, the base-spec §7 administration spine
   plus term-level party-by-tenure strata, the 37 × 334 state panel with declared-empty dose columns,
   the shock bands, and the Stage 3 quality status and 8 definition breaks travelling on it. 92 dbt
   tests and 20 break-tests; `tests/verify_harmonisation.py` recomputes the whole base independently.
4. **Stage 5 — the design memo.** The next unblocked step, and now the one that decides the most: it
   takes C-30 (the monthly spine is 10.1 % observed, so the 2023 window is not monthly-visible on the
   landed CPI), C-28 (the `donor_oda` contamination), C-27 (the 2025 CPI rebasing), the 60
   unadjudicated spikes and the 3 frequency gaps, and drops failing designs *on the record*. Attaching
   diagnostics to each DAG card is the whole of its work.
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

6. ~~**Stage 5 re-run — the design memo.**~~ **Done 2026-10-17 at vintage 2026-10-16.** The dose and
   Tier-3 checks were re-run against the post-FAAC base: the nominal column is now a measured dose axis,
   the specified axis `D1` (per capita) still decides the family, the Family A card text is derived
   rather than typed, all 36 cards were re-emitted, and `tests/verify_stage5.py` passes again (S5-10,
   S4-20, C-44). What the re-run **did not** do, and what now heads this list:
   - **X-09 — the state population denominator.** It is the only thing standing between the landed
     nominal dose and the per-capita axis Family A's estimand is written on, and it is a decision.
   - **A state-attributed outcome.** Family A's other blocker: the security series are the route and are
     credential-blocked (C-13/C-14); the health and education outcomes are national.
   - **A metric-catalogue entry for the FAAC panel** with a declared monthly-to-annual aggregation, which
     is what Family B's Tier-3 system is missing now that the series exists and is gated.
   - **`dag_designs.yml`'s `dose`/`faac` nodes still read `source_status: gap`,** deliberately — the node
     is specified as *per capita*, and the per-capita axis is absent. Noted in `docs/dags.md` rather than
     flipped, because `gap` is under-specified here, not wrong.
7. **Stage 6 — estimation (R).** Fill each card's `estimate` block (`did`/`fixest`, `vars`/`urca`/`dynlm`,
   `Synth`/`coresynth`/`scpi`). A card without an interval still does not ship.
8. **Stages 7–8** — specification curve, then the registry, narrative and RAG corpus.
9. **Stage 9 — the app**, reading `registry/dags/index.json`: pick an outcome → pick a causal model →
   read the assumption and adjustment set → then the estimate under that model.

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
