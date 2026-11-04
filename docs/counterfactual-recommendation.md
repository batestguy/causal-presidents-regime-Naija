# What-if comparisons: recommendation, ahead of follow-up

**Status: recommendation, not a result.** Nothing here changes the frozen registry
(vintage 2026-11-01). This document records the proposal in full, the evidence gathered so far, the exact
presentation contract, and the decisions that remain. It is written so a follow-up session can execute
without re-litigating the method.

## 1. The problem being solved

Thirty-four of the thirty-six design cards carry no number. They fall into three different groups, and the
proposal treats them differently:

| Group | Outcomes | Why no number | Can a what-if help? |
|---|---|---|---|
| Identified estimates exist | fatalities, incidents | number published, check failed | already numbered; what-if would be a robustness check |
| Estimated, not identified | u5mr, mmr, unemp, immun_penta3, gdp_growth, cpi_yoy | Design C ran; the donor simplex was underdetermined and the placebos did not clear | **yes, as a what-if, never as an effect** |
| No series at the design grain | literacy_youth, primary_completion, ner_primary | no donor series, no state-level native data | **no** |
| Classification question | cpi_yoy | Design B's oil→CPI local projections exist with intervals but are labelled channel-level | **publish the existing interval; no ML needed** |

The user's ask is to stop presenting a blank where something can honestly be shown. The proposal is a
**separate class of statement** — a model counterfactual — with its own label, its own artefact and its own
rules. It is not a new card number and it is not a causal claim.

## 2. What a "what-if" is, precisely

A counterfactual comparison asks: *what would Nigeria's outcome have looked like in this window if the
presidency had not changed*, built by matching Nigeria's pre-window path to comparable countries and carrying
that matched path forward. The gap is the actual outcome minus the matched path.

It is **not** an estimate of the effect of a president. It does not identify a cause. The window is a
calendar convention (the year belongs to the administration in office on 1 July), not a treatment
assignment. The matched path is a model output, and different defensible models disagree, as the pilot
shows.

What it can honestly say: *"against a matched path built from 99 countries, Nigeria's under-5 mortality sat
X above or below what that path predicted in this window, and the estimators agree or disagree on the
sign."* That is a descriptive counterfactual, useful to a reader, and true to the data.

## 3. The method

Three counterfactual estimators are fitted on identical windows and identical donors, and all three are
reported:

1. **Simplex synthetic control** — the existing Design C estimator (quadratic programme on the pre-period
   path). Kept because its numbers are already published as `estimated_not_identified`.
2. **Synthetic difference-in-differences (SDID)** — Arkhangelsky et al. (2021). Unit and time weights, robust
   to level differences between Nigeria and donors; placebo-based uncertainty. Implemented in R `synthdid`.
3. **Matrix completion / interactive fixed effects** — Athey, Bayati, Doudchenko, Imbens, Khosravi (2021)
   for the underdetermined-donor case; approximated in the pilot with `gsynth` (Xu 2017) where it runs.
   Rank and penalty chosen by pre-period cross-validation.

**Windows** are Design C's declared ones, inherited rather than retyped
(`analysis/specs/design_c.yml`): the year belongs to the administration in office on 1 July, pre-period is
every year from 1999 to the year before the window's first post year, and a window needs at least 8 pre
years and 2 post years. That gives Yar'Adua (2007–2009), Jonathan (2010–2014), Buhari (2015–2022) and
Tinubu (2023–2024); Obasanjo is refused for lack of pre years inside 1999+.

**Donors** are the countries in `fact_donor_panel` with a complete outcome path over the window, up to 99.
No donor selection, no hand-picking.

**Inference** is placebo-based throughout: in-space placebos (each donor treated in turn, same window) and
in-time placebos (window backdated 3, 5, 7 years where runnable). The 95 % bounds are the 2.5th and 97.5th
percentiles of the placebo gap distribution, declared as randomization inference, not a sampling interval.
This matches the inference philosophy already used by Design C.

## 4. Pilot evidence (u5mr, exploratory, nothing published)

Simplex gaps are Design C's published `mean_gap` per window. SDID was fitted on the same windows and donors
with the balanced 1999+ panel; the placebo standard error for Jonathan is from `synthdid`'s placebo variance.

| Window | Simplex gap | SDID gap | SDID placebo SE | Sign agreement |
|---|---|---|---|---|
| Yar'Adua (2007–2009) | **+2.11** | **−0.87** | not run | **disagree** |
| Jonathan (2010–2014) | **−11.56** | **+1.51** | ≈ 8.0 | **disagree** |
| Buhari (2015–2022) | **+8.59** | **+5.74** | not run | agree |
| Tinubu (2023–2024) | **+18.53** | **+1.70** | not run | agree |

Jonathan's SDID interval is roughly −14 to +17: it includes zero. Two of four windows flip sign between
estimators. Conclusion: for u5mr the what-if is presentable **only with the disagreement made visible**, and
it must not be summarised as a single effect.

This is the central finding of the pilot and the reason for the presentation rules in §5.

## 5. The presentation contract

### 5.1 What a reader sees

For each outcome with donor coverage, a **what-if** block under the estimate screen:

- badge: `what-if · not identified` (new, visually distinct from `answered` and from a card verdict);
- the gap per window from each estimator, in outcome units, with the placebo interval;
- the stability verdict: `methods agree` or `methods disagree`, with the range when they disagree;
- one plain sentence, e.g. *"Against a matched path built from 99 countries, Nigeria's under-5 mortality sat
  2.1 per 1,000 above that path in 2007–2009 under one estimator and 0.9 below under another. The data and
  the methods do not agree on the direction."*;
