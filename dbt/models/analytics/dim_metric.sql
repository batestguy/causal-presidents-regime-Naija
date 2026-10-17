-- The metric dimension: label, unit, **direction**, domain, frequency, source — plus the Stage 3
-- quality status carried alongside.
--
-- Base spec section 6 [LOCKED]: "Direction labels are mandatory. On an indexed chart, falling under-5
-- mortality looks like failure unless labeled ↓ better." and section 8: "direction labels are a
-- dimension column, never inferred at render time". A direction is therefore a stored attribute here,
-- not something the app guesses from the presence of "mortality" in a label. `none` is a real value
-- and it means something specific — a denominator or a price (`population`, `fx`, `oil`) is not better
-- either way, and claiming a direction for it would be a judgement the project has not made.
--
-- **Two frequencies, deliberately.** `catalogue_frequency` is what the metric is *supposed* to be —
-- base spec section 6 says the CPI is monthly and GDP growth is quarterly. `native_frequency` is what
-- the landed series actually is (Stage 3's gate result: the World Bank series are annual). The
-- difference, `frequency_gap`, is the honest bit: the app's chart spec promises a monthly CPI and the
-- open data is annual, and that gap must be visible in the dimension rather than discovered by a user
-- wondering why a "monthly" series has one point per year.
--
-- `is_landed` is derived from the native observations, not from the catalogue, so a metric listed in
-- the outcomes registry but never sourced (`fatalities`, `incidents`) is present in the dimension with
-- `is_landed = false` and its declared gap status — the gap is recorded, not silently absent (Stage 1
-- exit criterion).
with catalogue as (
    select * from {{ ref('raw_metric_catalogue') }}
),

quality as (
    select
        metric_id,
        max(quality_status) as quality_status,
        max(quality_vintage) as quality_vintage,
        max(n_observed_in_window) as n_observed_in_window,
        min(first_observed) as first_observed_label,
        max(last_observed) as last_observed_label,
        max(max_gap_months) as max_gap_months,
        coalesce(bool_or(gap_tripped), false) as gap_tripped,
        coalesce(sum(n_spikes), 0) as n_spikes,
        any_value(native_frequency) as native_frequency
    from {{ ref('stg_quality_series') }}
    where source in ('worldbank', 'fred')
    group by metric_id
),

native as (
    select
        metric_id,
        count(*) filter (where value is not null) as n_native_observations,
        min(period_start_date) as first_native_period,
        max(period_start_date) as last_native_period
    from {{ ref('fact_observation_native') }}
    group by metric_id
),

anchors as (
    select
        metric_id,
        anchor_period,
        anchor_rule
    from {{ ref('metric_anchor') }}
)

select
    c.metric_id,
    c.label,
    c.short_label,
    c.unit,
    c.direction,
    c.domain,
    c.is_outcome,
    c.coverage_status,
    c.catalogue_frequency,
    q.native_frequency,
    -- Only meaningful for a landed series: an unlanded metric has no native frequency to differ from,
    -- and reporting its absence as a frequency *gap* would dress a missing series up as a grain problem.
    (n.metric_id is not null
     and q.native_frequency is distinct from c.catalogue_frequency) as frequency_gap,
    c.source_label,
    c.source_dataset_id,
    c.note,
    (n.metric_id is not null) as is_landed,
    n.n_native_observations,
    n.first_native_period,
    n.last_native_period,
    q.quality_status,
    q.quality_vintage,
    q.n_observed_in_window,
    q.first_observed_label,
    q.last_observed_label,
    q.max_gap_months,
    q.gap_tripped,
    q.n_spikes,
    a.anchor_period,
    a.anchor_rule
from catalogue c
left join quality q
    on q.metric_id = c.metric_id
left join native n
    on n.metric_id = c.metric_id
left join anchors a
    on a.metric_id = c.metric_id
