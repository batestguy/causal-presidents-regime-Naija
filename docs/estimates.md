# What this project can actually answer

**Vintage 2026-10-18.** Written from the artifacts: `registry/estimates/2026-10-18/estimates.json`
(produced by `analysis/R/03_estimate.R` from `analysis/specs/estimation.yml`), every number recomputed
independently by `tests/verify_stage6.py`. The intervals are drawn as well as tabulated —
`registry/estimates/2026-10-18/forest_plot.svg`, one panel per design and one row per published
specification, with each design's decisive check (A's 24-month mis-timed dose, B's 6-month lead placebo)
drawn hollow beside its estimate: a forest plot of estimates alone would show a number that the artifact
beside it says is not identified, without showing the reason. Stage 5's verdicts are in
`docs/design-memo.md` and `registry/diagnostics/2026-10-18/`.

The question this answers is the one the data has to be asked before anything is estimated: **which
causal question can these artifacts carry?** The answer is not "the one the brief asked for".

> Stage 7 has since asked whether these two answers survive the choices they did not pin down, 105
> specifications of them: **`docs/robustness.md`**. Design B keeps its sign everywhere and its timing is
> the weak part; Design A's sign does not survive at all. The numbers below are unchanged.

---

## 1. The presidential-tenure question is not answerable, and no estimator makes it so

The brief's question — did PDP or APC tenures move health, education, security or the economy — is
**not answerable with the data that exists**, and the reason is arithmetic rather than methodological.

There are four to five administrations in the study window and 27 annual observations per national
series. Stage 5 rebuilt the actual design matrix and computed the smallest effect each design could
detect at 80 % power from the noise scale of a thin baseline model:

| Outcome | Residual DoF | MDE (Tier-3 design) | MDE (leaner design) |
|---|---|---|---|
| u5mr | 8 | 39.5 – 79.7 × residual SD | 1.9 – 5.1 × residual SD |
| mmr | 7 | 48.6 – 99.4 | 2.1 – 5.9 |
| gdp_growth | 9 | 38.6 – 53.2 | 1.8 – 4.5 |
| cpi_yoy | 9 | 37.7 – 49.3 | 1.8 – 4.5 |
| unemp | 9 | 35.1 – 47.3 | 1.8 – 4.5 |

Read the first column: the design could only detect a tenure effect *as large as the series' own
residual variation*. A mortality rate moving by its entire residual standard deviation because a
president changed is not a hypothesis, it is a placeholder. Sub-national monthly grain is the only way
out of it, and three of the four outcome domains have no sub-national monthly series at all
(`docs/data-dictionary.md`, declared gaps).

So: **any "Buhari caused X" or "the APC did Y" number this project could produce would be a restatement
of its own assumptions.** That is not a null result, and the project does not report it as one.

## 2. What the data *can* carry is the fiscal channel — and that is what landed after Stage 5

Two series landed after Stage 5 ran its verdicts, and both are monthly:

| Series | Grain | Span | Source |
|---|---|---|---|
| FAAC state allocation (the dose) | state × month, 36 states | 2016-12 → 2026-06 (114 months) | OAGF + NBS disbursement documents (2026-10-16) |
| Conflict fatalities and incidents (the outcome) | state × month, 37 units | 1990-09 → 2025-12 (343 active months) | UCDP GED bulk archive (26.1, adopted 2026-10-30, C-82) |

Their intersection is **3,888 state-months** (2016-12 → 2025-12), which is the first sample in this
project big enough to estimate anything at all. Two questions were pre-declared against it
(`analysis/specs/estimation.yml`), each with the check that could kill it.

### Design A — does a larger federal allocation reduce conflict where it lands?

**Estimated, and not identified.** The coefficient is reported with its bounds; the design fails its own
checks, and both are published.

| Outcome | Elasticity | 95 % CI | n |
|---|---|---|---|
| fatalities | +0.468 | [−0.083, +1.019] | 3,888 |
| incidents | +0.528 | [+0.147, +0.909] | 3,888 |
| fatalities_civilians | +0.343 | [−0.620, +1.305] | 3,564 |

Why the verdict is not "identified":

* **A mis-timed dose is as good as the timed one.** Refitting the same estimator with each state's dose
  series shifted by any non-zero offset from −30 to +30 months, **10 of 60 offsets return an estimate at
  least as large** as the estimate itself (p = 0.167). The deterministic 24-month placebo returns
  **+0.310** against the estimate's **+0.468**.
