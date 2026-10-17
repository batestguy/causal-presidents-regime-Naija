-- Country-year observations for the Design C donor pool, typed, at the native grain.
--
-- The donor panel is a separate source (`worldbank_donors`) holding the same five screening predictors
-- for each of 13 candidate comparison countries. It is kept apart from the national series on purpose:
-- these rows are not outcomes of the thing being estimated, they are the donor pool's pre-treatment
-- paths, and mixing them into the national spine would put 13 countries' outcomes on Nigeria's chart.
--
-- Country-level rows are keyed by ISO3 plus the country name the source returned, because the synthetic
-- control stage has to state which countries entered the pool and a bare code is not auditable at a glance.
with payloads as (
    select
        source,
        vintage,
        metric_id,
        dataset_id,
        content
    from {{ ref('stg_raw_payload') }}
    where source = 'worldbank_donors'
),

observations as (
    select
        metric_id,
        vintage,
        dataset_id,
        unnest(json_extract_string(content, '$[1][*].countryiso3code')) as country_iso3,
        unnest(json_extract_string(content, '$[1][*].country.value')) as country_name,
        unnest(json_extract_string(content, '$[1][*].date')) as period_label,
        unnest(json_extract_string(content, '$[1][*].value')) as value_raw
    from payloads
)

select
    metric_id,
    vintage,
    dataset_id,
    'worldbank_donors' as source,
    upper(country_iso3) as country_iso3,
    country_name,
    try_cast(period_label as integer) as period_year,
    try_cast(value_raw as double) as value
from observations
where period_label is not null
