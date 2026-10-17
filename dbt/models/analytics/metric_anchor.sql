-- One anchor row per metric: base spec section 8's "store both value and value_indexed plus the
-- anchor row", made explicit and auditable.
--
-- The rule (`analysis/specs/harmonisation.yml` `index`): the anchor is January 2000, and where a
-- metric has no value there — a series that begins in 2000 has its first anchor month in July, and a
-- series that begins later has none at all — the anchor falls back to the metric's **first available
-- month at or after** January 2000, and the row records that it did.
--
-- The fallback is the honest half of this table. Rebasing a series to its own first observation while
-- the subtitle still says "Indexed to 100 at January 2000" is exactly the kind of quiet lie the
-- project's honesty layer exists to prevent, so `anchor_rule` names which case applies to each metric
-- and `tests/verify_harmonisation.py` recomputes it independently.
--
-- `fact_metric` divides by `anchor_value`; nothing else does. A reader can therefore answer "100
-- relative to what?" for any series in the base without opening a chart.
with monthly as (
    select
        metric_id,
        period_month,
        value,
        observation_type,
        native_frequency,
        vintage
    from {{ ref('int_metric_monthly') }}
),

at_fixed_anchor as (
    select
        metric_id,
        period_month as anchor_period,
        value as anchor_value
    from monthly
    where period_month = DATE '2000-01-01'
      and value is not null
),

first_available as (
    select
        metric_id,
        min(period_month) as anchor_period
    from monthly
    where value is not null
      and period_month >= DATE '2000-01-01'
    group by metric_id
),

resolved as (
    select
        metric_id,
        anchor_period,
        anchor_value
    from at_fixed_anchor

    union all

    select
        f.metric_id,
        f.anchor_period,
        m.value
    from first_available f
    join monthly m
        on m.metric_id = f.metric_id
       and m.period_month = f.anchor_period
    where f.metric_id not in (select metric_id from at_fixed_anchor)
),

stats as (
    select
        metric_id,
        min(period_month) filter (where observation_type = 'observed') as first_observed_month,
        max(period_month) filter (where observation_type = 'observed') as last_observed_month,
        count(*) filter (where observation_type = 'observed') as n_observed_months,
        count(*) filter (where observation_type = 'interpolated') as n_interpolated_months,
        count(*) filter (where observation_type = 'unobserved') as n_unobserved_months,
        count(*) as n_spine_months,
        any_value(native_frequency) as native_frequency,
        any_value(vintage) as vintage
    from monthly
    group by metric_id
)

select
    s.metric_id,
    r.anchor_period,
    r.anchor_value,
    case
        when r.anchor_period = DATE '2000-01-01' then 'fixed_2000_01'
        else 'first_available_after_2000_01'
    end as anchor_rule,
    'value_indexed = value / anchor_value * 100' as formula,
    s.native_frequency,
    s.first_observed_month,
    s.last_observed_month,
    s.n_observed_months,
    s.n_interpolated_months,
    s.n_unobserved_months,
    s.n_spine_months,
    s.vintage,
    'analysis/specs/harmonisation.yml' as spec_path
from stats s
join resolved r
    on r.metric_id = s.metric_id