- the what-if is **never** averaged across estimators and **never** reduced to one "best" number.

### 5.2 Wording rules

- No causal verbs: no "caused", "effect of", "because of", "improved", "worsened", "blame", "credit".
- The words "effect" and "estimate" do not appear in a what-if block; "gap", "matched path", "counterfactual"
  do.
- Every window is shown, or the block states how many windows are refused and why. No cherry-picking.
- A card keeps its own reason unchanged; the what-if block lives beside it, not inside it.

### 5.3 Counts on the cover and About page

The cover currently says "2 of 36 cards carry a published number". That stays true and must not be
retitled. A second line is added: **"9 of 12 outcomes carry a what-if comparison; 3 carry neither."** The
About page explains the three classes: identified estimate, what-if, refusal.

## 6. Coverage

| Outcome | Donor series | What-if possible | Notes |
|---|---|---|---|
| u5mr | 99 complete donors 1999–2024 | yes | pilot done |
| mmr | donors exist but not complete over 1999–2024; per-window subsets | likely yes | window-specific donor set, state the count |
| unemp | 96 complete donors | yes | |
| immun_penta3 | 96 complete donors | yes | |
| gdp_growth | 94 complete donors | yes | |
| cpi_yoy | 75 complete donors | yes | plus the Design B interval already in the registry |
| skilled_birth | 1,220 donor rows; no complete 1999–2024 set | maybe, window-specific | sparse; label the donor count |
| oil_rents | donors exist (annual to 2021) | maybe | covariate, not an outcome card |
| population | donors exist | not an outcome | not presented |
| fatalities, incidents | donors exist (1989+) | already numbered | what-if as robustness, optional |
| literacy_youth, primary_completion, ner_primary | none | **no** | keep the reason, add "no comparable-country series" |

## 7. Artifact contract (for the follow-up build)

- New family: `registry/counterfactual/<vintage>/counterfactual.json`, one row per
  outcome × window × estimator:
  `outcome`, `window`, `first_year`, `last_year`, `pre_years`, `post_years`, `estimator`,
  `gap`, `interval_low`, `interval_high`, `interval_method` (`placebo`), `placebo_p`, `n_donors`,
  `rank_or_penalty`, `pre_fit_error`, `status` (`stable` / `unstable`), `notes`.
- A **new vintage** (e.g. 2026-11-xx) carries it; the frozen 2026-11-01 vintage is not edited, and cards
  are not rewritten. The what-if page reads the new artifact and joins on outcome.
- A verifier `tests/verify_counterfactual.py` that recomputes, from the artifact's own stored fits,
  the placebo distribution, the percentiles, the stability flag and the counts. It must fail if any
  window is missing without a stated reason.
- The site reads the artifact; no number is typed into a renderer (house rule).

## 8. Work plan

1. **Declare** `analysis/specs/counterfactual.yml` with the estimator parameters, window rule, donor rule,
   placebo counts, interval method, stability rule and the wording rules above.
2. **Extractor**: one read-only script building the per-outcome panel (`fact_metric` + `fact_donor_panel`),
   writing an intermediate table; no fits.
3. **Fitters**: simplex (reuse Design C's artefact), SDID (R `synthdid`), matrix completion / `gsynth`
   (R). Same windows, same donors, same placebo schedule. Store every fit's diagnostics.
4. **Artifact**: emit `counterfactual.json` for the new vintage, with all outcomes and windows, including
   the refused ones and the reasons.
5. **Verifier**: second implementation of the placebo intervals and the stability rule.
6. **Site**: a what-if block on the estimate screen (and a line on the outcome's card list), plus the cover
   count line and the About explanation.
7. **Checks**: `verify_site`, the new verifier, and a browser pass over three outcomes (one stable, one
   unstable, one impossible).

## 9. Decisions needed before execution

1. **Presentation placement**: a separate what-if block/page (recommended) versus a new card status. The
   recommendation is separate, because a card status invites the causal reading the site refuses.
2. **Vintage**: confirm that a new registry vintage may be created for this; the frozen one cannot change.
3. **Scope**: first batch only `u5mr`, `mmr`, `unemp` (the three Design C targets), or all donor-covered
   outcomes at once. Recommended: the three first, then extend.
4. **Inflation**: whether to reclassify `cpi_yoy` and publish Design B's existing oil→CPI intervals (a
   registry-vintage decision, not an ML run).
5. **Education**: confirm these three keep a refusal with the added sentence "no comparable-country series",
   rather than any number.

## 10. Risks and stop conditions

- **Estimator instability** (observed): if the three estimators disagree on the sign in most windows, the
  what-if is still presentable but must say so; it is not a number to quote.
- **Donor completeness**: mmr and skilled birth will need window-specific donor sets; if a window has fewer
  than ~20 complete donors, the block says "too few comparable countries" instead of a gap.
- **Multiple testing**: 9 outcomes × 4 windows × 3 estimators is a large surface; no "best window" may be
  selected after seeing results. The stability flag is the output, not a significance claim.
- **Narrative drift**: the largest risk is a reader (or a future summary) quoting one estimator's gap as the
  effect. The wording rules in §5.2 and the verifier exist to make that hard.

## 11. Environment (ready)

`causality-handbook` (Python 3.11.14): `duckdb` 2.0.0, `doubleml` 0.11.4, `tigramite` 5.2.10.1,
`causallearn`, `econml`, `dowhy`, `causalml`, `linearmodels`, `cvxpy`. R 4.5.2: `synthdid`, `gsynth`, `did`,
`dagitty`. `ds-general` was restored after the accidental discovery installs. The analytical base reads
read-only; the pilot scripts live in `.inspect/` and are not part of any pipeline.
