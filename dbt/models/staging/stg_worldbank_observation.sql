-- National annual observations, typed, at the **native** grain of the source.
--
-- The World Bank payload shape is a two-element array: `[{page metadata}, [row, row, ...]]`. The rows
-- live at `$[1]`, and the wildcard JSON path extracts one list per field which DuckDB then unnests in
-- lock-step. `try_cast` is deliberate: the API returns a JSON null (not a missing key) for a year with
-- no observation, `try_cast` maps it to SQL NULL, and a NULL is what the spine needs — a zero or a
-- carried-forward value would be an invented observation.
--
-- Nothing here is windowed or filtered to the study period. The floor belongs to the spine, and
-- keeping pre-1999 rows in staging preserves the pre-trend inspection and synthetic-control
-- pre-treatment window that PHASES.md Stage 3 kept them for.
with payloads as (
    select
        source,
        vintage,
        metric_id,
        dataset_id,
        content
    from {{ ref('stg_raw_payload') }}
    where source = 'worldbank'
),

observations as (
    select
        metric_id,
        vintage,
        dataset_id,
        unnest(json_extract_string(content, '$[1][*].countryiso3code')) as country_iso3,
        unnest(json_extract_string(content, '$[1][*].date')) as period_label,
        unnest(json_extract_string(content, '$[1][*].value')) as value_raw
    from payloads
)

select
    metric_id,
    vintage,
    dataset_id,
    'worldbank' as source,
    upper(country_iso3) as country_iso3,
    try_cast(period_label as integer) as period_year,
    try_cast(value_raw as double) as value
from observations
where period_label is not null
