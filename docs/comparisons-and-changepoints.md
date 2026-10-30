# The two descriptive artifacts — field by field

**Purpose.** This page is what `analysis/R/08_comparisons.R`, `analysis/R/09_changepoints.R` and their two
verifiers are written against. If a field is not here, it does not exist; if an invariant is here, the verifier
must fail on it.

Companions: `registry/schema/comparisons.schema.json`, `registry/schema/changepoints.schema.json`,
`presidents-guided-flow-spec.md` (§6.2, §6.3), `analysis/specs/comparisons.yml` and
`analysis/specs/changepoints.yml` — both written on 2026-10-25, before any number was fitted.

---

## 1. Why two artifacts and not one

They answer different questions and carry different honesty contracts:

| | `registry/comparisons/` | `registry/changepoints/` |
|---|---|---|
| Question | *How do groups differ, on average?* | *When does this series change?* |
| Grain | group series over the window | breaks in one series |
| Statistical content | **none** — group means only | **none** — break dates only |
| Failure mode it guards | a group mean read as a causal effect | a break read as a president's effect, or a break found in interpolated data |
| Verifier | `tests/verify_comparisons.py` | `tests/verify_changepoints.py` |

Neither artifact may contain a test statistic, a p-value, a standard error, a confidence interval (including a
break-date interval), a t-statistic or a verdict. Those belong to `registry/estimates/` and are subject to the
Stage 6 verdict rule. A descriptive artifact that grows one of those fields becomes an estimate with none of an
estimate's checks.

---

## 2. The common envelope

Both artifacts share this shape. The schema enforces every field listed here.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string `x.y.z` | starts at `0.1.0` |
| `stage` | string | e.g. `"9-prep"` |
| `layer` | string | one sentence: what the file is for |
| `vintage` | string `YYYY-MM-DD` | **must equal** `registry/dags/index.json`'s `vintage_date`; a mismatch is a build failure, not a warning |
| `generated_at` | string | ISO 8601 with offset, as the other artifacts write it |
| `generator.script` | string const | the schema pins it, so a file cannot claim another engine wrote it |
| `generator.git_sha` | string \| null | `git rev-parse --short HEAD`; null only in a dirty tree, and then the run says so |
| `spec.path` / `spec.md5` / `spec.version` | string / md5 / int | md5 of the declared spec **as run**; the verifier recomputes it and fails if the spec changed after the fit |
| `verifier` | string const | the schema pins the verifier's path |
| `input` | object | the database and tables read, by name — so the artifact names what produced it |
| `counts` | object | every count the narrative or the page quotes, computed, never typed |
| `rules` | object | the declared rules that were applied, copied from the spec |
| `notes` | array of string | the caveats a reader of the JSON should know |

**Invariant E-1.** `vintage` equals the registry index's. **E-2.** `spec.md5` equals the md5 of the spec on disk.
**E-3.** Every numeric count in `counts` equals the length of the array it describes.

---

## 3. `registry/comparisons/<vintage>/comparisons.json`

### 3.1 `counts`

| Field | Meaning | Invariant |
|---|---|---|
| `outcomes` | outcomes carried, including refused ones | equals `len(outcomes)` |
| `groupings` | groupings declared | equals `len(groupings)` |
| `charts` | figures written | equals the number of non-refused outcomes |
| `groups_total` | group objects across all outcomes | equals the sum of `len(outcome.groups)` |
| `outcomes_refused` | outcomes with `refused != null` | equals the count |

### 3.2 `rules`

| Field | Content |
|---|---|
| `group_mean` | the exact rule, in words — e.g. *"the unweighted mean of the group's observed months over the declared window; interpolated months are excluded from the mean and marked in the series"* |
| `grain` | the grain of the declared window (`national-month`, `state-month`, …) |
| `forbidden_fields` | the list the verifier greps for: `p_value`, `standard_error`, `ci_low`, `ci_high`, `t_stat`, `verdict`, `stars` |
| `min_units_per_group` | smallest group the artifact may publish |
| `declared_gap_rule` | what a month with no data is (never a zero) |

### 3.3 `groupings[]`

