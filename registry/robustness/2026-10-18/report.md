# Stage 7 — robustness and the multiverse, vintage 2026-10-18

Generated 2026-10-27T02:03:15+0100 by `analysis/R/04_robustness.R` from `analysis/specs/robustness.yml`. Every specification and every count is recomputed independently by `tests/verify_stage7.py`.

## What this stage is for

Stage 6 published two estimates. This stage asks whether they survive the choices that were not pinned down: 81 specifications for Design A and 24 for Design B, each declared in the spec before it was fitted, every one of them stored — including the ones that disagree. The count below is a count over a correlated grid, not a vote.

## Support counts

| Group | n | positive | positive, CI excludes 0 | negative | negative, CI excludes 0 |
|---|---|---|---|---|---|
| A — state dose-response | 81 | 45 | 13 | 36 | 5 |
| B — national transmission | 24 | 24 | 24 | 0 | 0 |
| overall | 105 | 69 | 37 | 36 | 5 |

> The count is descriptive, not a vote. The specifications are deliberately correlated — 81 of them reuse the same 3,456 rows, the same outcome and overlapping windows — so "70 of 81 are positive" is a statement about the grid, not 70 independent pieces of evidence. It is published as a count, never as a share of evidence, and never as a probability that the sign is right.

> **The near-zero band.** 6 of the 105 specifications sit within ±0.02 of zero — 6 of Design A's and 0 of Design B's. Their sign is rounding, not direction, and it is not stable across a rebuild of the base: the counts above moved by one specification (44/37 to 45/36) between two bases for exactly that reason. They stay in the counts and are declared here, because removing them from `n` would hide the instability rather than name it.

Excluding the band, the counts are:

| Group | positive outside the band | negative outside the band |
|---|---|---|
| A | 42 | 33 |
| B | 24 | 0 |

### Where the sign changes

**The sign of Design A is not stable, and the axis that moves it is the dose lag.** With the dose lagged one month and state and month effects, the estimate is negative in all 3 windows, while the pre-registered same-month specification is positive. At a lag of 1 month, 17 of 27 specifications are on the opposite side of zero (17 negative). A quantity whose sign depends on a one-month timing choice is not a direction, and that is a stronger statement than Stage 6 could make from one specification and its placebo.

- **Design A, outcome = fatalities**: 14 of 27 specifications carry the opposite sign to the preferred one (13 positive, 14 negative)
- **Design A, outcome = fatalities_civilians**: 20 of 27 specifications carry the opposite sign to the preferred one (7 positive, 20 negative)
- **Design A, dose_lag_months = 1**: 17 of 27 specifications carry the opposite sign to the preferred one (10 positive, 17 negative)
- **Design A, adjustment_set = state_fe**: 16 of 27 specifications carry the opposite sign to the preferred one (11 positive, 16 negative)
- **Design A, adjustment_set = state_month_fe_state_trend**: 14 of 27 specifications carry the opposite sign to the preferred one (13 positive, 14 negative)

Every axis level, with the count on each side of zero and the count opposite the preferred sign:

| Design | Axis | Level | n | positive | negative | opposite to preferred |
|---|---|---|---|---|---|---|
| A | outcome | fatalities | 27 | 13 | 14 | 14 |
| A | outcome | fatalities_civilians | 27 | 7 | 20 | 20 |
| A | outcome | incidents | 27 | 25 | 2 | 2 |
| A | dose_lag_months | 0 | 27 | 17 | 10 | 10 |
| A | dose_lag_months | 1 | 27 | 10 | 17 | 17 |
| A | dose_lag_months | 2 | 27 | 18 | 9 | 9 |
| A | adjustment_set | state_fe | 27 | 11 | 16 | 16 |
| A | adjustment_set | state_month_fe | 27 | 21 | 6 | 6 |
| A | adjustment_set | state_month_fe_state_trend | 27 | 13 | 14 | 14 |
| A | window | exclude_covid | 27 | 16 | 11 | 11 |
| A | window | full | 27 | 15 | 12 | 12 |
| A | window | post_2019 | 27 | 14 | 13 | 13 |
| B | shock | d_log_oil_1m | 12 | 12 | 0 | 0 |
| B | shock | d_log_oil_3m | 12 | 12 | 0 | 0 |
| B | controls | month_of_year | 6 | 6 | 0 | 0 |
| B | controls | month_of_year_plus_covid | 6 | 6 | 0 | 0 |
| B | controls | month_of_year_plus_lagged_shock | 6 | 6 | 0 | 0 |
| B | controls | none | 6 | 6 | 0 | 0 |
| B | window | exclude_covid | 8 | 8 | 0 | 0 |
| B | window | full | 8 | 8 | 0 | 0 |
| B | window | post_2019 | 8 | 8 | 0 | 0 |

## The pre-registered specifications

Across the 24 Design B specifications the coefficient at h=2 runs from **0.3968** (`B|d_log_oil_1m|month_of_year_plus_lagged_shock|full`) to **2.3976** (`B|d_log_oil_3m|month_of_year_plus_lagged_shock|exclude_covid`). Holding the shock definition fixed, it spans 0.4073 across the control sets and windows; holding the covariate set fixed, it spans 0.7548 across the two shock definitions — a three-month average shock is a smoother regressor, so less of it is measurement noise and its coefficient is correspondingly larger. Every one of the 24 keeps the sign.

