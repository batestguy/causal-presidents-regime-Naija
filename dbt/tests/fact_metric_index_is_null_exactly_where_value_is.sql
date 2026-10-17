-- `analysis/specs/harmonisation.yml` `index.null_rule`: "value_indexed is null wherever value is null.
-- An index value computed from a missing value would be an invented observation."
--
-- The reverse matters as much: a non-null value with a null index would mean a series is invisible on
-- the indexed chart the app is built around, which no test elsewhere would notice.
select
    metric_id,
    period_month,
    value,
    value_indexed,
    observation_type
from {{ ref('fact_metric') }}
where (value is null) is distinct from (value_indexed is null)
