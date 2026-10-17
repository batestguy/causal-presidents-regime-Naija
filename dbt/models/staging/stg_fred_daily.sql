-- Daily Brent crude observations, typed, at the native grain.
--
-- FRED returns an object with an `observations` array. Its missing-value marker is the string `"."`,
-- and US market holidays have no row at all — 10,275 rows carry 9,102 values. Both become SQL NULL
-- here and neither is filled: the daily->monthly rule in `stg_fred_monthly` is defined as the mean of
-- the days *actually quoted*, so a holiday must stay absent rather than become a carried-forward price.
with payloads as (
    select
        source,
        vintage,
        metric_id,
        dataset_id,
        content
    from {{ ref('stg_raw_payload') }}
    where source = 'fred'
),

observations as (
    select
        metric_id,
        vintage,
        dataset_id,
        unnest(json_extract_string(content, '$.observations[*].date')) as observation_date,
        unnest(json_extract_string(content, '$.observations[*].value')) as value_raw
    from payloads
)

select
    metric_id,
    vintage,
    dataset_id,
    'fred' as source,
    try_cast(observation_date as date) as observation_date,
    try_cast(value_raw as double) as value
from observations
where observation_date is not null
