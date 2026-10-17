-- Base spec section 8: index to 100 at the anchor, fixed, with the anchor row stored. If the anchor
-- period had no value, or the index were ever computed against a different month, this fails.
--
-- A NULL `value_indexed` at the anchor is a failure too, not a skip: the anchor period is chosen as the
-- first month with a value, so an index of NULL there means the anchor row and the base disagree.
select
    f.metric_id,
    f.period_month,
    f.value,
    f.value_indexed,
    a.anchor_rule
from {{ ref('fact_metric') }} f
join {{ ref('metric_anchor') }} a
    on a.metric_id = f.metric_id
where f.period_month = a.anchor_period
  and (
        f.value_indexed is null
     or abs(f.value_indexed - 100) > 1e-9
  )
