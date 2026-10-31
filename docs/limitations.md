# What this project cannot say — the limitations, written before the findings

**Vintage 2026-10-18.** Every count below is derived from an artifact, not typed from memory:
`registry/quality/2026-10-18/`, `registry/diagnostics/2026-10-18/`,
`registry/estimates/2026-10-18/`, `registry/robustness/2026-10-18/`,
`registry/events/2026-10-18/` and `registry/dags/`. The narrative claims that can be checked
mechanically are registered in `tests/verify_registry.py`, `tests/verify_events.py` and
`tests/verify_stage5.py`, so a number that moves fails a verifier instead of being repeated here.

**Why this document comes first.** Base spec §19 asks for the limitations to be drafted *before* the
findings, and to be longer than them. This is longer than [`docs/estimates.md`](estimates.md) on purpose.
A limitations page written after the results tends to become a list of things that are nearly true; this
one is the boundary the results sit inside, and it was written as the last analysis stage rather than as
the first marketing one.

## 1. The question this project was asked is not answerable with this data

The brief asks whether PDP and APC tenures moved health, education, security or the economy. **They did
not answer that, and no estimator would have.** There are four to five administrations in the window and
22–23 annual observations per national outcome. Stage 5 rebuilt the actual design matrix and computed the
smallest effect each design could detect at 80 % power:

| Outcome | Residual DoF | MDE (Tier-3 design) | MDE (leaner design) |
|---|---|---|---|
| u5mr | 8 | 39.5 – 79.7 × residual SD | 1.9 – 5.1 × residual SD |
| mmr | 7 | 48.6 – 99.4 | 2.1 – 5.9 |
| gdp_growth | 9 | 38.6 – 53.2 | 1.8 – 4.5 |
| cpi_yoy | 9 | 37.7 – 49.3 | 1.8 – 4.5 |
| unemp | 9 | 35.1 – 47.3 | 1.8 – 4.5 |

The Tier-3 column is not a quirk of the estimator; it is the mandated `oil × tenure` interactions, which
are collinear with the tenure dummies at R² 0.997–0.999. The only effects this design can see are ones as
large as the series' own residual variation, which is not a hypothesis. **This is a statement about
arithmetic, not a null result**, and the distinction matters: "we found no tenure effect" would imply the
design could have found one.

**What would change it:** sub-national monthly health and education outcomes. DHIS2 has no verified
access, NEMIS/NEDI are unreachable, UNESCO UIS returns 404 at every path, and the DHS rounds are
five-yearly and non-redistributable. That is a data wall, not a modelling choice.

## 2. Most of the monthly spine is not observed

The analytical base holds **8,350 rows** (25 metrics × 334 months). Of those, **1,373 rows (16.4 %) are
observed**, 4,389 are interpolated and 2,588 are unobserved. The monthly series the app draws is
therefore a picture of the interpolation rule in most cells, which is why the base carries
`observation_type` on every row and why the app must render interpolated segments dashed.

- **Tests never run on the spine.** Every unit-root, cointegration, pre-fit and power test runs on the
  native grain a source published (S5-01). A test on interpolated rows reports the interpolator's
  serial correlation as if it were the data's.
- **Three frequency gaps are declared, not smoothed:** `cpi_yoy`, `gdp_growth`, `unemp`. The CPI series is
  annual, which is why the 2023 subsidy-removal window is **not monthly-visible** even though the spine
  now reaches it (C-30). A monthly VECM on `cpi_yoy` would estimate the interpolation.
- **Consequence for Design B:** its testable system is the annual cross-check, ~26 observations. That is
  the design the base spec already discloses, not a shortfall discovered late.

## 3. Coverage limits, node by node

