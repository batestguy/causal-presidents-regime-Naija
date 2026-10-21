# What changed inside a tenure — monthly conflict around 4 transitions, vintage 2026-10-18

Generated 2026-10-21T03:00:17+0100 by `analysis/R/06_events.R` from `analysis/specs/events.yml`. Every number is recomputed independently by `tests/verify_events.py`.

## What this stage is, and what it is not

**A timing comparison, per transition, on the only monthly outcome in the base.** Each of the 4
in-window civilian transitions is compared against its own path in the 96 months before it, with
month-of-year fixed effects and a linear trend, and the post window truncated at the next transition so no
month is counted twice.

**Not a tenure effect, not a party effect, not a causal claim.** Four events is four events: there is no
counterfactual here, and the party split below is a description with its n printed rather than a test.

## The series

- 312 months, 1999-01 to 2024-12. **25 month(s) absent from the archive were filled with zero** under the declared rule.
- The transition that cannot be compared: **obasanjo_1999** — No pre-period. The conflict series begins 1999-01, four months before the transition, and the design needs 96 pre-months. This is the reason the earliest tenure cannot be compared on monthly conflict at all — not a modelling choice but where the data starts.

## The estimates

| Transition | Outcome | h | shift | SE | 95 % CI | placebo p | variant | verdict |
|---|---|---|---|---|---|---|---|---|
| Yar'Adua sworn in | fatalities | 12 | -0.1712 | 0.8880 | [-0.8546, 3.7235] | 0.610 | seasonality_trend | check_not_available |
| Yar'Adua sworn in | fatalities | 12 | -0.1265 | 0.9863 | [-0.8736, 5.0366] | — | seasonality_trend_oil | — |
| Yar'Adua sworn in | incidents | 12 | -0.3434 | 0.3865 | [-0.6922, 0.4006] | 0.186 | seasonality_trend | check_not_available |
| Yar'Adua sworn in | incidents | 12 | 0.1760 | 0.2868 | [-0.3297, 1.0632] | — | seasonality_trend_oil | — |
| Yar'Adua sworn in | fatalities | 24 | 0.7176 | 0.9530 | [-0.7347, 10.1204] | 0.034 | seasonality_trend | — |
| Yar'Adua sworn in | fatalities | 24 | 0.9391 | 0.9870 | [-0.7198, 12.4187] | — | seasonality_trend_oil | — |
| Yar'Adua sworn in | incidents | 24 | -0.2306 | 0.4074 | [-0.6537, 0.7097] | 0.475 | seasonality_trend | — |
| Yar'Adua sworn in | incidents | 24 | -0.2871 | 0.4539 | [-0.7071, 0.7351] | — | seasonality_trend_oil | — |
| Jonathan sworn in | fatalities | 12 | 1.2770 | 0.8822 | [-0.5959, 11.8311] | 0.017 | seasonality_trend | not_interpretable_pre_trend |
| Jonathan sworn in | fatalities | 12 | 1.0720 | 0.8107 | [-0.5770, 9.1505] | — | seasonality_trend_oil | — |
| Jonathan sworn in | incidents | 12 | 3.9125 | 0.5211 | [0.7689, 12.6428] | 0.017 | seasonality_trend | shift_detected |
| Jonathan sworn in | incidents | 12 | 3.6919 | 0.4278 | [1.0287, 9.8510] | — | seasonality_trend_oil | — |
| Jonathan sworn in | fatalities | 24 | 1.6418 | 0.7424 | [-0.3834, 10.3185] | 0.017 | seasonality_trend | — |
| Jonathan sworn in | fatalities | 24 | 1.5333 | 0.6359 | [-0.2716, 7.8100] | — | seasonality_trend_oil | — |
| Jonathan sworn in | incidents | 24 | 5.2432 | 0.5155 | [1.2732, 16.1466] | 0.017 | seasonality_trend | — |
| Jonathan sworn in | incidents | 24 | 5.1092 | 0.4450 | [1.5540, 13.6129] | — | seasonality_trend_oil | — |
| Buhari sworn in | fatalities | 12 | -0.6747 | 0.1777 | [-0.7704, -0.5391] | 0.017 | seasonality_trend | not_interpretable_pre_trend |
| Buhari sworn in | fatalities | 12 | -0.7014 | 0.2566 | [-0.8194, -0.5062] | — | seasonality_trend_oil | — |
| Buhari sworn in | incidents | 12 | -0.4795 | 0.1171 | [-0.5862, -0.3453] | 0.085 | seasonality_trend | no_shift_detected |
| Buhari sworn in | incidents | 12 | -0.1073 | 0.1883 | [-0.3828, 0.2911] | — | seasonality_trend_oil | — |
| Buhari sworn in | fatalities | 24 | -0.7975 | 0.3784 | [-0.9035, -0.5748] | 0.017 | seasonality_trend | — |
| Buhari sworn in | fatalities | 24 | -0.8392 | 0.4210 | [-0.9295, -0.6330] | — | seasonality_trend_oil | — |
| Buhari sworn in | incidents | 24 | -0.5846 | 0.2110 | [-0.7253, -0.3719] | 0.017 | seasonality_trend | — |
| Buhari sworn in | incidents | 24 | -0.4028 | 0.2484 | [-0.6330, -0.0282] | — | seasonality_trend_oil | — |
| Tinubu sworn in | fatalities | 12 | 0.7664 | 0.1568 | [0.2989, 1.4021] | 0.017 | seasonality_trend | shift_detected |
| Tinubu sworn in | fatalities | 12 | 0.7618 | 0.1633 | [0.2792, 1.4265] | — | seasonality_trend_oil | — |
| Tinubu sworn in | incidents | 12 | 0.0671 | 0.1153 | [-0.1487, 0.3376] | 0.169 | seasonality_trend | not_interpretable_pre_trend |
| Tinubu sworn in | incidents | 12 | 0.0585 | 0.0919 | [-0.1160, 0.2674] | — | seasonality_trend_oil | — |
| Tinubu sworn in | fatalities | 24 | 0.6456 | 0.1571 | [0.2095, 1.2388] | 0.051 | seasonality_trend | — |
| Tinubu sworn in | fatalities | 24 | 0.6356 | 0.1623 | [0.1898, 1.2483] | — | seasonality_trend_oil | — |
| Tinubu sworn in | incidents | 24 | 0.0099 | 0.1276 | [-0.2136, 0.2969] | 0.034 | seasonality_trend | — |
| Tinubu sworn in | incidents | 24 | -0.0069 | 0.1091 | [-0.1981, 0.2298] | — | seasonality_trend_oil | — |

