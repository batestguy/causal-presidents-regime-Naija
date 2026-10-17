-- The gap rule, tested rather than asserted. `adult_literacy` has a 108-month hole; if interpolation
-- were ever allowed to span it, the months in the middle would sit more than twelve months from any real
-- observation and this test would return them.
--
-- Twelve months is the bound because that is one step of an annual series: interpolated months sit
-- strictly between two observations one step apart, so the furthest any of them can be from a real value
-- is eleven months. A month twelve-plus months from the nearest observation can only exist if something
-- drew a line across a hole.
with observations as (
    select metric_id, period_month
    from {{ ref('fact_metric') }}
    where observation_type = 'observed'
),

interpolated as (
    select metric_id, period_month
    from {{ ref('fact_metric') }}
    where observation_type = 'interpolated'
)

select
    i.metric_id,
    i.period_month,
    min(abs(datediff('month', o.period_month, i.period_month))) as months_to_nearest_observation
from interpolated i
join observations o
    on o.metric_id = i.metric_id
group by 1, 2
having min(abs(datediff('month', o.period_month, i.period_month))) > 12
