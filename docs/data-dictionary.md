# Data dictionary — the analytical base

PHASES.md Stage 4 exit criterion: *"A single analytical base table, every column documented, reproducible
from `vintage_date` + anchor config alone."* This is that documentation. It also closes the Stage 0 gap
(base spec §16 asks for a data dictionary; this project had not written one).

Built from the raw layer plus `analysis/specs/` by dbt, into a local DuckDB file:

```bash
conda run -p "C:/Users/TOSHIBA/ds-general" dbt build --project-dir dbt --profiles-dir dbt
conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_harmonisation.py   # independent check
```

**Nothing here is a source of truth.** The sources are `data/raw/` (bytes as received) and the specs in
`analysis/specs/`. This base is a reproducible function of those two, which is why the DuckDB file is
gitignored and `tests/verify_harmonisation.py` recomputes it from scratch.

---

## Grains at a glance

Vintages `2026-10-11` (`worldbank`, `worldbank_donors`, `fred`) and `2026-10-16-correction` (`faac`) — one
per source, chosen by `stg_raw_manifest`; spine `1999-01 → 2026-10` (334 months, floor from
`quality.yml study_window`).

| Table | Grain | Rows | Where it comes from |
|---|---|---|---|
| `fact_metric` | metric × month | 7,682 | **The analytical base.** 23 metrics × 334 months |
| `metric_anchor` | metric | 23 | One index-anchor row per metric |
| `dim_metric` | metric | 25 | 12 catalogue outcomes + 13 landed covariates (FAAC is deliberately not among them — it is a gated state panel with no declared national aggregation) |
| `dim_administration` | administration | 5 | Base spec §7 [LOCKED] |
| `dim_administration_term` | term | 7 | Derived: 4-year terms, the exposure models use |
| `dim_shock` | shock band | 3 | Base spec §8 |
| `dim_state` | state-level unit | 37 | 36 states + FCT |
| `dim_definition_break` | metric × break date | 8 | Stage 3 report, definition-drift gate (national series only) |
| `fact_observation_native` | metric × native period | 1,926 | Audit trail: 1,340 valued observations plus their empty periods |
| `int_metric_monthly` | metric × month | 7,682 | The spine before the index is attached |
| `fact_donor_panel` | country × metric × year | 3,866 | Design C donor pool, 13 countries |
| `state_panel` | state × month | 12,358 | 37 × 334, FAAC nominal dose populated, the rest empty by declaration |
| `faac_state_allocation` | state × month | 4,104 | The FAAC dose: 114 months × 36 states, one publisher chosen per row |
| `faac_national_monthly` | month | 114 | The same dose aggregated to the fiscal transfer channel as a national series |

Staging views mirror the raw payloads one-for-one (`stg_raw_manifest`, `stg_raw_payload`,
`stg_worldbank_observation`, `stg_fred_daily`, `stg_fred_monthly`, `stg_donor_observation`,
`stg_quality_series` — 125 rows, 37 of them the FAAC dose, gated from the parsed artifact rather than from
a payload), plus `stg_faac_allocation`, which types the CSV a Stage 2 parser wrote from the
PDF and XLSX payloads — a document source is parsed in Python and landed as a staging table rather than
made to look like a JSON payload.

---

## `fact_metric` — the base table

One row per (metric, month). Nothing is computed at render time (base spec §18 [LOCKED]).

