-- The project's single most-repeated distinction: `docs/dags.md`, PROGRESS.md and the outcomes registry
-- all say that "we found no education effect" and "we had no education outcome data after 2010" are
-- different statements, and only the second is true here.
--
-- An outcome that is not landed and carries no declared gap would let the app render an empty chart with
-- no explanation, which reads as a null result. This test makes that state impossible to reach.
select
    metric_id,
    label,
    is_outcome,
    is_landed,
    coverage_status
from {{ ref('dim_metric') }}
where is_outcome
  and not is_landed
  and (coverage_status is null or coverage_status not in ('declared_gap', 'blocked'))