| Design | Specification | Coefficient | SE | 95 % CI | n |
|---|---|---|---|---|---|
| A | fatalities | 0.4793 | 0.3023 | [-0.1132, 1.0718] | 3456 |
| B | d_log_oil_1m / month_of_year / full (h=2) | 0.5181 | 0.1664 | [0.1919, 0.8443] | 111 |

Both reproduce the Stage 6 artifact: A differs by 2.2e-12 and B by 4.3e-12, against a tolerance of 1e-08 — the pre-registered cell of the grid is the published estimate, not a neighbour of it.

## Sensitivity

### Oster delta (unobserved confounding)

- **Design B**, at h=2, on the preferred specification: beta(short) = 0.4882, beta(long) = 0.5181, R2 0.033 -> 0.139, R2max = 0.181. **delta = -44.04** for a zero estimate, and beta* at delta = 1 is 0.5299.
  the observed controls move the estimate away from zero, so delta is negative and Oster's usual cutoff (delta >= 1) does not apply; beta* at delta = 1 is reported instead
- **Design A**, on the **linear analogue** (log(1 + fatalities) on log_dose, state and month fixed effects): delta = -1.53, beta* at delta = 1 is 0.1457. This is a bound on the analogue, not on the PPML estimate, because Oster's delta requires an R-squared and PPML does not have one.
  the control set flips the sign of the estimate (-0.1023 without controls, 0.0882 with them), so delta has no attenuation reading: it is the amount of unobserved selection that would have to act *against* the observed controls to bring the estimate to zero.

### Leave-one-state-out (Design A)

36 refits of the preferred specification, dropping one state at a time: coefficients range **[0.1234, 0.6254]** around 0.4793, median 0.4790, with **0** sign flip(s). The three most influential states are Rivers (0.6254), Benue (0.6002), Akwa Ibom (0.5717).
Dropping the three oil-producing states named in the spec (Delta, Bayelsa, Rivers) returns **0.6663** on 3168 rows.

### In-time placebo (Design B)

The shock series shifted by each of 48 non-zero offsets (-24 to 24 months) and the preferred specification refitted at h=2: **p = 0.0625**. Placebo estimates average |0.1911| with a maximum of |0.6446|; the estimate is 0.5181.

The *sign* of Design B is the same in all 24 grid specifications and all 24 of its intervals exclude zero, but the in-time placebo does **not** clear 0.05: 3 of 48 shifted alignments return an estimate at least as large as the true one (p = 0.0625). The sign is the robust claim here; the *timing* is the weaker one, and it is what the placebo tests.

### HAC bandwidth (Design B, intervals only)

| maxlags | SE | 95 % CI |
|---|---|---|
| 12 | 0.1664 | [0.1919, 0.8443] |
| 6 | 0.1723 | [0.1805, 0.8557] |
| 18 | 0.1609 | [0.2028, 0.8335] |

Changing the bandwidth changes no coefficient; it shows how much of the interval's width is a 
bandwidth choice rather than a sample.

### Rosenbaum bounds

Not applicable. Rosenbaum bounds require a binary treatment or a matched sample. The dose is continuous and no matching was performed, so there is no gamma to report. Recorded rather than omitted because the rigor floor asks for "Rosenbaum bounds where applicable", and a reader should see the judgement.

## What the grid cannot vary, and why that is stated

- **population_denominator** — `not_built`. X-09 is an unmade decision, and `state_panel.d1_faac_per_capita` is 0 of 12,358 rows populated. Every specification in this grid is the nominal dose. The elasticity with state fixed effects is invariant to a state-constant denominator (S6-06), so the *slope* is not expected to move — but that is an argument, not a fitted specification, and the grid cannot test it.
- **state_igr_d2** — `not_acquired`. D2 is FAAC / (FAAC + internally generated revenue); the IGR half has no landed series, so the non-oil fiscal instrument that would let Design A vary within state for reasons other than the oil price does not exist yet (C-47).
- **donor_pool** — `not_run`. Design C is `not_run`: Stage 5 found the donor pool fails pre-treatment fit on every outcome.
- **imputation_handling** — `fixed`. no imputed value enters either design; see the header of this file.
- **index_anchor** — `fixed`. the designs use levels, not the indexed metric; the anchor is absorbed by the fixed effects.
- **event_window** — `not_applicable`. neither design is an event study; the tenure design that would need one is not estimable.

## Which base this was fitted on

Fingerprints, computed by the queries declared in `robustness.yml` at 10 significant digits: `state_panel` dd11d300f588, `faac_national_monthly` 0084ea1d7129, the oil series 167ff0dce42d. 
Reads the tables the grid actually uses at 10 significant digits. A mismatch means the artifact was fitted on a different base than the one on disk — re-run analysis/R/04_robustness.R. This is the C-44 invariant (an artifact describing a vintage other than the current one) applied to the base rather than to a report label.

## Where the figure is

`specification_curve.svg`, drawn by this engine: two panels, each sorted by coefficient with the 95 % interval, 
the zero line, the pre-registered specification marked, and the axis levels of every specification 
beneath it in the same order — so a sign change can be read against the choice that produced it.

## What this stage does not claim

- A count over this grid is **not** independent evidence: the specifications reuse the same rows and outcomes. It bounds how sensitive the sign is to the declared choices; it does not estimate a probability that the sign is right.
- The per-capita dose (D1) is **not** in the grid: `d1_faac_per_capita` is empty because the state population denominator is an unmade decision (X-09). The nominal dose is what the curve varies.
- No specification in this grid makes Design A identified. Stage 6's verdict stands: the identifying variation is the oil price moving the derivation share (C-47), and a robustness grid over controls and windows cannot create variation the dose does not have.