## Inference: exhaustive placebo assignment

58 eligible months were each tried as if they were the transition (the declared rule excludes months
within 24 months of a real one). The set is enumerated, not sampled, so there is no seed.

The p-value is the tail in the direction of the estimate: `(1 + #{that tail}) / (n + 1)` over those 58
months, so its floor is 1/59, and a decline counts as evidence exactly as an increase does. The null is
**not centred on zero** — the placebo distribution's mean is printed below — because reported fatalities
drift down through the window; the p-value uses that empirical distribution as it is.

| Outcome | h | placebo mean (log) | placebo SD | p05 | p50 | p95 | p99 |
|---|---|---|---|---|---|---|---|
| fatalities | 12 | -0.390 | 0.475 | -1.008 | -0.399 | 0.290 | 0.426 |
| fatalities | 24 | -0.361 | 0.562 | -1.180 | -0.260 | 0.398 | 0.566 |
| incidents | 12 | -0.204 | 0.239 | -0.691 | -0.186 | 0.163 | 0.172 |
| incidents | 24 | -0.251 | 0.226 | -0.710 | -0.230 | -0.000 | 0.010 |

Family-wise — the largest of the four events against that distribution:

- **fatalities, h=12**: largest of the four is buhari_2015, -0.6747 (log -1.123), p = 0.017 over 58 placebo months
- **fatalities, h=24**: largest of the four is buhari_2015, -0.7975 (log -1.597), p = 0.017 over 58 placebo months
- **incidents, h=12**: largest of the four is jonathan_2010, 3.9125 (log 1.592), p = 0.017 over 58 placebo months
- **incidents, h=24**: largest of the four is jonathan_2010, 5.2432 (log 1.831), p = 0.017 over 58 placebo months

## The checks that decide whether an estimate means anything

### Pre-trend placebo

