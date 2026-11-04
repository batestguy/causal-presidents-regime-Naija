# Causal ML phases: the workflow, and where we are

*Related: [`causal-ml-plan.md`](causal-ml-plan.md) (the declared first pass this workflow executes),
[`counterfactual-recommendation.md`](counterfactual-recommendation.md) (the what-if contract and the five
decisions only the requester can make), [`causal-ml-options.md`](causal-ml-options.md) (the method menu),
[`causal-discovery.md`](causal-discovery.md) (the other track, not started).*

**Status: P0–P4 opened and closed 2026-11-04; P5 is blocked by the stop rule; P6 needs requester sign-off.
The registry stays frozen at vintage 2026-11-01 and nothing in this workflow may edit it.** A published
what-if is a *new* vintage, and that is P6.

The first pass ran on `u5mr` alone, as the plan said it would. It answered the stop-rule question with a
**no**: matrix completion removes the solver dependence, but its gaps sit inside their own placebo
distributions on all four windows (rank p 0.28 to 0.79 against a 0.05 gate), so `u5mr` carries no
publishable what-if. The expensive extension to `mmr` and `unemp` therefore does not open. The numbers and
the reasoning are in `PROGRESS.md`, 2026-11-04.

This document is the control surface for the causal work. It answers three questions a reader will ask
next session: what phase are we in, what does that phase have to produce, and what evidence closes it.
It is deliberately a stub as of 2026-11-04: the phase list is fixed, the statuses are not.

---

## 1. The four rules the phases enforce

1. **Declared before fitted.** A spec in `analysis/specs/` fixes the outcomes, windows, donor rule,
   estimators, placebo schedule, gate and wording *before* a number exists. A parameter that changes after
   a fit is a new phase and a new spec version, never a quiet edit.
2. **The registry is frozen, including for agents.** `registry/2026-11-01` and the older `design_c`
   vintages are read-only input. Corrections are produced by the engine into a new vintage directory.
3. **A phase closes on a command, not on an opinion.** Every exit criterion below names the command whose
   output closes it. "Looks right" is not a status.
4. **A stop rule is part of the design.** P4 exists so the expensive extension to the other two outcomes
   can be refused on evidence rather than defended on sunk cost.

What the phases may never do, restated because it is the failure mode this project has already had once:
publish one estimator's gap as *the* effect, average estimators to hide disagreement, or turn a what-if
into a card number.

---

## 2. The phases

| Phase | Name | Deliverable | Exit criterion | Acceptance command | Status |
|---|---|---|---|---|---|
| **P0** | Declare | `analysis/specs/design_c_prime.yml` | spec parses; windows, donors, estimators, placebos, gate and refusals fixed; no outcome number typed into it | `python -c "import yaml,pathlib; yaml.safe_load(pathlib.Path('analysis/specs/design_c_prime.yml').read_text(encoding='utf-8'))"` | **done** |
| **P1** | Extract | `scripts/extract_design_c_prime.py` → `.inspect/design_c_prime_u5mr_panel.csv` + a printed reconciliation | row counts reconcile to the database; Nigeria from native observations; complete-donor count printed; no fit | the script's own reconciliation block | **done** |
| **P2** | Fit and compare | `scripts/fit_design_c_prime.py` + `analysis/R/12_design_c_prime_arms.R` → `.inspect/design_c_prime_u5mr_fits.json` | every declared window either carries each arm's gap or a stated refusal; solver dependence measured | `python scripts/fit_design_c_prime.py --outcome u5mr` | **done** |
| **P3** | Inference | in-space and in-time placebos, rank p, placebo percentiles | every runnable placebo is reported; the count of unrunnable ones is stated; gate evaluated exactly as declared | `python scripts/fit_design_c_prime.py --outcome u5mr --placebos` | **done** |
| **P4** | Verdict and stop rule | the written answer: does the clearest case hold, and does P5 open? | a yes/no with the numbers that decide it, recorded in `PROGRESS.md` | reading the P2/P3 output against the declared stop rule | **done: stop rule fails** |
| **P3** | Inference | in-space and in-time placebos, donor jackknife, rank p, placebo percentiles | every runnable placebo is reported; the count of unrunnable ones is stated; gate evaluated exactly as declared | same engine, second pass over the same spec | **not started** |
| **P4** | Verdict and stop rule | the exploratory finding: does matrix completion reproduce Design C's direction on `u5mr`, and does the solver dependence disappear? | a written yes/no with the numbers that decide it, recorded in `PROGRESS.md` | reading the P2/P3 output against the declared stop rule | **not started** |
| **P5** | Extend | `mmr` and `unemp` through the same spec | only opens if P4 says the clearest case holds | `python scripts/fit_design_c_prime.py --outcome mmr`, then `unemp` | **blocked by P4** |
| **P6** | Publish | new registry vintage, `counterfactual.json`, `tests/verify_counterfactual.py`, a what-if block on the site | verifier recomputes the placebo distribution from the artifact; site reads the artifact and types no number | `tests/verify_counterfactual.py` plus `tests/verify_site.py` | **blocked: requester decisions §9** |

---

## 3. Phase detail

### P0 — Declare

