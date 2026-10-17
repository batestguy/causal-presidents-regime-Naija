-- Native-grain observations, unified across grains, with the **anchor month** each series' rule
-- assigns to them. This is the audit table behind `fact_metric`: every spine value is traceable to a
-- row here, and every row here is traceable to a raw payload via `stg_raw_payload`.
--
-- The anchor month is where `analysis/specs/harmonisation.yml` `alignment` is applied:
--
--   * annual  -> July, the midpoint of the period the value describes. The monthly series it produces
--                does not claim the value happened in January or December, because the source does not
--                say that.
--   * monthly -> the first of the month (Brent already resampled under the frozen Stage 3 rule).
--
-- Scope is 'NGA' for the national series so a donor-panel row can never be mistaken for one of these.
with national as (
    select
        metric_id,
        vintage,
        source,
        period_year,
        value
    from {{ ref('stg_worldbank_observation') }}
    where country_iso3 = 'NGA'
),

annual as (
    select
        metric_id,
        source,
        vintage,
        'annual' as native_frequency,
        make_date(period_year, 1, 1) as period_start_date,
        make_date(period_year, 12, 31) as period_end_date,
        make_date(period_year, 7, 1) as anchor_month,
        'NGA' as scope,
        value
    from national
    where period_year is not null
),

monthly as (
    select
        metric_id,
        source,
        vintage,
        'monthly' as native_frequency,
        period_month as period_start_date,
        last_day(period_month) as period_end_date,
        period_month as anchor_month,
        null::VARCHAR as scope,
        value
    from {{ ref('stg_fred_monthly') }}
)

select
    metric_id,
    source,
    vintage,
    native_frequency,
    period_start_date,
    period_end_date,
    anchor_month,
    scope,
    value
from annual

union all

select
    metric_id,
    source,
    vintage,
    native_frequency,
    period_start_date,
    period_end_date,
    anchor_month,
    scope,
    value
from monthly