| Field | Type | Notes |
|---|---|---|
| `id` | string | `party_tenure`, `state_dose_quartile` |
| `plain` | string | how the flow names it — *"by who was in power"*. Lives in `guide.yml`, copied here for the artifact to be self-describing |
| `technical` | string | *"party × tenure stratum"* |
| `group_kind` | enum | `party_tenure` \| `state_dose_quartile` \| `donor_pool` |
| `grain` | enum | as above |
| `window.first` / `window.last` | `YYYY-MM` | the window over which the mean is taken |
| `n_groups` | int | equals `len(groups)` of every outcome that carries this grouping |
| `source_note` | string | where the grouping comes from — for the dose quartiles: the metric id and the months the dose exists |

### 3.4 `outcomes[]`

| Field | Type | Rule |
|---|---|---|
| `id`, `label`, `short`, `domain`, `unit`, `direction`, `native_frequency`, `quality_status` | as in the series index | read from `outcomes.yml` + `dim_metric`, not retyped |
| `window` | `{first,last}` | the study window: `1999-01` → `2026-10` |
| `observed.native_in_window` | int | count of rows in `fact_observation_native` for the metric inside the window — **the number that decides whether a series can be described at all** |
| `observed.observed_months` / `interpolated_months` / `unobserved_months` | int | from `fact_metric`, same definition as the series index; the three must sum to the window's month count |
| `definition_breaks[]` | `{date, name, note}` | from `dim_definition_break`; every chart marks these |
| `closest_evidence` | `{kind, artifact, outcome_id?, plain}` | the per-outcome mapping (A-03): `design_result` for economy outcomes, `event_study` for security, `series_panel` otherwise |
| `groups[]` | see 3.5 | empty only when `refused != null` |
| `caption` | string | assembled from the fields above, so it cannot disagree with them |
| `figure` | `{path, bytes}` | one SVG per outcome covering every grouping; `bytes` compared to disk. Every panel also draws the **tenancy bands** — one light band per administration, its president named in the headroom above the data, from `dim_administration`'s half-open spans (`figures.tenure_bands` in the spec) |
| `refused` | null \| `{reason, detail}` | closed set: `no_monthly_life`, `too_few_native_observations`, `declared_gap`, `no_grouping_declared` |

### 3.5 `outcomes[].groups[]`

| Field | Type | Rule |
|---|---|---|
| `grouping_id` | string | must exist in `groupings[]` |
| `group_id` | string | e.g. `PDP_first`, `state_dose_q1` |
| `plain` / `technical` | string | *"states that received the most"* / *"FAAC dose quartile 4"* |
| `n_units` | int | states, or 1 for a national grouping; must be ≥ `rules.min_units_per_group` |
| `months` | int | months the group series covers |
| `group_mean` | number \| null | computed by `rules.group_mean`; null only when the group has no observed month |
| `group_mean_native_only` | number \| null | the same mean over native observations only — published beside the first because a mean over interpolated months is a mean over a rule, and a reader is entitled to see both |
| `series[]` | `{month, value, observed}` | one row per month in the window; `observed` is the mark the chart uses (solid point vs dotted segment); `value` null only when unobserved and not interpolated |
| `caption` | string | assembled from the fields, never typed |

**Invariant C-1.** `series` length equals the window's month count.
**C-2.** `groups[].n_units` sums, per grouping, to the grouping's declared universe (37 state units, or 1 per national group).
**C-3.** No field named in `rules.forbidden_fields` appears anywhere in the file.
**C-4.** `group_mean_native_only` is computed from rows where `observed == true`; the verifier recomputes both means from DuckDB and compares to 1e-9.
**C-5.** A group with `group_mean == null` must have no `observed` month.

### 3.6 Minimal example

