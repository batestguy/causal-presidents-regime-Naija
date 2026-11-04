# Causal ML plan: environment and first declared pass

*Related: [`counterfactual-recommendation.md`](counterfactual-recommendation.md) (the full recommendation
this plan serves), [`causal-ml-options.md`](causal-ml-options.md) (method menu),
[`causal-discovery.md`](causal-discovery.md) (the other track).*

Status: environment ready; no fitting has started; the registry is untouched. This is the plan to agree
before anything is run, following the house rule that a design is declared before it is fitted.

## Environment

**Causal environment (the home for this work):** `C:\Users\TOSHIBA\miniconda3\envs\causality-handbook`
(Python 3.11.14). Verified to import and run:

| Package | Version | Role |
|---|---|---|
| `duckdb` | 2.0.0 | reads `data/analytics.duckdb` (verified: 8,350 rows in `fact_metric`) |
| `doubleml` | 0.11.4 | DML robustness arm |
| `tigramite` | 5.2.10.1 | PCMCI (discovery, separate question) |
| `causallearn` | present | PC/GES/FCI/LiNGAM |
| `econml`, `dowhy`, `causalml` | present | meta-learners and sensitivity tooling |
| `linearmodels`, `statsmodels`, `scipy`, `sklearn`, `cvxpy` | present | estimation and optimisation |

**R 4.5.2:** `gsynth`, `did`, `synthdid` (installed from `synth-inference/synthdid` on GitHub, CRAN has no
build for this R), `dagitty`. `synthdid` loads.

**`ds-general` cleaned:** the earlier accidental installs (`causal-learn`, `tigramite`) were removed, so the
verified build environment is back to its previous package set. Discovery work should run in
`causality-handbook`.

Known package warnings (pre-existing or upstream, not blocking): `numba` asks for numpy < 2.4 while numpy is
2.4.6 (PCMCI runs anyway, verified with a synthetic graph); `catboost` asks for numpy < 2.0; `dowhy` asks for
cython < 3. If a specific run fails on one of these, pin numpy to 2.3.x in the causal env and re-test, rather
than touching `ds-general`.

## The decision this plan implements

Design C refused four windows because the synthetic control's donor simplex was underdetermined: 99 donors,
8 to 24 pre-years, and the gap's sign depended on the solver. The plan replaces the simplex fit with a
**matrix-completion counterfactual** (Athey, Bayati, Doudchenko, Imbens, Khosravi 2021), which is built for
that exact case, and keeps the same windows, placebos and honesty gate the project already uses.

## Stages

**Stage 0: declare the spec (no numbers yet).** `analysis/specs/design_c_prime.yml` fixing:

- outcomes for the first pass: `u5mr`, `mmr`, `unemp` (the three Design C targets);
- windows: inherited from `analysis/specs/design_c.yml`, not retyped;
- donor pool: the 97 to 99 countries with a complete pre-period series for the outcome;
- estimator: nuclear-norm matrix completion with unit and time fixed effects, rank and penalty chosen by
  cross-validation on the masked pre-period;
- comparison estimators: SDID (R `synthdid`) and generalized SC (R `gsynth`), fitted on the same window and
  donors, reported side by side;
- inference: in-space placebos (each donor treated in turn) and in-time placebos (window backdated 3, 5 and
  7 years where runnable), plus a donor jackknife;
- the publication gate, fixed now: a window publishes only when (a) in-space rank p <= 0.05, (b) every
  runnable in-time placebo gap is smaller than the estimate, and (c) matrix completion, SDID and gsynth agree
  on the sign. Multiplicity across outcomes and windows controlled by Holm at 0.05;
- the interval: placebo-based 95 % bounds (2.5th and 97.5th percentile of the placebo gap distribution),
  declared as randomization inference, not a sampling interval.

**Stage 1: extraction.** One read-only script builds the treated/donor panel from `duckdb` (Nigeria from
`fact_metric`; donors from `fact_donor_panel`) and writes an exploratory table under `.inspect/`. No fitting.

**Stage 2: fit and compare.** Run matrix completion, SDID and gsynth on the declared windows; record gap,
rank, penalty, pre-fit error and the solver-agreement flags.

**Stage 3: inference.** Run the placebos and the jackknife; compute rank p and placebo bounds; evaluate the
gate exactly as declared.

**Stage 4: decide publication.** Windows passing the gate go to a new registry vintage
(`registry/design_c_prime/<vintage>/`) with a verifier that recomputes the placebo distribution from the
artifact. Windows failing it stay refused, with the reason. The frozen 2026-11-01 vintage is not edited.

**Stage 5 (parallel, cheap): the inflation classification.** Design B already publishes oil->CPI local
projections with intervals (n ~ 300; h=0 estimate +0.0043, interval -0.0066 to +0.0153). The `cpi_yoy` card
calls this channel-level, which appears to be a misclassification: CPI is the outcome, FAAC was the channel.
This is a v2 decision, not an ML run.

## What this plan will not do

- It will not give every card a number. The three education outcomes have no donor series and no state-level
  native data; they cannot be estimated by any method.
- It will not replace the placebo gate with a p-value from a model.
- It will not edit the frozen registry. Publication requires a new vintage, which is a requester decision.

## First milestone (proposed)

Stage 1 and Stage 2 on `u5mr` alone, reported as exploratory: does matrix completion reproduce the direction
of the published Design C gap, and does the solver dependence that broke the simplex disappear? If the answer
is no for the clearest case, the plan stops before spending compute on the other outcomes.
