# What this project can actually answer

**Vintage 2026-10-17.** Written from the artifacts: `registry/estimates/2026-10-17/estimates.json`
(produced by `analysis/R/03_estimate.R` from `analysis/specs/estimation.yml`), every number recomputed
independently by `tests/verify_stage6.py`. Stage 5's verdicts are in `docs/design-memo.md` and
`registry/diagnostics/2026-10-17/`.

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
| Conflict fatalities and incidents (the outcome) | state × month, 37 units | 1990-09 → 2024-12 (331 active months) | UCDP GED bulk archive (2026-10-17, C-45) |

Their intersection is **3,456 state-months** (2016-12 → 2024-12), which is the first sample in this
project big enough to estimate anything at all. Two questions were pre-declared against it
(`analysis/specs/estimation.yml`), each with the check that could kill it.

### Design A — does a larger federal allocation reduce conflict where it lands?

**Estimated, and not identified.** The coefficient is reported with its bounds; the design fails its own
checks, and both are published.

| Outcome | Elasticity | 95 % CI | n |
|---|---|---|---|
| fatalities | +0.479 | [−0.113, +1.072] | 3,456 |
| incidents | +0.546 | [+0.121, +0.971] | 3,456 |
| fatalities_civilians | +0.310 | [−0.615, +1.234] | 3,168 |

Why the verdict is not "identified":

* **A mis-timed dose is as good as the timed one.** Refitting the same estimator with each state's dose
  series shifted by any non-zero offset from −30 to +30 months, **8 of 60 offsets return an estimate at
  least as large** as the estimate itself (p = 0.133). The deterministic 24-month placebo returns
  **+0.302** against the estimate's **+0.479**.
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

#### Stage 7 pushed on this, and the sign did not survive

`docs/robustness.md` refits this question 81 ways (`registry/robustness/2026-10-17/`). The result:
**45 specifications positive, 36 negative**, and the estimate is negative in all three windows when the
dose is lagged one month rather than contemporaneous — while the pre-registered same-month specification
is positive. The 36 leave-one-state-out refits do *not* flip the sign (range [0.1234, 0.6254]), so the
problem is not one unit; it is that the dose's timing and the adjustment set each decide the direction.
A verdict of *estimated, not identified* therefore understates what Stage 6 found: the number is not a
direction, and the robustness grid is where that became visible.

### Design B — how much of a Brent shock reaches the states, and when?

**Estimated.** This is the design that works, because the direction of causation is defensible: Nigeria
is a price taker in a market two orders of magnitude larger than its exports, so the Brent shock can be
treated as exogenous to Nigerian fiscal outcomes. Local projection, cumulative response, Newey-West
(12 lags):

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

**What this does not establish:** the response is measured in naira against a dollar price, so the
elasticity mixes the price channel with the exchange-rate channel, and the naira moved twice inside the
window. A monthly NGN/USD series would separate them; it does not exist on any keyless source
(C-46). The confidence bounds are also wide, and 114 months is not many.

### Design C — synthetic control, not run

Stage 5 recorded it `infeasible`: the pre-treatment fit fails on every outcome and every window, with the
best single donor beating the fitted simplex. A synthetic control whose pre-period it cannot reproduce
has no post-period to believe, and nothing that landed since changes the donor pool. The next step is the
donor pool (screened on oil dependence and conflict exposure rather than GDP alone), not the estimator.

## 3. The answer, in one paragraph

**Of the four questions this project set out to answer, one is not answerable (presidential tenure
effects on national annual outcomes), one is now estimable but not identified (does federal money reduce
local violence), and one is answerable and answered (an oil-price shock reaches Nigeria's states with an
elasticity of roughly 0.5 at a two-to-three-month lag).** The fourth — synthetic control against a donor
pool — is blocked on the donor pool, and that is a stated next step rather than a silent failure.

The tenure question is not "unsupported by evidence yet". It is *not answerable* from national annual
data with four administrations, and the only route to an answer is sub-national monthly outcomes, which
is exactly why the FAAC dose and the UCDP outcome were worth acquiring.

## 4. What would change these answers

| To answer | What is needed | What blocks it |
|---|---|---|
| Tenure effects on health and education | Sub-national monthly health/education outcomes | DHIS2 credentials; NEMIS/NBS series stop in 2010 — a declared gap, not a fetching problem |
| Design A, identified rather than estimated | An exposure that varies within state for reasons unrelated to oil | The dose *is* oil revenue; a non-oil fiscal instrument (state IGR, VAT distribution) would be a different design |
| The naira channel separated from the price channel | Monthly NGN/USD | No keyless publisher: FRED has none (verified 2026-10-17), CBN is the only source and a monthly series has to be assembled by hand (C-46) |
| The last 22 months of the security outcome | GED 26.x (the archive ends 2024-12) | Publication cycle — the series is complete to its own last release |
| Design A before 2016 | A monthly FAAC series back to 1999 | Neither OAGF nor NBS publishes the PDP era online (declared gap `state_dose_d1_coverage`) |
