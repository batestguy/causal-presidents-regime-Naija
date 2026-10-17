-- The base table's grain. If a month were assigned to two terms, or an anchor fanned out a join, this
-- is where it would show up — before a model silently double-counted a month.
select
    metric_id,
    period_month,
    count(*) as n_rows
from {{ ref('fact_metric') }}
group by 1, 2
having count(*) > 1
