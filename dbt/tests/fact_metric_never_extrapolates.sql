-- `analysis/specs/harmonisation.yml`: "extrapolation: forbidden … a back-filled value is a fabricated
-- value, and the models would treat it as data."
--
-- Checked against each metric's own observed span rather than the spine's, because a series that starts
-- in 2016 legitimately has 331 unobserved months before it — all of them with a NULL value.
select
    f.metric_id,
    f.period_month,
    f.value,
    a.first_observed_month,
    a.last_observed_month
from {{ ref('fact_metric') }} f
join {{ ref('metric_anchor') }} a
    on a.metric_id = f.metric_id
where f.value is not null
  and (
        f.period_month < a.first_observed_month
     or f.period_month > a.last_observed_month
  )