* **The identifying variation is a commodity price.** What survives state and month fixed effects in the
  dose is concentrated in the oil-producing states: residual sd **0.50 in Delta, 0.50 in Bayelsa, 0.47 in
  Rivers** against **0.11** in Sokoto, Bauchi, Adamawa, Kaduna and Taraba. That is the 13 % derivation
  share moving with the oil price and with production volumes — a national shock interacted with a fixed
  state characteristic, which is not the as-good-as-random exposure a dose-response design assumes.

A secondary null — shuffling the dose across states within each month — returns p = 0.000, and it is
published *because* it was run, not as a rescue: that null destroys the cross-state mean, which the state
fixed effects already absorb, so it is far too easy to beat. The full distribution of all 60 mis-timed
estimates is in `estimates.json`, so a reader can check the claim rather than take it.

**The honest statement:** a state that received more federal money in a month did not visibly see less
violence, and this design cannot distinguish that from any other timing. The question is *asked* and
*answered as unanswerable at this identification*, which is a different thing from "there is no effect".

#### Stage 7 pushed on this: the grid now mostly agrees on the sign, and the verdict still fails

`docs/robustness.md` refits this question 81 ways (`registry/robustness/2026-10-30/`). The result:
**60 specifications positive, 21 negative**, and the check that fails is still the lead-shift placebo
(p = 0.167, 10 of 60 mis-timed doses at least as large as the published estimate). The 36
leave-one-state-out refits do *not* flip the sign (range [0.1429, 0.5950]), so the estimate is not carried
by one unit. The grid's sign share moved when the UCDP history was revised (25.1 → 26.1, C-82): under 25.1
it was 45 positive against 36 negative, and the lagged dose was negative in all three windows. A grid that
agrees on a sign is not an identification strategy — the verdict is still *estimated, not identified*, and
it is the lead-shift check rather than the count that makes it so.

### Design B — how much of a Brent shock reaches the states, and the price level?

**Two outcome families share one shock, one control set and one bandwidth** (C-85): the fiscal channel,
which is the design's pre-registered headline, and the price level, which is the question the subsidy
removal made urgent. They are reported separately because their verdicts differ.

#### The fiscal channel — estimated

This is the design that works, because the direction of causation is defensible: Nigeria is a price
taker in a market two orders of magnitude larger than its exports, so the Brent shock can be treated as
exogenous to Nigerian fiscal outcomes. Local projection, cumulative response, Newey-West (12 lags):

| Horizon (months) | Cumulative elasticity | SE | 95 % CI |
|---|---|---|---|
| 0 | −0.160 | 0.124 | [−0.402, +0.082] |
| 1 | +0.157 | 0.128 | [−0.093, +0.408] |
| **2** | **+0.518** | **0.166** | **[+0.192, +0.844]** |
| **3** | **+0.470** | **0.158** | **[+0.161, +0.779]** |
| 4 | +0.161 | 0.162 | [−0.156, +0.478] |
| 6 | +0.231 | 0.218 | [−0.197, +0.659] |
| 12 | +0.325 | 0.319 | [−0.300, +0.949] |

**A 10 % rise in Brent reaches the states as roughly a 5 % larger allocation, two to three months
later.** The lag is what the disbursement calendar implies rather than a curiosity: the allocation
published for a month is revenue accrued in an earlier one, so an immediate response would have been the
surprising result. The lead placebo — regressing today's allocation on a *future* oil shock — is
+0.095 (SE 0.152), an order of magnitude smaller than the peak response at h = 2.

Before h = 2 the response is zero (−0.160 at h = 0), which is the substantive claim of this design: the
oil channel reaches state budgets through an administrative lag, not a market one.

#### The price level — estimated as a null at the declared band

The same shock, on the NBS all-items CPI index (native monthly, 1999-01 → 2024-10, 310 months). The
cumulative coefficient is the log change in the price level h months after a 1 % Brent move, so it reads
as the inflation that passes through:

| Horizon (months) | Cumulative log change | SE | 95 % CI | p |
|---|---|---|---|---|
| 0 | +0.004 | 0.006 | [−0.007, +0.015] | 0.439 |
| 1 | +0.004 | 0.010 | [−0.016, +0.024] | 0.728 |
| 2 | −0.002 | 0.016 | [−0.033, +0.028] | 0.892 |
| 3 | −0.004 | 0.018 | [−0.040, +0.032] | 0.823 |
| 4 | −0.002 | 0.022 | [−0.046, +0.042] | 0.928 |
| 6 | −0.008 | 0.027 | [−0.062, +0.046] | 0.771 |
| 12 | −0.002 | 0.029 | [−0.058, +0.055] | 0.956 |

