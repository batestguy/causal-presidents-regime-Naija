# Modern causal ML: what is defensible here

**Decision brief, before any fitting.** Nothing here changes the registry. The question is which ML-based
causal method can be defended on this project's data, and what it would buy for the 34 cards that carry no
number.

## What the design-first books say

The Effect (Nick Huntington-Klein), Mostly Harmless Econometrics, Causal Inference: The Mixtape, and
Hernán and Robins all teach the same ordering: identification comes from the design and its assumptions;
the estimator is a second question. ML changes the second question (flexible nuisance models, better
counterfactuals, honest uncertainty) and cannot change the first. Any proposal that says "the model found a
causal structure" is selling the estimator as identification, which is the failure mode this site exists to
refuse.

Modern causal ML is defensible in exactly three roles here:

1. **Counterfactual construction** where no single donor exists (synthetic controls, matrix completion).
2. **Nuisance estimation with orthogonal scores** so flexible models cannot contaminate the treatment
   estimate (double machine learning, TMLE).
3. **Honest uncertainty** through placebo, randomization and bootstrap inference rather than asymptotic
   formulas that assume a sampling model these series do not have.

## The menu, ranked for this data

| Method | What it fixes | Fit here | Verdict |
|---|---|---|---|
| **Matrix-completion synthetic control** (Athey, Bayati, Doudchenko, Imbens, Khosravi 2021) | the underdetermined donor simplex (99 donors, 8–24 pre-years) that made Design C solver-dependent | 97–99 donor countries with outcome series; annual pre-periods | **first choice** |
| **Synthetic difference-in-differences** (Arkhangelsky et al. 2021) | unit and time heterogeneity; jackknife/bootstrap SEs; weights on both margins | same country panel and windows | **second estimator, same declared design** |
| **Generalized synthetic control** (Xu 2017, `gsynth`) | interactive fixed effects; cross-validated rank | same panel | robustness |
| **Double/debiased ML** (Chernozhukov et al. 2018; `DoubleML`) | flexible nuisance models with orthogonal scores and cross-fitting | state panel for Design A; cluster-robust | robustness arm for the security numbers |
| **BSTS / CausalImpact** (Brodersen et al. 2015) | posterior interval on a single treated series | national monthly series (CPI, conflict) | robustness only; model-based |
| **Causal forests** (Wager & Athey 2018) | heterogeneity | 36 states, 99 countries, 27–324 time points | **not defensible**: too few units for credible CATEs |
| **TMLE / meta-learners** | doubly robust estimation | needs larger effective n and a clean assignment | not now |
| **PC / PCMCI (discovery)** | hypothesis generation | see `docs/causal-discovery.md` | never an estimator |

## What the data can actually support

The donor panel (`fact_donor_panel`, 47,386 rows) carries the outcome series for **97–99 countries** on
eleven metrics: `cpi_yoy`, `fatalities`, `gdp_growth`, `immun_penta3`, `incidents`, `mmr`, `oil_rents`,
`population`, `skilled_birth`, `u5mr`, `unemp`. Nine of the twelve catalogue outcomes are therefore
eligible for a country-donor synthetic control; only the three education outcomes are not (no donor series,
no state-level native data).

Per-state discovery-grade data exists only for security (UCDP) and FAAC, so the state panel cannot host an
ML estimator for the other outcomes.

## The polish map

| Outcome | Status now | Defensible ML route | Chance of a number |
|---|---|---|---|
| fatalities, incidents | number published, check failed | matrix-completion and DML as robustness on the same design | already numbered; might tighten |
| **cpi_yoy** | card says channel-level | **an outcome-level result already exists**: Design B's oil→CPI local projections (h = 0..12, n ≈ 300, e.g. h=0: +0.0043, interval −0.0066 to +0.0153). Classifying inflation as "channel" looks wrong: CPI is the outcome, FAAC was the channel | **highest-value fix, no ML needed**: reclassify in a v2 vintage and publish the interval |
| u5mr, mmr, unemp | estimated, not identified (solver-dependent) | matrix-completion SC + placebo inference, SDID as second estimator | real chance: produces gaps and placebo intervals; stays absent if placebos fail |
| immun_penta3, gdp_growth, skilled_birth | channel or absent | country-donor matrix completion; sparse donor years for skilled birth (1,220 rows) | moderate to low |
| literacy_youth, primary_completion, ner_primary | no usable series | none: no donor series, no state native data | **impossible without new data** |

## Recommended declared design (v2)

1. **Design C′ (country-donor), matrix completion** on the 1999–2025 window for `u5mr`, `mmr`, `unemp`,
   `immun_penta3`, `gdp_growth`, `skilled_birth`, with SDID and `gsynth` as robustness. Pre-treatment
   windows declared per outcome; donors 97–99; rank chosen by cross-validation; placebo inference
   (in-space and in-time) exactly as Design C does today; a link is published only when the placebo gate
   clears. Multiple testing: Holm across outcomes, pre-declared.
2. **Reclassify `cpi_yoy`**: publish Design B's CPI local projections on the inflation card, with the
   design's own assumption and the horizon table; leave FAAC channel-level as it is.
3. **Design A robustness**: DoubleML (partially linear, state and month fixed effects, clustered scores,
   cross-fitting) beside the PPML estimate for the two security outcomes; published as a robustness line,
   not a replacement.
4. **No** causal forests, no discovery-as-estimator, no LLM-derived causality.

## What this will not do

It will not give ten new numbers. Two of the ten absences are data holes (education). One is a
classification bug (inflation). The rest may yield numbers **only if** their placebo gates clear, and the
pre-declared rule must be allowed to refuse them again.

## Tooling

Installed: `causal-learn`, `tigramite`. To add for this plan: `DoubleML` (Python) or its R twin,
`synthdid` (R, or Python `synthdid`), `gsynth` (R), and a matrix-completion routine (R `gsynth`/`firmc`,
or a nuclear-norm implementation in Python). Everything runs in `ds-general` unless a separate discovery
environment is created.
