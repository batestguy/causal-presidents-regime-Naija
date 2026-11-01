# Stage 8h - Design C, synthetic control - vintage 2026-11-01

Generated 2026-11-01T12:53:09+0100 by `analysis/R/11_design_c.R`. Spec `analysis/specs/design_c.yml` (md5 63f22a5639d74fda0f64ec5ccce19a5c), declared 2026-10-28 for u5mr, before any weight was fitted; extended to the panel's outcomes 2026-11-01, before any of them was fitted.

**This is not the effect of a president.** It is the gap between Nigeria's path and a simplex-weighted
combination of other countries' paths after a transition, published with the placebos that decide whether
the gap is distinguishable from what the same method produces where no transition happened.

Outcomes: 9; windows: 31 estimated, 14 refused; identified: 0.

## Under-5 mortality rate (u5mr)

Path: native annual observation. Gate basis: `stage5_prefit`; verdict: **estimated_not_identified** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | 2.11 | -2.60 | 97.27 | 0.5000 | **estimated_not_identified** |
| jonathan | 2010-2014 | -11.56 | -0.37 | 991.48 | 0.3200 | **estimated_not_identified** |
| buhari | 2015-2022 | 8.59 | 9.38 | 116.20 | 0.1700 | **estimated_not_identified** |
| tinubu | 2023-2024 | 18.53 | 18.50 | 4.37 | 0.3300 | **estimated_not_identified** |

Gaps are in per 1,000 live births; a negative number means Nigeria sat below the synthetic counterfactual.

## Maternal mortality ratio (mmr)

Path: native annual observation. Gate basis: `stage5_prefit`; verdict: **estimated_not_identified** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | 4.28 | -21.61 | 19.24 | 0.6200 | **estimated_not_identified** |
| jonathan | 2010-2014 | 135.82 | 140.69 | 91.98 | 0.1400 | **estimated_not_identified** |
| buhari | 2015-2022 | 171.53 | 171.53 | 7.04 | 0.5400 | **estimated_not_identified** |
| tinubu | - | - | - | - | - | refused (treated_series_incomplete) |

Gaps are in per 100,000 births; a negative number means Nigeria sat below the synthetic counterfactual.

## Penta3 immunisation coverage (immun_penta3)

Path: native annual observation. Gate basis: `stage5_prefit`; verdict: **estimated_not_identified** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | 10.87 | 10.90 | 3.78 | 0.6531 | **estimated_not_identified** |
| jonathan | 2010-2014 | -12.57 | -12.95 | 2.66 | 0.5918 | **estimated_not_identified** |
| buhari | 2015-2022 | 0.69 | 0.72 | 0.77 | 0.9796 | **estimated_not_identified** |
| tinubu | 2023-2024 | -2.11 | -2.09 | 0.30 | 0.9588 | **estimated_not_identified** |

Gaps are in % surviving infants; a negative number means Nigeria sat below the synthetic counterfactual.

## Skilled birth attendance (skilled_birth)

Path: native annual observation. Gate basis: `stage5_prefit`; verdict: **not_run** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | - | - | - | - | - | refused (treated_series_incomplete) |
| jonathan | - | - | - | - | - | refused (treated_series_incomplete) |
| buhari | - | - | - | - | - | refused (treated_series_incomplete) |
| tinubu | - | - | - | - | - | refused (treated_series_incomplete) |

Gaps are in % of births; a negative number means Nigeria sat below the synthetic counterfactual.

## Reported security fatalities (fatalities)

Path: calendar-year sum of the monthly count. Gate basis: `stage8h_annual_aggregation`; verdict: **estimated_not_identified** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | 44.83 | 44.70 | 0.48 | 0.9500 | **estimated_not_identified** |
| jonathan | 2010-2014 | 3349.09 | 3349.57 | 21.26 | 0.5700 | **estimated_not_identified** |
| buhari | 2015-2022 | -6728.37 | -6631.80 | 24.50 | 0.4600 | **estimated_not_identified** |
| tinubu | 2023-2024 | 370.19 | 428.57 | 0.38 | 0.8300 | **estimated_not_identified** |

Gaps are in count; a negative number means Nigeria sat below the synthetic counterfactual.

## Reported security incidents (incidents)

