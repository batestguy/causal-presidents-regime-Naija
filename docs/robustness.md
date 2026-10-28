# Does the answer survive its own choices? — Stage 7, the multiverse

**Vintage 2026-10-17.** Written from the artifacts: `registry/robustness/2026-10-17/robustness.json`
(produced by `analysis/R/04_robustness.R` from `analysis/specs/robustness.yml`), every specification and
every count recomputed independently by `tests/verify_stage7.py`. The figure is
`registry/robustness/2026-10-17/specification_curve.svg`. Stage 6's estimates are in
`docs/estimates.md`; the pre-check verdicts are in `docs/design-memo.md`.

Stage 6 published two numbers. This stage asks the question a reviewer asks next — *does either survive
the choices that were not pinned down?* — and the honest answer is asymmetric: **one does and one does
not.**

---

## 1. The grid

105 specifications, declared in `robustness.yml` before any of them was fitted:

| Design | Axes (levels) | Specifications |
|---|---|---|
| A — state dose-response (PPML) | outcome (3) × dose lag (3) × adjustment set (3) × sample window (3) | 81 |
| B — national transmission (local projection) | shock definition (2) × covariate set (4) × sample window (3) | 24 |

The design spec (§5.4) names eight axes. Four are live here; four are not, and the dead ones are declared with
their reason rather than quietly dropped: **imputation handling** (no imputed value enters either design — the
dose is read only where `dose_status = observed`, the count series is never interpolated, S6-05), **index
anchor** (the designs use levels, so the anchor is a scaling constant the fixed effects absorb), **donor pool**
(Design C is fitted in stage 8h on the one outcome the gate passes, and its pool axis — including the
leave-one-donor-out sweep — is reported on that artifact, because neither design in this grid uses a donor
pool), and **event window** (neither design is an event study; the tenure design that would need one is not
estimable at this sample size).

One axis is live in principle and **unbuilt in fact**: the per-capita dose. `state_panel.d1_faac_per_capita`
is 0 of 12,358 rows populated because the state population denominator is an unmade decision (X-09), so
every specification in this curve is the **nominal** dose. That is stated on the artifact, in the report
and here, because a curve that silently narrowed to the axes it happens to have would look more complete
than the analysis is.

## 2. Design B is robust in sign, and the timing is its weak part

All **24 of 24** specifications are positive, and **all 24 intervals exclude zero**. The pre-registered
specification is the published one — +0.5181 (SE 0.1664, 95 % CI [+0.1919, +0.8443]) on 111 months — and
the grid reproduces Stage 6's artifact to 4.3e-12, so the curve is drawn around the published estimate
rather than a neighbour of it.

Across the grid the coefficient at h = 2 runs from **+0.3968** to **+2.3976**. Which choice moves it is
a claim about the grid, so it is computed from the fitted rows and published in the artifact
(`robustness.json` → `spread.design_b`) rather than typed here: holding the shock definition and the
window fixed, the range across the four covariate sets averages **0.4073** (mean of the six shock × window
cells); holding the covariate set and the window fixed, the gap between the two shock definitions averages
**0.7548** (mean of the twelve covariate-set × window cells). So the *magnitude* is a choice — mostly the
shock definition, a three-month average being a smoother and therefore larger-coefficient regressor —
while the *sign* is not. The decomposition is a mean of within-cell ranges rather than one chosen pair,
because a single pair would make the claim depend on which pair was picked.

Two checks say where the weakness is:

