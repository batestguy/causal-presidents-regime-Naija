# Design memo — what the data can support (Stage 5)

**Vintage 2026-10-11 · re-run at vintage 2026-10-16 · re-run again at vintage 2026-10-17.** Built by
`analysis/R/02_diagnostics.R` from the analytical base and `analysis/specs/diagnostics.yml`; every number
recomputed independently by `tests/verify_stage5.py`. The current artifact is
`registry/diagnostics/2026-10-17/`.

> **This memo's verdicts are pre-estimation, and Stage 6 has since run two of them.** The third re-run
> (2026-10-17) followed the security outcome landing (C-45), which cleared Family A's *outcome* blocker:
> the family is still dropped on the dose **axis** — per capita waits on X-09 — but it is now estimable on
> the nominal axis, and Stage 6 estimated it. **Read `docs/estimates.md` before acting on the Family A
> row**: the estimate is published as `estimated_not_identified`, because the dose's post-fixed-effect
> variation is the 13 % derivation share moving with the oil price and a mis-timed dose fits just as well
> (C-47). Design B's row below says its testable system is `{Y, log(oil), fx}`; Stage 6 ran
> `{Y, log(oil)}` at monthly grain on the FAAC side and found a real transmission channel (C-48).

> **The re-run changed the reasons, not the verdicts (2026-10-17).** The 2026-10-11 run was computed
> against a base that no longer exists. Family A read "dropped — **0 of 12,358** dose values present" and
> Family B read "FAAC is absent"; the dose has since been acquired, parsed and **Stage 3 gated** — 114
> months × 36 states, `state_panel.faac_gross_total_naira`, with `dose_gate_status` on the panel per state
> (S4-13…S4-19, C-39…C-43). What the re-run established is narrower and more useful than "A is now
> fine":
>
> * **A dose exists, but not on the axis this design is written on.** `dose.specified_axis` is `D1`
>   (FAAC *per capita*), which needs the state population denominator decision (X-09); the nominal axis is
>   present and passes its variation checks. Family A therefore stays **dropped** with the blocker
>   `specified_dose_axis_absent:D1 and no_state_attributed_outcome` — a present-but-unspecified axis is
>   not allowed to turn the gate green by proxy (S5-10).
> * **Family B's deviation is now about the catalogue, not the data.** The national FAAC series exists and
>   is gated; what it lacks is a metric-catalogue entry, which needs a declared monthly-to-annual
>   aggregation and an outcome decision for a series that begins 2016-12.
>
> The verdict totals are unchanged (15 fail, 7 degraded, 14 not attempted, 0 pass), and the sections below
> have been updated where their reasons changed. Everything else — the grain, the cointegration ranks, the
> detectable-effect sizes, the donor-pool infeasibility — was measured against the base and is unaffected.
Machine-readable companion: `registry/diagnostics/2026-10-16/diagnostics.json` (the re-run); the human
page is `registry/diagnostics/2026-10-16/report.md`. This memo is the Stage 5 output PHASES.md names — for
each outcome, which design family is credible, which is not attempted, and **the diagnostic that
justifies the call**.

The governing rule is PHASES.md's: *models failing their pre-check are dropped here, on the record,
which is far cheaper than dropping them after their estimate looks inconvenient.* Nothing below is
a result. It is the boundary inside which results will be obtained at Stage 6.

---

## The verdict in one screen

| Design | Status | Deciding diagnostic | What it would take to revive it |
|---|---|---|---|
| **A** — state dose-response DiD | **dropped** | dose validation: **0 of 12,358** values on the specified axis (`D1`, per capita) across 37 states — the nominal axis is present and gated | the state-population denominator decision (X-09), **and** a state-attributed outcome (the security series are the route and are credential-blocked) |
| **B** — national VECM / ARDL | **degraded** | cointegration rank, DoF, collinearity; the base-spec Tier-3 system has no FAAC — the series exists and is gated, but has **no catalogue entry** | a metric-catalogue entry for the FAAC panel, and a decision on whether an annual-grain estimate is worth publishing |
| **C** — synthetic control | **feasible on one outcome** (re-run 2026-10-18) | pre-treatment fit over a **99-country** pool: `u5mr` passes **3 of its 4** windows; `gdp_growth` 1 of 4 and `cpi_yoy` 0 of 4 do not pass the declared strict-majority rollup | build the estimator and its placebos on the `u5mr` windows |

