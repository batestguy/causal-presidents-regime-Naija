-- A synthetic control whose donor pool contains the treated unit estimates a counterfactual from itself.
-- The extraction does not include Nigeria today, so this test passes on an empty set — but it is the
-- guard that fails if a future extraction widens the country list, which is exactly when nobody would be
-- looking at the join.
select
    country_iso3,
    country_name,
    metric_id,
    period_year
from {{ ref('fact_donor_panel') }}
where is_treated_unit