| Column | Type | Meaning |
|---|---|---|
| `metric_id` | VARCHAR | Metric key, joins `dim_metric` |
| `period_month` | DATE | First day of the month. Spine floor 1999-01, ceiling = last observed month (2026-10) |
| `value` | DOUBLE | The value. NULL exactly when `observation_type = 'unobserved'` |
| `value_indexed` | DOUBLE | `value / anchor_value × 100`, anchor in `metric_anchor` (base spec §8). NULL exactly where `value` is NULL |
| `observation_type` | VARCHAR | `observed` · `interpolated` · `unobserved` — see *Imputation* below |
| `native_frequency` | VARCHAR | The grain the value actually arrived at: `annual` (World Bank) or `monthly` (Brent) |
| `source` | VARCHAR | `worldbank` or `fred` |
| `vintage` | VARCHAR | The raw vintage this value came from (2026-10-11). Only ever one per source |
| `term_id` | INTEGER | Term key, joins `dim_administration_term`. NULL for the 5 months before the first inauguration |
| `admin_id` | INTEGER | Administration key, joins `dim_administration` |
| `term_ordinal` | INTEGER | 1 or 2 — the president's term in office |
| `president` | VARCHAR | Denormalised for convenience; `dim_administration_term` is authoritative |
| `party` | VARCHAR | `PDP` or `APC` |
| `tenure_stratum` | VARCHAR | `PDP_first` · `PDP_second` · `APC_first` · `APC_second` (base spec §9 [LOCKED]) |
| `pdp_first` … `apc_second` | BOOLEAN | The four strata as dummies, for models that want columns rather than a name. Exactly one is true per assigned month |
| `is_unassigned_month` | BOOLEAN | True only for 1999-01 … 1999-05: inside the spine's floor, before the first administration's span |
| `is_transition_month` | BOOLEAN | The month contains a term boundary (7 such months). Assigned to the **outgoing** term — see *Month assignment* |

### Month assignment

A month belongs to the term containing its **first day**. An inauguration on 29 May means May's first day
still falls under the outgoing administration, so the transition month goes to the outgoing term and is
flagged `is_transition_month`. Without the flag, a Tier-2 inherited-conditions view or a robustness axis
would have to reconstruct the boundary dates itself.

### Why the spine is only 10.1 % observed

775 of 7,682 rows are direct observations; 4,389 are interpolated and 2,518 are empty. That ratio is the
honest consequence of a monthly spine over annual sources, and it is the most consequential number in
this stage: **a monthly model on `cpi_yoy` cannot see the 2023-06→2023-12 subsidy window**, because the
landed CPI series is annual and that window contains two observations. `dim_metric.frequency_gap` flags
exactly this (see below). Stage 5 owns the decision that follows.

---

## `metric_anchor`

| Column | Meaning |
|---|---|
| `metric_id` | Metric key |
| `anchor_period` | The month indexed to 100 |
| `anchor_value` | The value at that month; the divisor |
| `anchor_rule` | `fixed_2000_01` (16 metrics) or `first_available_after_2000_01` (7 metrics) |
| `formula` | Literal text of the formula, so the arithmetic is not folklore |
| `native_frequency` | As in `fact_metric` |
| `first_observed_month`, `last_observed_month` | The span the base may never exceed — the boundary `fact_metric_never_extrapolates` tests |
| `n_observed_months`, `n_interpolated_months`, `n_unobserved_months`, `n_spine_months` | Recomputed by the verifier |
| `vintage` | Raw vintage |
| `spec_path` | `analysis/specs/harmonisation.yml` — the declared rules this row implements |

The fallback rule exists because a series that begins after January 2000 has no value at the fixed anchor.
Rebasing it to its own first observation *without saying so* is exactly the kind of quiet lie the honesty
layer exists to prevent, so `anchor_rule` names the case and the verifier recomputes it.

---

## `dim_metric`