All **36** (outcome × design) cards carry their own pre-check verdict: **15 fail, 7 degraded,
14 not attempted, 0 pass.** No outcome clears its gate under any design at this vintage. That is the
finding.

---

## 1. The grain the tests run on

Every test runs on the **native observation** a source actually published — never on the monthly
spine. The spine used by the app is only **10.1 % observed** (775 of 7,682 rows; 4,389 interpolated,
2,518 empty). A unit-root or cointegration test on interpolated rows reports the properties of the
interpolator, not of the data: linear interpolation induces near-perfect serial correlation by
construction, so ADF would fail to reject stationarity for a series that is strongly mean-reverting,
and Johansen would find rank in a system of straight lines.

**Consequence.** Family B is evaluated at its **annual** cross-check (~26 observations), which base
spec §9 already assumes and its sample-size constraint already discloses — *not* monthly. This is the
same constraint Stage 4 surfaced as C-30 and it is now a Stage 5 gate, not a note.

---

## 2. Family A — state dose-response DiD — **dropped**

PHASES.md risk table: *"Dose D1 fails the variation check → the whole Family A collapses to a level
comparison."* It fails.

| Axis | Column | Non-null | States with dose | Verdict |
|---|---|---|---|---|
| D1 | `d1_faac_per_capita` | 0 | 0 | **absent** |
| D2 | `d2_faac_share_of_state_revenue` | 0 | 0 | **absent** |
| D3 | *(constructed)* | 0 | — | **not built** |

The state panel exists and is complete — **12,358 rows = 37 states × 334 months** — and on the specified
axis its dose column is still typed and empty: **D1 (FAAC per capita) is `absent`, 0 values**, because the
state population denominator is an unmade decision (X-09). The other axes are measured and reported
separately (`D1=absent, D1_nominal=pass, D2=absent, D3=not_built`), and the row-level status is now
earned rather than table-wide: `dose_status` is `observed` on **4,104** state-months, `not_covered` on 36
and `declared_gap` on 8,218, and the nominal dose carries its Stage 3 gate result per state. There is no
state-attributed outcome either, so the panel's outcome side is still structure without data. The parallel-trends pre-check is therefore `not_run` rather than passed or failed: with no
exposure groups there is nothing to compare.

**Why this is a data finding, not a null result.** "We found no dose-response effect" and "we had no
dose to estimate one from" are different statements. The card for every Design A outcome says so
(`docs/dags.md`, G-05). The two blockers are `specified_dose_axis_absent:D1` and
`no_state_attributed_outcome` — and the first of those is a *decision*, not an acquisition: the FAAC
documents are landed, parsed and gated, and what is missing is the state population denominator (X-09)
that turns the nominal allocation into the per-capita exposure this estimand is written on.

---

## 3. Family B — national VECM / ARDL — **degraded**

Design B runs, but not as base spec §9 specifies. The `faac_in_tier3_system` check is recorded as a
**deviation**, not a failure: the design is estimable, it just is not the model §9 describes.

### 3.1 Integration order (18 testable series of 26, native grain)

Each series is classified I(0) / I(1) / I(2) only when all three tests agree at the level **and** at
the first difference. A single level-regime break (Brent 2008; the naira 2016 and 2023) must not be
read as a second unit root. Where the three tests disagree the series is carried as **I(1)** —the conservative branch, which can only make the reported cointegration rank smaller — and the card marks
it inconclusive. **10 of the 18 testable series are inconclusive** (`I(1)*` in the report; the other 8
of the 26 are too short to test at all); that is an honest reading of ~26 annual observations, not noise
to be averaged away.

### 3.2 Cointegration (Johansen, `{Y, log(oil), fx}`, K=2)

| Outcome | n | Trace rank | Max-eig rank | Taken | Estimator |
|---|---|---|---|---|---|
| `u5mr` | 26 | 3 | 3 | 3 | VAR in levels (reads as stationary) |
| `mmr` | 25 | 3 | 3 | 3 | VAR in levels — **rank marginal (~9 %)** |
| `immun_penta3` | 26 | 0 | 0 | 0 | ARDL bounds fallback |
| `gdp_growth` | 27 | 0 | 0 | 0 | ARDL bounds fallback |
| `cpi_yoy` | 27 | 1 | 1 | 1 | VECM |
| `unemp` | 27 | 1 | 1 | 1 | VECM |