For each event the same statistic is estimated with the post-window placed 24 months *before* the real transition (so the real transition is not inside the pseudo-post window). If a shift of comparable size is already there, the post-window shift is a continuation, not a change, and the event is reported with that check failed rather than with a coefficient. The check needs `pre_months + 24` months of history before the transition; where the series does not reach back that far the event is marked `check_not_available` with the months it had, and no verdict is attached.

| Transition | Outcome | pre-window shift (h=12 equivalent) | post-window shift (h=12) | verdict |
|---|---|---|---|---|
| Yar'Adua sworn in | fatalities | — | -0.1712 | check_not_available |
| Jonathan sworn in | fatalities | 1.9558 | 1.2770 | not_interpretable_pre_trend |
| Buhari sworn in | fatalities | 0.8381 | -0.6747 | not_interpretable_pre_trend |
| Tinubu sworn in | fatalities | 0.5275 | 0.7664 | shift_detected |
| Yar'Adua sworn in | incidents | — | -0.3434 | check_not_available |
| Jonathan sworn in | incidents | 0.8758 | 3.9125 | shift_detected |
| Buhari sworn in | incidents | 0.4041 | -0.4795 | no_shift_detected |
| Tinubu sworn in | incidents | 0.2547 | 0.0671 | not_interpretable_pre_trend |

Where the check could not be run, the artifact says so instead of scoring it as a pass:

- **yaradua_2007**: the check needs 120 months before the transition; the series has 100 before this one

### Reporting divergence

Both outcomes are estimated at every event. A violation of the archive's reporting — a change in what the archive records rather than in what happened — can move one series without moving the other; the artifact reports the two shifts side by side and flags any event where their signs disagree.

- **yaradua_2007**: fatalities -0.1712, incidents -0.3434 — signs agree
- **jonathan_2010**: fatalities 1.2770, incidents 3.9125 — signs agree
- **buhari_2015**: fatalities -0.6747, incidents -0.4795 — signs agree
- **tinubu_2023**: fatalities 0.7664, incidents 0.0671 — signs agree

### Detectable effect

The minimum detectable proportional shift at 80 % power is computed per event from the pre-window residual scale and published beside the estimate, as in Stage 5, because "not significant" and "not detectable" are different statements and the second is what four events buys.

- Yar'Adua sworn in / fatalities: MDE 11.0334 against an estimate of -0.1712
- Yar'Adua sworn in / incidents: MDE 1.9531 against an estimate of -0.3434
- Jonathan sworn in / fatalities: MDE 10.8397 against an estimate of 1.2770
- Jonathan sworn in / incidents: MDE 3.3061 against an estimate of 3.9125
- Buhari sworn in / fatalities: MDE 0.6454 against an estimate of -0.6747
- Buhari sworn in / incidents: MDE 0.3882 against an estimate of -0.4795
- Tinubu sworn in / fatalities: MDE 0.5518 against an estimate of 0.7664
- Tinubu sworn in / incidents: MDE 0.3812 against an estimate of 0.0671

## The party split, as description

The four estimates are grouped by the incoming tenure stratum (PDP for 2007 and 2010, APC for 2015 and 2023) and reported as counts and their median. **No test statistic is computed**, because two events against two events has no sampling distribution: any p-value would be a number manufactured by an assumption. The verifier asserts that no test field is populated.

| Party | events | median shift (fatalities, h=12) | the shifts |
|---|---|---|---|
| APC | 2 | 0.0459 | -0.6747, 0.7664 |
| PDP | 2 | 0.5529 | -0.1712, 1.2770 |

`no_test_computed = true` — and the verifier fails if a test statistic appears on this artifact.

## What this stage does not claim

- A causal effect of a tenure, a party or a president on conflict. The design is a within-series timing comparison and nothing here identifies a counterfactual.
- That conflict is measured without reporting bias. UCDP GED is a reported-events archive; the divergence check is a guard, not a fix.
- A pooled 'tenure effect'. Four event-level estimates are published; there is no average.
- Anything about the annual outcome domains. They have no monthly series, which is the same wall Stage 5 hit.

## Where the figure is

`event_study.svg` — the monthly series with the four transitions marked, and the per-transition h=12 shift
with its interval against the 5th and 95th percentiles of the placebo distribution (both are drawn: the
p-value is a same-side tail and the null is not centred on zero).