| Node | What landed | What it cannot carry | Where it is recorded |
|---|---|---|---|
| FAAC state allocation (the dose) | 2016-12 → 2026-06, 36 states, 174 documents | Nothing before 2016-12: the PDP era is a declared gap. `dose_status` is `observed` on **4,104** of 12,358 state-months, `declared_gap` on **8,218**, `not_covered` on 36 | `state_panel`; C-39…C-43 |
| D1 — FAAC **per capita** | **0 of 12,358** rows | The per-capita *form* of Family A's estimand: the fitted elasticity is nominal, because state fixed effects absorb `-log(population)` (S6-06), while the **level** claim — "a state with more people gets more money" — still needs the series. X-09 (the population denominator) is an unmade decision | S5-10, S6-06, X-09 |
| D2 — FAAC share of state revenue | **0 rows** | The NBS state-IGR half is not parsed | diagnostics `dose` block |
| UCDP GED (security outcome) | state × month, 1990-09 → 2025-12 (GED 26.1) | The 10 months after 2025-12; a reported-events archive, not a census | C-45, C-82 |
| ACLED | not wired | Richer event data, but OAuth registration, a 12-month embargo and no redistribution | Stage 1 register |
| DHIS2 immunisation | unverified tenant | Monthly health outcome | Stage 1 register |
| Education (NEMIS/NEDI, UNESCO) | unreachable / 404 | Annual completion and literacy after 2010 | C-11, C-12 |
| NGN/USD monthly | absent | Separating the price channel from the exchange-rate channel inside Design B | C-46 |
| Brent crude | daily 1987 → 2026 | Nothing, once the daily→monthly rule is frozen — which it is (`mean_of_daily_observations`) | Stage 3 |

**The FX omission is substantive, not cosmetic.** A naira-denominated allocation response to a
dollar-denominated shock mixes two channels, and the naira was devalued twice inside the 2016-12 →
2026-06 window. No keyless publisher carries a monthly NGN/USD series; it would have to be assembled from
CBN by hand.

## 4. The quality gates flagged almost half the landed series

**674 series** are gated: **359 `ok`, 313 `flagged`, 2 `empty`**. `flagged` does not mean unusable — it
means a rule fired and the reason travels with the series into the base and the registry. The two empty
series are Eritrea's and Somalia's CPI in the donor panel, which the source has no data for. (The two
series added on 2026-10-29 are the NBS monthly CPI's index and year-on-year change, both `ok`:
`registry/quality/2026-10-29/`.)

- **8 definition breaks** are annotated rather than removed: GDP rebasing (2014), the unemployment
  methodology change, the January-2025 CPI rebasing (C-27), and the FX regime breaks among them.
- **`donor_oda` contamination** is carried on every health and education card: donor flows are a
  confounder that no adjustment set in this registry closes (C-28).
- **The FAAC dose is flagged on spikes that fire in every state at once** — a distribution-cycle artefact,
  not 36 independent shocks (C-43). The gate result is on the panel per row, so no model can use the dose
  without inheriting that statement.

## 5. Design A is estimated, not identified — and its interval includes zero

| Outcome | Coefficient | SE | 95 % CI | p |
|---|---|---|---|---|
| fatalities | **+0.4678** | 0.2812 | **[−0.0833, +1.0189]** | 0.096 |
| incidents | +0.5278 | 0.1944 | [+0.1467, +0.9088] | 0.007 |
| civilian fatalities | +0.3427 | 0.4911 | [−0.6198, +1.3052] | 0.485 |

Read the first row before any sentence that uses the number: **the interval crosses zero on its own**, and
the design's own decisive check fails. A dose shifted 24 months forward within each state returns
**+0.3101** against the published **+0.4678**, and across 60 non-zero lead shifts **10 return an estimate
at least as large** (p = **0.167**). The verdict is `estimated_not_identified`, and it is the artifact's,
not this page's.

**Why the identification fails, measured rather than asserted:** after state and month fixed effects, the
dose's residual variation is **0.50 in Delta/Bayelsa/Rivers against 0.11 elsewhere**. What survives two-way
differencing is mostly the 13 % derivation share moving with the oil price and with production volumes — a
national oil shock interacted with a fixed state characteristic, not the randomised-looking exposure a
dose-response design assumes.