**FAAC is absent from the metric catalogue**, so the base-spec Tier-3 system (oil + FAAC + FX + lags +
trend) is reduced to `{Y, log(oil), fx}`. The deviation travels onto **every** Design B card.

A rank equal to the system dimension means the trace test rejected every rank below it — the system
simply reads as *stationary*, which is not cointegration, so the honest estimator is a VAR in levels
rather than a VECM that dresses a stationary system up as a long-run relationship. A rank of 0 gives
the declared ARDL-bounds fallback (base spec §9).

**A caveat the verifier found, recorded rather than buried.** `urca::ca.jo` and an independent
implementation agree to <0.2 % on a controlled synthetic system but diverge ~10 % on these strongly
trending series, because they handle the deterministic term differently. The **rank is invariant**
under that difference for five of six outcomes; for **`mmr` it is not** — the deciding statistic sits
only **8.9 %** over its critical value, so a different convention reaches rank 2 (a VECM) instead of
3. `mmr`'s Design B card carries `rank marginal` in the check detail; Stage 6 must not treat its
rank as settled. `tests/verify_stage5.py` warns on exactly this case and fails on any *non-marginal*
rank disagreement.

### 3.3 Degrees of freedom and the detectable effect

The MDE is the smallest tenure effect this design could detect at 80 % power / 5 % significance,
computed from the noise scale of a deliberately thin baseline model (`Y ~ log(oil) + trend`) so the
power reckoning never sees the estimate it is meant to precede. `xSD` is the MDE in units of the
residual SD — a value of 1 means the design can only see effects as large as the series' own
residual variation.

| Outcome | Annual rows | Params | Residual DoF | σ | cond(X) | MDE xSD (Tier-3) | MDE xSD (leaner) |
|---|---|---|---|---|---|---|---|
| `u5mr` | 22 | 14 | 8 | 5.38 | 3.1e5 | 39.5 – 79.7 | 1.9 – 5.1 |
| `mmr` | 21 | 14 | 7 | 48.16 | 4.3e5 | 48.6 – 99.4 | 2.1 – 5.9 |
| `immun_penta3` | 22 | 14 | 8 | 8.04 | 2.5e4 | 39.3 – 44.0 | 1.9 – 5.1 |
| `gdp_growth` | 23 | 14 | 9 | 2.50 | 2.7e4 | 38.6 – 53.2 | 1.8 – 4.5 |
| `cpi_yoy` | 23 | 14 | 9 | 5.19 | 3.1e4 | 37.7 – 49.3 | 1.8 – 4.5 |
| `unemp` | 23 | 14 | 9 | 0.71 | 2.4e4 | 35.1 – 47.3 | 1.8 – 4.5 |

Written down **before** any estimate, per PHASES.md. The Tier-3 MDE of **35–99 residual SDs** looks
absurd until it is separated from the data: dropping the mandated `oil × tenure` interactions (the
"leaner" column) brings it to **1.8–5.9 SD**. **The interaction terms alone widen the detectable
effect ~10–20×**, because they are nearly collinear with the tenure dummies themselves (R² 0.997–0.999).
That is a statement about the *design matrix*, not about the data — the base spec makes the
interaction non-negotiable (M-03), and it is what makes a ~23-row annual design unable to detect
anything short of a huge effect. Stage 6 must report the interval, never the point, and this table is
why.

No outcome hits the `min_dof = 3` floor; the binding constraint is power, not feasibility.

### 3.4 Collinearity

| Outcome | Max VIF | Term | Verdict |
|---|---|---|---|
| `u5mr` / `immun_penta3` | 19.9 | `trend` | flag |
| `mmr` | 21.7 | `trend` | flag |
| `gdp_growth` / `cpi_yoy` / `unemp` | 16.6 | `trend` | flag |

