-- The Design C donor panel: country-year screening predictors for the synthetic control's pool.
--
-- Kept separate from `fact_metric` on purpose. These rows are not outcomes of the thing being
-- estimated — they are the donor pool's pre-treatment paths, and they share metric ids with the
-- national series (the same `u5mr`, the same `population`). Putting them on the national spine would
-- put thirteen countries' outcomes on Nigeria's chart and make every national total wrong by a factor
-- of fourteen, so the grain difference is a guard, not just a convenience.
--
-- `is_treated_unit` marks Nigeria if it ever appears in this extraction. It does not today — the 13
-- countries landed here are all donors, and the treated unit's path comes from the national series —
-- so the column is a **guard, not a payload**: it documents the design (treated rows are not donors)
-- and would catch a future extraction that quietly added NGA, rather than letting the treated unit
-- enter its own donor pool. Which of these countries actually enter the pool is a Stage 5 screening
-- decision (pre-treatment fit), deliberately not taken here.
select
    metric_id,
    source,
    vintage,
    country_iso3,
    country_name,
    period_year,
    value,
    (country_iso3 = 'NGA') as is_treated_unit
from {{ ref('stg_donor_observation') }}
where value is not null