```json
{
  "schema_version": "0.1.0",
  "vintage": "2026-10-18",
  "generator": { "script": "analysis/R/08_comparisons.R", "git_sha": "abc1234" },
  "counts": { "outcomes": 12, "groupings": 2, "charts": 12, "groups_total": 28, "outcomes_refused": 0 },
  "rules": {
    "group_mean": "unweighted mean of observed months in the group over the window; interpolated months excluded and marked",
    "grain": "national-month",
    "forbidden_fields": ["p_value", "standard_error", "ci_low", "ci_high", "t_stat", "verdict", "stars"],
    "min_units_per_group": 3,
    "declared_gap_rule": "a month with no observation is a gap, never a zero"
  },
  "outcomes": [{
    "id": "fatalities",
    "groups": [{
      "grouping_id": "party_tenure", "group_id": "APC_first",
      "plain": "the first APC term", "technical": "APC_first",
      "n_units": 1, "months": 48,
      "group_mean": 1234.5, "group_mean_native_only": 1234.5,
      "series": [{ "month": "2015-06", "value": 900.0, "observed": true }],
      "caption": "48 months under the first APC term; 48 with an observation; mean 1,234.5 reported fatalities a month."
    }]
  }]
}
```

---

## 4. `registry/changepoints/<vintage>/changepoints.json`

### 4.1 `counts`

`outcomes_considered` = `len(outcomes)`; `outcomes_searched` / `outcomes_fixed_date` / `outcomes_refused` are
counts of `status`; `breaks_estimated` counts breaks with `kind == "estimated"`; `known_breaks_passed` counts
breaks with `kind == "known_definition_break"`.

### 4.2 `rules`

| Field | Content |
|---|---|
| `method` | *"Bai–Perron break search on the native observations, break count chosen by the declared criterion"* |
| `package` | const `strucchange` — the installed package; `changepoint` (PELT) is not installed and is not an option |
| `criterion` | the selection rule, in words (BIC over 0..max breaks) |
| `input_rule` | must state that **only native observations are fitted**: an interpolated month is a filled value, and a detector run on the spine finds the fills (C-30) |
| `min_native_search` | 20 — below this, no search |
| `min_native_fixed_date` | 7 — below this, nothing is fitted at all |
| `max_breaks` | per regime: monthly 2, annual 1, annual_short 1 |
| `definition_break_rule` | *"known definition breaks are passed in as fixed breaks or labelled `known_definition_break`; an estimated break within ±1 native period of one is relabelled as measurement, never reported as a change of era"* |
| `attribution_rule` | *"a break is never described as an effect of a president, party or tenure; `coincides_with_inauguration` records timing only"* |
| `forbidden_fields` | `p_value`, `standard_error`, `ci_low`, `ci_high`, `date_ci_low`, `date_ci_high`, `t_stat`, `RSS_p_value`, `verdict` |

### 4.3 `outcomes[]`

| Field | Type | Rule |
|---|---|---|
| `id`, `label`, `short` | string | from `outcomes.yml` |
| `native_frequency` | enum `monthly` \| `annual` | from `dim_metric` |
| `regime` | enum `monthly` \| `annual` \| `annual_short` | by `native_in_window`: ≥ 60 monthly, ≥ 20 annual, else short |
| `native_in_window` | int | the count that decides the regime — published so a reader can see why an outcome got one break and another got none |
| `span.first` / `span.last` | `YYYY-MM` | first and last native observation |
| `status` | enum `search` \| `fixed_date` \| `refused` | the branch taken |
| `method_detail` | string | *"Bai–Perron, 0–1 breaks, BIC selected 1"* / *"fixed-date segmented fit at the two inaugurations inside the span"* |
| `breaks[]` | `{month, kind, label, statement, coincides_with_inauguration?}` | `kind` ∈ `estimated` \| `known_definition_break` \| `inauguration`; `label` is the short chart label; `statement` is the plain sentence; `coincides_with_inauguration` names the administration slug when the break falls within ±2 months of a swearing-in, else null |
| `plain_caption` | string | assembled from the fields |
| `figure` | null \| `{path, bytes}` | the outcome's series with break markers; null when `status == "refused"` |
| `refused` | null \| `{reason, detail}` | closed set: `too_few_native_observations`, `series_stops_before_window`, `no_native_observations`, `declared_gap` |

