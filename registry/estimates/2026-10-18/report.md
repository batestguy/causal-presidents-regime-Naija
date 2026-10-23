# Stage 6 estimates — vintage 2026-10-18

Generated 2026-10-23T04:44:01+0100 by `analysis/R/03_estimate.R` from `analysis/specs/estimation.yml`. Every number is recomputed independently by `tests/verify_stage6.py`.

## The answer this stage arrived at

**The presidential-tenure question is not answerable with this data and no estimator makes it so** —
four to five administrations against 27 annual observations put the minimum detectable effect at
35–80 residual standard deviations (Stage 5). What *is* answerable is the fiscal channel, and this
stage answers two questions about it.

| Design | Question | Verdict |
|---|---|---|
| A | Does a larger federal allocation reduce conflict fatalities in the state that receives it? | **estimated_not_identified** |
| B | How much of a Brent shock reaches the states, and when? | **estimated** |
| C | Did the tenures move an outcome, against a synthetic counterfactual? | not run — Stage 5's donor pool fails the pre-treatment fit |

## Design A — state dose-response

Estimand: *The elasticity of monthly conflict fatalities in a state with respect to that state's FAAC gross allocation: a 1 % larger allocation, in a state-month, against the state's own average and the country's month.*

Sample: 3456 state-months, 36 states, 2016-12-01 → 2024-12-01. Estimator: PPML (Poisson pseudo-maximum-likelihood), fixest::fepois.

| Design | Outcome | Coefficient | n | SE | 95% CI | p |
|---|---|---|---|---|---|---|
| A | fatalities | 0.4793 | 3456 | 0.3023 | [-0.1132, 1.0718] | 0.1129 |
| A | incidents | 0.5460 | 3456 | 0.2168 | [0.1211, 0.9709] | 0.0118 |
| A | fatalities_civilians | 0.3095 | 3168 | 0.4718 | [-0.6153, 1.2342] | 0.5119 |

### Why the verdict is what it is

- **Lead-shift randomisation (the decisive check)**: 60 non-zero offsets, p = **0.133**. Mis-timed doses average |0.256| with a maximum of |1.181|; the estimate is 0.479.
- **Secondary null** (499 draws, shuffle the dose across states within each month): p = 0.000. Reported, not decisive — see the spec for why.
- **Placebo** (dose led 24 months within state): **+0.3021** (SE 0.1772) against the estimate of +0.4793.
  - the lead-shift p-value is 0.133: 8 of 60 mis-timed doses return an estimate at least as large as the estimate itself

What this design actually uses: the dose's within-state, within-month variation. That variation is not spread across the federation — it is concentrated in the oil-producing states (residual sd 0.50 in Delta/Bayelsa/Rivers against 0.11 elsewhere), because what survives two-way fixed effects is mostly the 13 % derivation share moving with the oil price and with production volumes. A dose whose variation is a national oil shock interacted with a fixed state characteristic is not the randomised-looking exposure a dose-response design assumes, and the placebo says the same thing from the other side.

## Design B — Brent crude to state allocations

Estimand: *The cumulative elasticity of the national monthly FAAC allocation to the 36 states with respect to a Brent crude shock: the proportional change in the allocation h months after a 1 % price move.*

| Design | Specification | Coefficient | n | SE | 95% CI | p |
|---|---|---|---|---|---|---|
| B | cumulative log change in national FAAC at h=0 | -0.1600 | 113 | 0.1235 | [-0.4019, 0.0820] | 0.1978 |
| B | cumulative log change in national FAAC at h=1 | 0.1571 | 112 | 0.1278 | [-0.0933, 0.4076] | 0.2215 |
| B | cumulative log change in national FAAC at h=2 | 0.5181 | 111 | 0.1664 | [0.1919, 0.8443] | 0.0024 |
| B | cumulative log change in national FAAC at h=3 | 0.4698 | 110 | 0.1576 | [0.1609, 0.7787] | 0.0036 |
| B | cumulative log change in national FAAC at h=4 | 0.1608 | 109 | 0.1617 | [-0.1562, 0.4778] | 0.3224 |
| B | cumulative log change in national FAAC at h=5 | 0.0327 | 108 | 0.1885 | [-0.3367, 0.4021] | 0.8626 |
| B | cumulative log change in national FAAC at h=6 | 0.2313 | 107 | 0.2183 | [-0.1966, 0.6592] | 0.2918 |
| B | cumulative log change in national FAAC at h=9 | 0.3961 | 104 | 0.3019 | [-0.1957, 0.9878] | 0.1925 |
| B | cumulative log change in national FAAC at h=12 | 0.3245 | 101 | 0.3188 | [-0.3003, 0.9493] | 0.3112 |

Peak response at h = 2 (declared band 2–4). Lead placebo at 6 months: +0.0953 (SE 0.1517).

A positive response at a lag of two to four months is what the disbursement calendar implies: the
allocation published for a month is revenue accrued in an earlier one, so an immediate response would
be the surprising result, not a lagged one. The confidence bounds are wide — this is 114 monthly
observations of a series the naira's two devaluations also move, and the FX channel is annual grain
(the monthly NGN/USD series has no keyless source: `docs/decisions.md` C-46).

## What was not run

Design C (synthetic control): The reason changed on 2026-10-18, and the change is the point. With the original 13-country pool Stage 5 recorded `infeasible`: the pre-treatment fit failed on every outcome and window. The pool has since been widened to 99 candidates screened on oil dependence, region/income band and coverage (`ingestion/flows/pull_worldbank_donors.py`), and re-running the gate (vintage 2026-10-18) passes **u5mr on 3 of its 4 runnable windows** (ratios 0.0014-0.0042 against the declared 0.10 threshold, ratio-on-differences 0.013-0.024) and fails `gdp_growth` (1 of 4) and `cpi_yoy` (0 of 4) — so the design is no longer infeasible *for want of a pool*. It is not estimated here because the estimator and its placebos are not built: `Synth`/`coresynth` still has to be fitted, and the in-space and in-time placebos Stage 5 deferred to Stage 6 have not been run. Two cautions travel with the pass and are on the artifact: a 99-donor simplex can fit any pre-period (the yaradua gdp_growth window reaches a ratio of 1.7e-06, which is interpolation rather than validation), and the gate was always declared necessary-not-sufficient. The pass is permission to build Design C, not evidence that its fit is real.

Next step for it: Build the Design C estimator and its placebos on the `u5mr` windows the gate now passes.

## Honesty notes carried with these numbers

- Every estimate is a pre-declared specification from analysis/specs/estimation.yml.
- Design A is reported as estimated, not identified, when its own checks say so; the number is still published with its bounds.
- Design C was not run and its reason is carried rather than dropped.
- 36 clusters is few; a wild-cluster bootstrap would be the fix and is not applied (declared in the spec).

