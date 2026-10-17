-- The spine is one grid: every metric gets the same months, from the study floor to the last observed
-- month across all metrics. A metric with a short grid would render as a line that simply stops, which
-- the app would have no way to distinguish from a series that stops.
with per_metric as (
    select
        metric_id,
        count(*) as n_rows
    from {{ ref('int_metric_monthly') }}
    group by metric_id
),

declared as (
    select
        metric_id,
        n_spine_months
    from {{ ref('metric_anchor') }}
),

global_months as (
    select count(distinct period_month) as n_months
    from {{ ref('int_metric_monthly') }}
)

select
    p.metric_id,
    p.n_rows,
    d.n_spine_months,
    (select n_months from global_months) as global_months
from per_metric p
join declared d
    on d.metric_id = p.metric_id
where p.n_rows <> d.n_spine_months
   or p.n_rows <> (select n_months from global_months)
