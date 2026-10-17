-- PHASES.md Stage 2 froze the Brent daily->monthly rule so that "changing it later changes every
-- adjusted estimate". This test is what makes that a fact rather than a comment: a future edit to
-- `stg_fred_monthly` that switched the rule to month-end or to a sum would fail here.
with recomputed as (
    select
        date_trunc('month', observation_date)::DATE as period_month,
        avg(value) as expected_value,
        count(*) as expected_n
    from {{ ref('stg_fred_daily') }}
    where value is not null
    group by 1
)

select
    m.period_month,
    m.value,
    r.expected_value,
    m.n_daily_observations,
    r.expected_n
from {{ ref('stg_fred_monthly') }} m
join recomputed r
    on r.period_month = m.period_month
where abs(m.value - r.expected_value) > 1e-9
   or m.n_daily_observations <> r.expected_n