**The planned estimator was not used, and that is recorded rather than glossed.** PHASES.md specified
Callaway & Sant'Anna group-time ATTs (`did`). That estimand needs a treatment date per unit; every state
receives an allocation every month and the variation is a magnitude, not a switch. `did` remains correct
for a future design with a real staggered adoption date — it is not a substitute for one.

**What would identify it:** a fiscal instrument that varies within state for reasons unrelated to oil —
state IGR, the VAT distribution, or a state-level policy with genuine start months. That is a different
acquisition, not a different estimator.

## 6. Design B's channel is estimated; its timing and its decomposition are not

| Horizon | Cumulative elasticity | SE | 95 % CI |
|---|---|---|---|
| 0 | −0.160 | 0.124 | [−0.402, +0.082] |
| 2 | **+0.518** | 0.166 | **[+0.192, +0.844]** |
| 3 | **+0.470** | 0.158 | **[+0.161, +0.779]** |
| 4 | +0.161 | 0.162 | [−0.156, +0.478] |
| 6 | +0.231 | 0.218 | [−0.197, +0.659] |
| 12 | +0.325 | 0.319 | [−0.300, +0.949] |

Only **h = 2 and h = 3 exclude zero**. The claim this supports is the sign and rough size of a
transmission channel, not a horizon at which it peaks: Stage 7's in-time placebo, over 48 shifted
alignments, puts **p = 0.0625** on the timing (3 of 48 shifted estimates are at least as large), and that
bound is published rather than widened until it passed (S7-04).

- **The FX channel is inside the estimate**, so "a 10 % Brent move reaches the states as ~5 % more money"
  is a price-plus-exchange-rate statement.
- **It is a national channel on a mediator.** FAAC is a *mediator* on every card, not an outcome, which is
  why the result sits once on the registry index with `result_is_card_level: false` and no Design B card
  carries a number.
- **114 months is not many**, and two devaluations sit inside them.

## 7. Design C was built, and it did not identify an effect

Stage 5's earlier `infeasible` verdict was a statement about the **donor pool**. Widened from 13 to **99
countries**, the pre-fit gate passes `u5mr` on **3 of its 4** runnable windows, `gdp_growth` on 1 of 4 and
`cpi_yoy` on **0 of 4**, under a strict-majority rollup that is declared rather than inferred (S5-12). The pass
carried its own warning: **a 99-donor simplex can fit almost any pre-period**, and in the 13-donor run a single
donor beat the fitted simplex (C-59).

The estimator and its in-space, in-time and leave-one-donor-out placebos now exist
(`registry/design_c/2026-10-18/`). **Four windows were estimated and none is identified.** The in-space rank p
runs from 0.17 to 0.50; the in-time placebo fails where it can be run; and **304 of 396 placebo fits also clear
the gate's own 0.10 threshold**, so the pre-fit gate does not discriminate on this pool. Two further limits:

- **The declared problem is underdetermined.** With 99 donors and 8 to 24 pre-years, a face of weights fits the
  pre-period equally well. The artifact publishes the solver's vertex and a unique ridge refit; for one window
  they disagree in sign, which means that gap is a property of the solver, not of Nigeria.
- **There is no interval.** A synthetic control's inference is a rank among placebos. The honesty layer publishes
  no point estimate without an interval, so no gap reaches a card; the `u5mr` card names the reason and points
  at the artifact.

## 8. Inference floors that no interval can hide

- **36 clusters, 114 national months.** A wild-cluster bootstrap would be the fix for the state-clustered
  errors and is **not applied**; the spec declares it.
- **A permutation null is not automatically a valid null.** Shuffling the dose across states within a
  month destroys the cross-state mean the state fixed effects already absorb. It returned p = 0.000 on a
  design whose own placebo was 63 % of the estimate (S6-07). The time-shift null is the one that decides a
  timing claim, and it is the one reported as decisive.