No outcome reaches the `vif_fail` = 30 mark, so the check is `flag`, not `fail`. But the term is the
same every time: the party-by-tenure dummies are functions of the calendar, so over five
administrations in ~27 years the dummies and the linear/quadratic trends compete for the same
variation. The dummies are **identified off the trend terms rather than off the administration** —
a property of the design, not of the data, and one Stage 7's trend specification must exercise.

The dosage-collinearity check across D1/D2/D3 is `not_computable` and the blocker (`no_dose_series`)
is named rather than reported as a pass.

### 3.5 A carried-in caveat: `donor_oda`

`donor` sits in Design B's adjustment set for every health and education outcome. Stage 3 found it
rose **+1006 % in 2005** because Paris Club debt relief is recorded as ODA (C-28). A design
conditioning on it is partially conditioning on a debt restructuring. This does not fail a Stage 5
gate, but it belongs in the memo because it bounds what a Design B health estimate means.

---

## 4. Family C — synthetic control — **feasible on one outcome**, after the pool was widened

**Re-run 2026-10-18** against a **99-country** candidate pool screened on oil dependence, region/income
band and coverage (`ingestion/flows/pull_worldbank_donors.py`, S5-11), where the first run had 13 chosen
on GDP comparability and geography. The gate is the **globally optimal** simplex fit to the
pre-treatment path (a quadratic program), so a failure is a statement about the donor pool, not an
optimiser. `ratio` = pre-RMSPE ÷ pre-period outcome SD; the threshold is 0.10.

| Outcome | Window | Pre yrs | Pre-RMSPE | Pre SD | ratio | best 1 donor | ratio on diffs | Verdict |
|---|---|---|---|---|---|---|---|---|
| `u5mr` | yaradua | 8 | 0.026 | 15.19 | **0.0017** | 3.874 | 0.024 | **pass** |
| `u5mr` | jonathan | 11 | 0.027 | 18.51 | **0.0014** | 3.439 | 0.018 | **pass** |
| `u5mr` | buhari | 16 | 0.089 | 21.41 | **0.0042** | 6.313 | 0.013 | **pass** |
| `u5mr` | tinubu | 24 | 4.250 | 21.42 | 0.198 | 9.737 | 0.064 | weak fit |
| `gdp_growth` | yaradua | 8 | ~0 | 2.96 | **~0** | 2.958 | ~0 | **pass** |
| `gdp_growth` | jonathan → tinubu | 11–24 | 2.06–2.80 | 2.60–3.20 | 0.29–0.51 | 2.60–3.19 | 0.08–0.43 | weak fit |
| `cpi_yoy` | yaradua → tinubu | 8–24 | 2.94–4.90 | 3.92–5.11 | 0.56–0.74 | 3.85–6.20 | 0.52–0.71 | weak fit |

**The verdict is `pass` on `u5mr` (3 of 4 windows, ratios 0.0014–0.0042 against the 0.10 threshold),
and not a pass on `gdp_growth` (1 of 4) or `cpi_yoy` (0 of 4).** That is the honest reading of a
sharp change, and it carries its own warning:

- **A 99-donor simplex can fit almost any pre-period.** The `gdp_growth`/yaradua window reaches a ratio of
  1.7e-06 and `u5mr`/yaradua 0.0017, i.e. the fit is interpolation, not validation. The gate was declared
  necessary-not-sufficient when the pool had 13 members; with 99 it is **weaker evidence than it was**,
  and the numbers that can still fail are the ones reported beside it: the fit on **first differences**
  (0.013–0.064 on the passing `u5mr` windows), the cross-check against the estimator the spec names, and
  the placebos Stage 5 defers to Stage 6. The verdict below is permission to build the design, not
  evidence that its fit is real.
- **The rollup rule was undeclared until now.** The engine used "any window passes" and nothing said so;
  with 13 donors nothing passed, so it never showed. With 99 it would have reported `gdp_growth: pass`
  while three of its four windows failed. The rule is now declared as a **strict majority of the runnable
  windows** (`diagnostics.yml` `outcome_rollup`), the engine and the Stage 5 verifier both implement it,
  a break-test mutates a minority-pass card to `pass` and requires the verifier to reject it, and the
  counts (`n_windows_pass` / `n_windows_runnable`) travel on every verdict.
