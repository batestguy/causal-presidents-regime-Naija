# Causal discovery: readiness

**Status: preparation, not a result.** The registry is frozen at vintage 2026-11-01; nothing in this note
changes it. This page records what a discovery pass could run on, what it could not, and the tooling that is
now installed. No discovery edge is published anywhere on the site.

## What discovery can and cannot do here

Causal discovery (PC, GES, FCI, LiNGAM, PCMCI) proposes a graph from the joint distribution of observed
series. It **generates hypotheses**; it does not identify effects. The site's rule stands: a card number needs
a declared design, its assumption, and a check that can fail. A discovery edge would enter the registry as a
new artifact family, linked from the methodology page, never as a card number and never as a causal verb.

Two properties of this data bound the exercise:

- **Sample size.** Most catalogue series are annual: 27 native points inside the study window, 66 if you
  extend to 1960 (the World Bank series start there). Even 66 annual points is below every established
  discovery sample-size floor once more than a handful of variables and lags are involved.
- **Fill versus record.** Twenty of the twenty-three national series are monthly *interpolations* of annual
  values (`fact_metric.observation_type = 'interpolated'`). A discovery algorithm run on those months would
  recover the fill rule, not the economy. They are excluded.

**Per-outcome verdict.** Only **fatalities** and **incidents** have native monthly outcome series (UCDP,
1990-09 onward; 343 national months, 37 units by 424 state-months). The other ten catalogue outcomes are
annual. Inflation is the near-exception: the catalogue series is annual, but an NBS monthly CPI source exists
(`nbs_cpi_national_monthly`, 358 months) and can serve as a monthly covariate. Discovery is therefore a
two-outcome exercise, not a twelve-outcome one; running it on the annual ten would mine the smoother.

## What the data can support

**Native monthly, national (recommended first target).** Four genuinely monthly sources overlap:

| source | table | rows | window |
|---|---|---|---|
| Brent crude (monthly) | `fact_metric` (`oil`) | 334 | 1999-01 to 2026-10 |
| NBS CPI (monthly) | `nbs_cpi_national_monthly` | 358 | full study window |
| FAAC national allocation (monthly) | `faac_national_monthly` | 114 | 2016-12 on |
| UCDP conflict (monthly) | `ucdp_national_monthly` | 343 | 1999 on |

Common complete window after differencing: **94 months, 2016-12 to 2024-10**, five usable variables
(`oil_ret`, `cpi_yoy`, `faac_growth`, `fatalities`, `incidents`). Five variables and 94 rows is a small but
runnable time-series graph with lags.

**Native monthly, state panel (second target).** `state_panel` holds 12,358 state-months of FAAC allocation
and UCDP security outcomes for 36 units from 2016-12. Per-state series run about 107 months; a pooled run
would ignore state heterogeneity, so the declared design should run PCMCI **per state** and report edge
stability across states (how many of 36 states show the edge) rather than one pooled graph. Two caveats:
`state_panel.d1_faac_per_capita` is empty for every row (the dose gate did not pass), so FAAC discovery at
state level must join `faac_state_allocation` (4,104 state-months, 2016-12 onward); and the security
outcomes alone run from 1990-09 in `ucdp_state_month` (37 units by 424 months) if the window is widened.

**Not discovery-grade.** The annual series (education, health spending, ODA, oil rents, population, GDP per
capita, unemployment) have 27 native points; they stay inside the existing declared designs.

## Toolchain

Installed in the verified interpreter (`ds-general`, Python 3.12):

- **causal-learn 0.1.4.8** — PC, GES, FCI, LiNGAM (cross-sectional and pooled graphs).
- **tigramite 5.2.10.1** — PCMCI / PCMCI+ for lagged time series, the appropriate method for both targets.
- Already present and used by the project: `dagitty` (R) for graph adjustment sets, `statsmodels`, `scipy`.

## Smoke test (pipeline check only)

Ran PCMCI (ParCorr, `tau_max=3`, `alpha=0.05`, `pc_alpha=0.05`) on the 93 differenced national months.
Fifteen links cleared the threshold, of which most are own-series autocorrelation, one is the mechanical
co-movement of fatalities and incidents, and the cross-links (for example `faac_growth(t-2) → fatalities`,
coef −0.219, p = 0.044) sit at the edge of significance on 93 rows. **This establishes that the toolchain
runs and that the sample is thin; it establishes nothing about Nigeria.**

## What a declared pass should fix in advance

1. **Variables and window**: the five native monthly variables, 2016-12 to 2024-10, differenced as above;
   or the per-state panel for FAAC and security.
2. **Method and parameters**: PCMCI with ParCorr, `tau_max = 3`, `pc_alpha = 0.05`, FDR (Benjamini-Hochberg)
   at q = 0.10 across all tested links.
3. **Stability**: block bootstrap (200 draws, block length 6) and keep a link only when it appears in at
   least 80 % of draws and clears p < 0.01 in at least 80 % of them. Unstable links are reported as absent.
4. **Panel rule**: per state, min 60 months; a panel edge is reported with its state count, never pooled into
   one graph.
5. **What counts as publishable**: an artifact with the edge list, the bootstrap frequencies, the parameters
   and the sample; a verifier that recomputes the stability from the artifact with a second implementation.
6. **What is never publishable**: a discovery edge as a card number, a per-president claim, or a causal verb.

## Execution

The smoke script lives outside the tracked tree (`.inspect/discovery_smoke.py`) until a discovery spec is
declared in `analysis/specs/`. Nothing else changes until then.