Writes `analysis/specs/design_c_prime.yml`. It borrows rather than retypes: the windows come from
`analysis/specs/design_c.yml` (which itself reads `diagnostics.yml → windows.candidate_treated_windows`),
the outcome list from `outcomes.yml`, the donor pool from `fact_donor_panel` by a rule. The one new object
is the estimator: nuclear-norm matrix completion, with SDID and gsynth as comparison arms on the same
window and donors.

May not: re-decide the seven-year pre-period floor, name a donor, or set a publication threshold after
seeing a gap.

### P1 — Extract

One read-only script. Nigeria's path comes from `fact_observation_native` at its native annual grain, never
from the interpolated monthly spine: the spine's `observation_type` column says which months are modelled,
and a counterfactual fitted to interpolated months is fitted to the interpolation rule. The exploratory
pilots under `.inspect/` used the spine's annual mean instead; the two agree to within 0.3 per 1,000 on
`u5mr` (checked 2005–2024), so the pilot's direction is not an artefact of that choice, but the declared
pass uses the native series anyway.

May not: fit, filter donors by outcome value, or write anything outside `.inspect/`.

### P2 — Fit and compare

Three estimators on the same window and the same 99-donor pool:

- **matrix completion** (Athey, Bayati, Doudchenko, Imbens, Khosravi 2021): nuclear-norm penalised, unit
  and year fixed effects, penalty chosen by cross-validation on the masked pre-period. This is the
  estimator the plan adopts because the 99-donor simplex is underdetermined at 8–24 pre-years.
- **SDID** (R `synthdid`, Arkhangelsky et al. 2021): requires a balanced panel over the window.
- **generalized SC** (R `gsynth`, Xu 2017): interactive fixed effects, cross-validated rank.

Every window gets all three or a stated refusal. The output of this phase is deliberately *not* a verdict:
it is the disagreement table that P3 then tries to explain.

### P3 — Inference

Placebos as declared: in space (each donor treated in turn, weights refitted from the rest) and in time
(the window backdated 3, 5 and 7 years where the pre-period still clears eight years). The interval is the
2.5th and 97.5th percentile of the placebo gap distribution, declared as randomization inference. The
donor jackknife reports how many leave-one-out fits flip the sign of the gap.

May not: substitute a model-based standard error, or report a p-value from a sampling distribution.

### P4 — Verdict and stop rule

The plan's own milestone, restated as a stop rule: *on `u5mr`, does matrix completion reproduce the
direction of Design C's published gap on the windows where the simplex and SDID disagreed, and does the
solver dependence that broke the simplex disappear?* If the clearest case says no, the workflow stops
before P5 and the plan is revised rather than extended.

This phase produces words, not an artifact. It is the phase most likely to be skipped by a future session
in a hurry, which is why the answer has to be written into `PROGRESS.md` before P5 opens.

### P5 — Extend

`mmr` (window-specific donor sets, `mmr` ends 2023) and `unemp` (96 complete donors) through the identical
spec. Blocked until P4's answer is written down.

### P6 — Publish

The only phase that writes `registry/`, and it writes a **new** vintage. It carries
`counterfactual.json` in the shape `counterfactual-recommendation.md` §7 declares, plus a verifier that
recomputes the placebo distribution, the percentiles, the stability flag and the counts from the artifact's
own stored fits. The site and the app read the artifact; no number is typed into a renderer.

Blocked on the five decisions in `counterfactual-recommendation.md` §9: placement, permission for a new
vintage, scope, the `cpi_yoy` reclassification, and the education refusal wording.

---

## 4. Status board

The board is updated by hand and only with evidence. Each row's evidence is the command that ran and the
line it printed; the full output lives in `PROGRESS.md`.

| Phase | Closed on | Evidence |
|---|---|---|
| P0 | 2026-11-04 | `design_c_prime.yml` parses; windows read from `design_c.yml` back to `diagnostics.yml`; gate fixed before any fit |
| P1 | 2026-11-04 | 26 native Nigeria years, 2,574 donor rows across 99 countries, 99 complete donors on every runnable window; all 5 windows match the frozen artifact's years |
| P2 | 2026-11-04 | 4 windows fitted; matrix completion and SDID on all four, gsynth refused on all four with its measured reason; solver spread 1e-5 or smaller on every fit |
| P3 | 2026-11-04 | 99 in-space placebos per window; rank p 0.43 / 0.79 / 0.70 / 0.28; in-time placebos run where the pre-period allows (1, 3, 3) and refused with the count where it does not (3, 2, 1) |
| P4 | 2026-11-04 | **stop rule fails**: every gap sits inside its placebo distribution, so no window clears the declared gate and P5 does not open |
| P5 | — | blocked by P4: not opened |
| P6 | — | blocked: there is no stable what-if to publish, and the five requester decisions are unanswered |

---

## 5. How a status changes

1. Run the phase's acceptance command. Paste its real output into `PROGRESS.md` under a dated entry.
2. Update one row of the status board, and the evidence cell, to point at that entry.
3. Do not mark a phase done because the code exists. P0 through P2 already exist as files; a phase closes
   when its command runs and its number reconciles.

A reviewer who cannot find the pasted output may treat the phase as open, whatever the table says.