- **The estimator the spec names still does not beat a single donor.** `Synth::synth` returns a fit worse
  than the best single donor (`u5mr`/yaradua: 85.22 vs 3.87). Its default V search failed on this pool too.
  Recorded as a finding for Stage 6, not relied upon: the gate rests on the QP, which is a global optimum.
- **The API blocked part of the pool and the block is recorded.** A content-based WAF rejects some country
  combinations (`LK;LR` → 200, `LK;LR;LS` → 403 every time); the flow splits and retries, and the manifest
  carries the split depth per request (C-60). Libya, Lesotho and Sri Lanka therefore land through narrower
  requests rather than being dropped silently.

Outcomes not in the donor panel (`mmr`, `immun_penta3`, `skilled_birth`, `literacy_youth`,
`primary_completion`, `ner_primary`, `fatalities`, `incidents`, `unemp`) are `not_attempted`: no
donor path exists to synthesise against. `fatalities` and `incidents` are in the UCDP *outcome* but not in
the World Bank predictor set, so a Design C for the conflict outcomes needs a donor conflict path — a
separate acquisition this re-run did not make.

---

## 5. Shock-window visibility

PHASES.md: *"confirm the 2016, 2020 and 2023 windows are visible in the data rather than assumed."*

| Window | Months | Visible on | Single anchor only | Not visible on |
|---|---|---|---|---|
| Oil crash & recession (2014-06 → 2016-12) | 31 | `oil` | 3 metrics | 3 metrics |
| COVID-19 (2020-03 → 2020-12) | 10 | `oil` | 16 metrics | 6 metrics |
| Fuel subsidy removal & naira float (2023-06 → 2023-12) | 7 | `oil` | 16 metrics | 6 metrics |

Brent is genuinely monthly and complete, so each shock is **visible on `oil`**. But on the annual
outcomes the window is measured by **one** observed point (the July anchor), and inside the 2023
window the other months are interpolated. Any claim about what happened *inside* such a window is a
claim about that one anchor month. This is the same constraint as §1 seen from the shock side, and it
is why the 2023 window is not monthly-visible on the landed CPI.

---

## 6. What was dropped, on the record

- **Family A** — dropped. PHASES.md Stage 5 dose validation: a dose with near-zero cross-state
  variance cannot support a dose-response design, and no estimator fixes that. (0 of 12,358 values.)
- **Family C** — feasible on `u5mr` only (re-run 2026-10-18 over a 99-country pool): 3 of its 4 windows
  pass the pre-fit gate, `gdp_growth` passes 1 of 4 and `cpi_yoy` none. No candidate treated window lets any convex combination of the donors
  track Nigeria's pre-treatment path. Reported infeasible rather than estimated, per the Stage 6 gate.
- **Family B** — degraded, not dropped. It can be estimated, but at annual grain and without FAAC, and
  with a ~38–99 SD detectable effect on the Tier-3 design. The deviations are named on every card.

---

## 7. What this hands to Stage 6

1. **Nothing clears its gate**, so Stage 6 does not estimate a headline effect. It estimates the
   *boundary*: what an annual Design B VECM/ARDL, and the narrower differenced Synthetic Control,
   can and cannot say — with the MDE table as the disclaimer.
2. **The single unblocking action** is the NBS FAAC parser (a PDF/HTML parser in the same family as the
   monthly NBS CPI parse). It revives Family A outright and restores the base-spec Tier-3 system for
   Family B.
3. **`mmr`'s Design B rank is marginal** and must not be reported as settled.
4. **Every point estimate carries its interval**, and a multiplier whose interval spans both signs is
   not a finding (PHASES.md Stage 6).

## 8. How to reproduce

```bash
Rscript analysis/R/02_diagnostics.R                    # writes diagnostics.json + report.md
Rscript analysis/R/01_build_dags.R                     # attaches the diagnostics to the 36 cards
conda run -p C:/Users/TOSHIBA/ds-general python tests/verify_stage5.py
```

`verify_stage5.py` recomputes the spec echo, the observed-spine fraction, all 69 shock-window counts,
the dose validation, the Johansen rank, the 12 pre-treatment QPs, the Tier-3 MDEs and the per-card
verdicts from the analytical base — and re-derives the design verdicts from the card statuses rather
than trusting the summary.