- **Oster's δ is negative for both designs** (A: −1.53 with the control set flipping the estimate's sign;
  B: −44.0 with the controls moving it away from zero). Oster's δ ≥ 1 cutoff does not apply, and the
  artifact says so rather than reporting a number that reads like a pass (S7-05).
- **Rosenbaum bounds are not applicable** — continuous treatment, no matching — and are recorded as such
  with the reason.
- **Four events.** The transition study's exhaustive placebo over 58 eligible months cannot produce a
  p-value below **1/59 = 0.017**, and the family-wise maximum is published because a reader looking at
  four estimates is looking at the largest of four.

## 9. Robustness: the sign survives for one design and not the other

**129 specifications** were declared before any was fitted and all are published (81 for Design A, 48 for Design B across its two outcome families).

- **Design A: 60 positive against 21 negative** of 81, with two inside the declared near-zero band.
  **One axis level flips by majority** — `outcome = fatalities_civilians`, 15 of 27. The pre-registered
  `outcome = fatalities` level does **not** flip (6 of 27), and neither does the dose lag any more
  (10 of 27): under the superseded 25.1 history it was negative in all three windows and is now positive in
  two of three. The 36 leave-one-state-out refits do not flip the sign ([0.1429, 0.5950], 0 flips), so the
  fragility is the identification rather than one unit. The verdict is unchanged because the check that
  decides it — the lead-shift placebo — still fails (C-82).
- **Design B: 36 of 48** specifications are positive across its two outcome families. The **fiscal**
  family is **24 of 24**, with every interval excluding zero and coefficients from 0.397 to 2.398; the
  pre-registered cell reproduces Stage 6 to 4.3e-12. The **price-level** family (C-85) is 12 positive and
  12 negative, and no coefficient in it is distinguishable from zero at any horizon — which is the same
  answer Stage 6 gives for that family, reached 24 ways. The timing remains the weak part of the fiscal
  one.
- **Four axes are declared dead with their reasons** rather than dropped: imputation handling, index
  anchor, donor pool, event window. A fifth — the per-capita dose — is live in principle and unbuilt in
  fact, so every cell of the curve is the nominal dose.

## 10. Measurement limits no design fixes

- **UCDP GED is a reported-events archive.** The reporting-divergence check is a guard, not a correction,
  and it cannot rule out that a change in what the archive records produced a change in the series.
- **The index has two anchor regimes:** 25 anchors, **18 at the fixed January-2000 anchor and 7 on the
  recorded fallback rule**. The fallback is disclosed per series in the base.
- **The dose is nominal, not per capita.** With state fixed effects the elasticity is invariant to a
  state-constant denominator (S6-06) — but that is an argument, not a measurement.
- **Flagged series stay flagged.** Passing a flagged series into a model is allowed; forgetting the flag
  is not, and the registry carries the status onto every card.

## 11. Reproduction limits

- **`data/raw/` is gitignored** (redistribution constraints). A stranger with their own credentials can
  rebuild every aggregate; a stranger without them cannot.
- **`oagf.gov.ng`'s TLS certificate expired 2026-10-17.** The FAAC vintage cannot be re-landed here or in
  CI until the publisher renews it. Nothing is bypassed: disabling verification would make a dead source
  look green.
- **CI has no R.** The Stage 6, 7, 8 and 8b engines are skipped there, so CI verifies the committed
  artifacts against the rebuilt base rather than re-estimating. That is weaker than a local run and is
  labelled as such rather than passed off.
- **The verifiers need the `ds-general` Python**, not the system 3.14 interpreter (no `duckdb`).

## 12. What is still claimed, stated narrowly

After all of the above, four things survive:

