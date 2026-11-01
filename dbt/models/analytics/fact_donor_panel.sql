-- The Design C donor panel: country-year paths for the synthetic control's pool.
--
-- Kept separate from `fact_metric` on purpose. These rows are not outcomes of the thing being
-- estimated — they are the donor pool's pre-treatment paths, and they share metric ids with the
-- national series (the same `u5mr`, the same `population`). Putting them on the national spine would
-- put thirteen countries' outcomes on Nigeria's chart and make every national total wrong by a factor
-- of fourteen, so the grain difference is a guard, not just a convenience.
--
-- Two kinds of path live here, and the `source` column says which:
--
--   * `worldbank_donors` / `worldbank_donor_outcomes` — the World Bank country-year series (predictors
--     and, since C-91, outcome paths for the same pool).
--   * `ucdp` — reported conflict fatalities and incidents for pool members, aggregated from the landed
--     GED archive (C-93). It is a derived table, joined on the same country list, so a donor cannot be
--     in one panel and not the other.
--
-- `is_treated_unit` marks Nigeria if it ever appears in this extraction. It does not today — the donor
-- sources exclude the treated unit — so the column is a **guard, not a payload**: it documents the
-- design (treated rows are not donors) and would catch a future extraction that quietly added NGA.
-- Which of these countries actually enter the pool is a Stage 5 screening decision (pre-treatment fit),
-- deliberately not taken here.
with worldbank as (
    select
        metric_id,
        source,
        vintage,
        country_iso3,
        country_name,
        period_year,
        value
    from {{ ref('stg_donor_observation') }}
    where value is not null
),

conflict as (
    select
        cy.metric_id,
        'ucdp' as source,
        cy.raw_vintage as vintage,
        cy.country_iso3,
        cy.country_name,
        cy.period_year,
        cast(cy.value as double) as value
    from {{ ref('stg_ucdp_country_year') }} cy
    where cy.country_iso3 in (select distinct country_iso3 from {{ ref('stg_donor_observation') }})
)

select
    metric_id,
    source,
    vintage,
    country_iso3,
    country_name,
    period_year,
    value,
    (country_iso3 = 'NGA') as is_treated_unit
from worldbank
union all
select
    metric_id,
    source,
    vintage,
    country_iso3,
    country_name,
    period_year,
    value,
    (country_iso3 = 'NGA') as is_treated_unit
from conflict
