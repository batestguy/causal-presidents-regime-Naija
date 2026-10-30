# Stage 6 estimates — vintage 2026-10-30

Generated 2026-10-30T15:28:15+0100 by `analysis/R/03_estimate.R` from `analysis/specs/estimation.yml`. Every number is recomputed independently by `tests/verify_stage6.py`.

## The answer this stage arrived at

**The presidential-tenure question is not answerable with this data and no estimator makes it so** —
four to five administrations against 27 annual observations put the minimum detectable effect at
35–80 residual standard deviations (Stage 5). What *is* answerable is the fiscal channel, and this
stage answers two questions about it.

| Design | Question | Verdict |
|---|---|---|
| A | Does a larger federal allocation reduce conflict fatalities in the state that receives it? | **estimated_not_identified** |
| B | How much of a Brent shock reaches the states, and the price level? | **faac estimated · cpi estimated_null_at_the_declared_band** |
| C | Did the tenures move an outcome, against a synthetic counterfactual? | **estimated_not_identified** |

## Design A — state dose-response

Estimand: *The elasticity of monthly conflict fatalities in a state with respect to that state's FAAC gross allocation: a 1 % larger allocation, in a state-month, against the state's own average and the country's month.*

Sample: 3888 state-months, 36 states, 2016-12-01 → 2025-12-01. Estimator: PPML (Poisson pseudo-maximum-likelihood), fixest::fepois.

| Design | Outcome | Coefficient | n | SE | 95% CI | p |
|---|---|---|---|---|---|---|
| A | fatalities | 0.4678 | 3888 | 0.2812 | [-0.0833, 1.0189] | 0.0962 |
| A | incidents | 0.5278 | 3888 | 0.1944 | [0.1467, 0.9088] | 0.0066 |
| A | fatalities_civilians | 0.3427 | 3564 | 0.4911 | [-0.6198, 1.3052] | 0.4852 |

### Why the verdict is what it is

- **Lead-shift randomisation (the decisive check)**: 60 non-zero offsets, p = **0.167**. Mis-timed doses average |0.240| with a maximum of |0.598|; the estimate is 0.468.
- **Secondary null** (499 draws, shuffle the dose across states within each month): p = 0.000. Reported, not decisive — see the spec for why.
- **Placebo** (dose led 24 months within state): **+0.3101** (SE 0.1519) against the estimate of +0.4678.
  - the lead-shift p-value is 0.167: 10 of 60 mis-timed doses return an estimate at least as large as the estimate itself

What this design actually uses: the dose's within-state, within-month variation. That variation is not spread across the federation — it is concentrated in the oil-producing states (residual sd 0.50 in Delta/Bayelsa/Rivers against 0.11 elsewhere), because what survives two-way fixed effects is mostly the 13 % derivation share moving with the oil price and with production volumes. A dose whose variation is a national oil shock interacted with a fixed state characteristic is not the randomised-looking exposure a dose-response design assumes, and the placebo says the same thing from the other side.

## Design B — Brent crude to the states and to prices

Estimand: *Two outcome families sharing one shock, one control set and one inference: (i) the **fiscal channel** — the cumulative elasticity of the national monthly FAAC allocation to the 36 states with respect to a Brent crude shock, i.e. the proportional change in the allocation h months after a 1 % price move; and (ii) the **price level** (C-85) — the cumulative log change in the NBS all-items CPI index h months after the same move, i.e. the inflation that passes through. They are not one estimand: one asks whether the money reaches the states, the other whether the shock reaches prices.*

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
| B | cumulative log change in the NBS CPI index at h=0 | 0.0043 | 309 | 0.0056 | [-0.0066, 0.0153] | 0.4394 |
| B | cumulative log change in the NBS CPI index at h=1 | 0.0035 | 308 | 0.0102 | [-0.0164, 0.0235] | 0.7281 |
| B | cumulative log change in the NBS CPI index at h=2 | -0.0021 | 307 | 0.0155 | [-0.0325, 0.0282] | 0.8921 |
| B | cumulative log change in the NBS CPI index at h=3 | -0.0041 | 306 | 0.0183 | [-0.0400, 0.0318] | 0.8231 |
| B | cumulative log change in the NBS CPI index at h=4 | -0.0020 | 305 | 0.0222 | [-0.0455, 0.0415] | 0.9276 |
| B | cumulative log change in the NBS CPI index at h=5 | -0.0091 | 304 | 0.0266 | [-0.0613, 0.0431] | 0.7331 |
| B | cumulative log change in the NBS CPI index at h=6 | -0.0080 | 303 | 0.0273 | [-0.0616, 0.0456] | 0.7707 |
| B | cumulative log change in the NBS CPI index at h=9 | -0.0143 | 300 | 0.0275 | [-0.0681, 0.0396] | 0.6039 |
| B | cumulative log change in the NBS CPI index at h=12 | -0.0016 | 297 | 0.0289 | [-0.0582, 0.0550] | 0.9563 |

- **faac** — cumulative log change in national FAAC: peak response at h = 2 (declared band 2–4); lead placebo at 6 months +0.0953 (SE 0.1517); verdict **estimated**.
- **cpi** — cumulative log change in the NBS CPI index: peak response at h = 0 (declared band 2–4); lead placebo at 6 months -0.0031 (SE 0.0075); verdict **estimated_null_at_the_declared_band**.

A positive response at a lag of two to four months is what the disbursement calendar implies for the
fiscal family: the allocation published for a month is revenue accrued in an earlier one, so an
immediate response would be the surprising result, not a lagged one. The price-level family shares
the shock, the controls and the bandwidth — so its interval is comparable — but it is a different
estimand with its own verdict, and Stage 5 measured it as usable only as short-run pass-through
(no cointegration with Brent under the conservative rank rule: C-86).

## Design C — the synthetic control

Design C is estimated in its own artifact (`registry/design_c/2026-10-30/design_c.json`), with its own spec and verifier: 4 window(s) estimated, 1 refused, 0 identified.

A synthetic control has no sampling distribution, so this stage carries no interval for it and the
number is not on a card. The verdict is a rank among placebos, and every window that failed names the
check that failed.

## Honesty notes carried with these numbers

- Every estimate is a pre-declared specification from analysis/specs/estimation.yml.
- Design A is reported as estimated, not identified, when its own checks say so; the number is still published with its bounds.
- Design C is published in its own artifact (registry/design_c/) and this file carries its status rather than a second copy of its numbers.
- 36 clusters is few; a wild-cluster bootstrap would be the fix and is not applied (declared in the spec).