**Nothing here is distinguishable from zero, and the declared rule says so rather than leaving it to a
reader:** no horizon in the two-to-four-month band reaches |t| > 1.96, so the family's verdict is
`estimated_null_at_the_declared_band`, with the lead placebo at −0.003. That is a result about *this*
channel, not about the 2023 inflation surge: the surge coincides with the subsidy withdrawal and the
devaluation, neither of which is a Brent shock, and Stage 5 measured the price level as sharing no
long-run path with Brent under the conservative rank rule (C-86). A design that can see the window and
still finds no oil-price pass-through is telling you the window's driver was domestic.

**What this does not establish:** for the fiscal family, the response is measured in naira against a
dollar price, so the elasticity mixes the price channel with the exchange-rate channel, and the naira
moved twice inside the window. A monthly NGN/USD series would separate them; it does not exist on any
keyless source (C-46). The confidence bounds are also wide, and 114 months is not many. For the
price-level family, the series ends in 2024-10, so nothing after it is claimed, and a null at monthly
frequency with 310 observations is not the same as a null on annual data.

### Design C — synthetic control: estimated, and not identified

The design moved twice. Stage 5 first recorded `infeasible`: the pre-treatment fit failed on every outcome and
every window against a 13-country pool, with the best single donor beating the fitted simplex. The pool was
then widened to **99 candidates** screened on oil dependence, region/income band and coverage, and the gate
re-run passed **`u5mr` on 3 of its 4 runnable windows** (ratios 0.0014–0.0042 against the declared 0.10
threshold). That pass was permission to build the design, not evidence that its fit was real — and the
warning was earned.

The estimator and its placebos now exist (`analysis/specs/design_c.yml`, `analysis/R/11_design_c.R`,
`registry/design_c/2026-10-18/`). **Four windows were estimated and none is identified.** The in-space rank p
runs from 0.17 to 0.50, the in-time placebo fails in the one window long enough to run it, and the declared
pre-fit gate turns out not to discriminate at all: **304 of the 396 placebo fits also clear the same 0.10
threshold.** A 99-donor simplex can interpolate any 8-to-24-year pre-period, so the gate's pass says almost
nothing about whether the fit is a counterfactual.

Two numbers travel with the gaps because the declared problem is underdetermined. With 99 donors and 8 to 24
pre-years, a face of weight vectors fits the pre-period equally well and they disagree about the post-period;
the artifact publishes the vertex the declared solver returns **and** a unique ridge refit beside it. For the
first window the two disagree in sign (+2.1 against −2.6 deaths per 1,000), which is the clearest statement
the design can make about itself: that estimate belongs to the solver, not to the data.

No gap is on a card, because a synthetic control has no sampling distribution and the honesty layer publishes
no point estimate without an interval. The `u5mr` card carries `design_estimated_not_identified` and points at
the artifact.

## 3. The answer, in one paragraph

**Of the four questions this project set out to answer, one is not answerable (presidential tenure
effects on national annual outcomes), one is now estimable but not identified (does federal money reduce
local violence), and one is answerable and answered (an oil-price shock reaches Nigeria's states with an
elasticity of roughly 0.5 at a two-to-three-month lag).** The fourth — synthetic control against a donor
pool — cleared its pre-fit gate on one outcome once the pool was widened (2026-10-18) and has now been
fitted: four windows, no identified effect, and a placebo distribution that says the gate's pass was
interpolation (`registry/design_c/2026-10-18/`). **A fifth question turned out to be answerable and is
answered: did conflict move inside each tenure?** (`docs/events.md`: two of eight event-outcome cells survive
both the placebo and the pre-trend check.)

The tenure question is not "unsupported by evidence yet". It is *not answerable* from national annual
data with four administrations, and the only route to an answer is sub-national monthly outcomes, which
is exactly why the FAAC dose and the UCDP outcome were worth acquiring.

## 4. What would change these answers

| To answer | What is needed | What blocks it |
|---|---|---|
| Tenure effects on health and education | Sub-national monthly health/education outcomes | DHIS2 credentials; NEMIS/NBS series stop in 2010 — a declared gap, not a fetching problem |
| Design A, identified rather than estimated | An exposure that varies within state for reasons unrelated to oil | The dose *is* oil revenue; a non-oil fiscal instrument (state IGR, VAT distribution) would be a different design |
| The naira channel separated from the price channel | Monthly NGN/USD | No keyless publisher: FRED has none (verified 2026-10-17), CBN is the only source and a monthly series has to be assembled by hand (C-46) |
| The security record after 2025-12 | The next GED release | Publication cycle — the adopted archive (26.1) is complete to 2025-12 |
| Design A before 2016 | A monthly FAAC series back to 1999 | Neither OAGF nor NBS publishes the PDP era online (declared gap `state_dose_d1_coverage`) |