**Invariant K-1.** `status == "refused"` → `breaks` empty, `figure` null, `refused` non-null. The schema
enforces this with `if/then`.
**K-2.** `status != "refused"` → `breaks` has at least one entry and `refused` is null.
**K-3.** Every `breaks[].month` lies inside `span`.
**K-4.** No field named in `rules.forbidden_fields` appears anywhere in the file.
**K-5.** The verifier re-runs the declared method on the native series and requires the same break months. A
method that cannot be re-run (a random seed, an undeclared penalty) fails this invariant by construction.
**K-6.** No break may be fitted on a month whose `observed` flag is false in `fact_metric`. This is the check that
closes the C-30 trap, and it is a failure condition, not a warning.

### 4.4 Minimal example

```json
{
  "schema_version": "0.1.0",
  "vintage": "2026-10-30",
  "generator": { "script": "analysis/R/09_changepoints.R", "git_sha": "abc1234" },
  "counts": { "outcomes_considered": 12, "outcomes_searched": 8, "outcomes_fixed_date": 0, "outcomes_refused": 4,
              "breaks_estimated": 10, "known_breaks_passed": 4 },
  "outcomes": [{
    "id": "fatalities", "native_frequency": "monthly", "regime": "monthly", "native_in_window": 299,
    "span": { "first": "1999-01", "last": "2025-12" },
    "status": "search", "method_detail": "Bai-Perron mean model, 0-2 breaks, BIC over 2m+1 parameters, 2 selected",
    "breaks": [
      { "month": "2013-04", "kind": "estimated", "label": "the series changes here",
        "statement": "Reported fatalities change level around April 2013; this is a description of the series, not an effect of an administration.",
        "coincides_with_inauguration": null }
    ],
    "plain_caption": "Security fatalities: 299 native observations; 2 marked months (2013-04, 2016-12).",
    "figure": { "path": "registry/changepoints/2026-10-30/figures/fatalities.svg", "bytes": 42714 },
    "refused": null
  }]
}
```

---

## 5. What each verifier must recompute

Written down here so the verifier is not a second opinion on the engine, and not a spelling check.

**`tests/verify_comparisons.py`**
1. Every `observed.*` count, re-derived from DuckDB, including `native_in_window` (excluding valueless rows the
   way the series verifier already must).
2. `group_mean` and `group_mean_native_only` per group, to 1e-9, from the base.
3. `n_units` and `months` per group; the sum per grouping; `min_units_per_group`.
4. Every `caption` string's numbers against the artifact's own fields — a caption that says 26 where the artifact
   says 25 fails.
5. Every figure's `bytes` against the file on disk.
6. The absence of every field in `rules.forbidden_fields`, by recursive key walk.
7. The vintage against the registry index; the spec md5 against the spec on disk.
8. That `closest_evidence.outcome_id`, when present, exists in the registry index.

**`tests/verify_changepoints.py`**
1. `native_in_window`, `span`, `regime` and therefore `status`, re-derived from `fact_observation_native`.
2. The break months, by re-running the declared method with the declared criterion (R is called once from the
   verifier with the same spec md5; the verifier does not import the engine).
3. That no break month is unobserved in `fact_metric` (K-6).
4. That every break within ±1 native period of a row in `dim_definition_break` is labelled
   `known_definition_break`, and that no break is captioned as an administration's effect (a grep over the
   statement for "caused", "because of", "under President …").
5. `coincides_with_inauguration` against the administration dates, ±2 months.
6. Figure bytes, forbidden fields, vintage, spec md5, as above.

Both verifiers must be able to fail for a real reason and must be break-tested (mutation → red → restored
byte-for-byte) before the artifacts are published, as every previous stage's verifier was.

---

## 6. Open items

- The two spec files (`comparisons.yml`, `changepoints.yml`) must be declared and frozen **before** either engine
  runs, and their md5 recorded in the artifact. Writing the engine first would let the method be chosen by its
  results.
- The state dose quartiles need `X-09` (the population denominator) only if the grouping is per capita; on the
  nominal axis the quartiles are computable today, from 2016-12, with the earlier months a declared gap.
- `group_mean_native_only` exists because the annual series carry 275–286 interpolated months each. Expect it to
  differ from `group_mean` on exactly the outcomes a reader would most want to compare, and expect the caption to
  say so.