- **In-time placebo: p = 0.0625.** The shock series shifted by each of 48 non-zero offsets and the
  preferred specification refitted: 3 of 48 alignments return an estimate at least as large as the true
  one (placebo estimates average |0.1911|, maximum |0.6446|, against the estimate's +0.5181). This does
  **not** clear 0.05. The sign is the robust claim; the claim that the response is *specific to a two-to-
  three-month lag* is weaker, and the placebo is the check that tests it.
- **HAC bandwidth:** SE 0.1723 / 0.1664 / 0.1609 at 6 / 12 / 18 lags. The interval's width is not a
  bandwidth artefact — it is the sample.

Oster's delta is reported and **does not have its usual reading here**: β runs 0.4882 with no controls to
0.5181 with month dummies, i.e. the controls move the estimate *away* from zero, so δ = −44.04 and Oster's
"δ ≥ 1" cutoff does not apply. The bias-adjusted β\* at δ = 1 is 0.5299. Reporting a negative delta as if
it were a robustness certification would be a misuse of the statistic, so the artifact says which case
it is in.

## 3. Design A is not robust, and that is the finding

**45 of 81 specifications are positive and 36 are negative**, and five axis levels have a *majority* on the
opposite side of zero from the pre-registered specification:

| Axis level | Specifications opposite the preferred sign |
|---|---|
| `outcome = fatalities_civilians` | 20 of 27 |
| `dose_lag_months = 1` | 17 of 27 |
| `adjustment_set = state_fe` (no month effects) | 16 of 27 |
| `outcome = fatalities` (the preferred outcome itself) | 14 of 27 |
| `adjustment_set = state_month_fe_state_trend` | 14 of 27 |

The count is not the whole story in either direction, which is why the minority is published beside it:
6 of the 105 specifications sit **within ±0.02 of zero** (6 Design A, 0 Design B) — the band is declared in
`robustness.yml` rather than chosen after the fact — and outside it the split is 42 positive / 33 negative
for Design A. A specification that is numerically zero is reported as a near-zero cell, not absorbed into
the sign counts as if it were a direction.

The one that matters most is the **dose lag**. With the dose lagged one month and state and month effects,
the estimate is negative in all three windows while the pre-registered same-month specification is
positive. A quantity whose sign depends on a one-month timing choice is not a direction.

Two sensitivities sharpen it rather than rescue it:

- **Leave-one-state-out (36 refits):** coefficients range [0.1234, 0.6254] around 0.4793 with **0** sign
  flips. The estimate is not carried by one state — but dropping the three oil-producing states named in
  the spec (Delta, Bayelsa, Rivers) raises it to **0.6663**, because those states carry most of the dose's
  variation (C-47).
- **Oster delta on the linear analogue** (log(1 + fatalities), the only form with an R²): the control set
  **flips the sign of the estimate**, from −0.1023 without controls to +0.0882 with state and month
  effects. δ = −1.53 therefore has no attenuation reading; it is the amount of unobserved selection that
  would have to act *against* the observed controls to zero the estimate. This is a bound on the analogue,
  not on the PPML estimate, and the artifact says so beside the number.

**Rosenbaum bounds are not applicable** — the treatment is continuous and no matching was performed.
Recorded rather than omitted, because the rigor floor asks for them "where applicable" and a reader should
see the judgement.

## 4. What this changes about Stage 6

Nothing in Stage 6's numbers moves: both pre-registered specifications reproduce to 1e-12. What moves is
how they should be read.

- **Design B stands** — with one bound added: its sign is invariant across the grid, its timing is not
  (placebo p = 0.0625), and its magnitude is a choice of shock definition.
- **Design A's verdict gets sharper, not softer.** Stage 6 said *estimated, not identified* because the
  dose's post-fixed-effect variation is the oil price moving the derivation share. This stage adds that
  the sign is not even stable across the declared choices — which is the same underlying fact seen from
  another angle, and a stronger statement than a single specification and its placebo could support.
  **No cell of this grid identifies Design A**, and the grid cannot create variation the dose does not
  have.
- **The per-capita axis is still missing (X-09).** Every cell here is the nominal dose. The elasticity
  with state fixed effects is invariant to a state-constant denominator (S6-06) — but that is an argument,
  not a fitted specification, and the curve cannot test it.

## 5. Reproducing it

```bash
Rscript analysis/R/04_robustness.R            # fits the 105 specifications, writes the curve
python tests/verify_stage7.py                 # re-fits every one of them independently
python scripts/validate_artifacts.py          # contracts: counts recomputed from the artifact's own rows
scripts/verify.sh                             # the whole chain, Stages 3-7
```

The verifier re-fits all 81 Design A PPML specifications with `statsmodels` (not `fixest`), all 24 local
projections, all 36 leave-one-state-out refits and all 48 placebo alignments, and recomputes the support
counts, the majority-flip rule, both Oster bounds, the HAC table and the spread decomposition — the last
from its own re-fitted coefficients rather than from the published rows, so a grid fitted on something
else is caught rather than the summary being checked against itself. Worst coefficient disagreement
observed: 6.5e-9; worst clustered-SE gap 0.85 %, against a stated 5 % allowance.

The artifact carries the **fingerprint of the base it was fitted on** — `state_panel` `dd11d300f588`,
`faac_national_monthly` `0084ea1d7129`, `oil_series` `167ff0dce42d`, hashed by the queries in
`robustness.yml` — and the verifier re-hashes the base on disk before it compares anything. A curve drawn
against a base that has since moved is visible as a mismatch rather than as a plausible-looking
disagreement, which is the failure mode C-42, C-44 and C-49 all belong to.
