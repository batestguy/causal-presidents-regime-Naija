# Stage 8h - Design C, synthetic control on u5mr - vintage 2026-10-18

Generated 2026-10-28T06:48:23+0100 by `analysis/R/11_design_c.R`. Spec `analysis/specs/design_c.yml` (md5 1e22f952b9f22dd753f70bc0b0cd82be), declared 2026-10-28, before any weight was fitted.

**This is not the effect of a president.** It is the gap between Nigeria's path and a simplex-weighted
combination of other countries' paths after a transition, published with the placebos that decide whether
the gap is distinguishable from what the same method produces where no transition happened.

| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |
|---|---|---|---|---|---|---|
| obasanjo | - | - | - | - | - | refused (gate_window_not_runnable) |
| yaradua | 2007-2009 | 2.11 | -2.60 | 97.27 | 0.5000 | **estimated_not_identified** |
| jonathan | 2010-2014 | -11.56 | -0.37 | 991.48 | 0.3200 | **estimated_not_identified** |
| buhari | 2015-2022 | 8.59 | 9.38 | 116.20 | 0.1700 | **estimated_not_identified** |
| tinubu | 2023-2024 | 18.53 | 18.50 | 4.37 | 0.3300 | **estimated_not_identified** |

The mean gap is in deaths per 1,000 live births; a negative number means Nigeria sat below the synthetic
counterfactual. The p-value is a rank among placebos, not a sampling distribution, and with 100 units the
smallest attainable value is 0.01.

**The two gap columns are the same problem solved twice.** With 99 donors and 8 to 24 pre-years the declared
simplex problem is underdetermined: a face of weight vectors fits the pre-period equally well and they do not
agree about the post-period. The first column is the vertex the declared QP returns; the second is the unique
ridge refit. Where the two disagree in sign the estimate is a property of the solver, not of the data, and the
artifact says so instead of publishing one of them.

- windows estimated: 4; refused: 1
- identified: 0; estimated but not identified: 4
- in-space placebos fitted: 396; in-time placebos fitted: 7; leave-one-donor-out fits: 396
- placebos whose own pre-fit also clears the 0.10 gate: 304 of 396 - the gate does not discriminate on this pool

## What this does not claim

- This is not the effect of a president. It is the gap between Nigeria's path and a weighted combination of other countries' paths after a transition.
- The counterfactual is not observed. A low pre-fit ratio shows the donors can reproduce the pre-period, not that they would have reproduced the post-period without the transition.
- The donor pool is countries, not Nigerian states: it cannot hold constant anything Nigeria-specific — the oil cycle, the naira, the security environment.
- The windows overlap in their pre-periods and are not additive: a later window's counterfactual already contains the earlier tenures.
- The pre-fit gate does not discriminate on this pool: 99 donors and 8 to 16 pre-years make the fit underdetermined, so the placebos carry the verdict.

## What it refuses to carry

- no standard error, confidence interval or p-value other than the rank p — a synthetic control has no sampling distribution
- no significance claim from the pre-fit ratio alone; the ratio is a fit diagnostic, and with 99 donors it is interpolation
- no per-president wording: windows are keyed by tenure id, and the artifact prints no surname