1. **A fiscal transmission channel:** a 10 % Brent move reaches the states as roughly 5 % more money two
   to three months later (Design B, sign robust in all 24 fiscal specifications; the price-level family is a null at every horizon; timing p = 0.0625).
2. **Two published cards** of 36 — the two Design A outcomes that have a card — each carrying its interval
   and its `estimated_not_identified` verdict. **34 cards carry a reason, not a number** (15
   `outcome_series_absent`, 7 `outcome_not_at_design_grain`, 9 `design_result_is_channel_level`, 2
   `design_not_run`, 1 `design_estimated_not_identified`).
3. **Two of eight event-outcome cells** show a shift that survives both the placebo and the pre-trend
   check; three fail the pre-trend, one shows no shift, and two cannot be checked at all.
4. **A boundary:** every design that failed its pre-check is dropped on the record, with the diagnostic
   that dropped it.

**What is not claimed, in the vocabulary the project refuses:** no ranking of presidents, no scorecard,
no pooled tenure effect, no party comparison (two events against two events has no sampling
distribution), no causal verb without a named design, and no monthly causal statement from an annual
series.

## 13. What would change each answer

| To get closer to | What is missing | What blocks it |
|---|---|---|
| An identified dose-response | A fiscal instrument that varies within state for reasons unrelated to oil | The dose *is* oil revenue; state IGR or the VAT distribution would be a different design |
| The per-capita axis | A state population denominator decision (X-09) | An unmade decision, not an unavailable source |
| D2 — FAAC share of state revenue | NBS state IGR parsed | Acquisition, same parser family as FAAC |
| The 2023 window monthly | Monthly NBS CPI | Annual CPI landed; the monthly series is a parser |
| An identified synthetic counterfactual | A donor pool that is not rich enough to interpolate the pre-period, or a shorter fit window | Built and measured: no window survives its placebos, and 304 of 396 placebos clear the same pre-fit gate |
| The security record after 2025-12 | The next GED release | Publication cycle — the adopted archive (26.1) is complete to 2025-12 |
| Tenure effects on health and education | Sub-national monthly outcomes | DHIS2 credentials; NEMIS/NEDI and UNESCO unreachable |
| The naira channel separated | Monthly NGN/USD | No keyless publisher; CBN by hand |

## 14. How this document is checked

The claims that can be recomputed are registered as claims, not trusted as prose:

| Claim | Artifact | Check |
|---|---|---|
| Observed share 1,373 / 8,350 (16.4 %) | `registry/diagnostics/2026-10-30/diagnostics.json → grain_decision` | `tests/verify_stage5.py`, and the memo's number is checked against it |
| 2 of 36 cards carry a number; 34 by reason | `registry/dags/index.json → registry.card_estimate_counts` | `tests/verify_registry.py` |
| Design A coefficient, interval, placebo, lead-shift p | `registry/estimates/2026-10-30/estimates.json` | `tests/verify_stage6.py`; doc claims in `tests/verify_registry.py` |
| Design B peak and its interval | same | `tests/verify_stage6.py`, `tests/verify_stage7.py` |
| 60 positive / 21 negative; 36 of 48 | `registry/robustness/2026-10-30/robustness.json` | `scripts/validate_artifacts.py` recomputes the counts from the rows |
| 2 / 3 / 2 / 1 event cells | `registry/events/2026-10-30/events.json` | `tests/verify_events.py` re-fits and re-derives every verdict |
| 674 gated series, 359 / 313 / 2 | `registry/quality/2026-10-30/report.json` | `tests/verify_quality.py` |

Two stale prose facts were found while writing this page and are corrected with it: **`docs/events.md`
said four cells fail the pre-trend** when the artifact has three failing and two that cannot be checked
(Yar'Adua, 100 of the required 120 months), and **`docs/design-memo.md` still described the spine as 10.1 %
observed** from the pre-FAAC base. Both had passed every verifier, because no check read the prose. They
are registered now, which is the only reason to believe the next drift will be caught.
