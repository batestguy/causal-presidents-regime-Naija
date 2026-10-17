-- A metric that is sourced, gated and in the dimension but missing from the base table is the silent
-- hole Stage 1's exit criterion forbids: it would render as nothing rather than as a gap. The reverse is
-- covered by the `relationships` test on `fact_metric.metric_id`.
select
    d.metric_id,
    d.label,
    d.quality_status
from {{ ref('dim_metric') }} d
where d.is_landed
  and not exists (
      select 1
      from {{ ref('fact_metric') }} f
      where f.metric_id = d.metric_id
  )
