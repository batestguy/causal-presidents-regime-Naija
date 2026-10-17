-- The monthly spine: one row per (metric, month), with `value` and an `observation_type` saying
-- whether that value is observed, interpolated, or absent.
--
-- Three rules from `analysis/specs/harmonisation.yml` are enforced here, and each of them is a refusal:
--
--   1. **No extrapolation.** The spine spans [1999-01, last anchor across all spine metrics]. A metric
--      whose first observation is later simply has `unobserved` rows before it, with a NULL value. A
--      series that starts in 2000 gets no invented 1999.
--   2. **No interpolation across a gap.** Months are interpolated only between two observations exactly
--      one annual step apart (`datediff = 12`). `adult_literacy` has a 108-month hole; drawing a line
--      through it would put nine years of values on a chart that look exactly like observed ones. A
--      wider spacing is treated as what it is — a hole — and stays `unobserved`.
--   3. **The study-window floor.** Rows before 1999-01 are dropped rather than carried as unobserved,
--      because the spine's job is the study window; Stage 3 already retains the pre-1999 data for
--      pre-trend and pre-treatment use, and it is not this table's to keep.
--
-- `int_` because `metric_anchor` reads this table to find each metric's anchor month and `fact_metric`
-- then joins that anchor back on — a direct fact_metric -> metric_anchor -> fact_metric cycle, which
-- dbt would (correctly) refuse.
with native as (
    select
        metric_id,
        native_frequency,
        source,
        vintage,
        anchor_month,
        value
    from {{ ref('fact_observation_native') }}
    where value is not null
      and anchor_month >= DATE '1999-01-01'
),

metrics as (
    select
        metric_id,
        any_value(native_frequency) as native_frequency,
        any_value(source) as source,
        any_value(vintage) as vintage
    from native
    group by metric_id
),

observed as (
    select
        metric_id,
        anchor_month as period_month,
        value,
        'observed' as observation_type
    from native
),

bounds as (
    select
        metric_id,
        anchor_month as a,
        value as va,
        lead(anchor_month) over (partition by metric_id order by anchor_month) as b,
        lead(value) over (partition by metric_id order by anchor_month) as vb
    from native
),

interpolated as (
    select
        bs.metric_id,
        gs.period_month,
        bs.va + (bs.vb - bs.va)
            * (datediff('month', bs.a, gs.period_month)::DOUBLE
               / datediff('month', bs.a, bs.b)::DOUBLE) as value,
        'interpolated' as observation_type
    from bounds bs,
        unnest(generate_series(
            bs.a + INTERVAL 1 MONTH,
            bs.b - INTERVAL 1 MONTH,
            INTERVAL 1 MONTH
        )) as gs(period_month)
    where bs.b is not null
      and datediff('month', bs.a, bs.b) <= 12
),

span as (
    select
        min(anchor_month) as first_month,
        max(anchor_month) as last_month
    from native
),

months as (
    select
        unnest(generate_series(
            greatest((select first_month from span), DATE '1999-01-01'),
            (select last_month from span),
            INTERVAL 1 MONTH
        ))::DATE as period_month
),

grid as (
    select m.metric_id, mo.period_month
    from metrics m
    cross join months mo
)

select
    g.metric_id,
    g.period_month,
    m.native_frequency,
    m.source,
    m.vintage,
    coalesce(o.value, i.value) as value,
    case
        when o.value is not null then 'observed'
        when i.value is not null then 'interpolated'
        else 'unobserved'
    end as observation_type
from grid g
join metrics m
    on m.metric_id = g.metric_id
left join observed o
    on o.metric_id = g.metric_id
   and o.period_month = g.period_month
left join interpolated i
    on i.metric_id = g.metric_id
   and i.period_month = g.period_month