Path: calendar-year sum of the monthly count. Gate basis: `stage8h_annual_aggregation`; verdict: **estimated_not_identified** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | 8.40 | 6.90 | 3.70 | 0.7200 | **estimated_not_identified** |
| jonathan | 2010-2014 | 287.65 | 117.83 | 150.72 | 0.4800 | **estimated_not_identified** |
| buhari | 2015-2022 | -18.54 | 96.24 | 14.28 | 0.4100 | **estimated_not_identified** |
| tinubu | 2023-2024 | 100.91 | 72.77 | 1.76 | 0.4300 | **estimated_not_identified** |

Gaps are in count; a negative number means Nigeria sat below the synthetic counterfactual.

## Real GDP growth (y/y) (gdp_growth)

Path: native annual observation. Gate basis: `stage5_prefit`; verdict: **estimated_not_identified** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | 2.42 | 2.62 | 482086.50 | 0.4490 | **estimated_not_identified** |
| jonathan | 2010-2014 | 5.35 | 5.25 | 6.64 | 0.4845 | **estimated_not_identified** |
| buhari | 2015-2022 | -3.14 | -3.15 | 2.36 | 0.5938 | **estimated_not_identified** |
| tinubu | 2023-2024 | 3.11 | 3.10 | 1.92 | 0.2526 | **estimated_not_identified** |

Gaps are in %; a negative number means Nigeria sat below the synthetic counterfactual.

## Headline inflation (y/y) (cpi_yoy)

Path: native annual observation. Gate basis: `stage5_prefit`; verdict: **estimated_not_identified** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | -2.37 | -1.78 | 2.32 | 0.7683 | **estimated_not_identified** |
| jonathan | 2010-2014 | 2.95 | 3.65 | 1.36 | 0.7683 | **estimated_not_identified** |
| buhari | 2015-2022 | 0.40 | 0.59 | 1.99 | 0.6753 | **estimated_not_identified** |
| tinubu | 2023-2024 | 5.31 | 5.62 | 2.76 | 0.2105 | **estimated_not_identified** |

Gaps are in %; a negative number means Nigeria sat below the synthetic counterfactual.

## Unemployment rate (unemp)

Path: native annual observation. Gate basis: `stage5_prefit`; verdict: **estimated_not_identified** over 5 window(s).

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | 0.13 | 0.15 | 10904.71 | 0.3100 | **estimated_not_identified** |
| jonathan | 2010-2014 | 0.08 | 0.02 | 21.91 | 0.3200 | **estimated_not_identified** |
| buhari | 2015-2022 | 1.37 | 0.73 | 177.53 | 0.1616 | **estimated_not_identified** |
| tinubu | 2023-2024 | -1.05 | -0.73 | 10.42 | 0.0825 | **estimated_not_identified** |

Gaps are in %; a negative number means Nigeria sat below the synthetic counterfactual.

The p-value is a rank among placebos, not a sampling distribution, and with 100 units the smallest
attainable value is 0.01.

**The two gap columns are the same problem solved twice.** With 99 donors and 8 to 24 pre-years the declared
simplex problem is underdetermined: a face of weight vectors fits the pre-period equally well and they do not
agree about the post-period. The first column is the vertex the declared QP returns; the second is the unique
ridge refit. Where the two disagree in sign the estimate is a property of the solver, not of the data, and the
artifact says so instead of publishing one of them.

- in-space placebos fitted: 2959; in-time placebos fitted: 53; leave-one-donor-out fits: 2959
- placebos whose own pre-fit also clears the 0.10 gate: 969 of 2959 - the gate does not discriminate on this pool

## What this does not claim

- This is not the effect of a president. It is the gap between Nigeria's path and a weighted combination of other countries' paths after a transition.
- The counterfactual is not observed. A low pre-fit ratio shows the donors can reproduce the pre-period, not that they would have reproduced the post-period without the transition.
- The donor pool is countries, not Nigerian states: it cannot hold constant anything Nigeria-specific — the oil cycle, the naira, the security environment.
- The windows overlap in their pre-periods and are not additive: a later window's counterfactual already contains the earlier tenures.
- The pre-fit gate does not discriminate on this pool: 99 donors and 8 to 24 pre-years make the fit underdetermined, so the placebos carry the verdict.
- The outcomes are not comparable to one another. Each is its own fit against its own donor paths, in its own unit; a gap of 2 in one outcome is not twice a gap of 1 in another.

## What it refuses to carry

- no standard error, confidence interval or p-value other than the rank p — a synthetic control has no sampling distribution
- no significance claim from the pre-fit ratio alone; the ratio is a fit diagnostic, and with 99 donors it is interpolation
- no per-president wording: windows are keyed by tenure id, and the artifact prints no surname