| Column | Meaning |
|---|---|
| `metric_id`, `label`, `short_label` | Identity. `label`/`short_label` validated against `outcomes.yml` for all 12 outcomes |
| `unit` | **Mandatory** (base spec §6). Unit strings are also cross-checked against `quality.yml`'s percentage-point series list |
| `direction` | **Mandatory**, never inferred at render: `up` · `down` · `none`. `none` means a denominator or a price (`population`, `fx`, `oil`) — not better either way |
| `domain` | `health` · `education` · `security` · `economy` · `context` |
| `is_outcome` | Whether it is one of the 12 catalogue outcomes |
| `coverage_status` | For outcomes: `ok` · `partial` · `declared_gap` · `blocked`, from `outcomes.yml` |
| `catalogue_frequency` | What the metric is *supposed* to be (base spec §6: CPI monthly, GDP quarterly) |
| `native_frequency` | What the landed series actually is (Stage 3's gate result: annual) |
| `frequency_gap` | True where those differ — 3 metrics: `cpi_yoy`, `gdp_growth`, `unemp` |
| `source_label`, `source_dataset_id` | Source name and dataset id |
| `note` | The caveat a reader needs (sparsity, contamination, blocking) |
| `is_landed` | Derived from the native observations, not from the catalogue: `fatalities`/`incidents` are present with `is_landed = false` and `blocked` |
| `n_native_observations`, `first_native_period`, `last_native_period` | Observed counts at the native grain |
| `quality_status` | `ok` · `flagged` · `empty` from the Stage 3 report; **verified to match the report exactly** |
| `quality_vintage`, `n_observed_in_window`, `first_observed_label`, `last_observed_label`, `max_gap_months`, `gap_tripped`, `n_spikes` | Carried gate results |
| `anchor_period`, `anchor_rule` | Denormalised from `metric_anchor` |

---

## `dim_administration` and `dim_administration_term`

`dim_administration` is the base spec §7 table unchanged — five rows, one per president, including the two
rows that cover two terms. `end_date_effective` is the **half-open** span bound: four boundaries have
`end_date` equal to the next `start_date`, one has a one-day gap (Yar'Adua 2010-05-05, Jonathan sworn
2010-05-06 — the decided boundary), so closed intervals would overlap four times and leave a one-day hole
once. `oil_price_on_start_date` (daily, may be NULL on a holiday) and `oil_price_at_start_month_mean`
(the frozen resampling rule) are both exposed, because base spec §7 says "Brent crude" without choosing.

`dim_administration_term` splits that into **7 terms** carrying the four strata. **"First/second term" is
the president's own term in office** (decision M-11): the alternative reading would leave 2007-2015 outside
all four strata. Term boundaries are four years from a 29 May inauguration.

| Column | Meaning |
|---|---|
| `term_id`, `admin_id`, `term_ordinal` | Keys |
| `president`, `party` | Denormalised |
| `term_start`, `term_end` | Half-open span |
| `is_open_ended` | True for the incumbent's term |
| `tenure_stratum` | `party` + `_first`/`_second` |
| `term_start_month`, `term_end_month` | Month bounds used by `fact_metric`'s assignment join |
| `oil_price_on_term_start_date`, `oil_price_at_term_start_month_mean` | The term's **own** start price (May 2003 ≈ $26 for Obasanjo II, not the 1999 price) |

---

## Dimension tables

| Table | Columns | Notes |
|---|---|---|
| `dim_shock` | `shock_id`, `label`, `start_date`, `end_date`, `start_month`, `end_month`, `n_months`, `note` | Base spec §8 bands: 2014-06→2016-12 (31m), 2020-03→2020-12 (10m), 2023-06→2023-12 (7m). Machine-readable month bounds so Stage 5 can test whether the windows are *visible in the data* rather than assumed |
| `dim_state` | `state_id`, `state_name`, `zone` | 37 units; `zone` is the six-zone classification (NC/NE/NW/SE/SS/SW) |
| `dim_definition_break` | `metric_id`, `source`, `break_date`, `break_month`, `label`, `note`, `declared_in_vintage` | 8 breaks: 2014 GDP rebasing (×2), 2016 float, 2023 unification, 2014 and 2023 unemployment methodology, the 2020 WTI episode carried on Brent, and the January-2025 CPI rebasing. National series only — the donor panel's rows for the same indicators would be 13 identical duplicates of each |

---

## `fact_donor_panel` and `state_panel`

`fact_donor_panel` — country × metric × year for Design C: 13 countries × 5 screening predictors × 66
years (1960–2025) = 4,290 extracted rows, 3,866 with a value. Kept off the national spine deliberately: it shares metric ids with the
national series, so mixing them would put thirteen countries' outcomes on Nigeria's chart.
`is_treated_unit` is a guard that must always be false — the treated unit's path comes from the national
series, and a treated unit inside its own donor pool would estimate a counterfactual from itself.

`state_panel` — the complete 37 × 334 grid. The FAAC nominal dose is populated where a publisher covers
the month; `d1_faac_per_capita`, `d2_faac_share_of_state_revenue`, `population_denominator`, `fatalities`
and `incidents` are **typed and empty**, each with its reason in `dose_note`. `dose_status` is per row —
`observed` (a FAAC document covers it) · `not_covered` (inside the publishers' span, no document) ·
`declared_gap` (before either publisher, or the FCT) — and a dbt test fails in both directions if the
status and the dose value disagree. The dose is **gated**: `dose_gate_status` is that state's own Stage 3
result (`flagged` for all 36 states — the dose spikes by more than 50 % in a month nine or ten times per
state, mostly at all 36 states at once, which is a movement of the distribution and not a per-state
extraction error). A second dbt test fails if `dose_gated` and `dose_gate_status` disagree, or if the FCT
is ever reported as gated.

| Column | Meaning |
|---|---|
| `faac_gross_total_naira` | The dose: statutory allocation + 13% derivation, nominal naira, at the month the revenue accrued |
| `faac_share_of_state_pool` | The state's share of the **36 states'** pool that month (not of the whole Federation Account — see below) |
| `faac_publisher` | `oagf` (primary) or `nbs` (fallback), from `faac_state_allocation` |
| `faac_is_cross_checked`, `faac_cross_check_rel_diff` | Whether the other publication carries the same state-month, and how far apart they are |
| `faac_source_file` | The payload the row came from |
| `dose_gated`, `dose_gate_status`, `dose_gate_vintage` | The Stage 3 result for **that state's** FAAC series, read from the quality report rather than set by hand. `true`/`flagged` for the 36 states, `false` for the FCT (no series of its own), with the report vintage that produced it |
| `d1_faac_per_capita` | Empty: the numerator is present, the denominator is an unmade decision (X-09) |
| `d2_faac_share_of_state_revenue` | Empty: needs the NBS state IGR series |

---

## `faac_state_allocation` — the fiscal dose

The exposure Family A's estimand is written on, and the reason the state panel exists. Built by
`ingestion/parsers/faac_disbursement.py` (174 documents, 2016-12 → 2026-06) and
`dbt/models/analytics/faac_state_allocation.sql`.

| Column | Meaning |
|---|---|
| `state_id`, `state_name`, `period_month` | The dose's key. 36 states — Table III distributes among 36 beneficiaries, so the FCT has no dose |
| `publisher` | Which publication supplied this row: `oagf` (primary) or `nbs` (fallback). Never silent |
| `gross_total` | **The dose.** Statutory allocation + the 13% derivation share. The only per-state figure all 174 documents publish in the same place under the same name |
| `gross_statutory_allocation`, `derivation_13pct`, `net_statutory_allocation`, `gross_vat_allocation`, `emtl`, `exchange_gain`, `n_lgcs` | Components, where the layout resolves them. **Absent means not resolved, not zero** — see the item-set caveat below |
| `total_gross_amount`, `total_net_amount` | The wider share (adds VAT, EMTL, ecology, augmentation) where a document carries it — the robustness axis, not the dose |
| `month_state_pool`, `n_beneficiaries` | The month's 36-state total and the count that made it, so an aggregate is auditable |
| `share_of_state_pool` | `gross_total / month_state_pool`. A share of the states' pool, **not** of the Federation Account: the FGN, FCT and 774 LGCs are distributed by tables this parser does not read |
| `is_cross_checked`, `other_publisher`, `other_gross_total`, `cross_check_rel_diff` | The independent publication's figure for the same state-month and how far apart they are |
| `source_dataset_id`, `source_file`, `source_sha256`, `source_location` | The payload, its hash, and where in it the table was found (`page-0002`, `sheet:SG Details`) |

**Cross-publisher agreement (checked, not assumed):** 2,124 of 2,160 overlapping state-months (98.3%)
agree to within a naira, and 59 of the 60 overlapping months agree at every state. The exception is
2023-04, where the NBS workbook reports ~1.83× the OAGF allocation at every state while both documents
reconcile to their own Total rows — so the dose's *level* is publisher-dependent for that month, which is
why `publisher` is a column and the choice is a robustness axis (`docs/decisions.md` C-39).

**Item-set caveat:** the table is long rather than wide so a missing item reads as "not carried". That is
bounded by a measured limit — 541 header cells across the 174 documents do not resolve and are enumerated
in `data/staging/faac_parse_report.json` — so for those cells a missing item means *not resolved*. The dose
is not among them: `gross_total` resolves in every document. `docs/decisions.md` C-40.

---

## `faac_national_monthly`

The dose summed over the 36 states, per month — the fiscal transfer channel on a national spine.
`gross_total_naira`, `n_beneficiaries`, `n_beneficiaries_from_primary`, `n_beneficiaries_cross_checked`,
`max_cross_check_rel_diff`, `n_beneficiaries_with_lgc_count`.

It is **not** in `dim_metric`, and deliberately — but the reason has changed. This series *is* now gated:
it is the `national` scope of the FAAC gate, one of the 37 rows added to the Stage 3 report on 2026-10-17.
What it still lacks is a **catalogue entry**, which needs a declared monthly-to-annual aggregation and an
outcome decision for a series that begins 2016-12 — so the Tier-3 blocker moves from "FAAC is absent
from the catalogue" to "FAAC is gated but 10 years long at the annual grain the outcomes are on" (S4-17
as narrowed by S4-19), which is a different blocker rather than the removal of one.

---

## Imputation, and how to tell it apart from data

`analysis/specs/harmonisation.yml` declares every alignment rule; this table is the implementation.

| Rule | Value |
|---|---|
| Annual value anchor | **July** — the midpoint of the period it describes. Not January, not December |
| Monthly value anchor | The first of the month |
| Interpolation | Linear, **only** between two observations exactly one step apart (12 months) |
| Across a gap | **Refused.** `adult_literacy`'s 108-month hole stays a hole: 9 years of drawn-through values would look exactly like observed data |
| Extrapolation | **Forbidden.** Nothing before the first or after the last observation |
| Quarterly | Declared (`mid-quarter month`), **not yet used** — no quarterly series is landed |

`observation_type` is what makes this usable downstream: the app draws `interpolated` dashed, and Stage 7
excludes it on a robustness axis. A dbt test fails if any interpolated month sits more than twelve months
from a real observation, which is how "no interpolation across a gap" is enforced rather than asserted.

## Vintage and provenance conventions

- Every fact and dimension row carries the raw `vintage` it came from. Only the latest vintage per source
  is read (`stg_raw_manifest` is the single place that decides), so `worldbank/2026-10-10` — retained on
  disk for revision detection — cannot leak into the base. A dbt test fails if it ever does.
- `vintage_date` = ingest date; corrections create a **new vintage**, never an edit (X-07).
- The Stage 3 report vintage travels as `quality_vintage`, and the verifier fails if a carried
  `quality_status` disagrees with the report it claims to come from.
- `declared_in_vintage` on `dim_definition_break` names the report the annotation came from.

## Declared gaps (nothing here is silently missing)

| Gap | Affects | Needs |
|---|---|---|
| FAAC per capita (D1) | Family A's per-capita specification, `state_panel.d1_faac_per_capita` | A decided state population denominator (X-09). **The nominal dose is now landed** — `faac_gross_total_naira` — so this is a decision, not an acquisition |
| FAAC before 2016-12 | Any pre-APC dose, and the annual-grain length of the Tier-3 system | A monthly FAAC archive reaching 1999. Neither publisher's online archive does (OAGF 2019-04, NBS 2016-12), so this is a property of the sources |
| A metric-catalogue entry for FAAC | Putting FAAC into `dim_metric` and the Tier-3 system | A declared monthly-to-annual aggregation and the national series' outcome decision. **The Stage 3 gate is no longer part of this** — the dose is gated (37 series, `flagged`); the remaining question is what the series *is* on a national spine, not whether it has been checked (S4-19) |
| FAAC share of revenue (D2) | Family A's secondary dose | The NBS quarterly state IGR series |
| A state population denominator | Any per-capita dose | A decision, not data (X-09) — NBS projections and World Bank population diverge |
| `fatalities`, `incidents` | The security domain, every design | A free UCDP token or an ACLED OAuth app |
| Education outcomes 2015+ | The education domain, every design | No open source reaches the APC tenures (C-07, C-11, C-12) |

Each is also recorded in `analysis/specs/harmonisation.yml` → `declared_gaps`, and the seed's
`coverage_status` carries the status that reaches the app.
